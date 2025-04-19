from typing import List, Dict, Tuple, cast, Optional

import pcbnew

from board_utils import BoardUtils


class HierarchyNamer:
    """Infers meaningful names for footprints based on hierarchy sheetnames."""
    @classmethod
    def _build_sheetfile_names(cls, footprints: List[pcbnew.FOOTPRINT]) -> Dict[Tuple[str, ...], Tuple[str, str]]:
        """Iterates through footprints in the board to try to determine the sheetfile and sheetname
        associated with a path."""
        path_sheetfile_names = {}
        for fp in footprints:
            fp_path_comps = BoardUtils.footprint_path(fp)
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

    def __init__(self, board: pcbnew.BOARD) -> None:
        self._sheetfile_names = self._build_sheetfile_names(board.Footprints())

    def name_path(self, path: Tuple[str, ...], footprint_ref: Optional[str] = None) -> Tuple[str, ...]:
        """Infers a structured name for the given path"""
        names = []
        for i in range(1, len(path) + 1):
            path_comps = path[:i]
            if path_comps in self._sheetfile_names:
                sheetfile, sheetname = self._sheetfile_names[path_comps]
                names.append(sheetname)
            elif i == len(path) and footprint_ref is not None:
                names.append(footprint_ref)  # special case for leaf level, which doesn't have a sheetname
            else:
                names.append('?')
        return tuple(names)

    def name_footprint(self, footprint: pcbnew.FOOTPRINT) -> str:
        """Returns a structured name for the footprint"""
        return self.name_path(BoardUtils.footprint_path(footprint), footprint.GetReference())

    def containing_name(self, footprint: pcbnew.FOOTPRINT) -> str:
        """Returns the name of the sheet containing the footprint"""
        fp_path = BoardUtils.footprint_path(footprint)
        comp_names = self.name_path(fp_path[:-1])
        return '/'.join(comp_names)
