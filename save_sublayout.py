from typing import Tuple, List

import pcbnew

from board_utils import BoardUtils


class SaveSublayout():
    def create_sublayout(self) -> pcbnew.BOARD:
        """Creates a (copy) board with only the sublayout."""
        board = BoardUtils.duplicate_board(self._board)  # create working copy
        in_scope, out_scope = self._filter_board(board, self.path_prefix)
        for item in out_scope:
            board.Delete(item)
        return board

    def __init__(self, board: pcbnew.BOARD, path_prefix: Tuple[str, ...]) -> None:
        self._board = board
        self.path_prefix = path_prefix

    @classmethod
    def _filter_board(cls, board: pcbnew.BOARD, path_prefix: Tuple[str, ...]) ->\
        Tuple[List[pcbnew.BOARD_ITEM], List[pcbnew.BOARD_ITEM]]:
        """Filters the footprints on the board, returning those that are in scope and those that are out of scope."""
        in_scope: List[pcbnew.BOARD_ITEM] = []
        out_scope: List[pcbnew.BOARD_ITEM] = []
        include_netcodes = set()  # nets that are part of the hierarchy
        exclude_netcodes = set()  # nets that are part of footprints not part of the hierarchy

        footprints = board.GetFootprints()  # type: List[pcbnew.FOOTPRINT]
        for footprint in footprints:
            if not BoardUtils.footprint_path_startswith(footprint, path_prefix):
                for pad in footprint.Pads():  # type: pcbnew.PAD
                    exclude_netcodes.add(pad.GetNetCode())
                out_scope.append(footprint)
            else:
                for pad in footprint.Pads():  # type: pcbnew.PAD
                    include_netcodes.add(pad.GetNetCode())
                in_scope.append(footprint)
        for track in board.GetTracks():  # type: List[pcbnew.PCB_TRACK]
            include_netcodes = include_netcodes.difference(exclude_netcodes)
            if track.GetNetCode() not in include_netcodes:
                out_scope.append(track)
            else:
                in_scope.append(track)
        for drawing in board.GetDrawings():  # type: List[pcbnew.DRAWINGS]
            out_scope.append(drawing)
        for zone_id in range(board.GetAreaCount()):
            zone = board.GetArea(zone_id)  # type: pcbnew.ZONE
            if zone.GetNetCode() not in include_netcodes:
                out_scope.append(zone)
            else:
                in_scope.append(zone)

        return in_scope, out_scope
