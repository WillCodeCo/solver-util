import typing
import asyncio
import logging
from titan.solver_util.solver_process.async_task_wrapper import (
    AsyncTaskWrapper
)
from titan.solver_util.solver_process.solver_process_client import (
    SolverProcessClient  
)

logger = logging.getLogger(__name__)


class SolverProcessClientProviderException(Exception):
    pass

class SolverProcessClientProvider(AsyncTaskWrapper):

    def __init__(self, solver_process_client_class: typing.Type[SolverProcessClient], initialize_timeout: int):
        super().__init__(coro=self.process_provider_loop())
        self._solver_process_client_class = solver_process_client_class
        self._initialize_timeout = initialize_timeout
        self._solver_fut = None
        self._is_reserved = False
        self._cycle_process_fut = None

    def has_solver(self):
        return (    (self.has_started()) and 
                    (self._solver_fut.done()) and
                    (not self._solver_fut.cancelled()) and
                    (self._solver_fut.exception() is None)   )

    def is_reserved(self) -> bool:
        return self._is_reserved

    def is_available(self):
        return self.has_solver() and (not self.is_reserved())

    def is_initializing(self):
        return (    (self.has_started()) and 
                    (not self._solver_fut.done())  )

    def is_restarting(self):
        return (    (self._cycle_process_fut is not None) and 
                    (self._cycle_process_fut.done()) and
                    (not self._cycle_process_fut.cancelled()) and
                    (self._cycle_process_fut.exception() is None)   )

    async def wait_for_solver(self):
        if (not self.has_started()):
            raise SolverProcessClientProviderException((  f"Cannot call {self.__class__.__name__}.wait_for_solver() since " +
                                                    f"{self.__class__.__name__} has not been started yet !"  ))
        elif (not self.active()):
            raise SolverProcessClientProviderException((  f"Cannot call {self.__class__.__name__}.wait_for_solver() since " +
                                                    f"{self.__class__.__name__} is not active !"  ))
        if self.has_solver():
            return
        else:
            await asyncio.shield(self._solver_fut)

    def reserve_solver(self):
        if (not self.has_solver()):
            raise SolverProcessClientProviderException((  f"Cannot call {self.__class__.__name__}.reserve_solver() since " +
                                                    f"{self.__class__.__name__} doesn't have a solver ready !"  ))
        elif self.is_reserved():
            raise SolverProcessClientProviderException((  f"Cannot call {self.__class__.__name__}.reserve_solver() since " +
                                                    f"{self.__class__.__name__} is already reserved !"  ))
        elif self.is_restarting():
            raise SolverProcessClientProviderException((  f"Cannot call {self.__class__.__name__}.reserve_solver() since " +
                                                    f"{self.__class__.__name__} is restarting !"  ))
        self._is_reserved = True
        return self._solver_fut.result()

    def release_reservation(self):
        self._is_reserved = False

    def restart_solver_process(self):
        if (not self.has_solver()):
            raise SolverProcessClientProviderException((  f"Cannot call {self.__class__.__name__}.restart_solver_process() since " +
                                                    f"{self.__class__.__name__} doesn't have a solver ready !"  ))
        # signal we need to cycle the process
        self._solver_fut = asyncio.get_running_loop().create_future()
        self._cycle_process_fut.set_result(True)


    async def process_provider_loop(self):
        try:
            while True:
                logger.info(f"Starting a new solver process")
                try:
                    async with self._solver_process_client_class() as solver:
                        await solver.initialize(timeout=self._initialize_timeout)
                        self._cycle_process_fut = asyncio.get_running_loop().create_future()
                        self._solver_fut.set_result(solver)
                        logger.info("solver process ready")
                        await self._cycle_process_fut
                except Exception as e:
                    logger.error(f"Uncaught exception : {e}", exc_info=True)
                    raise
        finally:
            logger.info(f"Exiting {self.__class__.__name__}.process_provider_loop()")


    async def start(self):
        self._solver_fut = asyncio.get_running_loop().create_future()
        await super().start()

    async def close(self):
        if (self.has_solver()):
            self._cycle_process_fut.cancel()
        await super().close()
