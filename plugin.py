import os
from typing import List

import pcbnew
import wx

from .sublayout.replicate_sublayout import ReplicateSublayout
from .sublayout.hierarchy_namer import HierarchyNamer
from .sublayout.save_sublayout import SaveSublayout
from .sublayout.board_utils import BoardUtils


class HighlightManager():
    @classmethod
    def _highlight_footprint(cls, footprint: pcbnew.FOOTPRINT, bright: bool = True) -> None:
        """Highlight a footprint on the board, including pads."""
        if bright:
            footprint.SetBrightened()
            for pad in footprint.Pads():  # type: pcbnew.PAD
                pad.SetBrightened()
        else:
            footprint.ClearBrightened()
            for pad in footprint.Pads():
                pad.ClearBrightened()

    def __init__(self, board: pcbnew.BOARD) -> None:
        self._board = board
        self._highlighted_items: List[pcbnew.EDA_ITEM] = []

    def highlight(self, items: List[pcbnew.EDA_ITEM]) -> None:
        """Highlights the given items on the board."""
        for item in items:
            if isinstance(item, pcbnew.FOOTPRINT):
                self._highlight_footprint(item, True)
            elif isinstance(item, pcbnew.PCB_GROUP):
                self.highlight(item.GetItems())
            else:
                item.SetBrightened()
        self._highlighted_items.extend(items)

    def clear(self) -> None:
        """Clears the highlights on the board."""
        for item in self._highlighted_items:
            if isinstance(item, pcbnew.FOOTPRINT):
                self._highlight_footprint(item, False)
            else:
                item.ClearBrightened()
        self._highlighted_items.clear()


class SubLayoutFrame(wx.Frame):
    def __init__(self, parent):
        wx.Frame.__init__(self, parent, title="SubLayout", size=(300, 200))
        panel = wx.Panel(self)
        sizer = wx.BoxSizer(wx.VERTICAL)

        self._board = pcbnew.GetBoard()  # type: pcbnew.BOARD
        self._namer = HierarchyNamer(self._board)
        self._highlighter = HighlightManager(self._board)
        self.Bind(wx.EVT_CLOSE, self._on_close)

        footprints = self._board.GetFootprints()  # type: List[pcbnew.FOOTPRINT]
        self._footprints = [fp for fp in footprints if fp.IsSelected()]

        self._status = wx.StaticText(panel, label="")
        sizer.Add(self._status, 0, wx.ALL)

        self._hierarchy_list = wx.ListBox(panel, style=wx.LB_SINGLE)
        self._hierarchy_list.Bind(wx.EVT_LISTBOX, self._on_select_hierarchy)
        sizer.Add(self._hierarchy_list, 1, wx.EXPAND | wx.ALL)
        #
        self._restore_button = wx.Button(panel, label="Restore")
        self._restore_button.Bind(wx.EVT_BUTTON, self._on_restore)
        sizer.Add(self._restore_button, 0, wx.ALL | wx.ALIGN_CENTER)

        self._save_button = wx.Button(panel, label="Save")
        self._save_button.Bind(wx.EVT_BUTTON, self._on_save)
        sizer.Add(self._save_button, 0, wx.ALL | wx.ALIGN_CENTER)

        panel.SetSizer(sizer)

        self._populate_hierarchy()

    def _populate_hierarchy(self) -> None:
        self._hierarchy_list.Clear()

        if len(self._footprints) < 1:
            self._status.SetLabel("Must select anchor footprint(s).")
            return

        # if one footprint is selected, also allow export mode
        if len(self._footprints) == 1:
            self._status.SetLabel("Select hierarchy level")
            path = BoardUtils.footprint_path(self._footprints[0])
            for i in range(len(path) - 1):  # ignore leaf path
                path_comps = path[:i+1]
                label = '/'.join(self._namer.name_path(path_comps))
                self._hierarchy_list.Append(label, path_comps)
        else:
            self._status.SetLabel("TODO support multiple selected footprints")
            # TODO allow restore of multiple footprints by finding common sheetfiles with differing sheetnames

    def _on_select_hierarchy(self, event: wx.CommandEvent) -> None:
        try:
            selected_path_comps = self._hierarchy_list.GetClientData(event.GetSelection())
            result = SaveSublayout(self._board, selected_path_comps)._filter_board()
            self._highlighter.clear()
            self._highlighter.highlight(result.elts + result.groups)
            pcbnew.Refresh()
        except Exception as e:
            wx.MessageBox(f"Error: {e}", "Error", wx.OK | wx.ICON_ERROR)

    def _on_close(self, event: wx.CommandEvent) -> None:
        self._highlighter.clear()
        pcbnew.Refresh()
        self.Destroy()

    def _on_restore(self, event: wx.CommandEvent) -> None:
        if len(self._footprints) != 1:
            wx.MessageBox("Must select anchor footprint(s).", "Error", wx.OK | wx.ICON_ERROR)
            return

        selected_path_comps = self._hierarchy_list.GetClientData(self._hierarchy_list.GetSelection())
        dlg = wx.FileDialog(self, "Restore sublayout from", os.getcwd(),
                            '_'.join(self._namer.name_path(selected_path_comps)),
                            "KiCad (sub)board (*.kicad_pcb)|*.kicad_pcb",
                            wx.FD_OPEN)
        res = dlg.ShowModal()
        if res != wx.ID_OK:
            self.Close()

        sublayout_board = pcbnew.PCB_IO_MGR.Load(pcbnew.PCB_IO_MGR.KICAD_SEXP, dlg.GetPath())  # type: pcbnew.BOARD
        if not sublayout_board:
            wx.MessageBox("Failed to load sublayout board.", "Error", wx.OK | wx.ICON_ERROR)
            return
        restore = ReplicateSublayout(sublayout_board, self._board, self._footprints[0], selected_path_comps)
        restore.replicate_footprints()  # TODO checkboxes
        restore.replicate_tracks()
        restore.replicate_zones()
        pcbnew.Refresh()
        self.Close()

    def _on_save(self, event: wx.CommandEvent) -> None:
        selected_path_comps = self._hierarchy_list.GetClientData(self._hierarchy_list.GetSelection())
        save_sublayout = SaveSublayout(self._board, selected_path_comps)
        sublayout_board = save_sublayout.create_sublayout()
        dlg = wx.FileDialog(self, "Save to", os.getcwd(),
                            '_'.join(self._namer.name_path(selected_path_comps)),
                            "KiCad (sub)board (*.kicad_pcb)|*.kicad_pcb",
                            wx.FD_SAVE)
        res = dlg.ShowModal()
        if res != wx.ID_OK:
            self.Close()

        sublayout_board.Save(dlg.GetPath())


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


if __name__ == '__main__':
    pass
