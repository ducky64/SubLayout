import os
import unittest

import pcbnew

from board_utils import BoardUtils
from replicate_sublayout import ReplicateSublayout


class ReplicateTestCase(unittest.TestCase):
    def test_correspondences(self):
        board = pcbnew.LoadBoard(os.path.join(os.path.dirname(__file__), 'tests', 'BareBlinkyComplete.kicad_pcb'))  # type: pcbnew.BOARD

        sublayout_board = pcbnew.LoadBoard(os.path.join(os.path.dirname(__file__), 'tests', 'McuSublayout.kicad_pcb'))  # type: pcbnew.BOARD
        sublayout = ReplicateSublayout(sublayout_board)
        anchor = board.FindFootprintByReference('U2')
        correspondences, extra_src, extra_tgt = sublayout.compute_correspondences(board, anchor, BoardUtils.footprint_path(anchor)[:-1])
        self.assertEqual(len(correspondences), 8)
        self.assertEqual(len(extra_src), 0)
        self.assertEqual(len(extra_tgt), 0)

        sublayout_board = pcbnew.LoadBoard(os.path.join(os.path.dirname(__file__), 'tests', 'UsbSublayout.kicad_pcb'))  # type: pcbnew.BOARD
        sublayout = ReplicateSublayout(sublayout_board)
        anchor = board.FindFootprintByReference('J1')
        correspondences, extra_src, extra_tgt = sublayout.compute_correspondences(board, anchor, BoardUtils.footprint_path(anchor)[:-1])
        self.assertEqual(len(correspondences), 3)
        self.assertEqual(len(extra_src), 0)
        self.assertEqual(len(extra_tgt), 0)

        # test correspondences of a sub-hierarchy block in the sublayout
        anchor = board.FindFootprintByReference('R2')
        correspondences, extra_src, extra_tgt = sublayout.compute_correspondences(board, anchor, BoardUtils.footprint_path(anchor)[:-1])
        self.assertEqual(len(correspondences), 2)
        self.assertEqual(len(extra_src), 1)  # just J1, which is out of scope
        self.assertEqual(len(extra_tgt), 0)

    def test_replicate(self):
        board = pcbnew.LoadBoard(os.path.join(os.path.dirname(__file__), 'tests', 'BareBlinkyComplete.kicad_pcb'))  # type: pcbnew.BOARD

        sublayout_board = pcbnew.LoadBoard(os.path.join(os.path.dirname(__file__), 'tests', 'McuSublayout.kicad_pcb'))  # type: pcbnew.BOARD
        sublayout = ReplicateSublayout(sublayout_board)
        anchor = board.FindFootprintByReference('U2')
        correspondences, extra_src, extra_tgt = sublayout.compute_correspondences(board, anchor, BoardUtils.footprint_path(anchor)[:-1])
        sublayout.replicate_footprints(board, correspondences)

        sublayout_board = pcbnew.LoadBoard(os.path.join(os.path.dirname(__file__), 'tests', 'UsbSublayout.kicad_pcb'))  # type: pcbnew.BOARD
        sublayout = ReplicateSublayout(sublayout_board)
        anchor = board.FindFootprintByReference('J1')
        correspondences, extra_src, extra_tgt = sublayout.compute_correspondences(board, anchor, BoardUtils.footprint_path(anchor)[:-1])
        sublayout.replicate_footprints(board, correspondences)
        sublayout.replicate_tracks(board, correspondences[0][0], correspondences[0][1])
        sublayout.replicate_zones(board, correspondences[0][0], correspondences[0][1])

        board.Save('test_output_replicate.kicad_pcb')
