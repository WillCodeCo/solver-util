import typing

class BlobTreeException(Exception):
    pass

class BlobTreeNode:
    """BlobTreeNode is useful for when we need to represent hierarchies of 'blobs'"""

    __slots__ = (   '_node_id',
                    '_parent_node_id',
                    '_child_id',
                    '_blob_bytes'  )

    def __init__(self, node_id: int, parent_node_id: int, child_id: str, blob_bytes: bytes):
        self._node_id = node_id
        self._parent_node_id = parent_node_id
        self._child_id = child_id
        self._blob_bytes = blob_bytes

    def node_id(self):
        return self._node_id

    def parent_node_id(self):
        return self._parent_node_id

    def child_id(self):
        return self._child_id

    def blob_bytes(self):
        return self._blob_bytes

    def __eq__(self, other):
        return (    other.node_id() == self.node_id() and
                    other.parent_node_id() == self.parent_node_id() and
                    other.child_id() == self.child_id() and
                    other.blob_bytes() == self.blob_bytes()  )


class BlobTree:
    """
    Principal data structure for navigating blob tree hierarchies
    """

    ROOT_NODE_ID = 0
    
    __slots__ = (   '_nodes',
                    '_node_children_lookup' )


    def __init__(self):
        self._nodes = {}
        self._node_children_lookup = {}


    def get_node(self, node_id: int):
        """Resolve a node_id into a BlobTreeNode object

        Args:
            node_id: The node_id value to resolve

        Returns:
            The BlobTreeNode object

        Raises:
            BlobTreeException: If the specified node_id is not yet in the tree
        """
        try:
            return self._nodes[node_id]
        except KeyError:
            raise BlobTreeException(f"Failed to resolve node with node_id {node_id}")


    def root_node(self):
        """Return the root BlobTreeNode object

        Returns:
            The root BlobTreeNode object

        Raises:
            BlobTreeException: If the specified node_id is not yet in the tree
        """
        return self.get_node(self.ROOT_NODE_ID)


    def add_node(self, node: BlobTreeNode):
        """Add a node to the tree.

        Args:
            node: BlobTreeNode object to add to the tree.
        """
        self._nodes[node.node_id()] = node
        # record the parent/child relationship
        if node.node_id() != node.parent_node_id():
            try:
                self._node_children_lookup[node.parent_node_id()][node.child_id()] = node.node_id()
            except KeyError:
                self._node_children_lookup[node.parent_node_id()] = {node.child_id(): node.node_id()}




    def gen_child_nodes(self, node_id: int):
        """Generate all BlobTreeNode objects which are a direct child of the specified node

        Args:
            node_id: The node_id of the node to start at

        Returns:
            A generator of BlobTreeNode

        Raises:
            BlobTreeException: If any node cannot be resolved
        """
        for node_id in self._node_children_lookup.get(node_id, {}).values():
            yield self.get_node(node_id)



    def gen_nodes_in_bfs_traversal(self, node_id: int):
        """Generate all nodes during a full BFS traversal starting from the specified node

        Args:
            node_id: The node_id of the node to start at

        Returns:
            A generator of BlobTreeNode

        Raises:
            BlobTreeException: If any node cannot be resolved
        """
        to_visit = [self.get_node(node_id)]
        while to_visit:
            node = to_visit.pop(0)
            to_visit.extend(list(self.gen_child_nodes(node.node_id())))
            yield node



    def __eq__(self, other):
        if type(self) != type(other):
            return False
        bfs_self = tuple(self.gen_nodes_in_bfs_traversal(self.ROOT_NODE_ID))
        bfs_other = tuple(other.gen_nodes_in_bfs_traversal(self.ROOT_NODE_ID))
        return bfs_self == bfs_other

