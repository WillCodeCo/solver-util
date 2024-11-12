from titan.solver_util.solver_process.types import (
    SolverConfig
)
from titan.solver_util.spot_models import (
    ActionSequence
)

class SolverImplementation:

    def solve_path(self, config: SolverConfig, action_sequence: ActionSequence):
        raise NotImplementedError

    def solve_subtree(self, config: SolverConfig, action_sequence: ActionSequence,
                                                            solve_depth: int):
        raise NotImplementedError

    def initialize(self):
        raise NotImplementedError

    def cancel(self):
        raise NotImplementedError

    def close(self):
        raise NotImplementedError