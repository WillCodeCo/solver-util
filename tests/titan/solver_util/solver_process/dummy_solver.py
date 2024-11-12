import typing
import time
import signal
import os
import struct
import ctypes
import random
from titan.solver_util.spot_models import (
    ActionSequence
)
from titan.solver_util.solver_process import (
    IpcMessage,
    IpcMessageStore,
    SolverConfig,
    SolverImplementation,
    SolverProcessLogging
)


logger = SolverProcessLogging.get_logger(__name__)



class DummyIpcMessageFactory:

    INT_SIZE = 4
    NUM_INTS_IN_RESULT = 100000

    @classmethod
    def create(cls, ipc_message_store: IpcMessageStore, int_tuple: typing.Tuple[int, ...]):
        buf_size = len(int_tuple) * cls.INT_SIZE
        ipc_message = ipc_message_store.create_empty_message(buf_size)
        for i, v in enumerate(int_tuple):
            offset = i*cls.INT_SIZE
            ipc_message.message_buf()[offset : offset + cls.INT_SIZE] = struct.pack('>I', v)
        ipc_message_store.save_message(ipc_message)
        return ipc_message

    @classmethod
    def generate_random(cls, ipc_message_store: IpcMessageStore, rng: random.Random, count: int):
        # predictable numbers
        for _ in range(count):
            int_tuple = tuple(rng.randint(0, 0xffffffff) for _ in range(cls.NUM_INTS_IN_RESULT))
            yield cls.create(ipc_message_store, int_tuple)

class DummySolveResultFactory:

    NUM_INTS_IN_RESULT = 100

    @classmethod
    def generate_random(cls, ipc_message_store: IpcMessageStore, rng: random.Random, count: int):
        for ipc_message in DummyIpcMessageFactory.generate_random(ipc_message_store, rng, count):
            # the result is the message_id
            yield ipc_message.message_id()
            # now we can release the message from this process
            ipc_message_store.release_message(ipc_message)


class DummyConfig(SolverConfig):

    def __init__(self, num_solve_results: int):
        self._num_solve_results = num_solve_results

    def num_solve_results(self) -> int:
        return self._num_solve_results


class DummySolver(SolverImplementation):


    RNG_SEED = 42
    SPEEDUP = 1
    SIMULATE_COMPUTE_TIME = 1
    SIMULATE_IO_TIME = 0.01


    def __init__(self):
        self._ipc_message_store = IpcMessageStore()
        self._rng = random.Random(self.RNG_SEED)

    def gen_dummy_solve_result(self, num_solve_results: int):
        yield from DummySolveResultFactory.generate_random(self._ipc_message_store, self._rng, num_solve_results)

    def simulate_processing(self, sleep_time: float, log_msg: str):
        time.sleep(sleep_time / self.SPEEDUP)

    def initialize(self):
        logger.event({'type': 'operation_started', 'operation': 'initialize'})
        self.simulate_processing(self.SIMULATE_COMPUTE_TIME, "Simulating postflop solver process initialization ...")

    def cancel(self):
        logger.event({'type': 'operation_started', 'operation': 'cancel'})
        self.simulate_processing(self.SIMULATE_COMPUTE_TIME, "Simulating postflop solver process cancellation ...")

    def close(self):
        logger.event({'type': 'operation_started', 'operation': 'close'})
        self.simulate_processing(self.SIMULATE_IO_TIME, "Simulating postflop solver process closure ...")

    def simulate_solve(self, num_solve_results: int):
        # simulate processing
        self.simulate_processing(self.SIMULATE_COMPUTE_TIME, "Simulating solving ...")
        for solve_result in self.gen_dummy_solve_result(num_solve_results):
            yield solve_result
            self.simulate_processing(self.SIMULATE_IO_TIME, "Simulating tree traversal work ...")

    def solve_path(self, config: SolverConfig, action_sequence: ActionSequence):
        logger.event({'type': 'operation_started', 'operation': 'solve_path'})
        yield from self.simulate_solve(num_solve_results=config.num_solve_results())

    def solve_subtree(self, config: SolverConfig, action_sequence: ActionSequence, solve_depth: int):
        logger.event({'type': 'operation_started', 'operation': 'solve_subtree'})
        yield from self.simulate_solve(num_solve_results=config.num_solve_results())



class SegFaultDummySolver(DummySolver):

    def simulate_segfault(self):
        os.kill(os.getpid(), signal.SIGKILL)


    def solve_path(self, config: SolverConfig, action_sequence: ActionSequence):
        logger.event({'type': 'operation_started', 'operation': 'solve_path'})
        self.simulate_segfault()


class HangingDummySolver(DummySolver):

    def simulate_hang(self):
        while True:
            self.simulate_processing(self.SIMULATE_IO_TIME, "Simulating a process hang ...")

    def solve_path(self, config: SolverConfig, action_sequence: ActionSequence):
        logger.event({'type': 'operation_started', 'operation': 'solve_path'})
        self.simulate_hang()

class ExceptionDummySolver(DummySolver):

    def solve_path(self, config: SolverConfig, action_sequence: ActionSequence):
        logger.event({'type': 'operation_started', 'operation': 'solve_path'})
        raise Exception('Something went wrong !')


class NeverFinishingDummySolver(DummySolver):

    def solve_path(self, config: SolverConfig, action_sequence: ActionSequence):
        logger.event({'type': 'operation_started', 'operation': 'solve_path'})
        while True:
            yield from self.simulate_solve(num_solve_results=config.num_solve_results())


class NoResultDummySolver(DummySolver):

    def solve_path(self, config: SolverConfig, action_sequence: ActionSequence):
        logger.event({'type': 'operation_started', 'operation': 'solve_path'})
        self.simulate_processing(self.SIMULATE_COMPUTE_TIME, "Simulating a solve with no result ...")
        yield from ()