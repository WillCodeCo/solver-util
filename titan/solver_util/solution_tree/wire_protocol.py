import struct
import typing
from numpy import typing as npt    
import numpy as np
from titan.solver_util.solution_tree.types import (
    StrategyOption,
    CheckOption,
    CallOption,
    FoldOption,
    RaiseOption,
    RangeMatrix,
    SolvedSpot
)


class WireProtocolException(Exception):
    pass


class WireProtocolConst:
    """Constants used in the serialization/deserialization"""
    INT32_SIZE = 4
    FOLD_OPTION_BYTE = ord('f')
    CALL_OPTION_BYTE = ord('c')
    CHECK_OPTION_BYTE = ord('x')
    RAISE_OPTION_BYTE = ord('r')

class Serializer:
    """Primary class for serializing SolvedSpot objects into bytes
    """

    @classmethod
    def serialized_size_of_int(cls):
        return WireProtocolConst.INT32_SIZE

    @classmethod
    def serialize_int(cls, dest_buf, value: int):
        dest_buf[0:4] = struct.pack('>I', value)
        return WireProtocolConst.INT32_SIZE

    @classmethod
    def serialized_size_of_strategy_option(cls, strategy_option: StrategyOption):
        if type(strategy_option) in {CheckOption, CallOption, FoldOption}:
            return 1
        elif type(strategy_option) == RaiseOption:
            return 1 + (2 * cls.serialized_size_of_int())
        else:
            raise WireProtocolException(f"Unrecognized strategy_option {strategy_option}")

    @classmethod
    def serialize_strategy_option(cls, dest_buf, strategy_option: StrategyOption):
        if type(strategy_option) == CheckOption:
            dest_buf[0] = WireProtocolConst.CHECK_OPTION_BYTE
            return 1
        elif type(strategy_option) == CallOption:
            dest_buf[0] = WireProtocolConst.CALL_OPTION_BYTE
            return 1
        elif type(strategy_option) == FoldOption:
            dest_buf[0] = WireProtocolConst.FOLD_OPTION_BYTE
            return 1
        elif type(strategy_option) == RaiseOption:
            dest_buf[0] = WireProtocolConst.RAISE_OPTION_BYTE
            offset = 1
            offset += cls.serialize_int(dest_buf[offset:], strategy_option.amount())
            offset += cls.serialize_int(dest_buf[offset:], strategy_option.pot_size_ratio_bps())
            return offset
        else:
            raise WireProtocolException(f"Unrecognized strategy_option {strategy_option}")

    @classmethod
    def serialized_size_of_strategy_option_sequence(cls, strategy_options: typing.Iterable[StrategyOption]):
        options_size = sum((cls.serialized_size_of_strategy_option(option)
                                    for option in strategy_options     ))
        return cls.serialized_size_of_int() + options_size

    @classmethod
    def serialize_strategy_option_sequence(cls, dest_buf,
                                            strategy_options: typing.Iterable[StrategyOption]):
        offset = 0
        offset += cls.serialize_int(dest_buf[offset:], len(strategy_options))
        for option in strategy_options:
            offset += cls.serialize_strategy_option(dest_buf[offset:], option)
        return offset

    @classmethod
    def serialized_size_of_int_sequence(cls, int_sequence: typing.Iterable[int]):
        return cls.serialized_size_of_int() + (len(int_sequence)*cls.serialized_size_of_int())

    @classmethod
    def serialize_int_sequence(cls, dest_buf, int_sequence: typing.Iterable[int]):
        seq_len = len(int_sequence)
        num_ints = seq_len + 1
        num_bytes = num_ints * WireProtocolConst.INT32_SIZE
        dest_buf[0: num_bytes] = struct.pack(f">{num_ints}I", seq_len, *int_sequence)
        return num_bytes

    @classmethod
    def serialized_size_of_int_array(cls, int_array: npt.NDArray[np.int32]):
        result = cls.serialized_size_of_int_sequence(int_array.shape)
        result += np.prod(int_array.shape) * cls.serialized_size_of_int()
        return result

    @classmethod
    def serialize_int_array(cls, dest_buf, int_array: npt.NDArray[np.int32]):
        offset = 0
        # copy the shape information
        offset += cls.serialize_int_sequence(dest_buf, int_array.shape)
        # copy ints in array
        num_ints = np.prod(int_array.shape)
        if num_ints > 0:
            out_int_array = np.ndarray( shape=int_array.shape,
                                    buffer=dest_buf,
                                    offset=offset,
                                    dtype=np.dtype('>i4') )
            out_int_array[:] = int_array
            offset += (num_ints * WireProtocolConst.INT32_SIZE)
        return offset

    @classmethod
    def serialized_size_of_range_matrix(cls, range_matrix: RangeMatrix):
        return cls.serialized_size_of_int_array(range_matrix.values())

    @classmethod
    def serialize_range_matrix(cls, dest_buf, range_matrix: RangeMatrix):
        return cls.serialize_int_array(dest_buf, range_matrix.values())


    @classmethod
    def serialized_size_of_solved_spot(cls, solved_spot: SolvedSpot):
        # node_id and parent_id 
        result = cls.serialized_size_of_strategy_option_sequence(solved_spot.strategy_options())
        result += cls.serialized_size_of_range_matrix(solved_spot.strategy_matrix())
        result += cls.serialized_size_of_range_matrix(solved_spot.ev_matrix())
        return result


    @classmethod
    def serialize_solved_spot(cls, dest_buf, solved_spot: SolvedSpot) -> int:
        """Serialize the given solved_spot into bytes, written to the specified dest_buf

        Args:
            dest_buf: Destination MemoryView interface buffer to write to
            solved_spot: SolvedSpot to serialize

        Returns:
            The number of bytes written to dest_buf

        Raises:
            WireProtocolException: If serialization fails
        """
        offset = 0
        offset += cls.serialize_strategy_option_sequence(dest_buf[offset:], solved_spot.strategy_options())
        offset += cls.serialize_range_matrix(dest_buf[offset:], solved_spot.strategy_matrix())
        offset += cls.serialize_range_matrix(dest_buf[offset:], solved_spot.ev_matrix())
        return offset

