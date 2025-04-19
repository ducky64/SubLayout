from typing import Tuple, List, Dict

import pcbnew

from board_utils import BoardUtils


class ReplicateSublayout():
    def __init__(self, src_board: pcbnew.BOARD) -> None:
        self._src_board = src_board

    @classmethod
    def replicate_footprints(cls, target_board: pcbnew.BOARD,
                             correspondences: List[Tuple[pcbnew.FOOTPRINT, pcbnew.FOOTPRINT]]) -> None:
        """Replicates the footprints with the given footprint correspondences, as tuples of (source footprint, target footprint).
        The first correspondence are the anchor footprints, the rest are the footprints to be replicated."""


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
                footprint_postfix = footprint_path[len(footprint_path) - len(target_postfix):]
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

    def replicate_tracks(self, target_board: pcbnew.BOARD, target_anchor: pcbnew.FOOTPRINT) -> None:
        """Replicates the tracks from the source board to the target board."""
        # TODO implement this
        pass
