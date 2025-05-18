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

    def check_transform_equality(self, src_board: pcbnew.BOARD, target_board: pcbnew.BOARD, target_anchor_ref: str):
        anchor = target_board.FindFootprintByReference(target_anchor_ref)
        correspondence = FootprintCorrespondence.by_tstamp(src_board, target_board, BoardUtils.footprint_path(anchor)[:-1])
        transform = PositionTransform(src_board.FindFootprintByReference(target_anchor_ref),
                                      target_board.FindFootprintByReference(target_anchor_ref))
        for src_footprint, target_footprint in correspondence.mapped_footprints:
            self.assertEqual(transform.transform(src_footprint.GetPosition()), target_footprint.GetPosition())
            self.assertEqual(transform.transform_orientation(src_footprint.GetOrientation().AsRadians(), src_footprint.GetSide() != 0), target_footprint.GetOrientation().AsRadians())
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
