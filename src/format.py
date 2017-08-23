import collections
import os
import re
import traceback

import sublime
import sublime_plugin

from . import util

ERROR_RE = re.compile(r'\A.*:(\d+):(\d+):\s+(.*)\Z')
ERROR_TEMPLATE = """
<div><b>{row}:</b> {text}</div>
"""

Error = collections.namedtuple(
    'Error', ['message', 'region', 'row', 'col', 'filename'])


def parse_stderr(stderr, region, view):
    """Extract errors from stderr of `gofmt`, `goimports` or `goreturns`.
    """
    errors = []
    region_row, region_col = view.rowcol(region.begin())

    if not isinstance(stderr, str):
        stderr = stderr.decode('utf-8')

    name = os.path.basename(view.file_name())
    stderr = stderr.replace('<standard input>', name)

    for line in stderr.splitlines():
        match = ERROR_RE.match(line)
        if not match:
            continue

        row = int(match.group(1)) - 1
        col = int(match.group(2)) - 1
        text = match.group(3)

        if row == 0:
            col += region_col

        row += region_row
        a = view.text_point(row, col)
        b = view.line(a).end()

        errors.append(Error(text, sublime.Region(a, b), row, col, name))

    return errors


class Formatter(object):
    """Formatter is used to format Go code.
    :param sublime.View view: View containing the code to be formatted.
    """
    def __init__(self, view):
        self.view = view
        self.encoding = self.view.encoding()
        if self.encoding == 'Undefined':
            self.encoding = 'utf-8'
        self.window = view.window()
        cmds = settings.get('cmds', ['gofmt', '-e', '-s']) or []
        self.cmds = [Command(cmd, self.view, self.window) for cmd in cmds]

    def format(self, region):
        """Format the code in the given region.
        This will format the code with all the configured commands, passing
        the output of the previous command as the input to the next command.
        If any commands fail, this will show the errors and return None.
        :param sublime.Region region: Region of text to format.
        :returns: str or None
        """
        self._clear_errors()
        code = self.view.substr(region)
        for cmd in self.cmds:
            code, stderr, return_code = cmd.run(code)
            if stderr or return_code != 0:
                errors = Error.parse_stderr(stderr, region, self.view)
                self._show_errors(errors, return_code, cmd)
                raise FormatterError(errors)
        self._hide_error_panel()
        return code.decode(self.encoding)

    def _clear_errors(self):
        """Clear previously displayed errors."""
        self.view.set_status('gofmt', '')
        self.view.erase_regions('gofmt')

    def _hide_error_panel(self):
        """Hide any previously displayed error panel."""
        self.window.run_command('hide_panel', {'panel': 'output.gofmt'})

    def _show_errors(self, errors, return_code, cmd):
        """Show errors from a failed command.
        :param int return_code: Exit code of the command.
        :param str stderr: Stderr output of the command.
        :param Command cmd: Command object.
        :param sublime.Region region: Formatted region.
        """
        self.view.set_status('gofmt', '{} failed with return code {}'.format(
            cmd.name, return_code))
        self._show_error_panel(errors)
        self._show_error_regions(errors)

    def _show_error_regions(self, errors):
        """Mark the regions which had errors.
        :param str stderr: Stderr output of the command.
        :param sublime.Region: Formatted region.
        """
        self.view.add_regions(
            'gofmt', [e.region for e in errors], 'invalid.illegal', 'dot',
            (sublime.DRAW_NO_FILL | sublime.DRAW_NO_OUTLINE |
             sublime.DRAW_SQUIGGLY_UNDERLINE))

    def _show_error_panel(self, errors):
        """Show the stderr of a failed command in an output panel.
        :param str stderr: Stderr output of the command.
        """
        characters = '\n'.join([e.text for e in errors])
        p = self.window.create_output_panel('gofmt')
        p.set_scratch(True)
        p.run_command('select_all')
        p.run_command('right_delete')
        p.run_command('insert', {'characters': characters})


def run_formatter(edit, view, regions):
    """Run a formatter on regions of the view.
    :param sublime.Edit: Buffer modification group.
    :param sublime.View: View containing the code to be formatted.
    :param sublime.Region: Regions of the view to format.
    """
    global view_errors
    if view.id() in view_errors:
        del view_errors[view.id()]
    try:
        formatter = Formatter(view)
        for region in regions:
            view.replace(edit, region, formatter.format(region))
    except FormatterError as e:
        view_errors[view.id()] = e.errors
    except Exception:
        sublime.error_message(traceback.format_exc())


class GofmtCommand(sublime_plugin.TextCommand):

    def run(self, edit):
        if not is_go_source(self.view):
            return
        run_formatter(edit, self.view, [sublime.Region(0, self.view.size())])


class GofmtListener(sublime_plugin.EventListener):

    def _show_errors_for_row(self, view, row, point):
        if not is_go_source(view):
            return
        errors = view_errors.get(view.id())
        if not errors:
            return
        row_errors = [e for e in errors if e.row == row]
        if not row_errors:
            return
        html = '\n'.join([ERROR_TEMPLATE.format(row=e.row + 1, text=e.text)
                          for e in row_errors])
        view.show_popup(html, flags=sublime.HIDE_ON_MOUSE_MOVE_AWAY,
                        location=point, max_width=600)

    def on_hover(self, view, point, hover_zone):
        if hover_zone != sublime.HOVER_TEXT:
            return
        row, _ = view.rowcol(point)
        self._show_errors_for_row(view, row, point)

    def on_pre_save(self, view):
        if not settings.get('format_on_save', True):
            return
        view.run_command('gofmt')
