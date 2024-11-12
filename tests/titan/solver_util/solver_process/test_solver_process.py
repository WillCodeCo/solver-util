import typing
import logging
import pytest
import random
import time
import asyncio
import sys
from titan.solver_util import solver_process
from titan.solver_util.solver_process import (
    SolverProcessException,
    IpcMessageStore,
    IpcMessage
)
from tests.titan.solver_util.solver_process.dummy_solver import (
    DummyIpcMessageFactory,
    DummyConfig,
    DummySolver,
    SegFaultDummySolver,
    HangingDummySolver,
    ExceptionDummySolver,
    NeverFinishingDummySolver,
    NoResultDummySolver,
)
from tests.titan.solver_util.solver_process.dummy_solver_process import (
    DummySolverProcessClient
)
from tests.titan.solver_util.solver_process.solver_process_tester import (
    SolverProcessTester
)

logger = logging.getLogger(__name__)



def gen_num_solve_results_per_solve(num_solves, seed):
    rng = random.Random(seed)
    return (rng.randint(2, 40) for _ in range(num_solves))

def gen_expected_ipc_messages(ipc_message_store, num_solves, seed):
    rng = random.Random(seed)
    return (    ipc_message
                    for num_solve_results in gen_num_solve_results_per_solve(num_solves, seed)
                        for ipc_message in DummyIpcMessageFactory.generate_random(ipc_message_store, rng, num_solve_results)    )





