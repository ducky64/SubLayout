from typing import Tuple, cast, Optional, List, Hashable, Any, Iterable, Union, TYPE_CHECKING

import pcbnew

if TYPE_CHECKING:
    from .save_sublayout import FilterResult


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
    def highest_covering_groups(groups: List['GroupWrapper']) -> List['GroupWrapper']:
        """Returns the minimal set of groups at the highest level of hierarchy that cover all input groups."""
        output_groups: List['GroupWrapper'] = []
        for group in groups:
            if group in output_groups:  # deduplicate
                continue
            test_group = group
            while test_group._group is not None:
                test_group = GroupWrapper(test_group._group.GetParentGroup())
                if test_group in groups:  # is child of a higher element in the group
                    break
            if test_group._group is None:  # made it to root
                output_groups.append(group)
        return output_groups

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
        elif isinstance(elt, pcbnew.PCB_GROUP):
            return GroupWrapper(elt)
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
            self._key: Optional[frozenset[Any]] = frozenset([self._elt_to_key(item) for item in self._group.GetItems()])
        else:
            self._key = None

    def recursive_items(self):
        """Recursively yields all items in the group and its subgroups"""
        if self._group is None:
            return
        for item in self._group.GetItems():
            if isinstance(item, pcbnew.PCB_GROUP):
                yield from GroupWrapper(item).recursive_items()
            else:
                yield item

    def sorted_footprint_refs(self) -> Tuple[str, ...]:
        """Returns the sorted footprint references in the group"""
        if self._group is None:
            return ()
        footprints = [elt for elt in self._group.GetItems() if isinstance(elt, pcbnew.FOOTPRINT)]
        return tuple(sorted([fp.GetReference() for fp in footprints]))

    def __repr__(self) -> str:
        if self._group is None:
            return f"GroupWrapper(None)"

        sorted_refs = self.sorted_footprint_refs()
        item_count = len(self._group.GetItems())
        if self._group.GetName():
            return f"GroupWrapper({self._group.GetName()}: {item_count}; {', '.join(sorted_refs)})"
        else:
            return f"GroupWrapper({item_count}; {', '.join(sorted_refs)})"


GroupLike = Union[pcbnew.PCB_GROUP, pcbnew.BOARD, 'FilterResult']

def group_like_items(grouplike: GroupLike) -> Iterable[pcbnew.BOARD_ITEM]:
    """Given a grouplike, returns the items in the group.
    Straightforward for groups, does some computation for boards and hierarchy selection results"""
    from .save_sublayout import FilterResult
    
    if isinstance(grouplike, pcbnew.PCB_GROUP):
        return grouplike.GetItems()
    elif isinstance(grouplike, pcbnew.BOARD):
        groups = [group for group in grouplike.Groups()]  # type: List[pcbnew.PCB_GROUP]
        footprints = [item for item in grouplike.GetFootprints()]  # type: List[pcbnew.FOOTPRINT]
        tracks = [item for item in grouplike.GetTracks()]  # type: List[pcbnew.PCB_TRACK]
        zones = [grouplike.GetArea(i) for i in range(grouplike.GetAreaCount())]  # type: List[pcbnew.ZONE]
        return [item for item in groups + footprints + tracks + zones
                if item.GetParentGroup() is None]
    elif isinstance(grouplike, FilterResult):
        if len(grouplike.groups) == 1 and len(grouplike.ungrouped_elts) == 0:
            return group_like_items(grouplike.groups[0])  # single group, flatten out
        else:
            return grouplike.groups + grouplike.ungrouped_elts  # return groups and elts
    else:
        raise TypeError(f"unknown grouplike type {grouplike}")

def group_like_recursive_footprints(grouplike: GroupLike) -> Iterable[pcbnew.FOOTPRINT]:
    """Given a grouplike, returns the footprints in the group, recursively."""
    for item in group_like_items(grouplike):
        if isinstance(item, pcbnew.FOOTPRINT):
            yield item
        elif isinstance(item, pcbnew.PCB_GROUP):
            yield from group_like_recursive_footprints(item)