class Deserializer:
    """Primary class for de-serializing bytes into SolvedSpot objects
    """
    @classmethod
    def deserialize_int(cls, src_buf):
        result = struct.unpack(">I", src_buf[:4])[0]
        return (result, WireProtocolConst.INT32_SIZE)

    @classmethod
    def deserialize_strategy_option(cls, src_buf):
        option_byte = src_buf[0]
        offset = 1
        if option_byte == WireProtocolConst.CHECK_OPTION_BYTE:
            return (CheckOption(), offset)
        elif option_byte == WireProtocolConst.CALL_OPTION_BYTE:
            return (CallOption(), offset)
        elif option_byte == WireProtocolConst.FOLD_OPTION_BYTE:
            return (FoldOption(), offset)
        elif option_byte == WireProtocolConst.RAISE_OPTION_BYTE:
            amount, bytes_read = cls.deserialize_int(src_buf[offset:])
            offset += bytes_read
            pot_size_ratio_bps, bytes_read = cls.deserialize_int(src_buf[offset:])
            offset += bytes_read
            return (RaiseOption(amount, pot_size_ratio_bps), offset)
        else:
            raise WireProtocolException(f"Invalid option_byte 0x{option_byte.hex()}")

    @classmethod
    def deserialize_strategy_option_sequence(cls, src_buf):
        result = []
        offset = 0
        num_options, bytes_read = cls.deserialize_int(src_buf[offset:])
        offset += bytes_read
        for _ in range(num_options):
            strategy_option, bytes_read = cls.deserialize_strategy_option(src_buf[offset:])
            offset += bytes_read
            result.append(strategy_option)
        return (tuple(result), offset)

    @classmethod
    def deserialize_int_sequence(cls, src_buf):
        result = []
        offset = 0
        num_ints, bytes_read = cls.deserialize_int(src_buf[offset:])
        offset += bytes_read
        num_bytes = num_ints * WireProtocolConst.INT32_SIZE        
        result = struct.unpack(f">{num_ints}I", src_buf[offset: offset + num_bytes])
        offset += num_bytes 
        return (result, offset)


    @classmethod
    def deserialize_int_array(cls, src_buf):
        offset = 0        
        matrix_shape, bytes_read = cls.deserialize_int_sequence(src_buf[offset:])
        offset += bytes_read
        int_array = np.ndarray( shape=matrix_shape,
                                buffer=src_buf,
                                offset=offset,
                                dtype=np.dtype('>i4')  )
        offset += np.prod(matrix_shape, dtype=np.int32) * WireProtocolConst.INT32_SIZE
        return (int_array, offset)


    @classmethod
    def deserialize_range_matrix(cls, src_buf):
        int_array, offset = cls.deserialize_int_array(src_buf)
        return (RangeMatrix(int_array), offset)

    @classmethod
    def deserialize_solved_spot(cls, src_buf):
        """Parse the bytes in the specified src_buf and return a SolvedSpot object

        Args:
            src_buf: A MemoryView interface buffer

        Returns:
            A tuple (SolvedSpot, bytes_read)

        Raises:
            WireProtocolException: If the bytes could not be de-serialized
        """
        offset = 0
        strategy_options, bytes_read = cls.deserialize_strategy_option_sequence(src_buf[offset:])
        offset += bytes_read
        strategy_matrix, bytes_read = cls.deserialize_range_matrix(src_buf[offset:])
        offset += bytes_read
        ev_matrix, bytes_read = cls.deserialize_range_matrix(src_buf[offset:])
        offset += bytes_read
        result = SolvedSpot(    strategy_options=strategy_options,
                                strategy_matrix=strategy_matrix,
                                ev_matrix=ev_matrix  )        
        return (result, offset)

