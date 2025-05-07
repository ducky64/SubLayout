import os
import unittest

import pcbnew

from .board_utils import BoardUtils
from .save_sublayout import SaveSublayout


class SaveTestCase(unittest.TestCase):
    def test_save(self):
        src_board = pcbnew.LoadBoard(os.path.join(os.path.dirname(__file__), 'tests', 'TestBlinkyComplete.kicad_pcb'))
        board = SaveSublayout(src_board, BoardUtils.footprint_path(src_board.FindFootprintByReference('U2'))[:-1]
                              ).create_sublayout()
        board.Save('test_output_mcu.kicad_pcb')
        footprint_refs = {footprint.GetReference() for footprint in board.GetFootprints()}
        self.assertEqual(footprint_refs, {'U2', 'C3', 'C4', 'C5', 'C6', 'C7', 'C8', 'J2'})
        self.assertEqual(board.GetAreaCount(), 0)

        board = SaveSublayout(src_board, BoardUtils.footprint_path(src_board.FindFootprintByReference('D1'))[:-1]
                              ).create_sublayout()
        footprint_refs = {footprint.GetReference() for footprint in board.GetFootprints()}
        self.assertEqual(footprint_refs, {'D1', 'R3'})

        # test that sub-hierarchy items are included
        board = SaveSublayout(src_board, BoardUtils.footprint_path(src_board.FindFootprintByReference('J1'))[:-1]
                              ).create_sublayout()
        board.Save('test_output_usb.kicad_pcb')
        footprint_refs = {footprint.GetReference() for footprint in board.GetFootprints()}
        self.assertEqual(footprint_refs, {'J1', 'R1', 'R2'})

        # test that outer hierarchy items are not included
        board = SaveSublayout(src_board, BoardUtils.footprint_path(src_board.FindFootprintByReference('R1'))[:-1]
                              ).create_sublayout()
        footprint_refs = {footprint.GetReference() for footprint in board.GetFootprints()}
        self.assertEqual(footprint_refs, {'R1', 'R2'})

    def test_save_group(self):
        src_board = pcbnew.LoadBoard(os.path.join(os.path.dirname(__file__), 'tests', 'TestBlinkyComplete_GroupedUsb.kicad_pcb'))
        board = SaveSublayout(src_board, BoardUtils.footprint_path(src_board.FindFootprintByReference('J1'))[:-1]
                              ).create_sublayout()
        self.assertEqual(board.GetAreaCount(), 1)
        self.assertGreater(len(board.GetTracks()), 0)
        board.Save('test_output_usb_grouped.kicad_pcb')
