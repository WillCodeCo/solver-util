import struct
from titan.solver_util.blob_tree import (
    BlobTreeNode
)


class WireProtocolException(Exception):
    pass


class WireProtocolConst:
    """Constants used in the serialization/deserialization"""
    INT32_SIZE = 4


class Serializer:
    """Primary class for serializing BlobTreeNode objects into bytes
    """

    @classmethod
    def serialized_size_of_int(cls):
        return WireProtocolConst.INT32_SIZE

    @classmethod
    def serialize_int(cls, dest_buf, value: int):
        dest_buf[0:4] = struct.pack('>I', value)
        return WireProtocolConst.INT32_SIZE

    @classmethod
    def serialized_size_of_bytes(cls, some_bytes: bytes):
        return cls.serialized_size_of_int() + len(some_bytes)

    @classmethod
    def serialize_bytes(cls, dest_buf, some_bytes: bytes):
        num_bytes = len(some_bytes)
        offset = 0
        offset += cls.serialize_int(dest_buf[offset:], num_bytes)        
        dest_buf[offset: offset+num_bytes] = some_bytes
        offset += num_bytes
        return offset

    @classmethod
    def serialize_string(cls, dest_buf, some_string: str):
        return cls.serialize_bytes(dest_buf, some_string.encode('ascii'))

    @classmethod
    def serialized_size_of_string(cls, some_string: str):
        return cls.serialized_size_of_int() + len(some_string)

    @classmethod
    def serialized_size_of_blob_tree_node(cls, node: BlobTreeNode):
        # node_id and parent_id 
        result = cls.serialized_size_of_int() * 2
        result += cls.serialized_size_of_string(node.child_id())
        result += cls.serialized_size_of_bytes(node.blob_bytes())
        return result

    @classmethod
    def serialize_blob_tree_node(cls, dest_buf, node: BlobTreeNode):
        offset = 0
        offset += cls.serialize_int(dest_buf[offset:], node.node_id())
        offset += cls.serialize_int(dest_buf[offset:], node.parent_node_id())
        offset += cls.serialize_string(dest_buf[offset:], node.child_id())
        offset += cls.serialize_bytes(dest_buf[offset:], node.blob_bytes())
        return offset



class Deserializer:
    """Primary class for de-serializing bytes into BlobTreeNode objects
    """

    @classmethod
    def deserialize_int(cls, src_buf):
        result = struct.unpack(">I", src_buf[:4])[0]
        return (result, WireProtocolConst.INT32_SIZE)

    @classmethod
    def deserialize_bytes(cls, src_buf):
        offset = 0
        len_bytes, bytes_read = cls.deserialize_int(src_buf[offset:])
        offset += bytes_read
        result = src_buf[offset: offset+len_bytes]
        offset += len_bytes
        return (result, offset)

    @classmethod
    def deserialize_string(cls, src_buf):
        result, offset = cls.deserialize_bytes(src_buf)
        try:
            return bytes(result).decode('ascii'), offset
        except UnicodeDecodeError:
            raise WireProtocolException(f"Unable to deserialize string")

    @classmethod
    def deserialize_blob_tree_node(cls, src_buf):
        """Parse the bytes in the specified src_buf and return a BlobTreeNode object

        Args:
            src_buf: A MemoryView interface buffer

        Returns:
            A tuple (BlobTreeNode, bytes_read)

        Raises:
            WireProtocolException: If the bytes could not be de-serialized
        """
        offset = 0
        node_id, bytes_read = cls.deserialize_int(src_buf[offset:])
        offset += bytes_read
        parent_node_id, bytes_read = cls.deserialize_int(src_buf[offset:])
        offset += bytes_read
        child_id, bytes_read = cls.deserialize_string(src_buf[offset:])
        offset += bytes_read
        blob_bytes, bytes_read = cls.deserialize_bytes(src_buf[offset:])
        offset += bytes_read
        result = BlobTreeNode(  node_id=node_id,
                                parent_node_id=parent_node_id,
                                child_id=child_id,
                                blob_bytes=blob_bytes  )
        return (result, offset)

