import pathlib
import os
import sys
import typing
import contextlib
import traceback
import enum
import time
from multiprocessing import (
    Process,
    Pipe
)
from multiprocessing.connection import (
    Connection
)
from titan.solver_util.solver_process.types import (
    SolverProcessException,
    SolverState,
    SolverConfig,
    CommandId
)
from titan.solver_util.solver_process.ipc import (
    IpcMessage
)
from titan.solver_util.solver_process.stream_to_file_redirection import (
    StreamToFileRedirection
)
from titan.solver_util.solver_process.solver_process_logging import (
    SolverProcessLogging
)
from titan.solver_util.spot_models import (
    ActionSequence
)
from titan.solver_util.solver_process.solver_implementation import (
    SolverImplementation
)
from multiprocessing import (
    Process
)


logger = SolverProcessLogging.get_logger(__name__)



class SolverProcessDaemonLogging:

    @staticmethod
    @contextlib.contextmanager
    def setup(log_path, log_name: str):
        SolverProcessLogging.setup_for_file_output( txt_log_file_path=log_path / f"{log_name}.log",
                                                    event_log_file_path=log_path / f"{log_name}.events.jsonl" )
        # redirect streams (to get output of native solver)
        with StreamToFileRedirection.create_for_stdout(log_path / f"{log_name}.stdout"):
            with StreamToFileRedirection.create_for_stderr(log_path / f"{log_name}.stderr"):
                yield


