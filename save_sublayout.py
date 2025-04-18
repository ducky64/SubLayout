from typing import Tuple, List

import pcbnew

from board_utils import BoardUtils


class SaveSublayout():
    """Function and utilities to save a sub-layout given a hierarchy path prefix.
    Does not affect the original board object."""
    def __init__(self, board: pcbnew.BOARD, path_prefix: Tuple[str, ...]) -> None:
        self.board = BoardUtils.duplicate_board(board)  # create working copy
        self.path_prefix = path_prefix
        self._filter_board()

    def _filter_board(self) -> None:
        """Filters the footprints on the board to only include those in the given hierarchy path prefix,
        and tracks that are part of nets between the footprints in the hierarchy."""
        footprints = self.board.GetFootprints()  # type: List[pcbnew.FOOTPRINT]
        include_netcodes = set()  # nets that are part of the hierarchy
        exclude_netcodes = set()  # nets that are part of footprints not part of the hierarchy
        for footprint in footprints:
            if not BoardUtils.footprint_path_startswith(footprint, self.path_prefix):
                for pad in footprint.Pads():  # type: pcbnew.PAD
                    exclude_netcodes.add(pad.GetNetCode())
                self.board.Delete(footprint)
            else:
                for pad in footprint.Pads():  # type: pcbnew.PAD
                    include_netcodes.add(pad.GetNetCode())
        for track in self.board.GetTracks():  # type: List[pcbnew.PCB_TRACK]
            include_netcodes = include_netcodes.difference(exclude_netcodes)
            if track.GetNetCode() not in include_netcodes:
                self.board.Delete(track)
        for drawing in self.board.GetDrawings():  # type: List[pcbnew.DRAWINGS]
            self.board.Delete(drawing)
        for zone_id in range(self.board.GetAreaCount()):
            zone = self.board.GetArea(zone_id)
            self.board.Delete(zone)

    def save(self, filename: str) -> None:
        """Saves the sub-layout to a new board file and returns the new board object."""
        self.board.Save(filename)
