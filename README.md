gsmon
=====

gsmon is a script for scraping gradesource for new grades.  Provides default
support for sending notifications through pushover. It should be easy to add
support for other notification systems, but I don't use any of them. Depends on
lxml.

Just run `python3 gsmon.py <options>`.

Since the program doesn't fork, it's recommended to run inside something like
screen or tmux.
