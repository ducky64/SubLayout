from typing import Tuple, List

import pcbnew

from board_utils import BoardUtils


class ReplicateSublayout():
    def __init__(self, src_board: pcbnew.BOARD) -> None:
        self._src_board = src_board

    @classmethod
    def replicate_footprints(cls, target_board: pcbnew.BOARD, target_anchor: pcbnew.FOOTPRINT,
                             correspondences: List[Tuple[pcbnew.FOOTPRINT, pcbnew.FOOTPRINT]]) -> None:
        """Replicates the footprints with the given footprint correspondences, as tuples of (source footprint, target footprint).
        The first correspondence are the anchor footprints, the rest are the footprints to be replicated.
        The target anchor may be part of correspondences, it will be ignored."""


    def compute_correspondences(self, target_board: pcbnew.BOARD, target_path_prefix: Tuple[str, ...]) ->\
        Tuple[List[Tuple[pcbnew.FOOTPRINT, pcbnew.FOOTPRINT]], List[pcbnew.FOOTPRINT], List[pcbnew.FOOTPRINT]]:
        """Computes the correspondences between the source and target footprints.
        Returns the correspondences (with anchor first), extra source footprints and extra target footprints.
        Exceptions out if there is any ambiguity, e.g. unable to match the source path prefix."""
        footprints = target_board.GetFootprints()  # type: List[pcbnew.FOOTPRINT]
        correspondences = []
        extra_source_footprints = []
        extra_target_footprints = []

        for footprint in footprints:
            if not BoardUtils.footprint_path_startswith(footprint, target_path_prefix):
                continue
            path_postfix = BoardUtils.footprint_path(footprint)[len(target_path_prefix):]
            

    def replicate_tracks(self, target_board: pcbnew.BOARD, target_anchor: pcbnew.FOOTPRINT) -> None:
        """Replicates the tracks from the source board to the target board."""
        # TODO implement this
        pass
