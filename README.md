gsmon
=====

gsmon is a script for scraping gradesource for new grades.  Provides default
support for sending notifications through pushover. It should be easy to add
support for other notification systems, but I don't use any of them. Depends on
lxml.

Just run `python3 gsmon.py <options>`. See `python3 gsmon.py -h` for details.

Since the program doesn't fork, it's recommended to run inside something like
screen or tmux.

As you will probably have many options, you can instead put them into a line
separated file, and call `python3 gsmon.py @file`.
