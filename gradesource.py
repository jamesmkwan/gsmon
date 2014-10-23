#!/usr/bin/env/python3
import argparse
import time
import yaml
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from urllib.request import urlopen

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
        if self.scores is None:
            return dict(zip(self.labels, self.scores[x]))
        else:
            scores = ['/'.join(a for a in i if a)
                      for i in zip(self.scores[x], self.scales)]
            return dict(zip(self.labels, scores))

    def __hasitem__(self, x):
        return x in self.scores

class GradeSourceMonitor:
    def __init__(self, url, secret):
        self.cur = None
        self.secret = secret
        self.last = None
        try:
            self.gs = GradeSource(url)
            self.cur = self.gs[self.secret]
        except Exception:
            print("TOP LEL")
            raise

    def update(self):
        try:
            self.gs.update()
            self.last = self.cur
            self.cur = self.gs[self.secret]
        except Exception:
            pass

        if self.last != self.cur:
            for removed in self.last.keys() - self.cur.keys():
                yield "%s removed" % removed

            for new in self.cur.keys() - self.last.keys():
                yield "%s: %s" % (new, self.cur[new])

            for same in self.cur.keys() & self.last.keys():
                if self.cur[same] != self.last[same]:
                    yield "%s: %s (from %s)" % (
                        same,
                        self.cur[same],
                        self.last[same]
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
    for name, target in config['targets'].items():
        mon[name] = GradeSourceMonitor(target['url'], str(target['secret']))

    while True:
        for course, grades in mon.items():
            for notices in grades.update():
                print("%s: %s" % (course, notices))
            time.sleep(config['wait']/len(mon))