class TesterEventLogValidator:

    TIMEOUT_TOLERANCE = 0.2
    MAX_EXCEPTION_DELAY_MS = 200
    MAX_CONFIGURE_TIME_MS = 200
    MAX_CLOSE_TIME_MS = 200
    MAX_INITIALIZATION_TIME_MS = 5000

    @classmethod
    def ensure_successful_initialization(cls, event_log):
        for i, ev in enumerate(event_log):
            if ev.event_type() == 'completed_initialization':
                assert event_log[i-1].event_type() == 'started_initialization'
                assert (ev.timestamp() - event_log[i-1].timestamp()) < cls.MAX_INITIALIZATION_TIME_MS
                return True
        pytest.fail(f"Event log did not show a successful initialize() operation")

    @classmethod
    def ensure_successful_configure(cls, event_log):
        for i, ev in enumerate(event_log):
            if ev.event_type() == 'completed_configure':
                assert event_log[i-1].event_type() == 'started_configure'
                assert (ev.timestamp() - event_log[i-1].timestamp()) < cls.MAX_CONFIGURE_TIME_MS
                return True
        pytest.fail(f"Event log did not show a successful configure() operation")

    @classmethod
    def ensure_successful_close(cls, event_log):
        for i, ev in enumerate(event_log):
            if ev.event_type() == 'completed_close':
                assert event_log[i-1].event_type() == 'started_close'
                assert (ev.timestamp() - event_log[i-1].timestamp()) < cls.MAX_CLOSE_TIME_MS
                return True
        pytest.fail(f"Event log did not show a successful close() operation")

    @classmethod
    def ensure_prompt_exception_after_solve(cls, event_log):
        for i, ev in enumerate(event_log):
            if ev.event_type() == 'raised_exception':
                assert event_log[i-1].event_type() in { 'started_path_solve',
                                                        'started_subtree_solve' }
                assert type(ev.fields()['exception']) == SolverProcessException
                assert (ev.timestamp() - event_log[i-1].timestamp()) < cls.MAX_EXCEPTION_DELAY_MS
                return True
        pytest.fail(f"Event log did not show an exception being raised during a solve operation")


    @classmethod
    def ensure_solve_failed(cls, event_log):
        backwards_events = event_log[::-1]
        for i, ev in enumerate(backwards_events):
            if ev.event_type() in { 'completed_path_solve',
                                    'completed_subtree_solve' }:
                assert event_log[i+1].event_type()  == 'raised_exception'
                assert (ev.timestamp() - event_log[i+1].timestamp()) < cls.MAX_EXCEPTION_DELAY_MS
                return
        pytest.fail(f"Event log does not contain any record of a failing solve operation !")



    @classmethod
    def ensure_timeout_exception_after_solve(cls, event_log, timeout):
        for i, ev in enumerate(event_log):
            if ev.event_type() == 'raised_exception':
                assert event_log[i-1].event_type() in { 'started_path_solve',
                                                        'started_subtree_solve' }
                assert type(ev.fields()['exception']) == SolverProcessException
                exception_delay = (ev.timestamp() - event_log[i-1].timestamp())
                assert exception_delay >= timeout
                assert exception_delay <= timeout+(timeout * cls.TIMEOUT_TOLERANCE)
                return True
        pytest.fail(f"Event log did not show a timeout exception being raised during a solve operation")

    @classmethod
    def ensure_timeout_exception_after_first_event(cls, event_log, timeout):
        assert len(event_log) >= 2, "Event log must have at least 2 events in !"
        for ev in event_log[1:]:
            if ev.event_type() == 'raised_exception':
                assert type(ev.fields()['exception']) == SolverProcessException
                exception_delay = (ev.timestamp() - event_log[0].timestamp())
                assert exception_delay >= timeout
                assert exception_delay <= timeout+(timeout * cls.TIMEOUT_TOLERANCE)
                return True
        pytest.fail(f"Event log did not show a timeout exception being raised")


    @classmethod
    def ensure_prompt_exception_after_initialize(cls, event_log):
        for i, ev in enumerate(event_log):
            if ev.event_type() == 'raised_exception':
                assert event_log[i-1].event_type() == 'started_initialization'
                assert type(ev.fields()['exception']) == SolverProcessException
                assert (ev.timestamp() - event_log[i-1].timestamp()) < cls.MAX_EXCEPTION_DELAY_MS
                return True
        pytest.fail(f"Event log did not show an exception being raised during an initialize operation")

    @classmethod
    def ensure_prompt_exception_after_configure(cls, event_log):
        for i, ev in enumerate(event_log):
            if ev.event_type() == 'raised_exception':
                assert event_log[i-1].event_type() == 'started_configure'
                assert type(ev.fields()['exception']) == SolverProcessException
                assert (ev.timestamp() - event_log[i-1].timestamp()) < cls.MAX_EXCEPTION_DELAY_MS
                return True
        pytest.fail(f"Event log did not show an exception being raised during a configure operation")

    @classmethod
    def ensure_completed_last_solve(cls, event_log):
        for ev in event_log[::-1]:
            if ev.event_type() in { 'completed_path_solve',
                                    'completed_subtree_solve' }:
                return True
            elif ev.event_type() in {   'started_path_solve',
                                        'started_subtree_solve' }:
                pytest.fail(f"Event log shows that the last solve did not complete !")
        pytest.fail(f"Event log does not contain any record of any solve operation being attempted !")


    @classmethod
    def calc_last_solve_time(cls, event_log):
        solve_end_timestamp = None
        solve_start_timestamp = None
        for ev in event_log[::-1]:
            if ev.event_type() in { 'completed_path_solve',
                                    'completed_subtree_solve' }:
                if solve_end_timestamp is not None:
                    raise ValueError(f"Failed to calc_last_solve_time() due to invalid event ordering")
                solve_end_timestamp = ev.timestamp()
            elif ev.event_type() in {   'started_path_solve',
                                        'started_subtree_solve' }:
                solve_start_timestamp = ev.timestamp()
                if solve_end_timestamp is None:
                    raise ValueError(f"Failed to calc_last_solve_time() since the event log does not include the solve completion event")
                return (solve_end_timestamp - solve_start_timestamp)
        raise ValueError(f"Failed to calc_last_solve_time() because the requisite events were not found in the log")


@pytest.mark.asyncio
async def test_solver_process_close():
    TIMEOUT = 2.0
    solver_process_client = DummySolverProcessClient(solver_implementation=NeverFinishingDummySolver())
    async with SolverProcessTester(solver_process_client) as solver_process_tester:
        # validate the initialize()
        await solver_process_tester.initialize(timeout=TIMEOUT)
        TesterEventLogValidator.ensure_successful_initialization(solver_process_tester.event_log())
        solver_process_tester.clear_event_log()
        # try a close
        await solver_process_tester.close()
        TesterEventLogValidator.ensure_successful_close(solver_process_tester.event_log())

