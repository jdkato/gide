import sublime
import sublime_plugin

from . import util


class GideGotoDefCommand(sublime_plugin.WindowCommand):
    """GideSignatureCommand allows the user to trigger in-editor hints.
    """
    def run(self):
        """Go to the defintion for the symbol under the cursor.
        """
        view = self.window.active_view()
        results = util.info_for_symbol(view, view.sel()[0].begin())
        if results.get('pos'):
            self.window.open_file(results.get('pos'), sublime.ENCODED_POSITION)
        else:
            util.set_status('Failed to get position.')

    def is_enabled(self):
        """We only want to be available for Golang source.
        """
        return util.is_golang(self.window.active_view())
