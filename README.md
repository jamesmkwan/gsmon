gsmon
=====

gsmon is a script for scraping gradesource for new grades.  Provides default
support for sending notifications through pushover. It should be easy to add
support for other notification systems, but I don't use any of them.

Run with `python3 gsmon.py <config>` where config is a yaml file with your
configuration. See config\_example.yaml for an example configuration.

Since the program doesn't fork, it's recommended to run inside something like
screen or tmux.

Configuration options
---------------------

**wait**: Approximate number of seconds to wait between checking the same class *(default: 60)*

**pushover**: configuration to use [pushover](https://pushover.net/) to send
new grades notifications *(optional)*
- **app**: application api token
- **user**: user key
- **priority**: priority of messages *(optional)*

**courses**: *list* of courses to check
- **name**: name of a course
- **url**: URL to gradesource (ex: http://www.gradesource.com/reports/XXXX/XXXXX/)
- **secret**: your secret number

**logging**: standard python logging config dictionary, see [python
documentation](https://docs.python.org/3/library/logging.config.html#logging-config-dictschema)

Dependencies
------------
- [PyYAML](https://pypi.python.org/pypi/PyYAML)
- [BeautifulSoup4](https://pypi.python.org/pypi/beautifulsoup4)