@pytest.mark.asyncio
async def test_solver_crashing_process():
    TIMEOUT = 2.0
    solver_process_client = DummySolverProcessClient(solver_implementation=SegFaultDummySolver())
    try:
        async with SolverProcessTester(solver_process_client) as solver_process_tester:
            # validate the initialize()
            await solver_process_tester.initialize(timeout=TIMEOUT)
            TesterEventLogValidator.ensure_successful_initialization(solver_process_tester.event_log())
            solver_process_tester.clear_event_log()
            # validate the configure
            solver_process_tester.configure(config={})
            TesterEventLogValidator.ensure_successful_configure(solver_process_tester.event_log())
            solver_process_tester.clear_event_log()
            # validate the solve
            ipc_message_gen = solver_process_tester.solve_path_as_ipc_messages(action_sequence=None,
                                                                                timeout=TIMEOUT  )
            ipc_messages = [ipc_message async for ipc_message in ipc_message_gen]
            TesterEventLogValidator.ensure_prompt_exception_after_solve(solver_process_tester.event_log())            
            # solver_process_tester.clear_event_log()
            # # subsequent operations should fail immediately
            # solver_process_tester.configure(config={})
            # TesterEventLogValidator.ensure_prompt_exception_after_configure(solver_process_tester.event_log())
            # solver_process_tester.clear_event_log()
            # # and a solve too
            # ipc_message_gen = solver_process_tester.solve_path_as_ipc_messages(action_sequence=None)
            # ipc_messages = [ipc_message async for ipc_message in ipc_message_gen]
            # TesterEventLogValidator.ensure_prompt_exception_after_solve(solver_process_tester.event_log())
    finally:
        pass



@pytest.mark.asyncio
async def test_solver_hanging_process():
    TIMEOUT = 2.0
    solver_process_client = DummySolverProcessClient(solver_implementation=HangingDummySolver())

    try:
        async with SolverProcessTester(solver_process_client) as solver_process_tester:
            # validate the initialize()
            await solver_process_tester.initialize(timeout=TIMEOUT)
            TesterEventLogValidator.ensure_successful_initialization(solver_process_tester.event_log())
            solver_process_tester.clear_event_log()
            # validate the configure
            solver_process_tester.configure(config={})
            TesterEventLogValidator.ensure_successful_configure(solver_process_tester.event_log())
            solver_process_tester.clear_event_log()
            # validate the solve
            ipc_message_gen = solver_process_tester.solve_path_as_ipc_messages(  action_sequence=None,
                                                                                timeout=TIMEOUT  )
            ipc_messages = [ipc_message async for ipc_message in ipc_message_gen]
            TesterEventLogValidator.ensure_timeout_exception_after_solve(   solver_process_tester.event_log(),
                                                                            timeout=TIMEOUT*1000  )            
            solver_process_tester.clear_event_log()
    finally:
        pass

@pytest.mark.asyncio
async def test_solver_exception_process():
    TIMEOUT = 2.0
    solver_process_client = DummySolverProcessClient(solver_implementation=ExceptionDummySolver())
    try:
        async with SolverProcessTester(solver_process_client) as solver_process_tester:
            # validate the initialize()
            await solver_process_tester.initialize(timeout=TIMEOUT)
            TesterEventLogValidator.ensure_successful_initialization(solver_process_tester.event_log())
            solver_process_tester.clear_event_log()
            # validate the configureensure_timeout_exception_after_first_event
            solver_process_tester.configure(config={})
            TesterEventLogValidator.ensure_successful_configure(solver_process_tester.event_log())
            solver_process_tester.clear_event_log()
            # validate the solve
            ipc_message_gen = solver_process_tester.solve_path_as_ipc_messages(  action_sequence=None,
                                                                                timeout=TIMEOUT  )
            ipc_messages = [ipc_message async for ipc_message in ipc_message_gen]
            TesterEventLogValidator.ensure_prompt_exception_after_solve(solver_process_tester.event_log())
            solver_process_tester.clear_event_log()
            # subsequent operations should fail immediately
            solver_process_tester.configure(config={})
            TesterEventLogValidator.ensure_prompt_exception_after_configure(solver_process_tester.event_log())
            solver_process_tester.clear_event_log()
            # and a solve too
            ipc_message_gen = solver_process_tester.solve_path_as_ipc_messages(  action_sequence=None,
                                                                                timeout=TIMEOUT  )
            ipc_messages = [ipc_message async for ipc_message in ipc_message_gen]
            TesterEventLogValidator.ensure_prompt_exception_after_solve(solver_process_tester.event_log())
    finally:
        pass



