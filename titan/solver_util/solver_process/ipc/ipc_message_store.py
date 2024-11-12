from __future__ import annotations
import typing
import tempfile
import os
import multiprocessing
import multiprocessing.shared_memory
from titan.solver_util.solver_process.ipc.types import (
    IpcException,
    IpcMessage
)



class FileBackedIpcMessageStore:

    MESSAGE_NAME_PREFIX = 'msg_'

    __slots__ = (   '_fd_lookup',
                    '_ipc_messages'  )

    @classmethod
    def is_supported(cls) -> bool:
        return True

    def __init__(self):
        self._fd_lookup = {}
        self._ipc_messages = {}

    def create_empty_message(self, size: int) -> IpcMessage:
        file_obj, file_path = tempfile.mkstemp(prefix=self.MESSAGE_NAME_PREFIX)
        self._fd_lookup[file_path] = file_obj
        self._ipc_messages[file_path] = IpcMessage(message_id=file_path, message_buf=memoryview(bytearray(size)))
        return self._ipc_messages[file_path]

    def load_message(self, message_id: str) -> IpcMessage:     
        try:
            # open file if not already
            if message_id not in self._fd_lookup:
                self._fd_lookup[message_id] = os.open(message_id, os.O_RDWR)
            file_size = os.stat(message_id).st_size
            os.lseek(self._fd_lookup[message_id], 0, os.SEEK_SET)
            file_buf = os.read(self._fd_lookup[message_id], file_size)
            self._ipc_messages[message_id] = IpcMessage(message_id=message_id, message_buf=memoryview(file_buf))
            return self._ipc_messages[message_id]
        except KeyError:
            raise IpcException(f"{self.__class__.__name__}.load_message(...) Failed because file handle for `{message_id}` does not exist !")
        except FileNotFoundError:
            raise IpcException(f"{self.__class__.__name__}.load_message(...) Failed because file `{message_id}` could not be found !")

    def save_message(self, ipc_message: IpcMessage):
        try:
            os.lseek(self._fd_lookup[ipc_message.message_id()], 0, os.SEEK_SET)
            os.write(self._fd_lookup[ipc_message.message_id()], ipc_message.message_buf())
        except KeyError:
            raise IpcException(f"{self.__class__.__name__}.save_message(...) Failed because file_obj for message `{ipc_message.message_id()}` could not be found !")

    def release_message(self, ipc_message: IpcMessage):
        try:
            os.close(self._fd_lookup[ipc_message.message_id()])
            del self._fd_lookup[ipc_message.message_id()]
            del self._ipc_messages[ipc_message.message_id()]
            # de-alloc memory
            ipc_message.message_buf().release()
        except KeyError:
            raise IpcException(f"{self.__class__.__name__}.release_message(...) Failed because file handle for `{ipc_message.message_id()}` does not exist !")

    def destroy_message(self, ipc_message: IpcMessage):
        try:
            os.close(self._fd_lookup[ipc_message.message_id()])
            del self._fd_lookup[ipc_message.message_id()]
            del self._ipc_messages[ipc_message.message_id()]
            # delete the file
            os.remove(ipc_message.message_id())
            # de-alloc memory
            ipc_message.message_buf().release()
        except KeyError:
            raise IpcException(f"{self.__class__.__name__}.destroy_message(...) Failed because file handle for `{ipc_message.message_id()}` does not exist !")

    def memory_usage(self):
        return sum((ipc_message.size() for ipc_message in self._ipc_messages.values()))

    def release_all_messages(self):
        for fd in self._fd_lookup.values():
            os.close(fd)
        for ipc_message in self._ipc_messages.values():
            ipc_message.message_buf().release()
        self._fd_lookup = {}
        self._ipc_messages = {}

    def destroy_all_messages(self):
        for fd in self._fd_lookup.values():
            os.close(fd)
        for ipc_message in self._ipc_messages.values():
            ipc_message.message_buf().release()
            # delete the file
            os.remove(ipc_message.message_id())
        self._fd_lookup = {}
        self._ipc_messages = {}



