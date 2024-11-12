import random
import typing
from titan.solver_util.blob_tree import (
    BlobTree,
    BlobTreeNode
)


class RandomValueFactory:

    @classmethod
    def create_blob_bytes(cls):
        blob_size = random.randint(0, 1000)
        return random.randbytes(blob_size)

    @classmethod
    def create_child_id(cls):
        return f"random_child_{random.randint(0, 999999)}"

    @classmethod
    def create_blob_tree_node(cls, node_id: int,
                                    prev_nodes: typing.Iterable[BlobTreeNode]):
        if not prev_nodes:
            # root node
            return BlobTreeNode(node_id=node_id,
                                parent_node_id=0,
                                child_id='',
                                blob_bytes=cls.create_blob_bytes())
        else:
            # choose a parent !
            parent_node_id = random.choice(prev_nodes).node_id()
            return BlobTreeNode(node_id=node_id,
                                parent_node_id=parent_node_id,
                                child_id=cls.create_child_id(),
                                blob_bytes=cls.create_blob_bytes())

    @classmethod
    def create_blob_tree_nodes(cls, num_nodes: int):
        result = []
        for node_id in range(num_nodes):
            result.append(cls.create_blob_tree_node(node_id, result))
        return result

    @classmethod
    def create_blob_tree(cls, num_nodes: int):
        result = BlobTree()
        for node in cls.create_blob_tree_nodes(num_nodes):
            result.add_node(node)
        return result
