import os
import unittest

import pcbnew

from .board_utils import GroupWrapper


class GroupUtilsTestCase(unittest.TestCase):
    def test_group_equals(self):
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

    def test_group_lca(self):
        src_board = pcbnew.LoadBoard(os.path.join(os.path.dirname(__file__), 'tests', 'TestBlinkyComplete_GroupedUsb.kicad_pcb'))
        group_j1 = GroupWrapper(src_board.FindFootprintByReference('J1').GetParentGroup())
        group_r1 = GroupWrapper(src_board.FindFootprintByReference('R1').GetParentGroup())
        group_r2 = GroupWrapper(src_board.FindFootprintByReference('R2').GetParentGroup())
        group_r1r2 = GroupWrapper(src_board.FindFootprintByReference('R2').GetParentGroup().GetParentGroup())
        self.assertEqual(group_j1.lowest_common_ancestor([group_j1, group_j1]), group_j1)
        self.assertEqual(group_j1.lowest_common_ancestor([group_r1, group_j1]), group_j1)
        self.assertEqual(group_j1.lowest_common_ancestor([group_r1, group_r1]), group_r1)
        self.assertEqual(group_j1.lowest_common_ancestor([group_r1, group_r2]), group_r1r2)

        group_u2 = GroupWrapper(src_board.FindFootprintByReference('U2').GetParentGroup())
        self.assertIsNone(group_j1.lowest_common_ancestor([group_u2, group_j1]))

        group_none = GroupWrapper(None)
        self.assertIsNone(group_j1.lowest_common_ancestor([group_none, group_j1]))

    def test_group_highest_covering(self):
        src_board = pcbnew.LoadBoard(os.path.join(os.path.dirname(__file__), 'tests', 'TestBlinkyComplete_GroupedUsb.kicad_pcb'))
        group_j1 = GroupWrapper(src_board.FindFootprintByReference('J1').GetParentGroup())
        group_r1 = GroupWrapper(src_board.FindFootprintByReference('R1').GetParentGroup())
        group_r2 = GroupWrapper(src_board.FindFootprintByReference('R2').GetParentGroup())
        group_r1r2 = GroupWrapper(src_board.FindFootprintByReference('R2').GetParentGroup().GetParentGroup())
        self.assertEqual(group_j1.highest_covering_groups([group_j1, group_j1]), [group_j1])  # check deduplication
        self.assertEqual(group_j1.highest_covering_groups([group_r1, group_j1]), [group_j1])
        self.assertEqual(group_j1.highest_covering_groups([group_r1, group_r1]), [group_r1])
        self.assertEqual(group_j1.highest_covering_groups([group_r1, group_r2]), [group_r1, group_r2])

        group_u2 = GroupWrapper(src_board.FindFootprintByReference('U2').GetParentGroup())
        self.assertEqual(group_j1.highest_covering_groups([group_u2, group_j1]), [group_u2, group_j1])

        group_none = GroupWrapper(None)
        # None groups are passed through but deduplicated
        self.assertEqual(group_j1.highest_covering_groups([group_none]), [group_none])
        self.assertEqual(group_j1.highest_covering_groups([group_none, group_none]), [group_none])
        self.assertEqual(group_j1.highest_covering_groups([group_none, group_j1]), [group_none, group_j1])
