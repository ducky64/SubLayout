from typing import Tuple, List, Dict, Set, NamedTuple, Union, Sequence

import pcbnew

from .board_utils import BoardUtils, GroupWrapper


class FilterResult(NamedTuple):
    elts: List[Union[pcbnew.FOOTPRINT, pcbnew.PCB_TRACK, pcbnew.ZONE]]
    groups: Sequence[GroupWrapper]  # groups that are wholly part of the hierarchy


class SaveSublayout():
    def create_sublayout(self) -> pcbnew.BOARD:
        """Creates a (copy) board with only the sublayout."""
        board = pcbnew.CreateEmptyBoard()  # type: pcbnew.BOARD
        result = self._filter_board()

        # TODO copy groups to new board, ignoring top-level group
        # algo: gather items by group, including ungrouped items
        # for all groups, check for conflicts (groups containing other footprints, even recursively)
        #   move items to ungrouped
        # for remaining groups, remove sub-groups
        # replicate groups, recursively, maintaining group structure
        #   exception: if there is only one remaining group, it is the top-level board


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
        include_netcodes: Set[int] = set()  # nets that are part of the hierarchy
        exclude_netcodes: Set[int] = set()  # nets that are part of footprints not part of the hierarchy

        # footprints and tracks / zones of internal netlists, keyed by group
        elts_by_group: Dict[GroupWrapper, List[Union[pcbnew.FOOTPRINT, pcbnew.PCB_TRACK, pcbnew.ZONE]]] = {}
        # groups that are not part of the hierarchy, by footprint
        exclude_groups: Set[GroupWrapper] = set()

        footprints = self._board.GetFootprints()  # type: List[pcbnew.FOOTPRINT]
        for footprint in footprints:
            footprint_group = GroupWrapper(footprint.GetParentGroup())
            if not BoardUtils.footprint_path_startswith(footprint, self.path_prefix):
                exclude_groups.add(footprint_group)
                for pad in footprint.Pads():  # type: pcbnew.PAD
                    exclude_netcodes.add(pad.GetNetCode())
            else:
                elts_by_group.setdefault(footprint_group, []).append(footprint)
                for pad in footprint.Pads():
                    include_netcodes.add(pad.GetNetCode())

        include_netcodes = include_netcodes.difference(exclude_netcodes)
        for track in self._board.GetTracks():  # type: pcbnew.PCB_TRACK
            if track.GetNetCode() in include_netcodes:
                track_group = GroupWrapper(track.GetParentGroup())
                elts_by_group.setdefault(track_group, []).append(track)
        for zone_id in range(self._board.GetAreaCount()):
            zone = self._board.GetArea(zone_id)  # type: pcbnew.ZONE
            if zone.GetNetCode() in include_netcodes:
                track_group = GroupWrapper(zone.GetParentGroup())
                elts_by_group.setdefault(track_group, []).append(zone)

        # for exclude_groups in elts_by_group, move them to the None group
        for group in exclude_groups:
            if group in elts_by_group:
                elts_by_group.setdefault(GroupWrapper(None), []).extend(elts_by_group[group])
                # TODO warn on overlap include/exclude groups
                del elts_by_group[group]

        # prune groups with highest covering group
        covering_groups = GroupWrapper.highest_covering_groups(list(elts_by_group.keys()))
        for group in list(elts_by_group.keys()):
            if group not in covering_groups:
                del elts_by_group[group]

        ungrouped_elts = elts_by_group.pop(GroupWrapper(None), [])

        return FilterResult(ungrouped_elts, list(elts_by_group.keys()))
