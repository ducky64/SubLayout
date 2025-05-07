from typing import Tuple, List, Dict, Set, Optional, NamedTuple

import pcbnew

from .board_utils import BoardUtils, GroupWrapper
from .hierarchy_namer import HierarchyNamer


class FilterResult(NamedTuple):
    footprints: List[pcbnew.FOOTPRINT]
    tracks: List[pcbnew.PCB_TRACK]  # includes vias
    zones: List[pcbnew.ZONE]
    groups: Set[GroupWrapper]  # excluding root group, if any
    root_group: Optional[GroupWrapper]


class SaveSublayout():
    def create_sublayout(self) -> pcbnew.BOARD:
        """Creates a (copy) board with only the sublayout."""
        board = pcbnew.CreateEmptyBoard()  # type: pcbnew.BOARD
        result = self._filter_board()
        nets_by_netcode: Dict[int, pcbnew.NETINFO_ITEM] = self._board.GetNetsByNetcode()
        for netcode, net in nets_by_netcode.items():
            board.Add(net)
        for item in result.footprints + result.tracks + result.zones:
            cloned = item.Duplicate()
            board.Add(cloned)
        return board

    def __init__(self, board: pcbnew.BOARD, path_prefix: Tuple[str, ...]) -> None:
        self._board = board
        self.path_prefix = path_prefix

    def _filter_board(self) -> FilterResult:
        """Filters the footprints on the board, returning those that are in scope."""
        result = FilterResult([], [], [], set(), None)
        include_netcodes: Set[int] = set()  # nets that are part of the hierarchy
        exclude_netcodes: Set[int] = set()  # nets that are part of footprints not part of the hierarchy
        has_ungrouped_footprints = False
        exclude_groups: Set[GroupWrapper] = set()  # we don't care about None here

        footprints = self._board.GetFootprints()  # type: List[pcbnew.FOOTPRINT]
        for footprint in footprints:
            footprint_group = footprint.GetParentGroup()  # type: Optional[pcbnew.PCB_GROUP]
            if not BoardUtils.footprint_path_startswith(footprint, self.path_prefix):
                for pad in footprint.Pads():  # type: pcbnew.PAD
                    exclude_netcodes.add(pad.GetNetCode())
                if footprint_group is not None:
                    exclude_groups.add(GroupWrapper(footprint_group))
            else:
                for pad in footprint.Pads():
                    include_netcodes.add(pad.GetNetCode())
                result.footprints.append(footprint)
                if footprint_group is not None:
                    result.groups.add(GroupWrapper(footprint_group))
                else:
                    has_ungrouped_footprints = True

        for track in self._board.GetTracks():  # type: pcbnew.PCB_TRACK
            include_netcodes = include_netcodes.difference(exclude_netcodes)
            if track.GetNetCode() in include_netcodes or GroupWrapper(track.GetParentGroup()) in result.groups:
                result.tracks.append(track)
        for zone_id in range(self._board.GetAreaCount()):
            zone = self._board.GetArea(zone_id)  # type: pcbnew.ZONE
            if zone.GetNetCode() in include_netcodes or GroupWrapper(zone.GetParentGroup()) in result.groups:
                result.zones.append(zone)

        # TODO warn on overlap include/exclude groups
        # TODO delete top-level groups from save

        return result
