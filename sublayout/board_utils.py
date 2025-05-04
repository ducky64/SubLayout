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


class GroupWrapper():
    """A wrapper around a PCB group that is hashable and can be used as a dict key / set element"""
    def __hash__(self):
        return hash(self._sorted_refs)

    def __eq__(self, other):
        if not isinstance(other, GroupWrapper):
            return NotImplemented
        return self._sorted_refs == other._sorted_refs

    def __init__(self, group: pcbnew.PCB_GROUP) -> None:
        self._group = group
        footprints = [elt for elt in self._group.GetItems() if isinstance(elt, pcbnew.FOOTPRINT)]
        self._sorted_refs = tuple(sorted([fp.GetReference() for fp in footprints]))

    def __repr__(self) -> str:
        name = self._group.GetName()
        if name:
            return f"GroupWrapper({name}: {', '.join(self._sorted_refs)})"
        else:
            return f"GroupWrapper({', '.join(self._sorted_refs)})"
