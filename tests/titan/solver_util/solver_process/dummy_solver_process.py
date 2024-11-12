import typing
from multiprocessing import (
    Process
)
from multiprocessing.connection import (
    Connection
)
from titan.solver_util.spot_models import (
    ActionSequence
)
from titan.solver_util.solver_process import (
    SolverProcessLogging,
    SolverProcessDaemon,
    SolverProcessClient,
    SolverImplementation
)
from tests.titan.solver_util.solver_process.dummy_solver import (
    DummyConfig
)

logger = SolverProcessLogging.get_logger(__name__)


class DummySolverProcessDaemonFactory:

    @classmethod
    def create(cls, solver_implementation: SolverImplementation):
        # the class
        class DummySolverProcessDaemon(SolverProcessDaemon):
            @classmethod
            def run(cls, parent_connection: Connection, child_connection: Connection, log_directory: str):
                super().run(solver_implementation, parent_connection, child_connection, log_directory)
        return DummySolverProcessDaemon

class DummySolverProcessClient(SolverProcessClient):

    def __init__(self, solver_implementation: SolverImplementation):
        SolverProcessClient.__init__(self)
        self._solver_implementation = solver_implementation


    def create_process(self, parent_connection: Connection, child_connection: Connection, log_directory: str) -> Process:        
        daemon = DummySolverProcessDaemonFactory.create(self._solver_implementation)
        return Process( target=daemon.run,
                        args=(parent_connection, child_connection, log_directory) )




