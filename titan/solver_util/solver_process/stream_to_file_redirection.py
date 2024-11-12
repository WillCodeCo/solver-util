from __future__ import annotations
import sys
import os


class StreamToFileRedirection(object): 

    __slots__ = (   '_orig_stream_fileno',
                    '_orig_stream_dup',
                    '_file_path',
                    '_file_obj'  )

    def __init__(self, stream, file_path: str):
        self._orig_stream_fileno = stream.fileno()
        self._file_path = file_path

    def __enter__(self):
        self._orig_stream_dup = os.dup(self._orig_stream_fileno)
        self._file_obj = open(self._file_path, 'w')
        os.dup2(self._file_obj.fileno(), self._orig_stream_fileno)
        return self

    def __exit__(self, type, value, traceback):
        os.close(self._orig_stream_fileno)
        os.dup2(self._orig_stream_dup, self._orig_stream_fileno)
        os.close(self._orig_stream_dup)
        self._file_obj.close()

    @classmethod
    def create_for_stdout(cls, file_path: str) -> StreamToFileRedirection:
        return cls(sys.stdout, file_path)

    @classmethod
    def create_for_stderr(cls, file_path: str) -> StreamToFileRedirection:
        return cls(sys.stderr, file_path)