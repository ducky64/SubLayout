from typing import Dict, List, Tuple, cast

import pcbnew
import os
import wx


class BoardUtils():
    @classmethod
    def calculate_path_sheetfile_names(cls, footprints: List[pcbnew.FOOTPRINT]) -> Dict[Tuple[str, ...], Tuple[str, str]]:
        """Iterates through footprints in the board to try to determine the sheetfile and sheetname
        associated with a path."""
        path_sheetfile_names = {}
        for fp in footprints:
            fp_path = fp.GetPath()  # type: pcbnew.KIID_PATH
            fp_path_comps = tuple(cast(str, fp_path.AsString()).strip('/').split('/'))
            if len(fp_path_comps) < 2:  # ignore root components
                continue
            fp_path_comps = fp_path_comps[:-1]  # remove the last component (leaf footprint)
            sheetfile_name = (cast(str, fp.GetSheetfile()), cast(str, fp.GetSheetname()))
            if not sheetfile_name[0] or not sheetfile_name[1]:
                continue
            if fp_path_comps in path_sheetfile_names:
                assert path_sheetfile_names[fp_path_comps] == sheetfile_name
            else:
                path_sheetfile_names[fp_path_comps] = sheetfile_name
        return path_sheetfile_names


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

        footprints = board.GetFootprints()  # type: List[pcbnew.FOOTPRINT]
        path_sheetfile_names = BoardUtils.calculate_path_sheetfile_names(footprints)
        footprints = [fp for fp in footprints if fp.IsSelected()]
        if len(footprints) < 1:
            wx.MessageBox("Must select anchor footprint(s).", "Error", wx.OK | wx.ICON_ERROR)
            return

        # calculate the possible hierarchy sheets for selected footprints by finding the common prefixes
        

        self.frame = SubLayoutFrame(editor)
        self.frame.Show()
