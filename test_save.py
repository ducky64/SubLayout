import os
import unittest
from typing import List

import pcbnew

from board_utils import BoardUtils
from save_sublayout import SaveSublayout


class SaveTestCase(unittest.TestCase):
    def test_save(self):
        src_board = pcbnew.LoadBoard(os.path.join(os.path.dirname(__file__), 'tests', 'TestBlinkyComplete.kicad_pcb'))
        save = SaveSublayout(src_board, BoardUtils.footprint_path(src_board.FindFootprintByReference('U2'))[:-1])
        save.board.Save('test_mcu.kicad_pcb')
        footprints = save.board.GetFootprints()  # type: List[pcbnew.FOOTPRINT]
        footprint_refs = {footprint.GetReference() for footprint in footprints}
        self.assertEqual(footprint_refs, {'U2', 'C3', 'C4', 'C5', 'C6', 'C7', 'C8', 'J2'})

        save = SaveSublayout(src_board, BoardUtils.footprint_path(src_board.FindFootprintByReference('D1'))[:-1])
        footprints = save.board.GetFootprints()  # type: List[pcbnew.FOOTPRINT]
        footprint_refs = {footprint.GetReference() for footprint in footprints}
        self.assertEqual(footprint_refs, {'D1', 'R3'})

        # test that sub-hierarchy items are included
        save = SaveSublayout(src_board, BoardUtils.footprint_path(src_board.FindFootprintByReference('J1'))[:-1])
        footprints = save.board.GetFootprints()  # type: List[pcbnew.FOOTPRINT]
        footprint_refs = {footprint.GetReference() for footprint in footprints}
        self.assertEqual(footprint_refs, {'J1', 'R1', 'R2'})

        # test that outer hierarchy items are not included
        save = SaveSublayout(src_board, BoardUtils.footprint_path(src_board.FindFootprintByReference('R1'))[:-1])
        footprints = save.board.GetFootprints()  # type: List[pcbnew.FOOTPRINT]
        footprint_refs = {footprint.GetReference() for footprint in footprints}
        self.assertEqual(footprint_refs, {'R1', 'R2'})
