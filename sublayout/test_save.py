import os
import unittest

import pcbnew

from .board_utils import BoardUtils, GroupWrapper
from .save_sublayout import HierarchySelector


class SaveTestCase(unittest.TestCase):
    def test_save(self):
        src_board = pcbnew.LoadBoard(os.path.join(os.path.dirname(__file__), 'tests', 'TestBlinkyComplete.kicad_pcb'))
        board = HierarchySelector(src_board, BoardUtils.footprint_path(src_board.FindFootprintByReference('U2'))[:-1]
                                  ).create_sublayout()
        board.Save('test_output_mcu.kicad_pcb')
        footprint_refs = {footprint.GetReference() for footprint in board.GetFootprints()}
        self.assertEqual(footprint_refs, {'U2', 'C3', 'C4', 'C5', 'C6', 'C7', 'C8', 'J2'})
        self.assertEqual(board.GetAreaCount(), 0)

        board = HierarchySelector(src_board, BoardUtils.footprint_path(src_board.FindFootprintByReference('D1'))[:-1]
                                  ).create_sublayout()
        footprint_refs = {footprint.GetReference() for footprint in board.GetFootprints()}
        self.assertEqual(footprint_refs, {'D1', 'R3'})

        # test that sub-hierarchy items are included
        board = HierarchySelector(src_board, BoardUtils.footprint_path(src_board.FindFootprintByReference('J1'))[:-1]
                                  ).create_sublayout()
        board.Save('test_output_usb.kicad_pcb')
        footprint_refs = {footprint.GetReference() for footprint in board.GetFootprints()}
        self.assertEqual(footprint_refs, {'J1', 'R1', 'R2'})

        # test that outer hierarchy items are not included
        board = HierarchySelector(src_board, BoardUtils.footprint_path(src_board.FindFootprintByReference('R1'))[:-1]
                                  ).create_sublayout()
        footprint_refs = {footprint.GetReference() for footprint in board.GetFootprints()}
        self.assertEqual(footprint_refs, {'R1', 'R2'})

    def test_save_group(self):
        src_board = pcbnew.LoadBoard(os.path.join(os.path.dirname(__file__), 'tests', 'TestBlinkyComplete_GroupedUsb.kicad_pcb'))
        selector = HierarchySelector(src_board, BoardUtils.footprint_path(src_board.FindFootprintByReference('J1'))[:-1])
        result = selector.get_elts()
        self.assertEqual(len(result.ungrouped_elts), 0)  # no loose elts
        self.assertEqual(len(result.groups), 1)  # main group only
        self.assertEqual(GroupWrapper(result.groups[0]).sorted_footprint_refs(), ('J1', ))  # direct contents only
        board = selector.create_sublayout()
        board.Save('test_output_usb_grouped.kicad_pcb')

    def test_delete_group(self):
        src_board = pcbnew.LoadBoard(os.path.join(os.path.dirname(__file__), 'tests', 'TestBlinkyComplete_GroupedUsb.kicad_pcb'))
        selector = HierarchySelector(src_board, BoardUtils.footprint_path(src_board.FindFootprintByReference('J1'))[:-1])
        self.assertIsNotNone(src_board.FindFootprintByReference('J1').GetParentGroup())
        selector.delete((pcbnew.FOOTPRINT,))
        self.assertIsNotNone(src_board.FindFootprintByReference('J1'))
        self.assertIsNotNone(src_board.FindFootprintByReference('R1'))
        self.assertIsNotNone(src_board.FindFootprintByReference('R2'))
        self.assertIsNone(src_board.FindFootprintByReference('J1').GetParentGroup())
        src_board.Save('test_output_deletedusb.kicad_pcb')
