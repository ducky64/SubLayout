from typing import Tuple, List

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
        source_footprints = target_board.GetFootprints()  # type: List[pcbnew.FOOTPRINT]
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

        correspondences = []
        extra_source_footprints = []
        extra_target_footprints = []
        footprints = target_board.GetFootprints()  # type: List[pcbnew.FOOTPRINT]
        for footprint in footprints:
            if not BoardUtils.footprint_path_startswith(footprint, target_path_prefix):
                continue
            path_postfix = BoardUtils.footprint_path(footprint)[len(target_path_prefix):]


    def replicate_tracks(self, target_board: pcbnew.BOARD, target_anchor: pcbnew.FOOTPRINT) -> None:
        """Replicates the tracks from the source board to the target board."""
        # TODO implement this
        pass
