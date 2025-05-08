import os
import unittest

import pcbnew

from .board_utils import GroupWrapper


class GroupUtilsTestCase(unittest.TestCase):
    def test_group_ops(self):
        src_board = pcbnew.LoadBoard(os.path.join(os.path.dirname(__file__), 'tests', 'TestBlinkyComplete_GroupedUsb.kicad_pcb'))
        group1 = GroupWrapper(src_board.FindFootprintByReference('J1').GetParentGroup())
        group2 = GroupWrapper(src_board.FindFootprintByReference('J1').GetParentGroup())
        self.assertIsNotNone(group1._group)
        self.assertIsNotNone(group2._group)
        self.assertIsNot(group1, group2)
        self.assertEqual(group1, group2)

        group_r1 = GroupWrapper(src_board.FindFootprintByReference('R1').GetParentGroup())
        self.assertIsNotNone(group_r1._group)
        self.assertNotEqual(group1, group_r1)

        group_r2 = GroupWrapper(src_board.FindFootprintByReference('R2').GetParentGroup())
        self.assertIsNotNone(group_r2._group)
        self.assertNotEqual(group1, group_r2)