class SharedMemoryIpcMessageStore:

    __slots__ = (   '_shm_lookup',
                    '_ipc_messages'  )

    @classmethod
    def monkey_patch_resource_tracker(cls):
        """Monkey-patch multiprocessing.resource_tracker so SharedMemory won't be tracked

        More details at: https://bugs.python.org/issue38119
        """
        def fix_register(name, rtype):
            if rtype == "shared_memory":
                return
            return multiprocessing.resource_tracker._resource_tracker.register(name, rtype)
        multiprocessing.resource_tracker.register = fix_register
        #
        def fix_unregister(name, rtype):
            if rtype == "shared_memory":
                return
            return multiprocessing.resource_tracker._resource_tracker.unregister(name, rtype)
        multiprocessing.resource_tracker.unregister = fix_unregister
        #
        if "shared_memory" in multiprocessing.resource_tracker._CLEANUP_FUNCS:
            del multiprocessing.resource_tracker._CLEANUP_FUNCS["shared_memory"]


    @classmethod
    def is_supported(cls) -> bool:
        try:
            shm = multiprocessing.shared_memory.SharedMemory(create=True, size=100)
            shm.close()
            shm.unlink()
            return True
        except OSError:
            return False

    def __init__(self):
        self._shm_lookup = {}
        self._ipc_messages = {}

    def create_empty_message(self, size: int) -> IpcMessage:
        shm = multiprocessing.shared_memory.SharedMemory(create=True, size=size)
        self._shm_lookup[shm.name] = shm
        self._ipc_messages[shm.name] = IpcMessage(message_id=shm.name, message_buf=shm.buf)
        return self._ipc_messages[shm.name]

    def load_message(self, message_id: str) -> IpcMessage:
        shm = multiprocessing.shared_memory.SharedMemory(name=message_id)
        self._shm_lookup[shm.name] = shm
        self._ipc_messages[shm.name] = IpcMessage(message_id=shm.name, message_buf=shm.buf)
        return self._ipc_messages[shm.name]

    def save_message(self, ipc_message: IpcMessage):
        # nothing to do
        pass

    def release_message(self, ipc_message: IpcMessage):
        try:
            self._shm_lookup[ipc_message.message_id()].close()
            del self._shm_lookup[ipc_message.message_id()]
            del self._ipc_messages[ipc_message.message_id()]
        except KeyError as e:
            raise IpcException(f"{self.__class__.__name__}.release_message(...) failed because message `{ipc_message.message_id()}` could not be found !")

    def destroy_message(self, ipc_message: IpcMessage):
        try:
            self._shm_lookup[ipc_message.message_id()].close()
            self._shm_lookup[ipc_message.message_id()].unlink()
            del self._shm_lookup[ipc_message.message_id()]
            del self._ipc_messages[ipc_message.message_id()]
        except KeyError as e:
            raise IpcException(f"{self.__class__.__name__}.destroy_message(...) failed because message `{ipc_message.message_id()}` could not be found !")

    def memory_usage(self):
        return sum((ipc_message.size() for ipc_message in self._ipc_messages.values()))

    def release_all_messages(self):
        for ipc_message in self._ipc_messages.values():
            self._shm_lookup[ipc_message.message_id()].close()
        self._shm_lookup = {}
        self._ipc_messages = {}

    def destroy_all_messages(self):
        for ipc_message in self._ipc_messages.values():
            self._shm_lookup[ipc_message.message_id()].close()
            self._shm_lookup[ipc_message.message_id()].unlink()
        self._shm_lookup = {}
        self._ipc_messages = {}


# Decide which implementation to use by default
if SharedMemoryIpcMessageStore.is_supported():
    SharedMemoryIpcMessageStore.monkey_patch_resource_tracker()
    IpcMessageStore = SharedMemoryIpcMessageStore
else:
    IpcMessageStore = FileBackedIpcMessageStore
