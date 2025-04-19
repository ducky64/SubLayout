import os
import unittest

import pcbnew

from board_utils import BoardUtils
from hierarchy_namer import HierarchyNamer
from replicate_sublayout import ReplicateSublayout


class ReplicateTestCase(unittest.TestCase):
    def test_correspondences(self):
        board = pcbnew.LoadBoard(os.path.join(os.path.dirname(__file__), 'tests', 'BareBlinkyComplete.kicad_pcb'))  # type: pcbnew.BOARD
        sublayout_board = pcbnew.LoadBoard(os.path.join(os.path.dirname(__file__), 'tests', 'McuSublayout.kicad_pcb'))  # type: pcbnew.BOARD

        sublayout = ReplicateSublayout(sublayout_board)
        anchor = board.FindFootprintByReference('U2')
        correspondences, extra_src, extra_tgt = sublayout.compute_correspondences(board, anchor, BoardUtils.footprint_path(anchor)[:-1])
        namer = HierarchyNamer(board)
        print([(namer.name_footprint(a), namer.name_footprint(b)) for (a, b) in correspondences])

        self.assertEqual(len(extra_src), 0)
        self.assertEqual(len(extra_tgt), 0)
