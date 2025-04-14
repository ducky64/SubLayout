import pcbnew
import os
import wx


class SubLayout(pcbnew.ActionPlugin):
    def defaults(self):
        self.name = "Sublayout"
        self.category = "Placement"
        self.description = "Merge (or create) a sub-pcb-layout into (or from) a top-level board."
        self.show_toolbar_button = True
        # self.icon_file_name = os.path.join(os.path.dirname(__file__), 'simple_plugin.png') # Optional, defaults to ""

    def Run(self):
        # The entry function of the plugin that is executed on user action
        wx.MessageBox("Hello World")
