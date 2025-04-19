import os
import unittest

import pcbnew

from hierarchy_namer import HierarchyNamer


class ReplicateTestCase(unittest.TestCase):
    def test_replicate(self):
        board = pcbnew.LoadBoard(os.path.join(os.path.dirname(__file__), 'tests', 'BareBlinkyComplete.kicad_pcb'))  # type: pcbnew.BOARD
        sublayout = pcbnew.LoadBoard(os.path.join(os.path.dirname(__file__), 'tests', 'McuSublayout.kicad_pcb'))  # type: pcbnew.BOARD

