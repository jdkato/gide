import subprocess
import os

import sublime


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


class GideSettings(object):
    """Global access to and management of Gide's settings.
    """
    settings_file = 'Gide.sublime-settings'
    settings = sublime.load_settings(settings_file)

    def __init__(self):
        self.error_template = None
        self.warning_template = None
        self.info_template = None
        self.css = None
        self.settings.add_on_change('reload', lambda: self.load())
        self.load()

    def load(self):
        """Load Vale's settings.
        """
        self.settings = sublime.load_settings(self.settings_file)
        self.__load_resources()

    def put(self, setting, value):
        """Store and save `setting` as `value`.
        Args:
            setting (str): The name of the setting to be accessed.
            value (str, int, bool): The value to be stored.
        """
        self.settings.set(setting, value)
        sublime.save_settings(self.settings_file)

    def get(self, setting):
        """Return the value associated with `setting`.
        Args:
            setting (str): The name of the setting to be accessed.
        Returns:
            (str, int, bool): The value associated with `setting`. The default
                value is ''.
        """
        return self.settings.get(setting, '')

    def __load_resources(self):
        """Load Vale's static resources.
        """
        self.error_template = sublime.load_resource(
            self.settings.get('vale_error_template'))
        self.warning_template = sublime.load_resource(
            self.settings.get('vale_warning_template'))
        self.info_template = sublime.load_resource(
            self.settings.get('vale_info_template'))
        self.css = sublime.load_resource(self.settings.get('vale_css'))
