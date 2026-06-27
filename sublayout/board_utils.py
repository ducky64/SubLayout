from typing import Tuple, cast, Optional, List, Hashable, Any, Iterable, Union, TYPE_CHECKING

import pcbnew

if TYPE_CHECKING:
    from .save_sublayout import FilterResult

try:
    from pcbnew import EDA_GROUP
    PcbGroupType = EDA_GROUP
    IsKicad10 = True

except ImportError:
    PcbGroupType = pcbnew.PCB_GROUP
    IsKicad10 = False


def iterable_to_py(iterable: Any) -> List[Any]:
    """Newer KiCad versions do not properly wrap some iterator types, this works around it."""
    try:
        return iter(iterable)
    except TypeError:
        output = []
        while True:
            item = iterable.next()
            if item is None:
              break
            output.append(item)
        return output
        
def group_parent(group: Any) -> Any:  # pcbnew.EDA_GROUP in newer KiCad versions
    """Newer KiCad versions change the parent group API"""
    try:
        return group.GetParentGroup()
    except AttributeError:
        return group.AsEdaItem().GetParentGroup()
        

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
                group = GroupWrapper(group._board, group_parent(group._group))
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
                test_group = GroupWrapper(test_group._board, group_parent(test_group._group))
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
            return (elt.GetReference(), x, y)
        elif isinstance(elt, pcbnew.PCB_TRACK):
            sx, sy = elt.GetStart()
            ex, ey = elt.GetEnd()
            return (sx, sy, ex, ey)
        elif isinstance(elt, pcbnew.ZONE):
            return tuple((elt.GetCornerPosition(i)[0], elt.GetCornerPosition(i)[1]) for i in range(elt.GetNumCorners()))
        elif isinstance(elt, PcbGroupType):
            return GroupWrapper(elt.GetBoard(), elt)
        else:
            return None

    def __hash__(self):
        return hash(self._key)

    def __eq__(self, other):
        if not isinstance(other, GroupWrapper):
            return NotImplemented
        return (self._group is None) == (other._group is None) and self._key == other._key

    @staticmethod
    def empty() -> "GroupWrapper":
      return GroupWrapper(None, None)

    def __init__(self, board: Optional[pcbnew.BOARD], group: Optional[PcbGroupType]) -> None:
        self._board = board
        assert isinstance(board, pcbnew.BOARD) or board is None
        self._group = group
        if self._group is not None:
            self._key: Optional[frozenset[Any]] = frozenset([self._elt_to_key(item) for item in self.items()])
        else:
            self._key = None

    def items(self) -> Iterable[pcbnew.BOARD_ITEM]:
        """Yields all items in the group (non-recursive)"""
        if self._group is None:
            return []
        member_ids = self._group.GetGroupMemberIds()
        return [self._board.ResolveItem(member_id).Cast() for member_id in member_ids]
        # return self._group.GetItems()

    def recursive_items(self):
        """Recursively yields all items in the group and its subgroups"""
        if self._group is None:
            return
        for item in self.items():
            if isinstance(item, PcbGroupType):
                yield from GroupWrapper(self._board, item).recursive_items()
            else:
                yield item

    def sorted_footprint_refs(self) -> Tuple[str, ...]:
        """Returns the sorted footprint references in the group"""
        if self._group is None:
            return ()
        footprints = [elt for elt in self.items() if isinstance(elt, pcbnew.FOOTPRINT)]
        return tuple(sorted([fp.GetReference() for fp in footprints]))

    def __repr__(self) -> str:
        if self._group is None:
            return f"GroupWrapper(None)"

        sorted_refs = self.sorted_footprint_refs()
        item_count = len(self.items())
        if self._group.GetName():
            return f"GroupWrapper({self._group.GetName()}: {item_count}; {', '.join(sorted_refs)})"
        else:
            return f"GroupWrapper({item_count} items: {', '.join(sorted_refs)})"


GroupLike = Union[PcbGroupType, pcbnew.BOARD, 'FilterResult']

def group_like_items(board: pcbnew.BOARD, grouplike: GroupLike) -> Iterable[pcbnew.BOARD_ITEM]:
    """Given a grouplike, returns the items in the group.
    Straightforward for groups, does some computation for boards and hierarchy selection results"""
    from .save_sublayout import FilterResult

    if isinstance(grouplike, PcbGroupType):
        return GroupWrapper(board, grouplike).items()
    elif isinstance(grouplike, pcbnew.BOARD):
        groups = [group for group in grouplike.Groups()]  # type: List[PcbGroupType]
        footprints = [item for item in grouplike.GetFootprints()]  # type: List[pcbnew.FOOTPRINT]
        tracks = [item for item in grouplike.GetTracks()]  # type: List[pcbnew.PCB_TRACK]
        zones = [grouplike.GetArea(i) for i in range(grouplike.GetAreaCount())]  # type: List[pcbnew.ZONE]
        return [item for item in groups + footprints + tracks + zones
                if item.GetParentGroup() is None]
    elif isinstance(grouplike, FilterResult):
        if len(grouplike.groups) == 1 and len(grouplike.ungrouped_elts) == 0:
            return group_like_items(board, grouplike.groups[0])  # single group, flatten out
        else:
            return grouplike.groups + grouplike.ungrouped_elts  # return groups and elts
    else:
        raise TypeError(f"unknown grouplike type {grouplike}")

def group_like_recursive_footprints(board: pcbnew.BOARD, grouplike: GroupLike) -> Iterable[pcbnew.FOOTPRINT]:
    """Given a grouplike, returns the footprints in the group, recursively."""
    for item in group_like_items(board, grouplike):
        if isinstance(item, pcbnew.FOOTPRINT):
            yield item
        elif isinstance(item, PcbGroupType):
            yield from group_like_recursive_footprints(board, item)
