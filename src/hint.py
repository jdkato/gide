import json

import mdpopups
import sublime
import sublime_plugin

from .util import (
    run_command,
    is_golang,
    load_template
)

SIGNATURE = load_template('signature.md')


def get_completions(view, point):
    """...
    """
    stdout, stderr, ret = run_command(
        ['gocode', '-f=json', 'autocomplete', str(point)],
        view.substr(sublime.Region(0, view.size())))

    if ret != 0:
        return

    results = json.loads(stdout)
    if not results:
        return

    completions = [
        ('{}\t{}'.format(r['name'], r['type'])) for r in results[1]]

    return (completions, sublime.INHIBIT_WORD_COMPLETIONS)


def show_signature(view, point, flags):
    """Display a documentation signature.
    """
    filename = view.file_name()
    pos = '{0}:#{1}'.format(filename, point)
    buf = view.substr(sublime.Region(0, view.size()))

    stdout, stderr, ret = run_command(
        ['gogetdoc', '-u', '-json', '-modified', '-pos', pos],
        '{0}\n{1}\n{2}'.format(filename, view.size(), buf))

    if ret != 0:
        return

    results = json.loads(stdout)
    print(results)
    if results['decl'] and results['doc']:
        md = SIGNATURE.format(
            declaration=results['decl'],
            documentation=results['doc'].strip())

        mdpopups.show_popup(
            view,
            content=md,
            flags=flags,
            css=sublime.load_resource('Packages/gide/static/gide.css'),
            location=point,
            max_width=600)


class GideHintEventListener(sublime_plugin.EventListener):
    """...
    """
    def on_query_completions(self, view, prefix, locations):
        """...
        """
        point = view.sel()[0].begin()
        if not is_golang(view, point):
            return
        return get_completions(view, point)

    def on_modified_async(self, view):
        """Called after changes has been made to a view
        """
        if view.command_history(0)[0] in ('expand_tabs', 'unexpand_tabs'):
            return

        if not is_golang(view):  # TODO: check settings
            return

        point = view.rowcol(view.sel()[0].begin())
        if view.substr(view.sel()[0].begin()) in ['(', ')']:
            point = (point[0], point[1] - 1)

        show_signature(view, point, sublime.COOPERATE_WITH_AUTO_COMPLETE)

    def on_hover(self, view, point, hover_zone):
        if hover_zone != sublime.HOVER_TEXT or not is_golang(view):
            return
        show_signature(view, point, sublime.HIDE_ON_MOUSE_MOVE_AWAY)
