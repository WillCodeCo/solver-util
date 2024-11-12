import sys
import time
import tempfile
import json
import os
import pathlib
import shutil
import typing
import asyncio
import logging
from multiprocessing.connection import (
    Connection
)
from multiprocessing import (
    Process,
    Pipe
)
from titan.solver_util.spot_models import (
    ActionSequence
)
from titan.solver_util.solver_process.types import (
    SolverProcessException,
    SolverState,
    SolverConfig
)
from titan.solver_util.solver_process.solver_process_daemon import (
    SolverProcessDaemon
)
from titan.solver_util.solver_process.ipc import (
    IpcMessage,
    IpcMessageStore
)
from titan.solver_util.solution_tree import (
    SolutionTreeNode,
    SolutionTree,
    SolutionTreeException,
    SolutionTreeBuilder
)
from titan.solver_util.blob_tree.wire_protocol import (
    Deserializer as BlobTreeDeserializer
)
from titan.solver_util.solution_tree.wire_protocol import (
    Deserializer as SolutionTreeDeserializer
)

logger = logging.getLogger(__name__)



class SolverProcessMonitor:

    def __init__(self):
        self._log_directory = None

    def log_directory(self):
        return self._log_directory

    def is_initialized(self):
        return self._log_directory is not None

    @classmethod
    def gen_lines_from_file(cls, file_obj):
        for l in file_obj.readlines():
            yield l.rstrip(os.linesep)

    @classmethod
    def gen_event_dicts_from_file(cls, file_obj):
        yield from (json.loads(line) for line in cls.gen_lines_from_file(file_obj))

    @classmethod
    def last_event_log_path(cls, log_directory: str):
        return sorted(pathlib.Path(log_directory).glob('*.events.jsonl'))[-1]

    @classmethod
    def last_log_path(cls, log_directory: str):
        return sorted(pathlib.Path(log_directory).glob('*.log'))[-1]

    @classmethod
    def last_stdout_path(cls, log_directory: str):
        return sorted(pathlib.Path(log_directory).glob('*.stdout'))[-1]

    @classmethod
    def last_stderr_path(cls, log_directory: str):
        return sorted(pathlib.Path(log_directory).glob('*.stderr'))[-1]

    def initialize(self):
        if self.is_initialized():
            raise ValueError(f"SolverProcessMonitor has already been initialized !")
        self._log_directory = tempfile.mkdtemp()

    def finalize(self):
        if self.is_initialized():
            shutil.rmtree(self.log_directory())
            self._log_directory = None

    def gen_output_lines(self):
        if not self.is_initialized():
            raise SolverProcessException(f"SolverProcessMonitor has not been initialized !")
        with open(self.last_stdout_path(self.log_directory()), 'r') as f:
            yield from self.gen_lines_from_file(f)

    def gen_log_lines(self):
        if not self.is_initialized():
            raise SolverProcessException(f"SolverProcessMonitor has not been initialized !")
        with open(self.last_log_path(self.log_directory()), 'r') as f:
            yield from self.gen_lines_from_file(f)

    def gen_error_lines(self):
        if not self.is_initialized():
            raise SolverProcessException(f"SolverProcessMonitor has not been initialized !")
        with open(self.last_stderr_path(self.log_directory()), 'r') as f:
            yield from self.gen_lines_from_file(f)

    def gen_event_dicts(self):
        if not self.is_initialized():
            raise SolverProcessException(f"SolverProcessMonitor has not been initialized !")
        with open(self.last_event_log_path(self.log_directory()), 'r') as f:
            yield from self.gen_event_dicts_from_file(f)

    def __enter__(self):
        self.initialize()
        return self

    def __exit__(self, exc_type, exc_value, exc_traceback):
        self.finalize()



