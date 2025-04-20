import math
from typing import Tuple, List, Dict

import pcbnew

from .board_utils import BoardUtils


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

        self._correspondences = []
        self._extra_source_footprints = []
        self._extra_target_footprints = []
        self._compute_correspondences()

    def _compute_correspondences(self) -> None:
        """Computes the correspondences between the source and target footprints.
        Returns the correspondences (with anchor first), extra source footprints and extra target footprints.
        Exceptions out if there is any ambiguity, e.g. unable to match the source path prefix.

        Must only be called once."""
        assert not self._correspondences and not self._extra_source_footprints and not self._extra_target_footprints
        # calculate source path prefix using the target anchor
        # iterate through all source footprints to find the correspondence to the anchor
        source_footprints = self._src_board.GetFootprints()  # type: List[pcbnew.FOOTPRINT]
        assert BoardUtils.footprint_path_startswith(self._target_anchor, self._target_path_prefix)
        target_postfix = BoardUtils.footprint_path(self._target_anchor)[len(self._target_path_prefix):]
        source_anchor_candidates = []
        for footprint in source_footprints:
            footprint_path = BoardUtils.footprint_path(footprint)
            if len(footprint_path) >= len(target_postfix) and\
                    footprint_path[len(footprint_path) - len(target_postfix):] == target_postfix:
                source_anchor_candidates.append(footprint)
        assert len(source_anchor_candidates) == 1  # TODO better error handling
        source_anchor = source_anchor_candidates[0]
        source_prefix = BoardUtils.footprint_path(source_anchor)[:-len(target_postfix)]

        source_footprint_by_postfix: Dict[Tuple[str, ...], pcbnew.FOOTPRINT] = {}
        # calculate source footprint postfixes, adding those without the right prefix to extra_source_footprints
        for footprint in source_footprints:
            if BoardUtils.footprint_path_startswith(footprint, source_prefix):
                footprint_path = BoardUtils.footprint_path(footprint)
                footprint_postfix = footprint_path[len(source_prefix):]
                assert footprint_postfix not in source_footprint_by_postfix, \
                    f'duplicate footprint in hierarchy in source {footprint.GetReference()}'
                source_footprint_by_postfix[footprint_postfix] = footprint
            else:
                self._extra_source_footprints.append(footprint)

        footprints = self._target_board.GetFootprints()  # type: List[pcbnew.FOOTPRINT]
        for footprint in footprints:
            if not BoardUtils.footprint_path_startswith(footprint, self._target_path_prefix):
                continue
            target_postfix = BoardUtils.footprint_path(footprint)[len(self._target_path_prefix):]
            if target_postfix in source_footprint_by_postfix:
                source_footprint = source_footprint_by_postfix[target_postfix]
                if footprint.GetReference() == self._target_anchor.GetReference():  # anchor footprint, add to correspondences first
                    self._correspondences.insert(0, (source_footprint, footprint))
                else:
                    self._correspondences.append((source_footprint, footprint))
                del(source_footprint_by_postfix[target_postfix])

    def compute_target_position(self, source_pos: pcbnew.VECTOR2I) -> pcbnew.VECTOR2I:
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

    def compute_new_layout(self, source_footprint: pcbnew.FOOTPRINT) -> Tuple[bool, pcbnew.VECTOR2I, float]:
        """Returns the target position for the source footprint, given the source and target anchors.
        Position is returned as (flipped, x, y, rot), with x, y in KiCad units in target absolute board space,
        and rot in radians."""
        source_anchor, target_anchor = self._correspondences[0]
        rel_flipped = source_footprint.GetSide() != source_anchor.GetSide()
        flipped = (target_anchor.GetSide() == 0 and rel_flipped) or \
                  (target_anchor.GetSide() != 0 and not rel_flipped)
        rel_orientation = source_footprint.GetOrientation().AsRadians() - source_anchor.GetOrientation().AsRadians()

        return (flipped,
                self.compute_target_position(source_footprint.GetPosition()),
                target_anchor.GetOrientation().AsRadians() + rel_orientation)

    def replicate_footprints(self) -> None:
        """Replicates the footprints with the given footprint correspondences, as tuples of (source footprint, target footprint).
        The first correspondence are the anchor footprints, the rest are the footprints to be replicated."""
        source_anchor, target_anchor = self._correspondences[0]
        for source_footprint, target_footprint in self._correspondences[1:]:
            tgt_flipped, tgt_pos, tgt_rot = self.compute_new_layout(source_footprint)
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
            target_track.SetStart(self.compute_target_position(track.GetStart()))
            target_track.SetEnd(self.compute_target_position(track.GetEnd()))
            # TODO update netcodes

    def replicate_zones(self) -> None:
        """Replicates the zones from the source board to the target board."""
        for zone_id in range(self._src_board.GetAreaCount()):
            zone = self._src_board.GetArea(zone_id)  # type: pcbnew.ZONE
            target_zone = zone.Duplicate()
            self._target_board.Add(target_zone)
            for corner_id in range(target_zone.GetNumCorners()):
                target_zone.SetCornerPosition(
                    corner_id,
                    self.compute_target_position(zone.GetCornerPosition(corner_id)))
            # TODO update netcodes
