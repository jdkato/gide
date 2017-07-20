import requests
import sublime
import sublime_plugin

from . import util


def search_packages(query):
    """Search GoDoc for packages matches `query`.
    """
    r = requests.get('https://api.godoc.org/search?q={0}'.format(query))
    if r.status_code != 200:
        return None
    else:
        return r.json().get('results')


class GidePackageSearchCommand(sublime_plugin.WindowCommand):
    """Allow the user to seach GoDoc for packages to install.
    """
    def run(self):
        """TODO
        """
        self.window.show_input_panel(
            'Search by keyword', '', self.search, None, None)

    def search(self, query):
        """TODO
        """
        packages = search_packages(query)
        if packages:
            by_stars = sorted(
                packages, key=lambda k: k.get('stars', 0), reverse=True)
            items = []
            paths = []
            for pkg in by_stars:
                stars = pkg.get('stars', 0)
                header = '{0} ({1} stars)'.format(pkg['name'], stars)
                items.append([
                    header,
                    pkg.get('synopsis', 'No synopsis provided.'),
                    'go get {0}'.format(pkg['path'])
                ])
                paths.append(pkg['path'])
            self.window.show_quick_panel(items, None)
        else:
            sublime.error_message('No packages for "{0}" found.'.format(query))

    def is_enabled(self):
        """We only want to be available for Golang source.
        """
        return util.is_golang(self.window.active_view())