class SolverProcessClient:

    MAX_SOLVE_DEPTH = 1000
    ROOT_NODE_ID = 0
    RECV_POLL_TIMEOUT = 0.001
    RECV_WAIT_SLEEP = 0.05
    PROCESS_TERMINATION_NOTICE_PERIOD = 0.05
    PROCESS_KILL_TIMEOUT = 1



    def __init__(self):
        self._solver_process_monitor = SolverProcessMonitor()
        self._ipc_message_store = IpcMessageStore()
        self._config = None
        self._solver_state = SolverState.UNKNOWN
        self._solver_process = None
        self._parent_connection = None
        self._child_connection = None

    def state(self) -> SolverState:
        return self._solver_state

    def has_config(self):
        return (self._config is not None)

    def has_running_process(self):
        return (self._solver_process is not None) and (self._solver_process.is_alive())

    def update_state(self, solver_state: SolverState):
        self._solver_state = solver_state

    def invalidate_state(self):
        self._solver_state = SolverState.UNKNOWN

    def has_known_state(self) -> bool:
        return self.state() != SolverState.UNKNOWN

    def is_solving(self) -> bool:
        """Convenience method to check if the Solver's state is BUSY"""
        return self.state() == SolverState.SOLVING

    def is_ready(self) -> bool:
        """Convenience method to check if the Solver's state is READY"""
        return self.state() == SolverState.READY

    def is_cancelling(self) -> bool:
        """Convenience method to check if the Solver's state is CANCELLING"""
        return self.state() == SolverState.CANCELLING

    def is_closing(self) -> bool:
        """Convenience method to check if the Solver's state is CLOSING"""
        return self.state() == SolverState.CLOSING

    def is_closed(self) -> bool:
        """Convenience method to check if the Solver's state is CLOSING"""
        return self.state() == SolverState.CLOSED

    def ipc_message_store(self):
        return self._ipc_message_store

    def create_process(self, parent_connection: Connection, child_connection: Connection, log_directory: str) -> Process:
        raise NotImplementedError

    @classmethod
    def timestamp(cls) -> float:
        return time.time()

    def spawn_process(self):
        self._parent_connection, self._child_connection = Pipe()
        self._solver_process = self.create_process( parent_connection=self._parent_connection,
                                                    child_connection=self._child_connection,
                                                    log_directory=self._solver_process_monitor.log_directory() )
        self._solver_process.start()


    def close_connections(self):
        if self._parent_connection:
            self._parent_connection.close()
        if self._child_connection:
            self._child_connection.close()
        self._child_connection = None
        self._parent_connection = None

    def ensure_process_is_closed(self):
        if self.has_running_process():
            logger.info("Child process is still running, so we will KILL it !")
            self._solver_process.kill()
            self._solver_process.join(timeout=self.PROCESS_KILL_TIMEOUT)
            if self.has_running_process():
                raise SolverProcessException(f"Failed to join the process after a KILL !")
        # make sure to update the state to reflect that process is dead
        self._solver_process = None
        self.update_state(SolverState.CLOSED)
        self.close_connections()

    @classmethod
    async def send_command(cls, daemon_connection: Connection, command_tuple: tuple):
        daemon_connection.send(command_tuple)

    @classmethod
    async def send_cancel(cls, daemon_connection: Connection):
        await cls.send_command(daemon_connection, SolverProcessDaemon.create_cancel_command())

    @classmethod
    async def send_solve_path_command(cls, daemon_connection: Connection, config: SolverConfig,
                                                        action_sequence: ActionSequence):
        command = SolverProcessDaemon.create_solve_path_command(config=config,
                                                                action_sequence=action_sequence)
        await cls.send_command(daemon_connection, command)

    @classmethod
    async def send_solve_subtree_command(cls, daemon_connection: Connection, config: SolverConfig,
                                                                        action_sequence: ActionSequence,
                                                                        solve_depth: int):
        command = SolverProcessDaemon.create_solve_sub_tree_command(config=config,
                                                                    action_sequence=action_sequence,
                                                                    solve_depth=solve_depth)
        await cls.send_command(daemon_connection, command)

    @classmethod
    async def send_ping(cls, daemon_connection: Connection):
        await cls.send_command(daemon_connection, SolverProcessDaemon.create_ping_command())

    async def recv_notification(self, daemon_connection: Connection, notification_timeout: float):
        try:
            # set timeout timestamp
            timeout_timestamp = (self.timestamp() + notification_timeout) if (notification_timeout > 0) else sys.maxsize
            while (self.timestamp() < timeout_timestamp) and (self._solver_process.is_alive()):
                if not daemon_connection.poll(self.RECV_POLL_TIMEOUT):
                    await asyncio.sleep(self.RECV_WAIT_SLEEP)
                else:
                    return daemon_connection.recv()
            if not self._solver_process.is_alive():            
                raise SolverProcessException((  f"solver subprocess died while waiting on daemon_connection in "+
                                                f"{self.__class__.__name__}.recv_notification()"))
            else:
                raise SolverProcessException((  f"Timeout waiting on daemon_connection in "+
                                                f"{self.__class__.__name__}.recv_notification()"))
        except EOFError:
            logger.error(f"daemon_connection got an EOF in {self.__class__.__name__}.recv_notification()")
            raise SolverProcessException(f"Got an EOF on daemon_connection !")
        except SolverProcessException:
            raise
        except Exception as e:
            logger.error(f"Unexpected exception `{type(e)}` in {self.__class__.__name__}.recv_notification(): {e}`")
            raise SolverProcessException(f"Unexpected exception with type `{type(e)}`")

    async def gen_notifications_until(self, daemon_connection: Connection, target_state: SolverState,
                                            timeout: float, notification_timeout: float):
        # use timeout if notification_timeout not specified
        if not notification_timeout:
            notification_timeout = timeout
        # set timeout timestamp
        timeout_timestamp = (self.timestamp() + timeout) if (timeout > 0) else sys.maxsize
        # wait until we enter target state
        solver_state = SolverState.UNKNOWN
        while (solver_state != target_state):
            if self.timestamp() > timeout_timestamp:
                raise SolverProcessException(f"Timeout waiting for target_state {target_state}")
            solver_state, solve_result = await self.recv_notification(  daemon_connection,
                                                                        notification_timeout )
            yield (solver_state, solve_result)


    async def initialize(self, timeout: float = 0, notification_timeout: float = 0):
        # setup the monitor
        self._solver_process_monitor.initialize()
        # spawn the process
        self.invalidate_state()
        self.spawn_process()
        # wait until we enter ready state
        notif_gen = self.gen_notifications_until(   daemon_connection=self._parent_connection,
                                                    target_state=SolverState.READY,
                                                    timeout=timeout,
                                                    notification_timeout=notification_timeout )
        async for solver_state, _ in notif_gen:
            self.update_state(solver_state)


    def configure(self, config: SolverConfig):
        if not self.is_ready():
            raise SolverProcessException((  f"Cannot call {self.__class__.__name__}.configure() " +
                                            f"when solver is not in READY state !"))
        self._config = config

    async def cancel(self, timeout: float = 0, notification_timeout: float = 0):
        if not self.is_solving():
            raise SolverProcessException((  f"Cannot call {self.__class__.__name__}.cancel() " +
                                            f"when solver is not in SOLVING state !"  ))
        self.invalidate_state()
        # wait until we enter ready state
        notif_gen = self.gen_notifications_until(   daemon_connection=self._parent_connection,
                                                    target_state=SolverState.READY,
                                                    timeout=timeout,
                                                    notification_timeout=notification_timeout )
        async for solver_state, _ in notif_gen:
            self.update_state(solver_state)

        
    async def close(self):
        try:
            if self.has_running_process():
                try:
                    logger.info("Politely closing down the child process ...")
                    self.update_state(SolverState.CLOSING)
                    # close the pipes
                    self.close_connections()
                    await asyncio.sleep(self.PROCESS_TERMINATION_NOTICE_PERIOD)
                finally:
                    self.ensure_process_is_closed()
        finally:
            #cleanup the monitor
            self._solver_process_monitor.finalize()


    async def solve_subtree_as_ipc_messages(self, action_sequence: ActionSequence,
                                                    solve_depth: int,
                                                    timeout: float = 0,
                                                    notification_timeout: float = 0) -> typing.AsyncIterator[IpcMessage]:
        if not self.is_ready():
            raise SolverProcessException((  f"Cannot call {self.__class__.__name__}.solve_subtree_as_ipc_messages() " +
                                            f"when solver is not in READY state !"  ))
        elif not self.has_config():
            raise SolverProcessException((  f"Cannot call {self.__class__.__name__}.solve_subtree_as_ipc_messages() " +
                                            f"when solver has not been configured yet !"  ))
        self.invalidate_state()
        await self.send_solve_subtree_command( daemon_connection=self._parent_connection,
                                                config=self._config,
                                                action_sequence=action_sequence,
                                                solve_depth=solve_depth  )
        # get notifications
        notif_gen = self.gen_notifications_until(   daemon_connection=self._parent_connection,
                                                    target_state=SolverState.READY,
                                                    timeout=timeout,
                                                    notification_timeout=notification_timeout)
        num_messages_yielded = 0
        async for solver_state, solve_result in notif_gen:
            self.update_state(solver_state)
            # solve result will be a string message id
            if solve_result:
                ipc_message = self.ipc_message_store().load_message(solve_result)
                yield ipc_message
                num_messages_yielded += 1
        # nothing was yielded ? raise an exception
        if num_messages_yielded == 0:
            raise SolverProcessException(f"Solver did not return any ipc messages for this subtree solve !")

    async def solve_path_as_ipc_messages(self, action_sequence: ActionSequence,
                                                timeout: float = 0,
                                                notification_timeout: float = 0) -> typing.AsyncIterator[IpcMessage]:
        if not self.is_ready():
            raise SolverProcessException((  f"Cannot call {self.__class__.__name__}.solve_path_as_ipc_messages() " +
                                            f"when solver is not in READY state !"  ))
        elif not self.has_config():
            raise SolverProcessException((  f"Cannot call {self.__class__.__name__}.solve_path_as_ipc_messages() " +
                                            f"when solver has not been configured yet !"  ))
        self.invalidate_state()
        await self.send_solve_path_command( daemon_connection=self._parent_connection,
                                            config=self._config,
                                            action_sequence=action_sequence  )
        # get notifications
        notif_gen = self.gen_notifications_until(   daemon_connection=self._parent_connection,
                                                    target_state=SolverState.READY,
                                                    timeout=timeout,
                                                    notification_timeout=notification_timeout   )
        
        num_messages_yielded = 0
        async for solver_state, solve_result in notif_gen:
            self.update_state(solver_state)
            # solve result will be a string message id
            if solve_result:
                ipc_message = self.ipc_message_store().load_message(solve_result)
                yield ipc_message
                num_messages_yielded += 1
        # nothing was yielded ? raise an exception
        if num_messages_yielded == 0:
            raise SolverProcessException(f"Solver did not return any ipc messages for this path solve !")



    @classmethod
    def gen_blob_tree_nodes(cls, ipc_message: IpcMessage):
        src_buffer = ipc_message.message_buf()
        offset = 0
        while offset < ipc_message.size():
            node, bytes_read = BlobTreeDeserializer.deserialize_blob_tree_node(src_buffer[offset:])
            offset += bytes_read
            yield node
            
    @classmethod
    def build_solution_tree_nodes(cls, builder: SolutionTreeBuilder,
                                            ipc_message: IpcMessage) -> typing.Iterator[SolutionTreeNode]:
        for blob_node in cls.gen_blob_tree_nodes(ipc_message):
            solved_spot, _ = SolutionTreeDeserializer.deserialize_solved_spot(blob_node.blob_bytes())
            # root node ?
            if blob_node.node_id() == cls.ROOT_NODE_ID:
                yield builder.create_root_node( node_id=blob_node.node_id(),
                                                solved_spot=solved_spot )
            else:
                yield builder.create_child_node(node_id=blob_node.node_id(),
                                                parent_node_id=blob_node.parent_node_id(),
                                                action_string=blob_node.child_id(),
                                                solved_spot=solved_spot)


    @classmethod
    async def gen_solution_tree_updates(cls, ipc_message_gen: typing.AsyncIterator[IpcMessage]):
        builder = SolutionTreeBuilder()
        async for ipc_message in ipc_message_gen:
            for solution_tree_node in cls.build_solution_tree_nodes(builder, ipc_message):
                yield (builder, solution_tree_node)

    async def solve_subtree_as_solution_tree_updates(self, action_sequence: ActionSequence,
                                                            solve_depth: int,
                                                            timeout: float = 0,
                                                            notification_timeout: float = 0) -> typing.AsyncIterator[typing.Tuple[SolutionTreeBuilder, SolutionTreeNode]]:
        ipc_message_gen = self.solve_subtree_as_ipc_messages(action_sequence=action_sequence,
                                                            solve_depth=solve_depth,
                                                            timeout=timeout,
                                                            notification_timeout=notification_timeout)
        async for builder, solution_tree_node in self.gen_solution_tree_updates(ipc_message_gen):
            yield (builder, solution_tree_node)

    async def solve_path_as_solution_tree_updates(self, action_sequence: ActionSequence,
                                                        timeout: float = 0,
                                                        notification_timeout: float = 0) -> typing.AsyncIterator[typing.Tuple[SolutionTreeBuilder, SolutionTreeNode]]:
        ipc_message_gen = self.solve_path_as_ipc_messages(   action_sequence=action_sequence,
                                                            timeout=timeout,
                                                            notification_timeout=notification_timeout  )        
        num_nodes_yielded = 0
        async for builder, solution_tree_node in self.gen_solution_tree_updates(ipc_message_gen):
            yield (builder, solution_tree_node)
            num_nodes_yielded += 1
        # did we yield the correct number of nodes ?
        expected_node_count = len(action_sequence) + 1
        if num_nodes_yielded != expected_node_count:
            raise SolverProcessException((  f"Solver returned {num_nodes_yielded} nodes for path `{str(action_sequence)}` " +
                                            f"instead of the expected {expected_node_count} !"  ))

    def gen_output_lines(self):
        yield from self._solver_process_monitor.gen_output_lines()

    def gen_log_lines(self):
        yield from self._solver_process_monitor.gen_log_lines()

    def gen_error_lines(self):
        yield from self._solver_process_monitor.gen_error_lines()

    def gen_event_dicts(self):
        yield from self._solver_process_monitor.gen_event_dicts()

    def shared_memory_usage(self) -> int:
        """Return the number of bytes used in shared_memory
        """
        return self._ipc_message_store.memory_usage()

    def release_shared_memory(self):
        """Release shared ipc messages that were previously created by the solver process

        This should be called periodically when the SolutionTrees or IpcMessages are no
        longer needed
        """
        self._ipc_message_store.destroy_all_messages()


    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_value, traceback):
        self.release_shared_memory()
        close_task = asyncio.create_task(self.close())
        try:
            await asyncio.shield(close_task)
        except asyncio.CancelledError:
            await close_task
            raise
        except Exception as e:
            logger.info(f"{self.__class__.__name__} is suppressing exception with type `{type(e)}` : {e}")
        finally:
            self._solver_process_monitor.finalize()