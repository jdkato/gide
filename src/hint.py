"""hint.py

This module manages everything to do with in-editor documentation, including
auto-complete, signature pop-ups, and external documentation access.

It exports the following `sublime_plugin` subclasses:

    * `GideSignatureCommand`: A `TextCommand` that will show a the signature
       for the symbol under the cursor when activated via the Command Palette
       or the Context Menu.

    * `GideHintEventListener`: An `EventListener` that controls getting
       completions from `gocode` and determines (based on the user's settings)
       when to display signatures.

    * `GidePackageSearchCommand`: A `WindowCommand` that prompts the user to
      enter a search term for GoDoc and then displays the results in a Phamtom.
"""
import json
import re
import urllib
import webbrowser

import jinja2
import mdpopups
import requests

import sublime
import sublime_plugin

from . import util

SIGNATURE = util.load_template('signature.md')
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
HAS_TYPE = re.compile('func \(\w+ \*?(\w+)\) .*')
DOC_URL = 'https://godoc.org/{0}#{1}'


def get_completions(view, point):
    """Return completions using `gocode`.
    """
    region = view.substr(sublime.Region(0, view.size()))
    stdout, stderr, ret = util.run_command(
        ['gocode', '-f=json', 'autocomplete', str(point)], region)

    if ret != 0:
        util.debug(
            'No completions for {0} in {1}'.format(point, view.file_name()))
        return

    results = json.loads(stdout)
    if not results:
        return

    completions = [
        ('{}\t{}'.format(r['name'], r['type']), r['name']) for r in results[1]]
    return (completions, sublime.INHIBIT_WORD_COMPLETIONS)


def format_doc(doc):
    """Format a Godoc comment for display in a popup.
    """
    fixed = ''
    for line in doc.split('\n'):
        if line.startswith(' ') or line.startswith('\t'):
            # We assume lines starting with a space or tab are intended to be
            # code blocks.
            line = line.strip('\t')
            while not line.startswith('    '):
                # We need 4 leading spaces.
                line = ' ' + line
            line = '\n' + line
        fixed += (line + '\n')
    # Lastly, we want to use line-wrapping rather than hard line breaks in the
    # pop-up, so we replace single newlines with spaces.
    return re.sub(r'(?<=[.!?,;\w])\n(?=\w)', ' ', fixed.strip())


def show_signature(view, point, flags):
    """Display a documentation signature popup using `gogetdoc`.
    """
    filename = view.file_name()
    if not filename:
        return

    pos = '{0}:#{1}'.format(filename, point)
    buf = view.substr(sublime.Region(0, view.size()))
    stdout, stderr, ret = util.run_command(
        ['gogetdoc', '-u', '-json', '-modified', '-pos', pos],
        '{0}\n{1}\n{2}'.format(filename, view.size(), buf))

    if ret != 0:
        util.debug('No signature for {0}'.format(pos))
        return

    results = json.loads(stdout)
    util.debug('signature: {0}'.format(results))
    if results['decl'] and results['doc']:
        md = SIGNATURE.format(
            declaration=results['decl'],
            documentation=format_doc(results['doc']))

        mdpopups.show_popup(
            view,
            content=md,
            flags=flags,
            css=sublime.load_resource(util.get_setting('popup_css')),
            location=point,
            max_width=util.get_setting('popup_width'),
            wrapper_class='gide',
            on_navigate=lambda x: handle_hint_navigation(x, results))


def handle_hint_navigation(url, args):
    """Handle URL navigation for popups.
    """
    pos = args.get('pos')
    if url == 'goto-def' and pos:
        sublime.active_window().open_file(pos, sublime.ENCODED_POSITION)
    elif url == 'goto-def' and args.get('import') == 'builtin':
        util.set_status('can\'t navigate to built-in symbol')
    elif url == 'godoc':
        # Format the URL
        has_type = HAS_TYPE.search(args['decl'])
        if has_type:
            name = has_type.group(1) + '.' + args['name']
            p = DOC_URL.format(args['import'], name)
        else:
            p = DOC_URL.format(args['import'], args['name'])

        # Open the page
        if urllib.request.urlopen(p).getcode() == 200:
            webbrowser.open(p)
        else:
            util.set_status('no page available at {0}'.format(p))


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


class GideSignatureCommand(sublime_plugin.TextCommand):
    """GideSignatureCommand allows the user to trigger in-editor hints.
    """
    def run(self, edit):
        """Show the signature for the symbol under the cursor.
        """
        point = self.view.sel()[0].begin()
        show_signature(self.view, point, sublime.HIDE_ON_MOUSE_MOVE_AWAY)

    def is_enabled(self):
        """We only want to be available for Golang source.
        """
        return util.is_golang(self.view)


class GideHintEventListener(sublime_plugin.EventListener):
    """GideHintEventListener handles events related to in-editor hints.
    """
    paren_pressed_point = None

    def on_query_completions(self, view, prefix, locations):
        """Get completions from `gocode`.
        """
        point = view.sel()[0].begin()
        if not util.is_golang(view, point):
            return
        return get_completions(view, point)

    def on_query_context(self, view, key, operator, operand, match_all):
        """
        Here, we look for the 'signature_trigger' key and store the location
        one unit back for use in `on_modified_async`.
        """
        if not util.is_golang(view):
            return

        if key == 'signature_trigger':
            self.paren_pressed_point = view.sel()[0].begin() - 1
            return False

    def on_modified_async(self, view):
        """
        If `signature_trigger` is set to either "edit" or "both" in the user's
        settings and they're currently in a Golang file, we display a signature
        after they press the "(" key.
        """
        if view.command_history(0)[0] in ('expand_tabs', 'unexpand_tabs'):
            return

        trigger = util.get_setting('signature_trigger')
        if not util.is_golang(view) or trigger in ('none', 'hover'):
            return

        point = self.paren_pressed_point
        self.paren_pressed_point = None
        if point is not None:
            show_signature(view, point, sublime.COOPERATE_WITH_AUTO_COMPLETE)

    def on_hover(self, view, point, hover_zone):
        """
        If `signature_trigger` is set to either "hover" or "both" in the user's
        settings and they're currently in a Golang file, we display a signature
        whenever they hover over a symbol.
        """
        if hover_zone != sublime.HOVER_TEXT or not util.is_golang(view):
            return

        trigger = util.get_setting('signature_trigger')
        if trigger in ('none', 'edit'):
            return

        show_signature(view, point, sublime.HIDE_ON_MOUSE_MOVE_AWAY)
