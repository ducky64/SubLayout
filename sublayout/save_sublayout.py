from typing import Tuple, List, Dict, Set, Optional

import pcbnew

from .board_utils import BoardUtils, GroupWrapper
from .hierarchy_namer import HierarchyNamer


class SaveSublayout():
    def create_sublayout(self) -> pcbnew.BOARD:
        """Creates a (copy) board with only the sublayout."""
        board = pcbnew.NewBoard('sublayout')  # type: pcbnew.BOARD
        in_scope = self._filter_board(self._board, self.path_prefix)
        nets_by_netcode: Dict[int, pcbnew.NETINFO_ITEM] = self._board.GetNetsByNetcode()
        for netcode, net in nets_by_netcode.items():
            board.Add(net)
        for item in in_scope:
            cloned = item.Duplicate()
            board.Add(cloned)
        return board

    def __init__(self, board: pcbnew.BOARD, path_prefix: Tuple[str, ...]) -> None:
        self._board = board
        self.path_prefix = path_prefix

    @classmethod
    def _filter_board(cls, board: pcbnew.BOARD, path_prefix: Tuple[str, ...]) ->\
        List[pcbnew.BOARD_ITEM]:
        """Filters the footprints on the board, returning those that are in scope."""
        in_scope: List[pcbnew.BOARD_ITEM] = []
        include_netcodes: Set[int] = set()  # nets that are part of the hierarchy
        exclude_netcodes: Set[int] = set()  # nets that are part of footprints not part of the hierarchy
        include_groups: Set[GroupWrapper] = set()  # PCB_GROUP.GetName, if not None
        exclude_groups: Set[GroupWrapper] = set()

        namer = HierarchyNamer(board)

        footprints = board.GetFootprints()  # type: List[pcbnew.FOOTPRINT]
        for footprint in footprints:
            footprint_group = footprint.GetParentGroup()  # type: Optional[pcbnew.PCB_GROUP]
            if not BoardUtils.footprint_path_startswith(footprint, path_prefix):
                for pad in footprint.Pads():  # type: pcbnew.PAD
                    exclude_netcodes.add(pad.GetNetCode())
                if footprint_group is not None:
                    exclude_groups.add(GroupWrapper(footprint_group))
            else:
                for pad in footprint.Pads():
                    include_netcodes.add(pad.GetNetCode())
                in_scope.append(footprint)
                if footprint_group is not None:
                    include_groups.add(GroupWrapper(footprint_group))

            # if footprint_group is not None:
            #     print(footprint_group.GetItems())
            if footprint_group is not None:
                parent = footprint_group.GetParentGroup()
                if parent is not None:
                    print(f"{GroupWrapper(footprint_group)}: {GroupWrapper(parent)}")
        for track in board.GetTracks():  # type: pcbnew.PCB_TRACK
            include_netcodes = include_netcodes.difference(exclude_netcodes)
            if track.GetNetCode() in include_netcodes:
                in_scope.append(track)
        for zone_id in range(board.GetAreaCount()):
            zone = board.GetArea(zone_id)  # type: pcbnew.ZONE
            if zone.GetNetCode() in include_netcodes:
                in_scope.append(zone)

        print(f"include: {include_groups}")
        print(f"exclude: {exclude_groups}")

        return in_scope
