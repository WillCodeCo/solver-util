import typing
from titan.solver_util.solution_tree import (
    SolutionTree,
    SolutionTreeNode,
    SolutionTreeBuilder,
)
from titan.solver_util.spot_models import (
    ActionSequence
)
from titan.solver_util.postflop_solver.types import (
    PostflopSolverConfig
)
from titan.solver_util.solver_process import (
    SolverProcessClient,
    SolverState,
    IpcMessage
)


class PostflopSolver:

    def __init__(self, solver_process_client: SolverProcessClient):
        self._solver_process_client = solver_process_client

    def state(self) -> SolverState:
        return self._solver_process_client.state()

    def is_solving(self) -> bool:
        return self._solver_process_client.is_solving()

    def is_ready(self) -> bool:
        return self._solver_process_client.is_ready()

    def is_cancelling(self) -> bool:
        return self._solver_process_client.is_cancelling()

    def is_closing(self) -> bool:
        return self._solver_process_client.is_closing()

    def is_closed(self) -> bool:
        return self._solver_process_client.is_closed()

    def ipc_message_store(self):
        return self._solver_process_client.ipc_message_store()


    async def initialize(self, timeout: float = 0, notification_timeout: float = 0):
        await self._solver_process_client.initialize(timeout, notification_timeout)

    def configure(self, config: PostflopSolverConfig):
        self._solver_process_client.configure(config)

    async def cancel(self, timeout: float = 0, notification_timeout: float = 0):
        await self._solver_process_client.cancel(timeout, notification_timeout)
        
    async def close(self):
        await self._solver_process_client.close()

    async def solve_subtree_as_ipc_messages(self, action_sequence: ActionSequence,
                                                    solve_depth: int,
                                                    timeout: float = 0,
                                                    notification_timeout: float = 0) -> typing.AsyncIterator[IpcMessage]:
        async for ipc_message in self._solver_process_client.solve_subtree_as_ipc_messages(  action_sequence=action_sequence,
                                                                                            solve_depth=solve_depth,
                                                                                            timeout=timeout,
                                                                                            notification_timeout=notification_timeout  ):
            yield ipc_message

    async def solve_path_as_ipc_messages(self, action_sequence: ActionSequence,
                                                timeout: float = 0,
                                                notification_timeout: float = 0) -> typing.AsyncIterator[IpcMessage]:
        async for ipc_message in self._solver_process_client.solve_path_as_ipc_messages( action_sequence=action_sequence,
                                                                                        timeout=timeout,
                                                                                        notification_timeout=notification_timeout):
            yield ipc_message


    async def solve_subtree_as_solution_tree_updates(self, action_sequence: ActionSequence,
                                                            solve_depth: int,
                                                            timeout: float = 0,
                                                            notification_timeout: float = 0) -> typing.AsyncIterator[typing.Tuple[SolutionTreeBuilder, SolutionTreeNode]]:
        async for update_tuple in self._solver_process_client.solve_subtree_as_solution_tree_updates(   action_sequence=action_sequence,
                                                                                                        solve_depth=solve_depth,
                                                                                                        timeout=timeout,
                                                                                                        notification_timeout=notification_timeout  ):
            yield update_tuple

    async def solve_path_as_solution_tree_updates(self, action_sequence: ActionSequence,
                                                        timeout: float = 0,
                                                        notification_timeout: float = 0) -> typing.AsyncIterator[typing.Tuple[SolutionTreeBuilder, SolutionTreeNode]]:
        async for update_tuple in self._solver_process_client.solve_path_as_solution_tree_updates(  action_sequence=action_sequence,
                                                                                                    timeout=timeout,
                                                                                                    notification_timeout=notification_timeout):
            yield update_tuple

    def gen_output_lines(self):
        yield from self._solver_process_client.gen_output_lines()

    def gen_log_lines(self):
        yield from self._solver_process_client.gen_log_lines()

    def gen_error_lines(self):
        yield from self._solver_process_client.gen_error_lines()

    def gen_event_dicts(self):
        yield from self._solver_process_client.gen_event_dicts()

    def shared_memory_usage(self) -> int:
        return self._solver_process_client.shared_memory_usage()

    def release_shared_memory(self):
        self._solver_process_client.release_shared_memory()

    async def __aenter__(self):
        await self._solver_process_client.__aenter__()
        return self

    async def __aexit__(self, exc_type, exc_value, traceback):
        await self._solver_process_client.__aexit__(exc_type, exc_value, traceback)