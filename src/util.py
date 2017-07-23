import subprocess
import json
import os

import sublime

SETTINGS_FILE = 'Gide.sublime-settings'


def set_status(msg):
    """Print a message to the active window's status bar.
    """
    msg = 'Gide: {0}'.format(msg)
    sublime.active_window().active_view().set_status('Gide', msg)


def info_for_symbol(view, point):
    """Extract information about the symbol given by `point`.
    """
    filename = view.file_name()
    if not filename:
        return {}

    pos = '{0}:#{1}'.format(filename, point)
    buf = view.substr(sublime.Region(0, view.size()))
    stdout, stderr, ret = run_command(
        ['gogetdoc', '-u', '-json', '-modified', '-pos', pos],
        '{0}\n{1}\n{2}'.format(filename, view.size(), buf))

    if ret != 0:
        debug('No signature for {0}'.format(pos))
        return {}

    return json.loads(stdout)


def debug(message, prefix='Gide', level='debug'):
    """Print a formatted entry to the console.

    Args:
        message (str): A message to print to the console
        prefix (str): An optional prefix
        level (str): One of debug, info, warning, error [Default: debug]

    Returns:
        str: Issue a standard console print command.
    """
    if get_setting('debug'):
        print('{prefix}: [{level}] {message}'.format(
            message=message,
            prefix=prefix,
            level=level
        ))


def get_setting(name):
    """Return the value associated with the setting `name`.
    """
    settings = sublime.load_settings(SETTINGS_FILE)
    return settings.get(name, '')


def set_setting(name, value):
    """Store and save `name` as `value`.
    """
    settings = sublime.load_settings(SETTINGS_FILE)
    settings.set(name, value)
    sublime.save_settings(SETTINGS_FILE)


def load_template(name):
    """...
    """
    p = os.path.join(os.path.dirname(__file__), os.pardir, 'templates', name)
    with open(p) as temp:
        return temp.read()


def is_golang(view, point=None):
    """Return if the given view is Golang source.
    """
    if point is None:
        point = view.sel()[0].begin()
    return view.score_selector(point, 'source.go') > 0


def run_command(command, stdin):
    """Run the given command.
    """
    startup_info = None
    if sublime.platform() == 'Windows':
        startup_info = subprocess.STARTUPINFO()
        startup_info.dwFlags |= subprocess.STARTF_USESHOWWINDOW

    p = subprocess.Popen(command,
                         stdin=subprocess.PIPE,
                         stderr=subprocess.PIPE,
                         stdout=subprocess.PIPE,
                         startupinfo=startup_info)

    stdout, stderr = p.communicate(stdin.encode('utf-8'))
    return stdout.decode('utf-8'), stderr.decode('utf-8'), p.returncode
