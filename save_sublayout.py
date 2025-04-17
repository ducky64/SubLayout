import pcbnew

from board_utils import BoardUtils


class SaveSublayout():
    """Function and utilities to save a sub-layout given a hierarchy path prefix.
    Does not affect the original board obect."""
    def __init__(self, board: pcbnew.BOARD, path_prefix: tuple[str, ...]) -> None:
        self._board = BoardUtils.duplicate_board(board)  # create working copy

    def save(self) -> pcbnew.BOARD:
        """Saves the sub-layout to a new board file and returns the new board object."""
        pass
