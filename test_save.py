import os
import unittest
import pcbnew

from board_utils import BoardUtils


class SaveTestCase(unittest.TestCase):
  def test_save(self):
    board = pcbnew.LoadBoard(os.path.join(os.path.dirname(__file__), 'tests', 'TestBlinkyComplete.kicad_pcb'))
    sublayout_board = BoardUtils.duplicate_board(board)
    sublayout_board.Save('test_output_saved.kicad_pcb')
    print(sublayout_board)
