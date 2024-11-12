import typing
import logging
import time
import asyncio
from titan.solver_util.solver_process import (
    IpcMessage,
    SolverConfig
)
from titan.solver_util.spot_models import (
    ActionSequence
)


logger = logging.getLogger(__name__)

class SolverProcessTestEvent:

    __slots__ = (   '_event_type',
                    '_timestamp',
                    '_fields'  )

    @classmethod
    def create_timestamp(cls):
        return int(time.time()*1000)

    @classmethod
    def create_started_initialization(cls):
        return cls('started_initialization', cls.create_timestamp(), {})

    @classmethod
    def create_completed_initialization(cls):
        return cls('completed_initialization', cls.create_timestamp(), {})

    @classmethod
    def create_started_configure(cls, config: SolverConfig):
        return cls('started_configure', cls.create_timestamp(), {'config': config})

    @classmethod
    def create_completed_configure(cls):
        return cls('completed_configure', cls.create_timestamp(), {})

    @classmethod
    def create_started_path_solve(cls, action_sequence: ActionSequence):
        return cls('started_path_solve', cls.create_timestamp(), {'action_sequence': action_sequence})

    @classmethod
    def create_completed_path_solve(cls):
        return cls('completed_path_solve', cls.create_timestamp(), {})

    @classmethod
    def create_started_subtree_solve(cls, action_sequence: ActionSequence, solve_depth: int):
        return cls('started_subtree_solve', cls.create_timestamp(), {   'action_sequence': action_sequence,
                                                                        'solve_depth': solve_depth  })
    @classmethod
    def create_completed_subtree_solve(cls):
        return cls('completed_subtree_solve', cls.create_timestamp(), {})

    @classmethod
    def create_started_cancel(cls):
        return cls('started_cancel', cls.create_timestamp(), {})

    @classmethod
    def create_completed_cancel(cls):
        return cls('completed_cancel', cls.create_timestamp(), {})

    @classmethod
    def create_started_close(cls):
        return cls('started_close', cls.create_timestamp(), {})

    @classmethod
    def create_completed_close(cls):
        return cls('completed_close', cls.create_timestamp(), {})

    @classmethod
    def create_received_ipc_message(cls, ipc_message: IpcMessage):
        return cls('received_ipc_message', cls.create_timestamp(), {'ipc_message': ipc_message})

    @classmethod
    def create_raised_exception(cls, e: Exception):
        return cls('raised_exception', cls.create_timestamp(), {'exception': e})

    def __init__(self, event_type: str, timestamp: int, fields: dict):
        self._event_type = event_type
        self._timestamp = timestamp
        self._fields = fields

    def event_type(self):
        return self._event_type

    def timestamp(self):
        return self._timestamp

    def fields(self):
        return self._fields

    def __str__(self):
        return f"{self.event_type()}({self.timestamp()}, {self.fields()})"



class SolverProcessTester:

    def __init__(self, solver_process_client):
        self._solver_process_client = solver_process_client
        self._event_log = []

    def event_log(self):
        return self._event_log

    def clear_event_log(self):
        self._event_log = []

    def record_event(self, event: SolverProcessTestEvent):
        self._event_log.append(event)

    async def initialize(self, timeout: float = 0, notification_timeout: float = 0):
        self.record_event(SolverProcessTestEvent.create_started_initialization())
        try:
            await self._solver_process_client.initialize(timeout, notification_timeout)
        except Exception as e:
            self.record_event(SolverProcessTestEvent.create_raised_exception(e))
            logger.info(f"Ignoring exception `{e}` in {self.__class__.__name__}.initialize() as it will be in the event log")
        finally:
            self.record_event(SolverProcessTestEvent.create_completed_initialization())


    def configure(self, config: SolverConfig):
        self.record_event(SolverProcessTestEvent.create_started_configure(config))
        try:
            self._solver_process_client.configure(config)
        except Exception as e:
            self.record_event(SolverProcessTestEvent.create_raised_exception(e))
            logger.info(f"Ignoring exception `{e}` in {self.__class__.__name__}.configure() as it will be in the event log")
        finally:
            self.record_event(SolverProcessTestEvent.create_completed_configure())

    async def cancel(self, timeout: float = 0, notification_timeout: float = 0):
        self.record_event(SolverProcessTestEvent.create_started_cancel())
        try:
            await self._solver_process_client.cancel(timeout, notification_timeout)
        except Exception as e:
            self.record_event(SolverProcessTestEvent.create_raised_exception(e))
            logger.info(f"Ignoring exception `{e}` in {self.__class__.__name__}.cancel() as it will be in the event log")
        finally:
            self.record_event(SolverProcessTestEvent.create_completed_cancel())
        
    async def close(self):
        self.record_event(SolverProcessTestEvent.create_started_close())
        try:
            await self._solver_process_client.close()
        except Exception as e:
            self.record_event(SolverProcessTestEvent.create_raised_exception(e))
            logger.info(f"Ignoring exception `{e}` in {self.__class__.__name__}.close() as it will be in the event log")
        finally:
            self.record_event(SolverProcessTestEvent.create_completed_close())


    async def solve_subtree_as_ipc_messages(self, action_sequence: ActionSequence,
                                                    solve_depth: int,
                                                    timeout: float = 0,
                                                    notification_timeout: float = 0) -> typing.AsyncIterator[IpcMessage]:
        self.record_event(SolverProcessTestEvent.create_started_subtree_solve(  action_sequence,
                                                                                solve_depth  ))
        try:
            async for ipc_message in self._solver_process_client.solve_subtree_as_ipc_messages(   action_sequence,
                                                                                                solve_depth,
                                                                                                timeout,
                                                                                                notification_timeout  ):
                self.record_event(SolverProcessTestEvent.create_received_ipc_message(ipc_message))
                yield ipc_message
        except Exception as e:
            self.record_event(SolverProcessTestEvent.create_raised_exception(e))
            logger.info(f"Ignoring exception `{e}` in {self.__class__.__name__}.solve_subtree_as_ipc_messages() as it will be in the event log")
        finally:
            self.record_event(SolverProcessTestEvent.create_completed_subtree_solve())


    async def solve_path_as_ipc_messages(self, action_sequence: ActionSequence,
                                                timeout: float = 0,
                                                notification_timeout: float = 0) -> typing.AsyncIterator[IpcMessage]:
        self.record_event(SolverProcessTestEvent.create_started_path_solve(action_sequence))
        try:
            async for ipc_message in self._solver_process_client.solve_path_as_ipc_messages(  action_sequence,
                                                                                            timeout,
                                                                                            notification_timeout ):
                self.record_event(SolverProcessTestEvent.create_received_ipc_message(ipc_message))
                yield ipc_message
        except Exception as e:
            self.record_event(SolverProcessTestEvent.create_raised_exception(e))
            logger.info(f"Ignoring exception `{e}` in {self.__class__.__name__}.solve_path_as_ipc_messages() as it will be in the event log")
        finally:
            self.record_event(SolverProcessTestEvent.create_completed_path_solve())


    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_value, traceback):
        return await self._solver_process_client.__aexit__(exc_type, exc_value, traceback)



