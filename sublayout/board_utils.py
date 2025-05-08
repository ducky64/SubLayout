from typing import Tuple, cast, Optional, List, Hashable, Any

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
    """A wrapper around a PCB group that is hashable and can be used as a dict key / set element.
    Supports None as a group."""
    @staticmethod
    def lowest_common_ancestor(groups: List['GroupWrapper']) -> Optional['GroupWrapper']:
        """Returns the lowest common ancestor (deepest group) of the groups, or None if there is none
        (LCA is the board)."""
        # for each group, get the path to the root, including self but not root
        group_paths: List[List[GroupWrapper]] = []
        for group in groups:
            if group._group is None:
                return None
            group_path = []
            while group._group is not None:
                group_path.append(group)
                group = GroupWrapper(group._group.GetParentGroup())
            group_paths.append(list(reversed(group_path)))
        # return the deepest group that is common to all paths
        i = 0  # base case
        for i in range(min(len(path) for path in group_paths)):
            group = group_paths[0][i]
            if all(path[i] == group for path in group_paths):
                continue
            else:
                if i == 0:  # at the root, no common ancestor
                    return None
                else:
                    return group_paths[0][i - 1]
        return group_paths[0][i]  # iterated through all groups, return the last one

    @staticmethod
    def _elt_to_key(elt: pcbnew.BOARD_ITEM) -> Optional[Hashable]:
        """Creates a hashable key for some types of BOARD_ITEMs"""
        if isinstance(elt, pcbnew.FOOTPRINT):
            x, y = elt.GetPosition()
            return (elt.GetReference(), x, y, elt.GetOrientationDegrees())
        elif isinstance(elt, pcbnew.PCB_TRACK):
            sx, sy = elt.GetStart()
            ex, ey = elt.GetEnd()
            return (sx, sy, ex, ey, elt.GetWidth())
        elif isinstance(elt, pcbnew.ZONE):
            return tuple((elt.GetCornerPosition(i)[0], elt.GetCornerPosition(i)[1]) for i in range(elt.GetNumCorners()))
        else:
            return None

    def __hash__(self):
        return hash(self._key)

    def __eq__(self, other):
        if not isinstance(other, GroupWrapper):
            return NotImplemented
        return (self._group is None) == (other._group is None) and self._key == other._key

    def __init__(self, group: Optional[pcbnew.PCB_GROUP]) -> None:
        self._group = group
        if self._group is not None:
            self._key = frozenset([self._elt_to_key(item) for item in self._group.GetItems()])
        else:
            self._key = None

    def __repr__(self) -> str:
        if self._group is None:
            return f"GroupWrapper(None)"

        footprints = [elt for elt in self._group.GetItems() if isinstance(elt, pcbnew.FOOTPRINT)]
        sorted_refs = tuple(sorted([fp.GetReference() for fp in footprints]))
        item_count = len(self._group.GetItems())
        if self._group.GetName():
            return f"GroupWrapper({self._group.GetName()}: {item_count}; {', '.join(sorted_refs)})"
        else:
            return f"GroupWrapper({item_count}; {', '.join(sorted_refs)})"
