import os
from typing import Tuple, cast

import pcbnew


class BoardUtils():
    @classmethod
    def footprint_path(cls, footprint: pcbnew.FOOTPRINT) -> Tuple[str, ...]:
        fp_path = footprint.GetPath()  # type: pcbnew.KIID_PATH
        return tuple(cast(str, fp_path.AsString()).strip('/').split('/'))

    @classmethod
    def footprint_path_startswith(cls, footprint: pcbnew.FOOTPRINT, path_prefix: Tuple[str, ...]) -> bool:
        """Returns true if the footprint path starts with the given prefix (is part of the path_prefix hierarchy)"""
        fp_path = cls.footprint_path(footprint)
        return fp_path[:len(path_prefix)] == path_prefix
