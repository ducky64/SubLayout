import os
import unittest

import pcbnew

from .hierarchy_namer import HierarchyNamer


class NamingTestCase(unittest.TestCase):
    def test_save(self):
        board = pcbnew.LoadBoard(os.path.join(os.path.dirname(__file__), 'tests', 'TestBlinkyComplete.kicad_pcb'))  # type: pcbnew.BOARD
        namer = HierarchyNamer(board)

        self.assertEqual(namer.containing_name(board.FindFootprintByReference('U2')), 'mcu')
        self.assertEqual(namer.containing_name(board.FindFootprintByReference('C4')), 'mcu')

        self.assertEqual(namer.containing_name(board.FindFootprintByReference('D1')), 'led')
        self.assertEqual(namer.containing_name(board.FindFootprintByReference('R3')), 'led')

        self.assertEqual(namer.containing_name(board.FindFootprintByReference('J1')), 'usb')
        # test a nested hierarchy
        self.assertEqual(namer.containing_name(board.FindFootprintByReference('R1')), 'usb/cc_pull')
        self.assertEqual(namer.containing_name(board.FindFootprintByReference('R2')), 'usb/cc_pull')
