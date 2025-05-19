import math
from typing import Tuple, List, Dict, NamedTuple, Set, Optional, Union

import pcbnew

from .board_utils import BoardUtils, GroupWrapper


class FootprintCorrespondence(NamedTuple):
    """A footprint correspondence between source board (sublayout) and target board footprints.
    This interface allows for different mappings between sublayout and target boards."""
    mapped_footprints: List[Tuple[pcbnew.FOOTPRINT, pcbnew.FOOTPRINT]] = []  # source, target
    source_only_footprints: List[pcbnew.FOOTPRINT] = []
    target_only_footprints: List[pcbnew.FOOTPRINT] = []

    @staticmethod
    def by_tstamp(src_board: pcbnew.BOARD, target_board: pcbnew.BOARD, target_path_prefix: Tuple[str, ...])\
            -> 'FootprintCorrespondence':
        """Calculates a footprint correspondence using relative-path tstamps.
        Source path prefix is automatically inferred and asserted checked for consistency"""
        mapped_footprints: List[Tuple[pcbnew.FOOTPRINT, pcbnew.FOOTPRINT]] = []
        source_only_footprints: List[pcbnew.FOOTPRINT] = []

        # calculate target footprints by postfix, since source prefix is not known
        target_footprints = target_board.GetFootprints()  # type: List[pcbnew.FOOTPRINT]
        target_footprint_by_postfix: Dict[Tuple[str, ...], pcbnew.FOOTPRINT] = {}
        for footprint in target_footprints:
            if not BoardUtils.footprint_path_startswith(footprint, target_path_prefix):
                continue  # ignore footprints outside the hierarchy
            footprint_postfix = BoardUtils.footprint_path(footprint)[len(target_path_prefix):]
            assert footprint_postfix not in target_footprint_by_postfix, \
                f'duplicate footprint in hierarchy in target {footprint.GetReference()}'
            target_footprint_by_postfix[footprint_postfix] = footprint

        # iterate through all source footprints and match by postfix, storing the prefix
        source_footprints = src_board.GetFootprints()  # type: List[pcbnew.FOOTPRINT]
        source_prefixes: Set[Tuple[str, ...]] = set()
        for footprint in source_footprints:
            footprint_path = BoardUtils.footprint_path(footprint)
            matched = False
            for i in range(len(footprint_path)):  # try all postfix lengths to match
                test_postfix = footprint_path[i:]
                target_footprint = target_footprint_by_postfix.get(test_postfix)
                if target_footprint is not None:
                    mapped_footprints.append((footprint, target_footprint))
                    source_prefixes.add(footprint_path[:i])
                    del target_footprint_by_postfix[test_postfix]
                    matched = True
                    break
            if not matched:
                source_only_footprints.append(footprint)

        # test prefixes for consistency
        if len(source_prefixes) > 1:
            raise ValueError('multiple source prefixes found, not supported')

        # calculate source footprints by postfix
        target_only_footprints = list(target_footprint_by_postfix.values())  # all unused source footprints

        return FootprintCorrespondence(mapped_footprints, source_only_footprints, target_only_footprints)


class PositionTransform():
    """A class that represents a position transform from source to target board.
    The transform is defined by the source and target anchor footprints and the source and target positions."""
    def __init__(self, src_anchor: pcbnew.FOOTPRINT, target_anchor: pcbnew.FOOTPRINT) -> None:
        self._source_anchor_pos = src_anchor.GetPosition()
        self._source_anchor_rot = src_anchor.GetOrientation().AsRadians()
        self._source_anchor_flipped = src_anchor.GetSide() != 0
        self._target_anchor_pos = target_anchor.GetPosition()
        self._target_anchor_rot = target_anchor.GetOrientation().AsRadians()
        self._target_anchor_flipped = target_anchor.GetSide() != 0

    def transform(self, src_pos: pcbnew.VECTOR2I) -> pcbnew.VECTOR2I:
        """Given a source position, return its position in the target"""
        dx = src_pos[0] - self._source_anchor_pos[0]
        # kicad uses computer graphics coordinates, which has Y increasing downwards, opposite of math conventions
        dy = -src_pos[1] + self._source_anchor_pos[1]
        dist = math.sqrt(dx ** 2 + dy ** 2)
        # angle in radians from anchor's zero orientation
        dist_angle = math.atan2(dy, dx)
        rel_dist_angle = dist_angle - self._source_anchor_rot
        if self._target_anchor_flipped == self._source_anchor_flipped:
            target_angle = self._target_anchor_rot + rel_dist_angle
        else:
            target_angle = self._target_anchor_rot - rel_dist_angle
        return pcbnew.VECTOR2I(
            self._target_anchor_pos[0] + round(math.cos(target_angle) * dist),
            self._target_anchor_pos[1] - round(math.sin(target_angle) * dist)
        )

    def transform_orientation(self, src_rot: float) -> float:
        """Given a source rotation (as radians), return its rotation (as radians) in the target"""
        rot = src_rot - self._source_anchor_rot
        if self._target_anchor_flipped != self._source_anchor_flipped:
            rot = -rot  # account for a flip
        rot = (self._target_anchor_rot + rot) % (math.pi * 2)
        if rot > math.pi:
            rot -= math.pi * 2
        return rot

    def transform_flipped(self, src_flipped: bool) -> bool:
        """Given a source flipped state, return its flipped state in the target"""
        if not self._target_anchor_flipped:  # target on top side
            return self._source_anchor_flipped != src_flipped
        else:  # target on bottom side
            return self._source_anchor_flipped == src_flipped

    def relative_flipped(self) -> bool:
        return self._source_anchor_flipped != self._target_anchor_flipped


