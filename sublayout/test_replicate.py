import os
import unittest

import pcbnew

from .board_utils import BoardUtils
from .replicate_sublayout import ReplicateSublayout


class ReplicateTestCase(unittest.TestCase):
    def test_correspondences(self):
        board = pcbnew.LoadBoard(os.path.join(os.path.dirname(__file__), 'tests', 'BareBlinkyComplete.kicad_pcb'))  # type: pcbnew.BOARD

        sublayout_board = pcbnew.LoadBoard(os.path.join(os.path.dirname(__file__), 'tests', 'McuSublayout.kicad_pcb'))  # type: pcbnew.BOARD
        anchor = board.FindFootprintByReference('U2')
        sublayout = ReplicateSublayout(sublayout_board, board, anchor, BoardUtils.footprint_path(anchor)[:-1])
        self.assertEqual(len(sublayout._correspondences), 8)
        self.assertEqual(len(sublayout._extra_source_footprints), 0)
        self.assertEqual(len(sublayout._extra_target_footprints), 0)

        sublayout_board = pcbnew.LoadBoard(os.path.join(os.path.dirname(__file__), 'tests', 'UsbSublayout.kicad_pcb'))  # type: pcbnew.BOARD
        anchor = board.FindFootprintByReference('J1')
        sublayout = ReplicateSublayout(sublayout_board, board, anchor, BoardUtils.footprint_path(anchor)[:-1])
        self.assertEqual(len(sublayout._correspondences), 3)
        self.assertEqual(len(sublayout._extra_source_footprints), 0)
        self.assertEqual(len(sublayout._extra_target_footprints), 0)

        # test correspondences of a sub-hierarchy block in the sublayout
        anchor = board.FindFootprintByReference('R2')
        sublayout = ReplicateSublayout(sublayout_board, board, anchor, BoardUtils.footprint_path(anchor)[:-1])
        self.assertEqual(len(sublayout._correspondences), 2)
        self.assertEqual(len(sublayout._extra_source_footprints), 1)  # just J1, which is out of scope
        self.assertEqual(len(sublayout._extra_target_footprints), 0)

    def test_replicate(self):
        board = pcbnew.LoadBoard(os.path.join(os.path.dirname(__file__), 'tests', 'BareBlinkyComplete.kicad_pcb'))  # type: pcbnew.BOARD

        sublayout_board = pcbnew.LoadBoard(os.path.join(os.path.dirname(__file__), 'tests', 'McuSublayout.kicad_pcb'))  # type: pcbnew.BOARD
        anchor = board.FindFootprintByReference('U2')
        sublayout = ReplicateSublayout(sublayout_board, board, anchor, BoardUtils.footprint_path(anchor)[:-1])
        sublayout.replicate_footprints()

        sublayout_board = pcbnew.LoadBoard(os.path.join(os.path.dirname(__file__), 'tests', 'UsbSublayout.kicad_pcb'))  # type: pcbnew.BOARD
        anchor = board.FindFootprintByReference('J1')
        sublayout = ReplicateSublayout(sublayout_board, board, anchor, BoardUtils.footprint_path(anchor)[:-1])
        sublayout.replicate_footprints()
        sublayout.replicate_tracks()
        sublayout.replicate_zones()

        board.Save('../test_output_replicate.kicad_pcb')
