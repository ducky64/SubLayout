import math
from typing import Tuple, List, Dict

import pcbnew

from board_utils import BoardUtils


class ReplicateSublayout():
    def __init__(self, src_board: pcbnew.BOARD) -> None:
        self._src_board = src_board

    def compute_correspondences(self, target_board: pcbnew.BOARD, target_anchor: pcbnew.FOOTPRINT,
                                target_path_prefix: Tuple[str, ...]) ->\
        Tuple[List[Tuple[pcbnew.FOOTPRINT, pcbnew.FOOTPRINT]], List[pcbnew.FOOTPRINT], List[pcbnew.FOOTPRINT]]:
        """Computes the correspondences between the source and target footprints.
        Returns the correspondences (with anchor first), extra source footprints and extra target footprints.
        Exceptions out if there is any ambiguity, e.g. unable to match the source path prefix."""
        # calculate source path prefix using the target anchor
        # iterate through all source footprints to find the correspondence to the anchor
        source_footprints = self._src_board.GetFootprints()  # type: List[pcbnew.FOOTPRINT]
        assert BoardUtils.footprint_path_startswith(target_anchor, target_path_prefix)
        target_postfix = BoardUtils.footprint_path(target_anchor)[len(target_path_prefix):]
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
        extra_source_footprints = []
        # calculate source footprint postfixes, adding those without the right prefix to extra_source_footprints
        for footprint in source_footprints:
            if BoardUtils.footprint_path_startswith(footprint, source_prefix):
                footprint_path = BoardUtils.footprint_path(footprint)
                footprint_postfix = footprint_path[len(source_prefix):]
                assert footprint_postfix not in source_footprint_by_postfix, \
                    f'duplicate footprint in hierarchy in source {footprint.GetReference()}'
                source_footprint_by_postfix[footprint_postfix] = footprint
            else:
                extra_source_footprints.append(footprint)

        correspondences = []
        extra_target_footprints = []
        footprints = target_board.GetFootprints()  # type: List[pcbnew.FOOTPRINT]
        for footprint in footprints:
            if not BoardUtils.footprint_path_startswith(footprint, target_path_prefix):
                continue
            target_postfix = BoardUtils.footprint_path(footprint)[len(target_path_prefix):]
            if target_postfix in source_footprint_by_postfix:
                source_footprint = source_footprint_by_postfix[target_postfix]
                if footprint is target_anchor:  # anchor footprint, add to correspondences first
                    correspondences.insert(0, (source_footprint, footprint))
                else:
                    correspondences.append((source_footprint, footprint))
                del(source_footprint_by_postfix[target_postfix])

        return correspondences, extra_source_footprints, extra_target_footprints

    @classmethod
    def compute_new_layout(cls, source_anchor_footprint: pcbnew.FOOTPRINT, source_footprint: pcbnew.FOOTPRINT,
                           target_anchor_footprint: pcbnew.FOOTPRINT) -> Tuple[bool, int, int, float]:
        """Returns the target position for the source footprint, given the source and target anchors.
        Position is returned as (flipped, x, y, rot), with x, y in KiCad units in target absolute board space,
        and rot in radians."""
        dx = source_footprint.GetPosition()[0] - source_anchor_footprint.GetPosition()[0]
        dy = source_footprint.GetPosition()[1] - source_anchor_footprint.GetPosition()[1]
        dist = math.sqrt(dx ** 2 + dy ** 2)
        # angle in radians from anchor's zero orientation
        if dx != 0:
            dist_angle = math.atan(dy / dx)
        else:
            if dy > 0:
                dist_angle = math.pi / 2
            else:
                dist_angle = -math.pi / 2
        rel_dist_angle = dist_angle - source_anchor_footprint.GetOrientation().AsRadians()
        target_angle = target_anchor_footprint.GetOrientation().AsRadians() + rel_dist_angle
        rel_flipped = source_footprint.GetSide() != source_anchor_footprint.GetSide()
        flipped = (target_anchor_footprint.GetSide() == 0 and rel_flipped) or \
                  (target_anchor_footprint.GetSide() != 0 and not rel_flipped)
        rel_orientation = source_footprint.GetOrientation().AsRadians() - source_anchor_footprint.GetOrientation().AsRadians()

        return (flipped,
                target_anchor_footprint.GetPosition()[0] + round(math.cos(target_angle) * dist),
                target_anchor_footprint.GetPosition()[1] + round(math.sin(target_angle) * dist),
                target_anchor_footprint.GetOrientation().AsRadians() + rel_orientation)

    @classmethod
    def replicate_footprints(cls, target_board: pcbnew.BOARD,
                             correspondences: List[Tuple[pcbnew.FOOTPRINT, pcbnew.FOOTPRINT]]) -> None:
        """Replicates the footprints with the given footprint correspondences, as tuples of (source footprint, target footprint).
        The first correspondence are the anchor footprints, the rest are the footprints to be replicated."""
        source_anchor, target_anchor = correspondences[0]
        for source_footprint, target_footprint in correspondences[1:]:
            tgt_flipped, tgt_x, tgt_y, tgt_rot = cls.compute_new_layout(source_anchor, source_footprint, target_anchor)
            if tgt_flipped:
                target_footprint.SetLayerAndFlip(pcbnew.B_Cu)
            else:
                target_footprint.SetLayerAndFlip(pcbnew.F_Cu)
            target_footprint.SetPosition(pcbnew.VECTOR2I(tgt_x, tgt_y))
            target_footprint.SetOrientationDegrees(tgt_rot * 180 / math.pi)

    def replicate_tracks(self, target_board: pcbnew.BOARD, target_anchor: pcbnew.FOOTPRINT) -> None:
        """Replicates the tracks from the source board to the target board."""
        # TODO implement this
        pass
