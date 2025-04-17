from typing import Dict, List, Tuple, cast

import pcbnew
import os
import wx


from .board_utils import BoardUtils


class SubLayoutFrame(wx.Frame):
    def __init__(self, parent):
        wx.Frame.__init__(self, parent, title="SubLayout", size=(300, 200))
        panel = wx.Panel(self)
        sizer = wx.BoxSizer(wx.VERTICAL)

        self._status = wx.StaticText(panel, label="")
        sizer.Add(self._status, 0, wx.ALL)

        self._hierarchy_list = wx.ListBox(panel, style=wx.LB_SINGLE)
        sizer.Add(self._hierarchy_list, 1, wx.EXPAND | wx.ALL)

        panel.SetSizer(sizer)
        self._hierarchy_list.Bind(wx.EVT_LISTBOX, self._on_select_hierarchy)

        self._populate_hierarchy()

    def _populate_hierarchy(self) -> None:
        self._hierarchy_list.Clear()

        board = pcbnew.GetBoard()  # type: pcbnew.BOARD
        footprints = board.GetFootprints()  # type: List[pcbnew.FOOTPRINT]
        path_sheetfile_names = BoardUtils.calculate_path_sheetfile_names(footprints)
        footprints = [fp for fp in footprints if fp.IsSelected()]
        if len(footprints) < 1:
            self._status.SetLabel("Must select anchor footprint(s).")
            return

        # if one footprint is selected, also allow export mode
        if len(footprints) == 1:
            self._status.SetLabel("Select hierarchy level")
            path = BoardUtils.footprint_path(footprints[0])
            for i in range(len(path) - 1):  # ignore leaf path
                path_comps = path[:i+1]
                path_comps_short = [path_elt[-8:] for path_elt in path_comps]
                if path_comps in path_sheetfile_names:
                    sheetfile, sheetname = path_sheetfile_names[path_comps]
                    label = f"{'/'.join(path_comps_short)}: {sheetname} ({sheetfile})"
                else:
                    label = f"{'/'.join(path_comps_short)}: <not found>"
                self._hierarchy_list.Append(label, path_comps)

        else:
            self._status.SetLabel("TODO support multiple selected footprints")
            # TODO allow restore of multiple footprints by finding common sheetfiles with differing sheetnames

    def _on_select_hierarchy(self, event: wx.CommandEvent) -> None:
        selected_path_comps = self._hierarchy_list.GetClientData(event.GetSelection())
        board = pcbnew.GetBoard()  # type: pcbnew.BOARD
        footprints = board.GetFootprints()  # type: List[pcbnew.FOOTPRINT]

        for footprint in footprints:
            if BoardUtils.footprint_path_startswith(footprint, selected_path_comps):
                BoardUtils.highlight_footprint(footprint, bright=True)
            else:
                BoardUtils.highlight_footprint(footprint, bright=False)
        pcbnew.Refresh()


class SubLayout(pcbnew.ActionPlugin):
    def defaults(self):
        self.name = "Sublayout"
        self.category = "Placement"
        self.description = "Merge (or create) a sub-pcb-layout into (or from) a top-level board."
        self.show_toolbar_button = True
        # self.icon_file_name = os.path.join(os.path.dirname(__file__), 'simple_plugin.png') # Optional, defaults to ""

    def Run(self):
        editor = wx.FindWindowByName("PcbFrame")
        self.frame = SubLayoutFrame(editor)
        self.frame.Show()
