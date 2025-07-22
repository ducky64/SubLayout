import os
import traceback
from typing import List, Callable, Tuple, Optional, cast

import pcbnew
import wx

from .sublayout.replicate_sublayout import ReplicateSublayout, FootprintCorrespondence
from .sublayout.hierarchy_namer import HierarchyData
from .sublayout.save_sublayout import HierarchySelector
from .sublayout.board_utils import BoardUtils, GroupLike


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


class SublayoutInitError(Exception):
    """Non-tracebacking exception during sublayout dialog initialization."""
    def __init__(self, message: str):
        super().__init__(message)
        self.message = message


class SubLayoutFrame(wx.Frame):
    _last_dir: Optional[str] = None  # class variable to persist across plugin runs
    _last_position: Optional[wx.Point] = None

    def __init__(self, parent):
        wx.Frame.__init__(self, parent, title="SubLayout", size=(300, 200))
        panel = wx.Panel(self)
        sizer = wx.BoxSizer(wx.VERTICAL)

        self._board = pcbnew.GetBoard()  # type: pcbnew.BOARD
        self._namer = HierarchyData(self._board)
        self._highlighter = HighlightManager(self._board)
        self.Bind(wx.EVT_CHAR_HOOK, self._on_key)
        self.Bind(wx.EVT_CLOSE, self._on_close)

        footprints = self._board.GetFootprints()  # type: List[pcbnew.FOOTPRINT]
        self._footprints = [fp for fp in footprints if fp.IsSelected()]

        hierarchy_instruction = wx.StaticText(panel, label="Select hierarchy level")
        sizer.Add(hierarchy_instruction, 0, wx.ALL)
        self._hierarchy_list = wx.ListBox(panel, style=wx.LB_SINGLE)
        self._hierarchy_list.Bind(wx.EVT_LISTBOX, self._on_select_hierarchy)
        sizer.Add(self._hierarchy_list, 1, wx.EXPAND | wx.ALL)

        instance_instruction = wx.StaticText(panel, label="Select instances for restore / replicate")
        sizer.Add(instance_instruction, 0, wx.ALL)
        self._instance_list = wx.ListBox(panel, style=wx.LB_MULTIPLE)
        self._instance_list.Bind(wx.EVT_LISTBOX, self._on_select_instances)
        sizer.Add(self._instance_list, 1, wx.EXPAND | wx.ALL)

        self._purge_restore = wx.CheckBox(panel, label="Clear tracks on restore")
        self._purge_restore.SetValue(True)
        sizer.Add(self._purge_restore, 0, wx.ALL | wx.ALIGN_CENTER)

        matching_bar = wx.BoxSizer(wx.HORIZONTAL)
        sizer.Add(matching_bar, 0, wx.ALL | wx.ALIGN_CENTER)
        self._match_by_refdes = wx.RadioButton(panel, label="match by relative refdes", style=wx.RB_GROUP)
        self._match_by_refdes.Bind(wx.EVT_RADIOBUTTON, self._on_select_hierarchy)  # changes the matching behavior
        self._match_by_refdes.SetValue(True)  # default, consistent with netlist loading behavior
        matching_bar.Add(self._match_by_refdes)
        self._match_by_tstamp = wx.RadioButton(panel, label="match by tstamp")
        self._match_by_tstamp.Bind(wx.EVT_RADIOBUTTON, self._on_select_hierarchy)
        matching_bar.Add(self._match_by_tstamp)

        button_bar = wx.BoxSizer(wx.HORIZONTAL)
        sizer.Add(button_bar, 0, wx.ALL | wx.ALIGN_CENTER)

        self._save_button = wx.Button(panel, label="Save")
        self._save_button.SetToolTip("Save the selected hierarchy as a sublayout board.")
        self._save_button.Bind(wx.EVT_BUTTON, self._on_save)
        self._save_button.Disable()
        button_bar.Add(self._save_button, 0, wx.ALL | wx.ALIGN_CENTER)

        self._replicate_button = wx.Button(panel, label="Replicate")
        self._replicate_button.SetToolTip("Replicate the selected hierarchy into other instances on the current board.")
        self._replicate_button.Bind(wx.EVT_BUTTON, self._on_replicate)
        self._replicate_button.Disable()
        button_bar.Add(self._replicate_button, 0, wx.ALL | wx.ALIGN_CENTER)

        self._restore_button = wx.Button(panel, label="Restore")
        self._restore_button.SetToolTip("Restore the selected hierarchy instances from a sublayout board.")
        self._restore_button.Bind(wx.EVT_BUTTON, self._on_restore)
        self._restore_button.Disable()
        button_bar.Add(self._restore_button, 0, wx.ALL | wx.ALIGN_CENTER)

        panel.SetSizer(sizer)
        sizer.SetSizeHints(self)

        if self._last_position is not None:
            self.SetPosition(self._last_position)

        self._populate_hierarchy()

    def _on_key(self, event):
        if event.GetKeyCode() == wx.WXK_ESCAPE:
            self.Close()
        else:
            event.Skip()

    def _populate_hierarchy(self) -> None:
        self._hierarchy_list.Clear()

        if len(self._footprints) != 1:
            raise SublayoutInitError("Must select exactly one anchor footprint.")

        path = BoardUtils.footprint_path(self._footprints[0])
        for i in reversed(range(len(path) - 1)):  # ignore leaf path
            path_comps = path[:i+1]
            label = f"{'/'.join(self._namer.name_path(path_comps))}: {self._namer.sheetfile_of(path_comps)}"
            self._hierarchy_list.Append(label, path_comps)

        if self._hierarchy_list.GetCount() > 0:  # automatically select deepest hierarchy level
            self._hierarchy_list.SetSelection(0)
            self._on_select_hierarchy(wx.CommandEvent(id=0))

    def _get_correspondence_fn(self) -> Callable[[GroupLike, pcbnew.BOARD, Tuple[str, ...]], FootprintCorrespondence]:
        if self._match_by_refdes.GetValue():
            return FootprintCorrespondence.by_refdes
        elif self._match_by_tstamp.GetValue():
            return FootprintCorrespondence.by_tstamp
        else:
            raise ValueError("no footprint matching option selected")

    def _on_select_hierarchy(self, event: wx.CommandEvent) -> None:
        try:
            selected_path_comps = self._hierarchy_list.GetClientData(self._hierarchy_list.GetSelection())
            result = HierarchySelector(self._board, selected_path_comps).get_elts()
            self._highlighter.clear()
            self._highlighter.highlight(result.ungrouped_elts + result.groups)
            self._save_button.Enable()
            self._replicate_button.Disable()
            self._restore_button.Disable()
            pcbnew.Refresh()

            # generate instance list
            self._instance_list.Clear()
            sheetfile = self._namer.sheetfile_of(selected_path_comps)
            assert sheetfile is not None, "internal consistency failure: no sheetfile for selected hierarchy"
            self_index = None
            for index, instance_path in enumerate(self._namer.instances_of(sheetfile)):
                if instance_path == selected_path_comps:
                    self_index = index
                    instance_anchor = self._footprints[0]
                else:
                    src_hierarchy = HierarchySelector(self._board, selected_path_comps).get_elts()
                    correspondence = self._get_correspondence_fn()(src_hierarchy, self._board, instance_path)
                    instance_anchor = correspondence.get_footprint(self._footprints[0])
                    if instance_anchor is None:
                        continue
                instance_name = '/'.join(self._namer.name_path(instance_path))
                self._instance_list.Append(f"{instance_anchor.GetReference()} {instance_name}",
                                           (instance_path, instance_anchor))
            assert self_index is not None, "internal consistency failure: no instance for selected hierarchy"
            self._instance_list.SetSelection(self_index)
            self._on_select_instances(wx.CommandEvent(id=self_index))
        except Exception as e:
            traceback_str = ''.join(traceback.format_exception(None, e, e.__traceback__))
            wx.MessageBox(f"Error: {e}\n\n{traceback_str}", "Error", wx.OK | wx.ICON_ERROR)

    def _on_select_instances(self, event: wx.CommandEvent) -> None:
        try:
            selected_instance_anchors = [self._instance_list.GetClientData(index)
                                         for index in self._instance_list.GetSelections()]
            if len(selected_instance_anchors) == 0:
                self._restore_button.Disable()
                self._replicate_button.Disable()
            elif (len(selected_instance_anchors) == 1 and
                  selected_instance_anchors[0][0] == self._hierarchy_list.GetClientData(self._hierarchy_list.GetSelection())):
                # disable replicate if src == target
                self._replicate_button.Disable()
                self._restore_button.Enable()
            else:
                self._replicate_button.Enable()
                self._restore_button.Enable()
        except Exception as e:
            traceback_str = ''.join(traceback.format_exception(None, e, e.__traceback__))
            wx.MessageBox(f"Error: {e}\n\n{traceback_str}", "Error", wx.OK | wx.ICON_ERROR)

    def _on_close(self, event: wx.CommandEvent) -> None:
        self.__class__._last_position = self.GetPosition()
        self._highlighter.clear()
        pcbnew.Refresh()
        self.Destroy()

    def _get_dialog_directory(self) -> str:
        """Returns the last used directory or the current working directory."""
        if self._last_dir is not None and os.path.exists(self._last_dir):
            return self._last_dir
        board_dir = os.path.dirname(cast(pcbnew.BOARD, pcbnew.GetBoard()).GetFileName())
        if board_dir and os.path.exists(board_dir):
            return board_dir
        return os.getcwd()  # fallback

    def _on_save(self, event: wx.CommandEvent) -> None:
        try:
            selected_path_comps = self._hierarchy_list.GetClientData(self._hierarchy_list.GetSelection())
            save_sublayout = HierarchySelector(self._board, selected_path_comps)
            dlg = wx.FileDialog(self, "Save to", self._get_dialog_directory(),
                                '_'.join(self._namer.name_path(selected_path_comps)),
                                "KiCad (sub)board (*.kicad_pcb)|*.kicad_pcb",
                                wx.FD_SAVE)
            res = dlg.ShowModal()
            self.__class__._last_dir = os.path.dirname(dlg.GetPath())
            if res != wx.ID_OK:
                return

            sublayout_board = save_sublayout.create_sublayout(dlg.GetPath())
            sublayout_board.Save(dlg.GetPath())

            self.Close()
        except Exception as e:
            traceback_str = ''.join(traceback.format_exception(None, e, e.__traceback__))
            wx.MessageBox(f"Error: {e}\n\n{traceback_str}", "Error", wx.OK | wx.ICON_ERROR)

    def _on_replicate(self, event: wx.CommandEvent) -> None:
        try:
            selected_instance_anchors = [self._instance_list.GetClientData(index)
                                         for index in self._instance_list.GetSelections()]
            all_errors = []
            source_instance_path = self._hierarchy_list.GetClientData(self._hierarchy_list.GetSelection())
            source_sublayout = HierarchySelector(self._board, source_instance_path).get_elts()

            self._highlighter.clear()  # clear highlights so they don't get replicated

            for instance_path, instance_anchor in selected_instance_anchors:
                if instance_path == source_instance_path:
                    continue  # skip self-replication

                restore = ReplicateSublayout(source_sublayout, self._board, instance_anchor, instance_path,
                                             self._get_correspondence_fn())
                if self._purge_restore.GetValue():
                    restore.purge_lca()
                result = restore.replicate()
                all_errors.extend(result.get_error_strs())

            pcbnew.Refresh()
            if all_errors:
                NEWLINE = '\n'
                wx.MessageBox(f"Restore succeeded with warnings:\n{NEWLINE.join(all_errors)}",
                              "Warning",
                              wx.OK | wx.ICON_WARNING)

            self.Close()
        except Exception as e:
            traceback_str = ''.join(traceback.format_exception(None, e, e.__traceback__))
            wx.MessageBox(f"Error: {e}\n\n{traceback_str}", "Error", wx.OK | wx.ICON_ERROR)

    def _on_restore(self, event: wx.CommandEvent) -> None:
        try:
            selected_path_comps = self._hierarchy_list.GetClientData(self._hierarchy_list.GetSelection())
            dlg = wx.FileDialog(self, "Restore sublayout from", self._get_dialog_directory(),
                                '_'.join(self._namer.name_path(selected_path_comps)),
                                "KiCad (sub)board (*.kicad_pcb)|*.kicad_pcb",
                                wx.FD_OPEN)
            res = dlg.ShowModal()
            self.__class__._last_dir = os.path.dirname(dlg.GetPath())
            if res != wx.ID_OK:
                return

            sublayout_board = pcbnew.PCB_IO_MGR.Load(pcbnew.PCB_IO_MGR.KICAD_SEXP, dlg.GetPath())  # type: pcbnew.BOARD
            if not sublayout_board:
                wx.MessageBox("Failed to load sublayout board.", "Error", wx.OK | wx.ICON_ERROR)
                return

            selected_instance_anchors = [self._instance_list.GetClientData(index)
                                         for index in self._instance_list.GetSelections()]
            all_errors = []
            for instance_path, instance_anchor in selected_instance_anchors:
                restore = ReplicateSublayout(sublayout_board, self._board, instance_anchor, instance_path,
                                             self._get_correspondence_fn())
                if self._purge_restore.GetValue():
                    restore.purge_lca()
                result = restore.replicate()
                all_errors.extend(result.get_error_strs())

            pcbnew.Refresh()
            if all_errors:
                NEWLINE = '\n'
                wx.MessageBox(f"Restore succeeded with warnings:\n{NEWLINE.join(all_errors)}",
                              "Warning",
                              wx.OK | wx.ICON_WARNING)

            self.Close()
        except Exception as e:
            traceback_str = ''.join(traceback.format_exception(None, e, e.__traceback__))
            wx.MessageBox(f"Error: {e}\n\n{traceback_str}", "Error", wx.OK | wx.ICON_ERROR)


class SubLayout(pcbnew.ActionPlugin):
    def defaults(self):
        self.name = "Sublayout"
        self.category = "Placement"
        self.description = "Merge (or create) a sub-pcb-layout into (or from) a top-level board."
        self.show_toolbar_button = True
        # self.icon_file_name = os.path.join(os.path.dirname(__file__), 'simple_plugin.png') # Optional, defaults to ""

    def Run(self):
        try:
            try:
                editor = wx.FindWindowByName("PcbFrame")
                self.frame = SubLayoutFrame(editor)
            except SublayoutInitError as e:
                wx.MessageBox(e.message, "Error", wx.OK | wx.ICON_ERROR)
                return
            self.frame.Show()
        except Exception as e:
            traceback_str = ''.join(traceback.format_exception(None, e, e.__traceback__))
            wx.MessageBox(f"Error: {e}\n\n{traceback_str}", "Error", wx.OK | wx.ICON_ERROR)


if __name__ == '__main__':
    pass