class ReplicateSublayout():
    """A class that represents a correspondence between a source board and a target board with anchor footprint
    and replication hierarchy level. The source anchor footprint is determined automatically.
    Computes correspondences on __init__, but replication is done explicitly."""
    def __init__(self, src_board: pcbnew.BOARD,
                 target_board: pcbnew.BOARD, target_anchor: pcbnew.FOOTPRINT,
                 target_path_prefix: Tuple[str, ...]) -> None:
        self._src_board = src_board
        self._target_board = target_board
        self._target_anchor = target_anchor
        self._target_path_prefix = target_path_prefix

        self._correspondences = FootprintCorrespondence.by_tstamp(self._src_board, self._target_board,
                                                                  self._target_path_prefix)
        correspondences_by_tstamp = {
            BoardUtils.footprint_path(target_footprint): src_footprint
            for src_footprint, target_footprint in self._correspondences.mapped_footprints
        }
        self._source_anchor = correspondences_by_tstamp.get(BoardUtils.footprint_path(self._target_anchor))
        assert self._source_anchor is not None, "could not find source anchor footprint in source board"
        self._transform = PositionTransform(self._source_anchor, target_anchor)

        # find LCA (if exists) based on footprints
        target_footprints = [target_footprint for src_footprint, target_footprint
                             in self._correspondences.mapped_footprints] \
                            + self._correspondences.target_only_footprints
        target_groups = [GroupWrapper(target_footprint.GetParentGroup()) for target_footprint in target_footprints]
        target_groups_lca = GroupWrapper.lowest_common_ancestor(target_groups)

        if target_groups_lca is not None and all(
            [BoardUtils.footprint_path_startswith(item, self._target_path_prefix)
             for item in target_groups_lca.recursive_items() if isinstance(item, pcbnew.FOOTPRINT)]):
            self._target_group: Optional[pcbnew.PCB_GROUP] = target_groups_lca._group
        else:
            self._target_group = None

    @staticmethod
    def _get_netcode_pads(board: pcbnew.BOARD, netcode: int) -> List[Tuple[pcbnew.FOOTPRINT, pcbnew.PAD]]:
        """Returns all pads in the target board with the given netcode"""
        pads = []
        for footprint in board.GetFootprints():
            for pad in footprint.Pads():
                if pad.GetNetCode() == netcode:
                    pads.append((footprint, pad))
        return pads

    def target_lca(self) -> Optional[pcbnew.PCB_GROUP]:
        """Returns the lowest common ancestor of the target footprints, or None if there is none"""
        return self._target_group

    def purge_lca(self) -> None:
        """Deletes replicate-able items (excluding footprints) from the LCA"""
        def recurse_group(group: pcbnew.PCB_GROUP) -> None:
            """Recursively deletes all items in the group."""
            for item in group.GetItems():
                if isinstance(item, pcbnew.PCB_GROUP):
                    recurse_group(item)
                if isinstance(item, (pcbnew.PCB_TRACK, pcbnew.ZONE)):
                    self._target_board.Delete(item)
        if self._target_group is not None:
            recurse_group(self._target_group)

    def replicate(self):
        if self._target_group is not None:
            target_group = self._target_group
        else:  # otherwise, create new group in root
            target_group = pcbnew.PCB_GROUP(self._target_board)
            self._target_board.Add(target_group)

        # iterate through all elements in source board, by group, replicating tracks and stuff, recursively
        target_footprint_by_src_tstamp = {
            BoardUtils.footprint_path(src_footprint): target_footprint
            for src_footprint, target_footprint in self._correspondences.mapped_footprints
        }
        def recurse_group(source_group: Union[pcbnew.PCB_GROUP, pcbnew.BOARD],
                          target_group: pcbnew.PCB_GROUP) -> None:
            if isinstance(source_group, pcbnew.BOARD):  # board does not provide GetItems() for top
                groups = [group for group in source_group.Groups()]
                footprints = [item for item in source_group.GetFootprints()]
                tracks = [item for item in source_group.GetTracks()]
                zones = [source_group.GetArea(i) for i in range(source_group.GetAreaCount())]
                items = [item for item in groups + footprints + tracks + zones
                         if item.GetParentGroup() is None]
            else:
                items = source_group.GetItems()

            for item in items:
                if isinstance(item, pcbnew.PCB_GROUP):
                    new_group = pcbnew.PCB_GROUP(self._target_board)
                    self._target_board.Add(new_group)
                    target_group.AddItem(new_group)
                    recurse_group(item, new_group)
                elif isinstance(item, pcbnew.FOOTPRINT):  # move footprints without replacing
                    target_footprint = target_footprint_by_src_tstamp.get(BoardUtils.footprint_path(item))
                    if target_footprint is None:
                        continue

                    target_group.AddItem(target_footprint)
                    target_footprint.SetParentGroup(target_group)

                    target_footprint.SetPosition(self._transform.transform(item.GetPosition()))
                    target_footprint.SetOrientationDegrees(self._transform.transform_orientation(
                        item.GetOrientation().AsRadians()) * 180 / math.pi)
                    if self._transform.transform_flipped(item.GetSide() != 0):
                        target_footprint.SetLayerAndFlip(pcbnew.B_Cu)
                    else:
                        target_footprint.SetLayerAndFlip(pcbnew.F_Cu)
                elif isinstance(item, (pcbnew.PCB_TRACK, pcbnew.ZONE)):  # duplicate everything else
                    cloned_item = item.Duplicate()
                    self._target_board.Add(cloned_item)
                    target_group.AddItem(cloned_item)
                    cloned_item.SetParentGroup(target_group)

                    # fix coordinates
                    if isinstance(cloned_item, pcbnew.PCB_TRACK):  # need to explicitly assign zone netcodes
                        cloned_item.SetStart(self._transform.transform(item.GetStart()))
                        cloned_item.SetEnd(self._transform.transform(item.GetEnd()))
                        if item.GetLayer() in (pcbnew.F_Cu, pcbnew.B_Cu):  # flip non-internal layers
                            if self._transform.transform_flipped(item.GetLayer() == pcbnew.B_Cu):
                                cloned_item.SetLayer(pcbnew.B_Cu)
                            else:
                                cloned_item.SetLayer(pcbnew.F_Cu)
                    if isinstance(cloned_item, pcbnew.ZONE):  # need to explicitly assign zone netcodes
                        cloned_item.UnFill()
                        for i in range(item.GetNumCorners()):
                            cloned_item.SetCornerPosition(i, self._transform.transform(item.GetCornerPosition(i)))
                        src_netcode_pads = self._get_netcode_pads(self._src_board, item.GetNetCode())
                        target_netcodes: Set[int] = set()
                        for footprint, pad in src_netcode_pads:
                            target_footprint = target_footprint_by_src_tstamp.get(BoardUtils.footprint_path(footprint))
                            if target_footprint is None:  # ignore
                                continue
                            target_pad = target_footprint.FindPadByNumber(pad.GetNumber())  # type: pcbnew.PAD
                            target_netcodes.add(target_pad.GetNetCode())
                        if len(target_netcodes) == 1:
                            cloned_item.SetNetCode(list(target_netcodes)[0])
                        else:
                            print("conflicting netcodes found for zone")  # TODO more debug info

                        # flip layers if needed
                        layers = item.GetLayerSet()  # type: pcbnew.LSET
                        if (layers.Contains(pcbnew.F_Cu) or layers.Contains(pcbnew.B_Cu)) and \
                            self._transform.relative_flipped():
                            cloned_layers = cloned_item.GetLayerSet()  # type: pcbnew.LSET
                            cloned_layers.RemoveLayer(pcbnew.F_Cu)
                            cloned_layers.RemoveLayer(pcbnew.B_Cu)
                            if layers.Contains(pcbnew.F_Cu):
                                cloned_layers.AddLayer(pcbnew.B_Cu)
                            if layers.Contains(pcbnew.B_Cu):
                                cloned_layers.AddLayer(pcbnew.F_Cu)
                            cloned_item.SetLayerSet(cloned_layers)
                else:
                    raise ValueError(f'unsupported item type {type(item)} in group {source_group.GetName()}')
        recurse_group(self._src_board, target_group)
