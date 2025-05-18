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

    def transform_orientation(self, src_rot: float, src_flipped: bool) -> float:
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

    def replicate(self):
        # if they're all in the same group (LCA) with no other footprints (in other paths),
        target_footprints = [target_footprint for src_footprint, target_footprint
                             in self._correspondences.mapped_footprints]\
            + self._correspondences.target_only_footprints
        target_groups = [GroupWrapper(target_footprint.GetParentGroup()) for target_footprint in target_footprints]
        target_groups_lca = GroupWrapper.lowest_common_ancestor(target_groups)

        if target_groups_lca is not None:
            target_group = target_groups_lca._group
        else:  # otherwise, create new group in root
            target_group = pcbnew.PCB_GROUP(self._target_board)
            self._target_board.Add(target_group)

        # iterate through all elements in source board, by group, replicating tracks and stuff
        target_footprint_by_src_tstamp = {
            BoardUtils.footprint_path(src_footprint): target_footprint
            for src_footprint, target_footprint in self._correspondences.mapped_footprints
        }
        def recurse_group(source_group: Union[pcbnew.BOARD, pcbnew.PCB_GROUP],
                          target_group: pcbnew.PCB_GROUP) -> None:
            for item in source_group.GetItems():
                if isinstance(item, pcbnew.PCB_GROUP):
                    new_group = pcbnew.PCB_GROUP(self._target_board)
                    self._target_board.Add(new_group)
                    target_group.AddItem(new_group)
                    recurse_group(item, new_group)
                elif isinstance(item, pcbnew.FOOTPRINT):
                    pass
                elif isinstance(item, (pcbnew.PCB_TRACK, pcbnew.ZONE)):
                    # TODO IMPLEMENT ME
                    # TODO: zones: fix netcode
                else:
                    raise ValueError(f'unsupported item type {type(item)} in group {source_group.GetName()}')
        recurse_group(self._src_board, target_group)

        # recursively within groups: replicate tracks and stuff
        # for footprints, move the existing footprint in to new position and into the t;arget group
        pass


    def _compute_target_position(self, source_pos: pcbnew.VECTOR2I) -> pcbnew.VECTOR2I:
        source_anchor, target_anchor = self._correspondences[0]
        dx = source_pos[0] - source_anchor.GetPosition()[0]
        # kicad uses computer graphics coordinates, which has Y increasing downwards, opposite of math conventions
        dy = -source_pos[1] + source_anchor.GetPosition()[1]
        dist = math.sqrt(dx ** 2 + dy ** 2)
        # angle in radians from anchor's zero orientation
        dist_angle = math.atan2(dy, dx)
        rel_dist_angle = dist_angle - source_anchor.GetOrientation().AsRadians()
        target_angle = target_anchor.GetOrientation().AsRadians() + rel_dist_angle
        return pcbnew.VECTOR2I(
            target_anchor.GetPosition()[0] + round(math.cos(target_angle) * dist),
            target_anchor.GetPosition()[1] - round(math.sin(target_angle) * dist)
        )

    def _compute_target_footprint(self, source_footprint: pcbnew.FOOTPRINT) -> Tuple[bool, pcbnew.VECTOR2I, float]:
        """Returns the target position for the source footprint, given the source and target anchors.
        Position is returned as (flipped, x, y, rot), with x, y in KiCad units in target absolute board space,
        and rot in radians."""
        source_anchor, target_anchor = self._correspondences[0]
        rel_flipped = source_footprint.GetSide() != source_anchor.GetSide()
        flipped = (target_anchor.GetSide() == 0 and rel_flipped) or \
                  (target_anchor.GetSide() != 0 and not rel_flipped)
        rel_orientation = source_footprint.GetOrientation().AsRadians() - source_anchor.GetOrientation().AsRadians()

        return (flipped,
                self._compute_target_position(source_footprint.GetPosition()),
                target_anchor.GetOrientation().AsRadians() + rel_orientation)

    def replicate_footprints(self) -> None:
        """Replicates the footprints with the given footprint correspondences, as tuples of (source footprint, target footprint).
        The first correspondence are the anchor footprints, the rest are the footprints to be replicated."""
        for source_footprint, target_footprint in self._correspondences[1:]:
            tgt_flipped, tgt_pos, tgt_rot = self._compute_target_footprint(source_footprint)
            if tgt_flipped:
                target_footprint.SetLayerAndFlip(pcbnew.B_Cu)
            else:
                target_footprint.SetLayerAndFlip(pcbnew.F_Cu)
            target_footprint.SetPosition(tgt_pos)
            target_footprint.SetOrientationDegrees(tgt_rot * 180 / math.pi)

    def replicate_tracks(self) -> None:
        """Replicates the tracks from the source board to the target board."""
        for track in self._src_board.GetTracks():  # type: pcbnew.PCB_TRACK
            target_track = track.Duplicate()  # type: pcbnew.PCB_TRACK
            self._target_board.Add(target_track)
            target_track.SetStart(self._compute_target_position(track.GetStart()))
            target_track.SetEnd(self._compute_target_position(track.GetEnd()))
            # TODO update netcodes

    def replicate_zones(self) -> None:
        """Replicates the zones from the source board to the target board."""
        for zone_id in range(self._src_board.GetAreaCount()):
            zone = self._src_board.GetArea(zone_id)  # type: pcbnew.ZONE
            target_zone = zone.Duplicate()  # type: pcbnew.ZONE
            self._target_board.Add(target_zone)
            for corner_id in range(target_zone.GetNumCorners()):
                target_zone.SetCornerPosition(
                    corner_id,
                    self._compute_target_position(zone.GetCornerPosition(corner_id)))
            target_zone.SetNetCode(0)
            target_zone.UnFill()
            # TODO update netcodes
