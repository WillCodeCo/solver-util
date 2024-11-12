import typing
from titan.solver_util.spot_models import (
    ActionSequence
)
from titan.solver_util.solution_tree.types import (
    SolvedSpot,
    SolutionTreeNodeIndex,
    SolutionTreeNode,
    SolutionTree
)


class SolutionTreeBuilderException(Exception):
    pass



class SolutionTreeBuilder:
    """SolutionTreeBuilder facilitates the creation of SolutionTree objects"""

    __slots__ = (   '_nodes',
                    '_solution_tree_node_index',
                    '_root_node_id' )

    def __init__(self):
        self._nodes = {}
        self._solution_tree_node_index = SolutionTreeNodeIndex()
        self._root_node_id = None

    def get_node(self, node_id: int) -> SolutionTreeNode:
        """Resolve a node_id into a SolutionTreeNode object

        Args:
            node_id: The node_id value to resolve

        Returns:
            The SolutionTreeNode object

        Raises:
            SolutionTreeBuilderException: If the specified node_id is not yet in the tree
        """
        try:
            return self._nodes[node_id]
        except KeyError:
            raise SolutionTreeBuilderException(f"Failed to resolve node with node_id {node_id}")

    def root_node(self):
        """Return the root SolutionTreeNode object

        Returns:
            The root SolutionTreeNode object

        Raises:
            SolutionTreeBuilderException: If the specified node_id is not yet in the tree
        """
        return self.get_node(self._root_node_id)

    def create_root_node(self, node_id: int, solved_spot: SolvedSpot):
        """Create the root node of the tree for the specified solved spot

        Args:
            node_id: Integer node identifier for this node to add
            solved_spot: SolvedSpot object representing the solver result for this spot
        """
        node = SolutionTreeNode.create_root_node(   action_sequence=ActionSequence.create_empty(),
                                                    solved_spot=solved_spot  )
        self._nodes[node_id] = node
        self._solution_tree_node_index.add_node(action_sequence=ActionSequence.create_empty(),
                                                node=node)
        return node

    def create_child_node(self, node_id: int, parent_node_id: int, action_string: str,
                                                                    solved_spot: SolvedSpot):
        """Add a new node representing a solved spot as a child of the specified parent

        Args:
            node_id: Integer node identifier for this node to add
            parent_node_id: Integer node identifier for the parent of this node
            action_string: The action_string representing the action that was taken from the parent node
            solved_spot: SolvedSpot object representing the solver result for this spot

        Raises:
            SolutionTreeBuilderException: If the parent node cannot be resolved
        """
        node = self.get_node(parent_node_id).create_child_node(action_string, solved_spot)
        self._nodes[node_id] = node
        self._solution_tree_node_index.add_node(action_sequence=node.action_sequence(),
                                                node=node)
        return node

    def build_solution_tree(self) -> SolutionTree:
        """Build the SolutionTree from the nodes that have been added

        Returns:
            The SolutionTreeNode object

        Raises:
            SolutionTreeBuilderException: If the SolutionTree could not be built
        """

        return SolutionTree(self._solution_tree_node_index)

