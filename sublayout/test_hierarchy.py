import os
import unittest

import pcbnew

from .board_utils import BoardUtils
from .hierarchy_namer import HierarchyData


class NamingTestCase(unittest.TestCase):
    def test_naming(self):
        board = pcbnew.LoadBoard(os.path.join(os.path.dirname(__file__), 'tests', 'TestBlinkyComplete.kicad_pcb'))  # type: pcbnew.BOARD
        namer = HierarchyData(board)

        self.assertEqual(namer.containing_name(board.FindFootprintByReference('U2')), 'mcu')
        self.assertEqual(namer.containing_name(board.FindFootprintByReference('C4')), 'mcu')

        self.assertEqual(namer.containing_name(board.FindFootprintByReference('D1')), 'led')
        self.assertEqual(namer.containing_name(board.FindFootprintByReference('R3')), 'led')

        self.assertEqual(namer.containing_name(board.FindFootprintByReference('J1')), 'usb')
        # test a nested hierarchy
        self.assertEqual(namer.containing_name(board.FindFootprintByReference('R1')), 'usb/cc_pull')
        self.assertEqual(namer.containing_name(board.FindFootprintByReference('R2')), 'usb/cc_pull')

    def test_instances_of(self):
        board = pcbnew.LoadBoard(os.path.join(os.path.dirname(__file__), 'tests', 'TestBlinkyComplete.kicad_pcb'))  # type: pcbnew.BOARD
        namer = HierarchyData(board)

        self.assertEqual(namer.sheetfile_of(BoardUtils.footprint_path(board.FindFootprintByReference('U2'))[:-1]), 'edg.parts.Microcontroller_Stm32f103.Stm32f103_48')

        self.assertEqual(namer.sheetfile_of(BoardUtils.footprint_path(board.FindFootprintByReference('J1'))[:-1]), 'edg.parts.UsbPorts.UsbCReceptacle')
        self.assertEqual(namer.sheetfile_of(BoardUtils.footprint_path(board.FindFootprintByReference('R1'))[:-1]), 'edg.parts.UsbPorts.UsbCcPulldownResistor')
        self.assertEqual(namer.sheetfile_of(BoardUtils.footprint_path(board.FindFootprintByReference('R1'))[:-2]), 'edg.parts.UsbPorts.UsbCReceptacle')

    def test_multi_instances_of(self):
        board = pcbnew.LoadBoard(os.path.join(os.path.dirname(__file__), 'tests', 'TofArray.kicad_pcb'))  # type: pcbnew.BOARD
        namer = HierarchyData(board)

        tof_path = BoardUtils.footprint_path(board.FindFootprintByReference('U4'))[:-1]
        self.assertEqual(namer.sheetfile_of(tof_path), 'edg.parts.Distance_Vl53l0x.Vl53l0x')
        self.assertEqual(len(namer.instances_of('edg.parts.Distance_Vl53l0x.Vl53l0x')), 5)
        self.assertEqual([namer.name_path(path)[1] for path in namer.instances_of('edg.parts.Distance_Vl53l0x.Vl53l0x')],
                         ['elt[0]', 'elt[1]', 'elt[2]', 'elt[3]', 'elt[4]'])
