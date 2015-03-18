#!/usr/bin/env python3
from lxml import html
from urllib.parse import urlencode
from urllib.request import urlopen
from urllib.error import URLError
import argparse
import collections
import datetime
import http
import itertools
import time
import traceback

def read_gradesource(url):
    with urlopen(url) as f:
        html_data = f.read().replace(b'&nbsp;', b'')
    root = html.fromstring(html_data)
    ele = next(x for x in root.iterdescendants('td')
                 if x.text_content() == 'Secret Number')
    table = next(x for x in ele.iterancestors() if x.tag == 'table')

    headers = []
    grades = {}
    for row in table.iterchildren():
        data = []
        for item in row.iterchildren():
            for repeat in range(int(item.attrib.get('colspan', 1))):
                data.append(str(item.text_content()))

        if len(data[0]) == 4:
            grades[data[0]] = data[2:]
        elif not grades:
            if headers:
                for header, h in zip(headers, itertools.islice(data, 2, None)):
                    header.append(h)
            else:
                for h in itertools.islice(data, 2, None):
                    headers.append([h])

    return headers, grades

Grade = collections.namedtuple('Grade', ['name', 'score', 'rank'])
def fetch_grades(gradesource, secretnumber):
    headers, all_grades = read_gradesource(gradesource)
    grades = all_grades[secretnumber]

    for header, score, *rest in zip(headers, grades, *all_grades.values()):
        if header[1] == 'Rank':
            continue
        assert header[1] == 'Score'

        try:
            scores = (x.rstrip('*') for x in rest)
            s = sorted((i for i in scores if i), key=float, reverse=True)
            rank = s.index(score) + 1
        except ValueError:
            rank = "?"

        if len(header) > 2 and header[2]:
            score = "%s/%s" % (score, header[2])

        yield Grade(header[0], score, rank)

def push_alert(msg, pushover_app, pushover_user):
    conn = http.client.HTTPSConnection("api.pushover.net:443")
    conn.request("POST", "/1/messages.json", urlencode({
        'token': pushover_app,
        'user': pushover_user,
        'message': msg,
    }), {'Content-type': 'application/x-www-form-urlencoded'})
    return conn.getresponse()

class Checker:
    def __init__(self, cls):
        self.cls = cls
        self.grades = set()

    def update(self):
        cls_name = self.cls.name
        grades = set(fetch_grades(self.cls.gradesource, self.cls.secretnumber))

        for g in sorted(self.grades - grades):
            self.grades.remove(g)
            yield "- %s %s: %s (Rank %s)" % (cls_name, g.name, g.score, g.rank)

        for g in sorted(grades - self.grades):
            self.grades.add(g)
            yield "+ %s %s: %s (Rank %s)" % (cls_name, g.name, g.score, g.rank)

def timestamped_print(s):
    print("%s %s" % (datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"), s))

def main(classes, interval, pushover=None):
    checkers = [Checker(c) for c in classes]

    for c in checkers:
        for update in c.update():
            timestamped_print(update)

    print('{:=^78}'.format("Initialized"))

    for c in itertools.cycle(checkers):
        time.sleep(interval)
        try:
            for update in c.update():
                timestamped_print(update)
                if pushover is not None:
                    push_alert(update, pushover[0], pushover[1])
        except URLError:
            pass
        except Exception:
            traceback.print_exc()

Class = collections.namedtuple('Class', ['name', 'gradesource', 'secretnumber'])
if __name__ == '__main__':
    parser = argparse.ArgumentParser(fromfile_prefix_chars='@')
    parser.add_argument('--interval', type=int, default=30,
            help='seconds between queries to gradesource')
    parser.add_argument('--pushover', nargs=2, metavar=('TOKEN', 'USER'),
            help='pushover app credentials')
    parser.add_argument('--class', action='append', nargs=3, default=[],
            metavar=('NAME', 'GRADESOURCE_URL', 'SECRET_NUMBER'), required=True,
            help='use the assessment page (/scores.html) for url')
    args = vars(parser.parse_args())

    main([Class(*c) for c in args['class']], args['interval'], args['pushover'])
