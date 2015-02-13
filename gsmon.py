#!/usr/bin/env python3
from lxml import html
from urllib.parse import urlencode
from urllib.request import urlopen
import argparse
import collections
import datetime
import http
import itertools
import textwrap
import time
import traceback

def read_gradesource(url):
    with urlopen(url) as f:
        html_data = f.read().replace(b'&nbsp;', b'')
    root = html.fromstring(html_data)
    ele = next(x for x in root.iterdescendants('td') if x.text_content() == 'Secret Number')
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

Grade = collections.namedtuple('Grade', ['score', 'name', 'rank'])
def fetch_grades(gradesource, secret_number):
    headers, all_grades = read_gradesource(gradesource)
    grades = all_grades[secret_number]

    for header, score, *rest in zip(headers, grades, *all_grades.values()):
        if header[1] == 'Rank':
            continue
        assert header[1] == 'Score'

        try:
            s = sorted((i for i in rest if i), key=float, reverse=True)
            rank = s.index(score) + 1
        except ValueError:
            rank = "?"

        if len(header) > 2 and header[2]:
            score = "%s/%s" % (score, header[2])

        yield Grade(score, header[0], rank)

def push_alert(msg, pushover_app, pushover_user):
    conn = http.client.HTTPSConnection("api.pushover.net:443")
    conn.request("POST", "/1/messages.json", urlencode({
        'token': pushover_app,
        'user': pushover_user,
        'message': msg,
    }), {'Content-type': 'application/x-www-form-urlencoded'})
    return conn.getresponse()

def checker(classes, grades, cb):
    for c in classes:
        prev = grades[c] if c in grades else set()
        cur = set(fetch_grades(c.gradesource, c.secret_number))
        if cur != prev:
            for g in cur - prev:
                cb("+ %s %s: %s (Rank %s)" % (c.name, g.name, g.score, g.rank))

            for g in prev - cur:
                cb("- %s %s: %s (Rank %s)" % (c.name, g.name, g.score, g.rank))

        grades[c] = cur

def sleepy(x, sleep=1):
    f = iter(x)
    try:
        e = next(f)
        while f:
            yield e
            e = next(f)
            time.sleep(sleep)
    except StopIteration:
        pass

def timestamped_print(s):
    print("%s %s" % (datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"), s))

def main(classes, interval, pushover=None):
    def cb(s):
        try:
            timestamped_print(s)
            if pushover is not None:
                push_alert(s, pushover[0], pushover[1])
        except Exception:
            traceback.print_exc()

    grades = {}
    checker(sleepy(classes), grades, timestamped_print)
    print('{:=^78}'.format("Initialized"))

    while True:
        time.sleep(interval)

        try:
            checker(sleepy(classes), grades, cb)
        except Exception:
            traceback.print_exc()

Class = collections.namedtuple('Class', ['name', 'gradesource', 'secret_number'])
if __name__ == '__main__':
    parser = argparse.ArgumentParser(fromfile_prefix_chars='@')
    parser.add_argument('--interval', type=int, default=60,
            help='Interval between checks')
    parser.add_argument('--pushover', nargs=2, metavar=('TOKEN', 'USER'),
            help='Pushover app credentials')
    parser.add_argument('--class', action='append', nargs=3, default=[],
            metavar=('NAME', 'GRADESOURCE_URL', 'SECRET_NUMBER'))
    args = parser.parse_args()

    main([Class(*c) for c in getattr(args, 'class')], args.interval, args.pushover)
