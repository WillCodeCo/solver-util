from __future__ import annotations
import typing

class IpcException(Exception):
    pass

class IpcMessage:

    __slots__ = (   '_message_id',
                    '_message_buf',  )

    def __init__(self, message_id: str, message_buf: memoryview):
        self._message_id = message_id
        self._message_buf = message_buf

    def message_id(self) -> str:
        return self._message_id

    def message_buf(self) -> memoryview:
        return self._message_buf

    def size(self) -> int:
        return self._message_buf.nbytes

    def __repr__(self):
        return f'{self.__class__.__name__}(message_id={repr(self.message_id())}, message_buf=<{self.size()} bytes>)'

    def __str__(self):
        return f'{self.__class__.__name__}(message_id={self.message_id()}, message_buf=<{self.size()} bytes>)'