class SolverProcessDaemon:
    
    RECV_POLL_TIMEOUT = 0.05
    RECV_POLL_TIMEOUT_IN_SOLVE = 0.001
    
    @classmethod
    def create_solve_path_command(cls, config: SolverConfig, action_sequence: ActionSequence) -> tuple:
        return (CommandId.SOLVE_PATH, config, action_sequence)

    @classmethod
    def create_solve_sub_tree_command(cls, config: SolverConfig, action_sequence: ActionSequence,
                                            solve_depth: int) -> tuple:
        return (CommandId.SOLVE_SUBTREE, config, action_sequence, solve_depth)

    @classmethod
    def create_cancel_command(cls):
        return (CommandId.CANCEL, )

    @classmethod
    def create_ping_command(cls):
        return (CommandId.PING, )

    @classmethod
    def notify_client(cls, child_connection: Connection, solver_state: SolverState,
                                                            solve_result: str):
        child_connection.send((solver_state, solve_result))
        logger.info(f"successful notify_client({solver_state}, {solve_result})")

    @classmethod
    def notify_state_change(cls, child_connection: Connection, solver_state: SolverState):
        cls.notify_client(child_connection, solver_state, None)

    @classmethod
    def notify_result(cls, child_connection: Connection, solver_state: SolverState, solve_result: str):
        cls.notify_client(child_connection, solver_state, solve_result)

    @classmethod
    def notify_initializing(cls, child_connection: Connection):
        cls.notify_state_change(child_connection, SolverState.INITIALIZING)

    @classmethod
    def notify_ready(cls, child_connection: Connection):
        cls.notify_state_change(child_connection, SolverState.READY)

    @classmethod
    def notify_solving(cls, child_connection: Connection):
        cls.notify_state_change(child_connection, SolverState.SOLVING)

    @classmethod
    def notify_cancelling(cls, child_connection: Connection):
        cls.notify_state_change(child_connection, SolverState.CANCELLING)


    @classmethod
    def gen_command_tuple_from_connection(cls, child_connection: Connection):
        try:
            while True:
                try:
                    yield child_connection.recv()
                except EOFError:
                    logger.info(f"EOFError in {cls.__name__}.gen_command_tuple_from_connection(): child_connection must have been closed by parent process so we should quit !")
                    break
        except SolverProcessException:
            raise
        except Exception as e:
            logger.error(f"Unexpected exception `{type(e)}` in {cls.__name__}.gen_command_tuple_from_connection(): {e}`")
            raise SolverProcessException(f"Unexpected exception with type `{type(e)}`")

    @classmethod
    def execute_command(cls, command_tuple, solver_state: SolverState, solver: SolverImplementation):
        if command_tuple[0] == CommandId.SOLVE_PATH:
            # parse command
            _, config, action_sequence = command_tuple
            # check state is appropriate
            if solver_state != SolverState.READY:
                raise SolverProcessException(f"Invalid state for the SOLVE_PATH command")
            yield (SolverState.SOLVING, None)
            for solve_result in solver.solve_path(config, action_sequence):
                yield (SolverState.SOLVING, solve_result)                
            yield (SolverState.READY, None)
        elif command_tuple[0] == CommandId.SOLVE_SUBTREE:
            # parse command
            _, config, action_sequence, solve_depth = command_tuple
            # check state is appropriate
            if solver_state != SolverState.READY:
                raise SolverProcessException(f"Invalid state for the SOLVE_SUBTREE command")
            yield (SolverState.SOLVING, None)
            for solve_result in solver.solve_subtree(config, action_sequence, solve_depth):
                yield (SolverState.SOLVING, solve_result)
            yield (SolverState.READY, None)
        elif command_tuple[0] == CommandId.CANCEL:
            if solver_state != SolverState.SOLVING:
                raise SolverProcessException(f"Invalid state for the CANCEL command")
            yield (SolverState.CANCELLING, None)
            solver.cancel()
            yield (SolverState.READY, None)
        elif command_tuple[0] == CommandId.PING:
            yield (solver_state, None)
        else:
            raise SolverProcessException(f"Invalid command_id `{command_tuple[0]}`")



    @classmethod
    def initialize(cls, solver: SolverImplementation, solver_state: SolverState):
        if solver_state != SolverState.UNKNOWN:
            raise SolverProcessException(f"Invalid state for initialization !")
        yield (SolverState.INITIALIZING, None, None)
        solver.initialize()
        yield (SolverState.READY, None, None)

    @classmethod
    def _handle_top_level_command(cls, command_tuple, solver_state: SolverState,
                                                            solver: SolverImplementation,
                                                            child_connection: Connection):
        for new_solver_state, solve_result in cls.execute_command(  command_tuple,
                                                                    solver_state,
                                                                    solver  ):
            solver_state = new_solver_state
            cls.notify_result(child_connection, solver_state, solve_result)
            # check if there is a command waiting            
            if child_connection.poll(cls.RECV_POLL_TIMEOUT_IN_SOLVE):
                try:
                    command_tuple = child_connection.recv()
                    for new_solver_state, solve_result in cls.execute_command(  command_tuple,
                                                                                solver_state,
                                                                                solver ):
                        solver_state = new_solver_state
                        cls.notify_result(child_connection, solver_state, solve_result)
                except EOFError:
                    # parent closed our connection so we should quit !
                    logger.info(f"EOFError in {cls.__name__}._handle_top_level_command(): child_connection must have been closed by parent process so we should quit !")
                    break
                # have we stopped solving ?
                if solver_state != SolverState.SOLVING:
                    break
        return solver_state

    @classmethod
    def _run_daemon(cls, solver: SolverImplementation, child_connection: Connection):
        # keep track of these values
        solver = solver
        solver_state = SolverState.UNKNOWN
        config = None
        action_sequence = None
        # initialize
        for (solver_state, config, action_sequence) in cls.initialize(solver, solver_state):
            cls.notify_state_change(child_connection, solver_state)
        # command recv loop
        for command_tuple in cls.gen_command_tuple_from_connection(child_connection):
            solver_state = cls._handle_top_level_command(   command_tuple=command_tuple,
                                                            solver_state=solver_state,
                                                            solver=solver,
                                                            child_connection=child_connection  )            
        # close
        solver.close()


    @classmethod
    def _run_daemon_with_logging(cls, solver: SolverImplementation, child_connection: Connection, log_path: pathlib.Path):
        # file paths to logs
        log_name = f"{cls.__name__.lower()}"
        # keep track of these values
        solver = solver
        solver_state = SolverState.UNKNOWN
        config = None
        action_sequence = None
        try:
            # initialize
            with SolverProcessDaemonLogging.setup(log_path=log_path, log_name=log_name):
                try:
                    for (solver_state, config, action_sequence) in cls.initialize(solver, solver_state):
                        cls.notify_state_change(child_connection, solver_state)
                except Exception as e:
                    # Prevent exception propagating further
                    print(f"Unexpected exception in {cls.__name__}.initialize(): {traceback.format_exc()}", file=sys.stderr)
                    logger.error(f"Unexpected exception in {cls.__name__}.initialize(): {e}", exc_info=True)
                    return
            # command recv loop
            for command_tuple in cls.gen_command_tuple_from_connection(child_connection):
                with SolverProcessDaemonLogging.setup(log_path=log_path, log_name=log_name):
                    try:
                        solver_state = cls._handle_top_level_command(   command_tuple=command_tuple,
                                                                        solver_state=solver_state,
                                                                        solver=solver,
                                                                        child_connection=child_connection  )
                    except Exception as e:
                        # Prevent exception propagating further
                        print(f"Unexpected exception in {cls.__name__}.run(): {traceback.format_exc()}", file=sys.stderr)
                        logger.error(f"Unexpected exception in {cls.__name__}.run(): {e}", exc_info=True)
                        return
        finally:
            # close
            solver.close()

    @classmethod
    def run(cls, solver: SolverImplementation, parent_connection: Connection, child_connection: Connection,
                                                    log_directory: typing.Optional[str] = None):
        # Since file descriptors are inherited by this child process we need to explicitly close this FD, otherwise
        #  when parent tries to close the pipe it will not work, due to the child process having a FD open
        parent_connection.close()
        #
        if (not log_directory):
            SolverProcessLogging.setup_for_stream_output()
            cls._run_daemon(solver, child_connection)
        else:
            try:
                cls._run_daemon_with_logging(   solver=solver,
                                                child_connection=child_connection,
                                                log_path=pathlib.Path(log_directory) )
            except IOError as e:
                raise SolverProcessException(f"Unexpected IOError in {cls.__name__}._run_daemon_with_logging(): {e}")