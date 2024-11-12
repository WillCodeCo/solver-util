from __future__ import annotations
import typing
import numpy as np
from numpy import typing as npt
from titan.solver_util.spot_models import (
    ActionSequence
)

class StrategyOption:

    def action_string(self):
        raise NotImplementedError

    def __repr__(self):
        return f"{self.__class__.__name__}()"

    def __eq__(self, other):
        return (type(other) == type(self))

    def __hash__(self):
        return hash(type(self))

class CheckOption(StrategyOption):
    def __str__(self):
        return "Check"

    def action_string(self):
        return "x"

class CallOption(StrategyOption):
    def __str__(self):
        return "Call"

    def action_string(self):
        return "c"

class FoldOption(StrategyOption):
    def __str__(self):
        return "Fold"

    def action_string(self):
        return "f"

class RaiseOption(StrategyOption):

    __slots__ = ('_amount', '_pot_size_ratio_bps')

    def __init__(self, amount: int, pot_size_ratio_bps: int):
        self._amount = amount
        self._pot_size_ratio_bps = pot_size_ratio_bps

    def amount(self):
        return self._amount

    def pot_size_ratio_bps(self):
        return self._pot_size_ratio_bps

    def action_string(self):
        return f"r{self.amount()}"

    def __str__(self):
        return f"Raise {self.amount()} ({self.pot_size_ratio_bps()/100:<.2f} %)"

    def __repr__(self):
        return f"{self.__class__.__name__}({self.amount()}, {self.pot_size_ratio_bps()})"

    def __eq__(self, other):
        return (    type(other) == type(self) and
                    other.amount() == self.amount()  and
                    other.pot_size_ratio_bps() == self.pot_size_ratio_bps()  )

    def __hash__(self):
        return hash((type(self), self.amount(), self.pot_size_ratio_bps()))




class RangeMatrix:

    __slots__ = ('_values', )

    def __init__(self, values: npt.NDArray[np.int32]):
        self._values = values

    def shape(self):
        return self._values.shape

    def values(self):
        return self._values

    def lookup(self, index: int):
        return self._values[index]

    def __eq__(self, other):
        return np.array_equal(self.values(), other.values())

    @classmethod
    def create_empty(cls):
        return cls(np.zeros(shape=(0,)))



class SolvedSpot:
    """SolvedSpot represents the solver result or solution for a particular spot in
    a street of a poker game tree"""

    __slots__ = (   '_strategy_options',
                    '_strategy_matrix',
                    '_ev_matrix'  )

    def __init__(self, strategy_options: typing.Tuple[StrategyOption],
                        strategy_matrix: RangeMatrix,
                        ev_matrix: RangeMatrix):
        self._strategy_options = strategy_options
        self._strategy_matrix = strategy_matrix
        self._ev_matrix = ev_matrix

    def strategy_options(self):
        return self._strategy_options

    def strategy_matrix(self):
        return self._strategy_matrix

    def ev_matrix(self):
        return self._ev_matrix

    def is_leaf_spot(self):
        """A leaf spot is any spot where further actions are not possible, because
        the street has been satisfied or the hand has finished. Any such leaf spot will not 
        have any strategy_options()

        Returns:
            True if the current Spot has no further strategy options, otherwise False
        """
        return self.strategy_options() == ()

    def __eq__(self, other):
        if type(self) != type(other):
            return False
        return (    (self.strategy_options() == other.strategy_options()) and
                    (self.strategy_matrix() == other.strategy_matrix()) and
                    (self.ev_matrix() == other.ev_matrix())  )


class SolutionTreeException(Exception):
    pass

class SolutionTreeNode:
    
    __slots__ = (   '_parent',
                    '_action_sequence',
                    '_solved_spot',
                    '_children'  )

    def __init__(self, parent: SolutionTreeNode, action_sequence: ActionSequence,
                                                        solved_spot: SolvedSpot):
        self._parent = parent
        self._action_sequence = action_sequence
        self._solved_spot = solved_spot
        self._children = {}

    def parent(self):
        if not self._parent:
            raise SolutionTreeException(f"Root node has no parent !")
        return self._parent

    def action_sequence(self):
        return self._action_sequence

    def depth(self):
        return len(self.action_sequence())

    def solved_spot(self):
        return self._solved_spot

    def strategy_options(self):
        return self._solved_spot.strategy_options()

    def strategy_matrix(self):
        return self._solved_spot.strategy_matrix()

    def ev_matrix(self):
        return self._solved_spot.ev_matrix()

    def is_leaf_spot(self):
        return self._solved_spot.is_leaf_spot()

    def children(self):
        return self._children.values()

    def has_children(self):
        return len(self._children) > 0

    def child_action_strings(self):
        return set(self._children.keys())

    def has_child(self, action_string: str):
        """Return whether a child node exists for the specified action_string

        Args:
            action_string: The string representing the action

        Returns:
            True if it exists, False otherwise
        """
        return action_string in self._children

    def get_child(self, action_string: str):
        """Return the child node for the specified action.

        Args:
            action_string: The string representing the action

        Returns:
            A SolutionTreeNode object

        Raises:
            SolutionTreeException: If the node cannot be resolved
        """
        try:
            return self._children[action_string]
        except KeyError:
            raise SolutionTreeException((   f"Failed to find a child node of `{self.action_sequence()}` " +
                                            f"with action_string `{action_string}`"  ))

    def add_child(self, action_string: str, node: SolutionTreeNode):
        if action_string in self._children:
            raise SolutionTreeException(f"Already a child node for action_string `{action_string}`: `{self.child_action_strings()}`")
        self._children[action_string] = node

    def create_child_node(self, action_string: str, solved_spot: SolvedSpot):
        child_action_sequence = self.action_sequence() + ActionSequence.create_from_string(action_string)
        child_node = SolutionTreeNode(self, child_action_sequence, solved_spot)
        self.add_child(action_string, child_node)
        return child_node

    def gen_descendants_on_path(self, action_sequence: ActionSequence) -> typing.Iterable[SolutionTreeNode]:
        """Traverse the descendants of this node according to the specified path of actions in action_sequence
        
        Args:
            action_sequence: ActionSequence isdescribing the path to the descendant nodes

        Returns:
            A generator of SolutionTreeNode

        Raises:
            SolutionTreeException: If any node cannot be resolved
        """
        cur_node = self
        for action in action_sequence:
            cur_node = cur_node.get_child(str(action))
            yield cur_node

    def gen_nodes_in_bfs_traversal(self, max_depth = None) -> typing.Iterable[SolutionTreeNode]:
        """Perform a Breadth-first traversal from the current node, yielding all nodes that are encountered
        along the way.

        Args:
            max_depth: An integer limit on how deep to traverse

        Returns:
            A generator of SolutionTreeNode
        """
        to_visit = [self]
        while to_visit:
            cur_node = to_visit.pop(0)
            if (max_depth is None) or (cur_node.depth() < max_depth):
                for child_node in cur_node.children():
                    to_visit.append(child_node)
            yield cur_node

    @classmethod
    def create_root_node(cls, action_sequence: ActionSequence, solved_spot: SolvedSpot):
        return cls( parent=None,
                    action_sequence=action_sequence,
                    solved_spot=solved_spot )


