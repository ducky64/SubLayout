import os
import unittest
import pcbnew


class SaveTestCase(unittest.TestCase):
  def test_save(self):
    board = pcbnew.LoadBoard(os.path.join(os.path.dirname(__file__),'tests', 'TestBlinkyComplete.kicad_pcb'))
    print(board)
