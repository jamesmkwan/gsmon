#!/usr/bin/env/python3
import argparse
import time
import yaml
import http
import logging
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlencode
from urllib.request import urlopen

def push_alert(msg, pushover_app, pushover_user):
    try:
        conn = http.client.HTTPSConnection("api.pushover.net:443")
        logging.info("Pushover: %s", msg)
        conn.request("POST", "/1/messages.json", urlencode({
            'token': pushover_app,
            'user': pushover_user,
            'message': msg,
        }), {'Content-type': 'application/x-www-form-urlencoded'})
        return conn.getresponse()
    except:
        pass

def parse_row(x):
    for a in x.find_all('td', recursive=False):
        r = a.get_text().strip()
        try:
            # If there is a colspan of x, we yield x times
            for x in range(int(a['colspan'])):
                yield r
        except KeyError:
            yield r

def find_grade_table(soup):
    # TODO: make it less ghetto
    for ele in soup.find_all('table'):
        for row in ele.find_all('tr', recursive=False):
            for dat in row.find_all('td', recursive=False):
                try:
                    if dat.get_text() == "Secret Number":
                        return ele
                except AttributeError:
                    pass

def grade_table(html_data):
    soup = BeautifulSoup(html_data)
    table = find_grade_table(soup)
    data = table.find_all('tr')
    return [list(parse_row(d)) for d in data]

class GradeSource:
    def __init__(self, url):
        self.url = url
        self.update()

    def update(self):
        with urlopen(urljoin(self.url, 'scores.html')) as f:
            html_data = f.read()

        rows = grade_table(html_data)

        self.labels = [' '.join(i for i in x if i) for x in zip(*rows[0:2])][2:]

        self.scores = {}
        self.scales = None
        for data in rows[2:]:
            if data[0] == '':
                self.scales = data[2:]
            else:
                self.scores[data[0]] = data[2:]

    def __getitem__(self, x):
        if self.scales is None:
            return dict(zip(self.labels, self.scores[x]))
        else:
            scores = ['/'.join(a for a in i if a)
                      for i in zip(self.scores[x], self.scales)]
            return dict(zip(self.labels, scores))

    def __hasitem__(self, x):
        return x in self.scores

    def __repr__(self):
        return "GradeSource(%s)" % self.url

class GradeSourceMonitor:
    def __init__(self, url, secret):
        self.cur = {}
        self.secret = secret
        try:
            self.gs = GradeSource(url)
            self.cur = self.gs[self.secret]
        except Exception:
            logging.exception("Could not load GradeSource for %s" % url)

    def update(self):
        try:
            self.gs.update()
            last = self.cur
            self.cur = self.gs[self.secret]
        except Exception:
            logging.exception("Could not update GradeSource for %s" % self.gs)

        if last != self.cur:
            for removed in last.keys() - self.cur.keys():
                yield "%s removed" % removed

            for new in self.cur.keys() - last.keys():
                yield "%s: %s" % (new, self.cur[new])

            for same in self.cur.keys() & last.keys():
                if self.cur[same] != last[same]:
                    yield "%s: %s (from %s)" % (
                        same,
                        self.cur[same],
                        last[same]
                    )

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Gradesource Monitor')
    parser.add_argument('config')
    args = parser.parse_args()

    config = {
        'wait': 60
    }

    with open(args.config) as f:
        config.update(yaml.safe_load(f.read()))

    mon = {}
    for course in config['courses']:
        mon[course['name']] = GradeSourceMonitor(course['url'], str(course['secret']))

    while True:
        for course, grades in mon.items():
            for notices in grades.update():
                msg = "%s: %s" % (course, notices)
                print(msg)
                if 'pushover' in config:
                    push_alert(msg, config['pushover']['app'], config['pushover']['user'])
            time.sleep(config['wait']/len(mon))