class SolutionTreeNodeIndex:

    __slots__ = ('_node_index', )

    def __init__(self):
        self._node_index = {}

    def add_node(self, action_sequence: ActionSequence, node: SolutionTreeNode):
        self._node_index[action_sequence] = node

    def get_node(self, action_sequence: ActionSequence):
        try:
            return self._node_index[action_sequence]
        except KeyError:
            raise SolutionTreeException(f"Failed to resolve node from action_sequence {action_sequence}")

    def has_node(self, action_sequence: ActionSequence):
        return action_sequence in self._node_index

    def gen_leaf_nodes(self) -> typing.Iterable[SolutionTreeNode]:
        yield from (node for node in self._node_index.values() if node.is_leaf_spot())

    def size(self):
        return len(self._node_index)



class SolutionTree:
    """
    Principal data structure for navigating the results of a poker solve.
    """

    __slots__ = ('_solution_tree_node_index', )

    def __init__(self, solution_tree_node_index: SolutionTreeNodeIndex):
        self._solution_tree_node_index = solution_tree_node_index

    def node_count(self):
        return self._solution_tree_node_index.size()

    def get_node(self, action_sequence: ActionSequence) -> SolutionTreeNode:
        """Resolve an action_sequence into a SolutionTreeNode object

        Args:
            action_sequence: ActionSequence is used as a path to the node to return

        Returns:
            The SolutionTreeNode object

        Raises:
            SolutionTreeException: If the specified node cannot be found
        """
        if type(action_sequence) != ActionSequence:
            raise SolutionTreeException(f"action_sequence has incorrect type `{type(action_sequence)}`")
        return self._solution_tree_node_index.get_node(action_sequence)


    def has_node(self, action_sequence: ActionSequence) -> bool:
        """Return whether a node exists for the specified action_sequence

        Args:
            action_sequence: ActionSequence is used as a path to the node of interest

        Returns:
            True if the node exists in the tree, False otherwise
        """
        if type(action_sequence) != ActionSequence:
            raise SolutionTreeException(f"action_sequence has incorrect type `{type(action_sequence)}`")
        return self._solution_tree_node_index.has_node(action_sequence)

    def root_node(self) -> SolutionTreeNode:
        """Return the root SolutionTreeNode object

        Returns:
            The root SolutionTreeNode object

        Raises:
            SolutionTreeException: If there is no root node available to return
        """
        return self.get_node(ActionSequence.create_empty())


    def gen_nodes_on_path(self, action_sequence: ActionSequence) -> typing.Iterable[SolutionTreeNode]:
        """Traverse the specified path of action_strings, yielding all nodes that are encountered
        along the way.

        It includes the root node at the beginning.
        
        Args:
            action_sequence: ActionSequence isdescribing the path

        Returns:
            A generator of SolutionTreeNode

        Raises:
            SolutionTreeException: If any node cannot be resolved
        """
        if type(action_sequence) != ActionSequence:
            raise SolutionTreeException(f"action_sequence has incorrect type `{type(action_sequence)}`")
        for prefix in action_sequence.gen_prefixes():
            yield self.get_node(prefix)

    def gen_nodes_in_bfs_traversal(self, max_depth = None) -> typing.Iterable[SolutionTreeNode]:
        """Perform a Breadth-first traversal from the root, yielding all nodes that are encountered
        along the way.

        Args:
            max_depth: An integer limit on how deep to traverse

        Returns:
            A generator of SolutionTreeNode
        """
        yield from self.root_node().gen_nodes_in_bfs_traversal(max_depth)

    def gen_leaf_nodes(self) -> typing.Iterable[SolutionTreeNode]:
        yield from self._solution_tree_node_index.gen_leaf_nodes()

    def __eq__(self, other):
        if type(self) != type(other):
            return False
        bfs_self = self.gen_nodes_in_bfs_traversal()
        bfs_other = other.gen_nodes_in_bfs_traversal()
        return all((    self_node.solved_spot() == other_node.solved_spot()
                            for self_node, other_node in zip(bfs_self, bfs_other)  ))