@pytest.mark.asyncio
async def test_solver_never_finishing_process():
    TIMEOUT = 2.0
    solver_process_client = DummySolverProcessClient(solver_implementation=NeverFinishingDummySolver())

    try:
        async with SolverProcessTester(solver_process_client) as solver_process_tester:
            # validate the initialize()
            await solver_process_tester.initialize(timeout=TIMEOUT)
            TesterEventLogValidator.ensure_successful_initialization(solver_process_tester.event_log())
            solver_process_tester.clear_event_log()
            # validate the configure
            solver_process_tester.configure(DummyConfig(num_solve_results=1))
            TesterEventLogValidator.ensure_successful_configure(solver_process_tester.event_log())
            solver_process_tester.clear_event_log()
            # validate the solve
            ipc_message_gen = solver_process_tester.solve_path_as_ipc_messages(  action_sequence=None,
                                                                                timeout=TIMEOUT  )
            ipc_messages = [ipc_message async for ipc_message in ipc_message_gen]
            TesterEventLogValidator.ensure_timeout_exception_after_first_event( solver_process_tester.event_log(),
                                                                                timeout=TIMEOUT*1000  )            
            solver_process_tester.clear_event_log()
    finally:
        pass



@pytest.mark.asyncio
async def test_solver_no_result_process():
    TIMEOUT = 2.0
    solver_process_client = DummySolverProcessClient(solver_implementation=NoResultDummySolver())

    try:
        async with SolverProcessTester(solver_process_client) as solver_process_tester:
            # validate the initialize()
            await solver_process_tester.initialize(timeout=TIMEOUT)
            TesterEventLogValidator.ensure_successful_initialization(solver_process_tester.event_log())
            solver_process_tester.clear_event_log()
            # validate the configure
            solver_process_tester.configure(config={})
            TesterEventLogValidator.ensure_successful_configure(solver_process_tester.event_log())
            solver_process_tester.clear_event_log()
            # validate the solve
            ipc_message_gen = solver_process_tester.solve_path_as_ipc_messages(  action_sequence=None,
                                                                                timeout=TIMEOUT )
            ipc_messages = [ipc_message async for ipc_message in ipc_message_gen]
            assert len(ipc_messages) == 0
            TesterEventLogValidator.ensure_completed_last_solve(solver_process_tester.event_log())
            TesterEventLogValidator.ensure_solve_failed(solver_process_tester.event_log())
    finally:
        pass



@pytest.mark.asyncio
async def test_solver_dummy_process():
    TIMEOUT = 2.0
    num_solves = 10
    rng_seed = 42
    DummySolver.RNG_SEED = rng_seed
    ipc_message_store = IpcMessageStore()
    expected_ipc_messages = list(gen_expected_ipc_messages( ipc_message_store=ipc_message_store,
                                                    num_solves=num_solves,
                                                    seed=rng_seed  ))
    solver_process_client = DummySolverProcessClient(solver_implementation=DummySolver())
    try:
        async with SolverProcessTester(solver_process_client) as solver_process_tester:
            # validate the initialize()
            await solver_process_tester.initialize(timeout=TIMEOUT)
            TesterEventLogValidator.ensure_successful_initialization(solver_process_tester.event_log())
            solver_process_tester.clear_event_log()
            ipc_message_count = 0
            for i, num_solve_results in enumerate(gen_num_solve_results_per_solve(num_solves, rng_seed)):
                # validate the configure
                solver_process_tester.configure(DummyConfig(num_solve_results=num_solve_results))
                TesterEventLogValidator.ensure_successful_configure(solver_process_tester.event_log())
                solver_process_tester.clear_event_log()
                # validate the solve
                ipc_message_gen = solver_process_tester.solve_path_as_ipc_messages(action_sequence=None)
                ipc_messages = [ipc_message async for ipc_message in ipc_message_gen]
                TesterEventLogValidator.ensure_completed_last_solve(solver_process_tester.event_log())
                solve_time = TesterEventLogValidator.calc_last_solve_time(solver_process_tester.event_log())
                logger.info(f"solve_time = {solve_time} ms")
                solver_process_tester.clear_event_log()
                # check the ipc messages match the expected ones
                assert len(ipc_messages) == num_solve_results
                for ipc_message in ipc_messages:
                    assert ipc_message.message_buf() == expected_ipc_messages[ipc_message_count].message_buf()
                    ipc_message_count += 1
    finally:
        ipc_message_store.destroy_all_messages()
