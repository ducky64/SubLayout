from typing import Dict, List, Tuple, cast

import pcbnew
import os
import wx


class BoardUtils():
    @classmethod
    def highlight_footprint(cls, footprint: pcbnew.FOOTPRINT, bright: bool = True) -> None:
        """Highlight a footprint on the board."""
        if bright:
            footprint.SetBrightened()
            for pad in footprint.Pads():  # type: pcbnew.PAD
                pad.SetBrightened()
        else:
            footprint.ClearBrightened()
            for pad in footprint.Pads():  # type: pcbnew.PAD
                pad.ClearBrightened()

    @classmethod
    def footprint_path(cls, footprint: pcbnew.FOOTPRINT) -> Tuple[str, ...]:
        fp_path = footprint.GetPath()  # type: pcbnew.KIID_PATH
        return tuple(cast(str, fp_path.AsString()).strip('/').split('/'))

    @classmethod
    def footprint_path_startswith(cls, footprint: pcbnew.FOOTPRINT, path_prefix: Tuple[str, ...]) -> bool:
        """Returns true if the footprint path starts with the given prefix (is part of the path_prefix hierarchy)"""
        fp_path = cls.footprint_path(footprint)
        return fp_path[:len(path_prefix)] == path_prefix

    @classmethod
    def calculate_path_sheetfile_names(cls, footprints: List[pcbnew.FOOTPRINT]) -> Dict[Tuple[str, ...], Tuple[str, str]]:
        """Iterates through footprints in the board to try to determine the sheetfile and sheetname
        associated with a path."""
        path_sheetfile_names = {}
        for fp in footprints:
            fp_path_comps = cls.footprint_path(fp)
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
