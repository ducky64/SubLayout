import os
from typing import Dict, List, Tuple, cast

import pcbnew


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

  @classmethod
  def duplicate_board(cls, board: pcbnew.BOARD) -> pcbnew.BOARD:
    """Duplicates the board by saving and loading."""
    assert not os.path.exists('temp.kicad_pcb'), 'temp board file must not exist'
    board.Save('temp.kicad_pcb')
    new_board = pcbnew.LoadBoard('temp.kicad_pcb')
    os.remove('temp.kicad_pcb')
    return new_board
