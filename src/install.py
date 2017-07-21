import webbrowser

import jinja2
import requests
import mdpopups

import sublime
import sublime_plugin

from . import util

PACKAGES = util.load_template('packages.md')
CSS = '''
div.gide { padding: 10px; margin: 0; }
.gide h1, .gide h2, .gide h3,
.gide h4, .gide h5, .gide h6 {
    {{'.string'|css}}
}
.gide blockquote { {{'.comment'|css}} }
.gide a { text-decoration: none; }
'''


def search_packages(query):
    """Search GoDoc for packages matches `query`.
    """
    r = requests.get('https://api.godoc.org/search?q={0}'.format(query))
    if r.status_code != 200:
        return []
    packages = r.json().get('results')
    # Return the matching packages sorted by number of Github stars.
    return sorted(packages, key=lambda k: k.get('stars', 0), reverse=True)


class GidePackageSearchCommand(sublime_plugin.WindowCommand):
    """Allow the user to seach GoDoc for packages to install.
    """
    def run(self):
        """Prompt the user for a search term(s).
        """
        self.window.show_input_panel(
            'Search by keyword', '', self.search, None, None)

    def on_navigate(self, href):
        """Open links.
        """
        webbrowser.open_new_tab(href)

    def search(self, query):
        """Get the packages from GoDoc and display them in a Phantom.
        """
        packages = search_packages(query)
        content = jinja2.Template(PACKAGES).render(packages=packages)

        view = self.window.new_file()
        view.set_name('GoDoc Search - {0}'.format(query))
        view.settings().set('gutter', False)
        view.settings().set('word_wrap', True)

        mdpopups.add_phantom(
            view,
            'packages',
            sublime.Region(0),
            content,
            sublime.LAYOUT_INLINE,
            wrapper_class='gide',
            css=CSS,
            on_navigate=self.on_navigate
        )

        view.set_read_only(True)
        view.set_scratch(True)

    def is_enabled(self):
        """We only want to be available for Golang source.
        """
        return util.is_golang(self.window.active_view())
