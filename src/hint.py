import json
import re
import urllib
import webbrowser

import mdpopups
import sublime
import sublime_plugin

from . import util

SIGNATURE = util.load_template('signature.md')
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


class GideHintEventListener(sublime_plugin.EventListener):
    """GideHintEventListener handles events related to in-editor hints.
    """
    def on_query_completions(self, view, prefix, locations):
        """Get completions from `gocode`.
        """
        point = view.sel()[0].begin()
        if not util.is_golang(view, point):
            return
        return get_completions(view, point)

    def on_modified_async(self, view):
        if view.command_history(0)[0] in ('expand_tabs', 'unexpand_tabs'):
            return

        if not util.is_golang(view):  # TODO: check settings
            return

        point = view.rowcol(view.sel()[0].begin())
        if view.substr(view.sel()[0].begin()) in ['(', ')']:
            point = (point[0], point[1] - 1)

        show_signature(view, point, sublime.COOPERATE_WITH_AUTO_COMPLETE)

    def on_hover(self, view, point, hover_zone):
        """Show popup signature from `gogetdoc`.
        """
        if hover_zone != sublime.HOVER_TEXT or not util.is_golang(view):
            return
        show_signature(view, point, sublime.HIDE_ON_MOUSE_MOVE_AWAY)
