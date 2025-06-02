import os
import unittest

import pcbnew

from .board_utils import BoardUtils
from .replicate_sublayout import ReplicateSublayout, FootprintCorrespondence, PositionTransform
from .save_sublayout import HierarchySelector


class ReplicateTestCase(unittest.TestCase):
    def test_correspondences(self):
        board = pcbnew.LoadBoard(os.path.join(os.path.dirname(__file__), 'tests', 'BareBlinkyComplete.kicad_pcb'))  # type: pcbnew.BOARD

        sublayout_board = pcbnew.LoadBoard(os.path.join(os.path.dirname(__file__), 'tests', 'McuSublayout.kicad_pcb'))  # type: pcbnew.BOARD
        anchor = board.FindFootprintByReference('U2')
        correspondence = FootprintCorrespondence.by_tstamp(sublayout_board, board, BoardUtils.footprint_path(anchor)[:-1])
        self.assertEqual(len(correspondence.mapped_footprints), 8)
        self.assertEqual(len(correspondence.source_only_footprints), 0)
        self.assertEqual(len(correspondence.target_only_footprints), 0)

        sublayout_board = pcbnew.LoadBoard(os.path.join(os.path.dirname(__file__), 'tests', 'UsbSublayout.kicad_pcb'))
        anchor = board.FindFootprintByReference('J1')
        correspondence = FootprintCorrespondence.by_tstamp(sublayout_board, board, BoardUtils.footprint_path(anchor)[:-1])
        self.assertEqual(len(correspondence.mapped_footprints), 3)
        self.assertEqual(len(correspondence.source_only_footprints), 0)
        self.assertEqual(len(correspondence.target_only_footprints), 0)

        # test correspondences of a sub-hierarchy block in the sublayout
        anchor = board.FindFootprintByReference('R2')
        correspondence = FootprintCorrespondence.by_tstamp(sublayout_board, board, BoardUtils.footprint_path(anchor)[:-1])
        self.assertEqual(len(correspondence.mapped_footprints), 2)
        self.assertEqual(len(correspondence.source_only_footprints), 1)  # just J1, which is out of scope
        self.assertEqual(len(correspondence.target_only_footprints), 0)

    def test_correspondences_multi(self):
        """Tests correspondence generation with a board with multiple instances of a hierarchy block"""
        board = pcbnew.LoadBoard(os.path.join(os.path.dirname(__file__), 'tests', 'TofArray_Unreplicated.kicad_pcb'))  # type: pcbnew.BOARD
        source_group = HierarchySelector(board, BoardUtils.footprint_path(board.FindFootprintByReference('U3'))[:-1]).get_elts()
        target_anchor = board.FindFootprintByReference('U4')
        correspondence = FootprintCorrespondence.by_tstamp(source_group, board, BoardUtils.footprint_path(target_anchor)[:-1])
        self.assertEqual(len(correspondence.mapped_footprints), 3)
        self.assertIn((board.FindFootprintByReference('U3'), board.FindFootprintByReference('U4')), correspondence.mapped_footprints)
        self.assertIn((board.FindFootprintByReference('C11'), board.FindFootprintByReference('C13')), correspondence.mapped_footprints)
        self.assertIn((board.FindFootprintByReference('C12'), board.FindFootprintByReference('C14')), correspondence.mapped_footprints)

        target_anchor = board.FindFootprintByReference('U7')
        correspondence = FootprintCorrespondence.by_tstamp(source_group, board, BoardUtils.footprint_path(target_anchor)[:-1])
        self.assertEqual(len(correspondence.mapped_footprints), 3)
        self.assertIn((board.FindFootprintByReference('U3'), board.FindFootprintByReference('U7')), correspondence.mapped_footprints)
        self.assertIn((board.FindFootprintByReference('C11'), board.FindFootprintByReference('C19')), correspondence.mapped_footprints)
        self.assertIn((board.FindFootprintByReference('C12'), board.FindFootprintByReference('C20')), correspondence.mapped_footprints)

    def check_transform_equality(self, src_board: pcbnew.BOARD, target_board: pcbnew.BOARD, target_anchor_ref: str):
        anchor = target_board.FindFootprintByReference(target_anchor_ref)
        correspondence = FootprintCorrespondence.by_tstamp(src_board, target_board, BoardUtils.footprint_path(anchor)[:-1])
        transform = PositionTransform(src_board.FindFootprintByReference(target_anchor_ref),
                                      target_board.FindFootprintByReference(target_anchor_ref))
        for src_footprint, target_footprint in correspondence.mapped_footprints:
            self.assertEqual(transform.transform(src_footprint.GetPosition()), target_footprint.GetPosition())
            self.assertEqual(transform.transform_orientation(src_footprint.GetOrientation().AsRadians()), target_footprint.GetOrientation().AsRadians())
            self.assertEqual(transform.transform_flipped(src_footprint.GetSide() != 0), target_footprint.GetSide() != 0)

    def test_transforms_identity(self):
        self.check_transform_equality(
            pcbnew.LoadBoard(os.path.join(os.path.dirname(__file__), 'tests', 'McuSublayout.kicad_pcb')),
            pcbnew.LoadBoard(os.path.join(os.path.dirname(__file__), 'tests', 'McuSublayout.kicad_pcb')),
            'U2')

    def test_transforms_rot(self):
        # test a sublayout that is moved and rotated
        self.check_transform_equality(
            pcbnew.LoadBoard(os.path.join(os.path.dirname(__file__), 'tests', 'McuSublayout_Rot.kicad_pcb')),
            pcbnew.LoadBoard(os.path.join(os.path.dirname(__file__), 'tests', 'McuSublayout.kicad_pcb')),
            'U2')

    def test_transforms_flips(self):
        # test a sublayout that is moved and rotated
        self.check_transform_equality(
            pcbnew.LoadBoard(os.path.join(os.path.dirname(__file__), 'tests', 'McuSublayout_FlipRot.kicad_pcb')),
            pcbnew.LoadBoard(os.path.join(os.path.dirname(__file__), 'tests', 'McuSublayout.kicad_pcb')),
            'U2')

        # test with target flipped and sublayout not
        self.check_transform_equality(
            pcbnew.LoadBoard(os.path.join(os.path.dirname(__file__), 'tests', 'McuSublayout.kicad_pcb')),
            pcbnew.LoadBoard(os.path.join(os.path.dirname(__file__), 'tests', 'McuSublayout_FlipRot.kicad_pcb')),
            'U2')

        # test with target flipped and sublayout flipped
        self.check_transform_equality(
            pcbnew.LoadBoard(os.path.join(os.path.dirname(__file__), 'tests', 'McuSublayout_FlipRot.kicad_pcb')),
            pcbnew.LoadBoard(os.path.join(os.path.dirname(__file__), 'tests', 'McuSublayout_FlipRot.kicad_pcb')),
            'U2')

    def test_replicate(self):
        board = pcbnew.LoadBoard(os.path.join(os.path.dirname(__file__), 'tests', 'BareBlinkyComplete.kicad_pcb'))  # type: pcbnew.BOARD

        sublayout_board = pcbnew.LoadBoard(os.path.join(os.path.dirname(__file__), 'tests', 'McuSublayout.kicad_pcb'))  # type: pcbnew.BOARD
        anchor = board.FindFootprintByReference('U2')
        sublayout = ReplicateSublayout(sublayout_board, board, anchor, BoardUtils.footprint_path(anchor)[:-1])
        self.assertIsNone(sublayout.target_lca())
        result = sublayout.replicate()
        self.assertFalse(result.get_error_strs())

        sublayout_board = pcbnew.LoadBoard(os.path.join(os.path.dirname(__file__), 'tests', 'UsbSublayout.kicad_pcb'))
        anchor = board.FindFootprintByReference('J1')
        sublayout = ReplicateSublayout(sublayout_board, board, anchor, BoardUtils.footprint_path(anchor)[:-1])
        self.assertIsNone(sublayout.target_lca())
        result = sublayout.replicate()
        self.assertFalse(result.get_error_strs())

        board.Save('test_output_replicate.kicad_pcb')

    def test_replicate_grouped(self):
        # example that replicates into a target group (instead of creating a new group)
        board = pcbnew.LoadBoard(os.path.join(os.path.dirname(__file__), 'tests', 'TestBlinkyComplete_GroupedUsb.kicad_pcb'))  # type: pcbnew.BOARD

        sublayout_board = pcbnew.LoadBoard(os.path.join(os.path.dirname(__file__), 'tests', 'UsbSublayout.kicad_pcb'))  # type: pcbnew.BOARD
        anchor = board.FindFootprintByReference('J1')
        sublayout = ReplicateSublayout(sublayout_board, board, anchor, BoardUtils.footprint_path(anchor)[:-1])
        self.assertIsNotNone(sublayout.target_lca())
        sublayout.purge_lca()
        result = sublayout.replicate()
        self.assertFalse(result.get_error_strs())

        board.Save('test_output_replicate_grouped.kicad_pcb')

    def test_replicate_footprint_error(self):
        board = pcbnew.LoadBoard(os.path.join(os.path.dirname(__file__), 'tests', 'TestBlinkyComplete_GroupedUsb.kicad_pcb'))  # type: pcbnew.BOARD

        sublayout_board = pcbnew.LoadBoard(os.path.join(os.path.dirname(__file__), 'tests', 'McuSublayout_ExtraFootprint.kicad_pcb'))  # type: pcbnew.BOARD
        anchor = board.FindFootprintByReference('U2')
        sublayout = ReplicateSublayout(sublayout_board, board, anchor, BoardUtils.footprint_path(anchor)[:-1])
        result = sublayout.replicate()
        self.assertEqual(len(result.source_footprints_unused), 1)
        self.assertEqual(len(result.get_error_strs()), 1)
        self.assertIn('C9001', result.get_error_strs()[0])

        sublayout_board = pcbnew.LoadBoard(os.path.join(os.path.dirname(__file__), 'tests', 'McuSublayout_MissingFootprint.kicad_pcb'))
        anchor = board.FindFootprintByReference('U2')
        sublayout = ReplicateSublayout(sublayout_board, board, anchor, BoardUtils.footprint_path(anchor)[:-1])
        result = sublayout.replicate()
        self.assertEqual(len(result.target_footprints_missing_source), 2)
        self.assertEqual(len(result.get_error_strs()), 1)
        self.assertIn('C3', result.get_error_strs()[0])
        self.assertIn('C6', result.get_error_strs()[0])

    def test_replicate_net_error(self):
        board = pcbnew.LoadBoard(os.path.join(os.path.dirname(__file__), 'tests', 'TestBlinkyComplete_GroupedUsb.kicad_pcb'))  # type: pcbnew.BOARD

        sublayout_board = pcbnew.LoadBoard(os.path.join(os.path.dirname(__file__), 'tests', 'McuSublayout_BadNet.kicad_pcb'))  # type: pcbnew.BOARD
        anchor = board.FindFootprintByReference('U2')
        sublayout = ReplicateSublayout(sublayout_board, board, anchor, BoardUtils.footprint_path(anchor)[:-1])
        result = sublayout.replicate()
        self.assertEqual(len(result.tracks_missing_netcode), 1)
        self.assertEqual(len(result.get_error_strs()), 1)
        self.assertIn('bad_new_net', result.get_error_strs()[0])

        sublayout_board = pcbnew.LoadBoard(os.path.join(os.path.dirname(__file__), 'tests', 'McuSublayout_BadZone.kicad_pcb'))
        anchor = board.FindFootprintByReference('U2')
        sublayout = ReplicateSublayout(sublayout_board, board, anchor, BoardUtils.footprint_path(anchor)[:-1])
        result = sublayout.replicate()
        self.assertEqual(len(result.zones_missing_netcode), 1)
        self.assertEqual(len(result.get_error_strs()), 1)
        self.assertIn('bad_zone', result.get_error_strs()[0])
