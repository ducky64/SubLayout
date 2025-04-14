import pcbnew
import os
import wx


class SubLayoutFrame(wx.Frame):
    def __init__(self, parent):
        wx.Frame.__init__(self, parent, title="SubLayout", size=(300, 200))
        panel = wx.Panel(self)
        sizer = wx.BoxSizer(wx.VERTICAL)

        self.text_ctrl = wx.TextCtrl(panel, style=wx.TE_MULTILINE)
        sizer.Add(self.text_ctrl, 1, wx.EXPAND | wx.ALL, 5)

        self.button = wx.Button(panel, label="Close")
        sizer.Add(self.button, 0, wx.ALIGN_CENTER | wx.ALL, 5)

        panel.SetSizer(sizer)

        self.Bind(wx.EVT_BUTTON, self.on_close_button_click, self.button)

    def on_close_button_click(self, event):
        self.Close()


class SubLayout(pcbnew.ActionPlugin):
    def defaults(self):
        self.name = "Sublayout"
        self.category = "Placement"
        self.description = "Merge (or create) a sub-pcb-layout into (or from) a top-level board."
        self.show_toolbar_button = True
        # self.icon_file_name = os.path.join(os.path.dirname(__file__), 'simple_plugin.png') # Optional, defaults to ""

    def Run(self):
        editor = wx.FindWindowByName("PcbFrame")
        board = pcbnew.GetBoard()  # type: pcbnew.BOARD

        msg = ""
        for fp in board.GetFootprints():  # type: pcbnew.FOOTPRINT
            fp.IsSelected()
            fp_path = fp.GetPath()  # type: pcbnew.KIID_PATH
            fp.GetFieldsText()

            fp.GetSheetfile()  # name of containing hierarchical block file
            fp.GetSheetname()  # name of containing hierarchical block instance
            msg += f"{fp.GetReference()} {fp.GetFPIDAsString()} {fp_path.AsString()}  {fp.GetSheetfile()}  {fp.GetSheetname()}\n"

        wx.MessageBox(f"Hello {msg}")
        self.frame = SubLayoutFrame(editor)
        self.frame.Show()

