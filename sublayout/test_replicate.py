import os
import unittest

import pcbnew

from .board_utils import BoardUtils
from .replicate_sublayout import ReplicateSublayout, FootprintCorrespondence, PositionTransform


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

    def test_transforms_identity(self):
        board = pcbnew.LoadBoard(os.path.join(os.path.dirname(__file__), 'tests', 'McuSublayout.kicad_pcb'))  # type: pcbnew.BOARD
        sublayout_board = pcbnew.LoadBoard(os.path.join(os.path.dirname(__file__), 'tests', 'McuSublayout.kicad_pcb'))  # type: pcbnew.BOARD
        anchor = board.FindFootprintByReference('U2')
        correspondence = FootprintCorrespondence.by_tstamp(sublayout_board, board, BoardUtils.footprint_path(anchor)[:-1])
        transform = PositionTransform(sublayout_board.FindFootprintByReference('U2'), board.FindFootprintByReference('U2'))
        for src_footprint, target_footprint in correspondence.mapped_footprints:
            self.assertEqual(transform.transform(src_footprint.GetPosition()), target_footprint.GetPosition())
            self.assertEqual(transform.transform_orientation(src_footprint.GetOrientation().AsRadians()), target_footprint.GetOrientation().AsRadians())

    def test_transforms_rot(self):
        # test a sublayout that is moved and rotated
        board = pcbnew.LoadBoard(os.path.join(os.path.dirname(__file__), 'tests', 'McuSublayout.kicad_pcb'))  # type: pcbnew.BOARD
        sublayout_board = pcbnew.LoadBoard(os.path.join(os.path.dirname(__file__), 'tests', 'McuSublayout_Rot.kicad_pcb'))  # type: pcbnew.BOARD
        anchor = board.FindFootprintByReference('U2')
        correspondence = FootprintCorrespondence.by_tstamp(sublayout_board, board, BoardUtils.footprint_path(anchor)[:-1])
        transform = PositionTransform(sublayout_board.FindFootprintByReference('U2'), board.FindFootprintByReference('U2'))
        for src_footprint, target_footprint in correspondence.mapped_footprints:
            self.assertEqual(transform.transform(src_footprint.GetPosition()), target_footprint.GetPosition())
            self.assertEqual(transform.transform_orientation(src_footprint.GetOrientation().AsRadians()), target_footprint.GetOrientation().AsRadians())

    def test_transforms_flip_rot(self):
        # test a sublayout that is moved and rotated
        board = pcbnew.LoadBoard(os.path.join(os.path.dirname(__file__), 'tests', 'McuSublayout.kicad_pcb'))  # type: pcbnew.BOARD
        sublayout_board = pcbnew.LoadBoard(os.path.join(os.path.dirname(__file__), 'tests', 'McuSublayout_FlipRot.kicad_pcb'))  # type: pcbnew.BOARD
        anchor = board.FindFootprintByReference('U2')
        correspondence = FootprintCorrespondence.by_tstamp(sublayout_board, board, BoardUtils.footprint_path(anchor)[:-1])
        transform = PositionTransform(sublayout_board.FindFootprintByReference('U2'), board.FindFootprintByReference('U2'))
        for src_footprint, target_footprint in correspondence.mapped_footprints:
            self.assertEqual(transform.transform(src_footprint.GetPosition()), target_footprint.GetPosition())
            self.assertEqual(transform.transform_orientation(src_footprint.GetOrientation().AsRadians()), target_footprint.GetOrientation().AsRadians())


    # def test_replicate(self):
    #     board = pcbnew.LoadBoard(os.path.join(os.path.dirname(__file__), 'tests', 'BareBlinkyComplete.kicad_pcb'))  # type: pcbnew.BOARD
    #
    #     sublayout_board = pcbnew.LoadBoard(os.path.join(os.path.dirname(__file__), 'tests', 'McuSublayout.kicad_pcb'))  # type: pcbnew.BOARD
    #     anchor = board.FindFootprintByReference('U2')
    #     sublayout = ReplicateSublayout(sublayout_board, board, anchor, BoardUtils.footprint_path(anchor)[:-1])
    #     sublayout.replicate_footprints()
    #
    #     sublayout_board = pcbnew.LoadBoard(os.path.join(os.path.dirname(__file__), 'tests', 'UsbSublayout.kicad_pcb'))
    #     anchor = board.FindFootprintByReference('J1')
    #     sublayout = ReplicateSublayout(sublayout_board, board, anchor, BoardUtils.footprint_path(anchor)[:-1])
    #     sublayout.replicate_footprints()
    #     sublayout.replicate_tracks()
    #     sublayout.replicate_zones()
    #
    #     board.Save('../test_output_replicate.kicad_pcb')
