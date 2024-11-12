import logging
import pytest
import random
import string
import tempfile
import pathlib
from titan.solver_util.spot_models import (
    ActionSequence
)
from titan.solver_util.solution_tree import (
    RandomValueFactory,
    SolutionTree,
    SolutionTreeException
)
from titan.solver_util.solving_session import (
    SolverResult,
    FailedSolve,
    CompletedSolve,
    SolverResultSerializer,
    SolverResultDeserializer,
    SolvingSession
)


logger = logging.getLogger(__name__)


def gen_rand_strings(count: int):
    for _ in range(count):
        yield ''.join(random.choices(string.ascii_uppercase + string.digits, k = random.randint(10, 50)))

def gen_rand_dicts(count: int):
    result = {}
    for _ in range(count):
        result[next(gen_rand_strings(1))] = next(gen_rand_strings(1))
    return result


def gen_rand_paths(count: int, max_depth: int):
    result = set()
    path_elems = list(gen_rand_strings(15))
    while len(result) < count:
        depth = random.randint(1, max_depth)
        path = tuple(random.choices(path_elems, k=depth))
        if path not in result:
            yield path
            result.add(path)


def gen_rand_solver_results(count: int):

    for _ in range(count):

        if random.choices([True, False]):
            solution_tree = RandomValueFactory.create_solution_tree(tree_height=7,
                                                                    range_size=169,
                                                                    num_bet_sizes=1 )
            yield CompletedSolve(   log_lines=tuple(gen_rand_strings(10)),
                                    output_lines=tuple(gen_rand_strings(10)),
                                    error_lines=tuple(gen_rand_strings(10)),
                                    event_dicts=tuple(gen_rand_dicts(20)),
                                    solution_tree=solution_tree )
        else:
            yield FailedSolve(  log_lines=tuple(gen_rand_strings(10)),
                                output_lines=tuple(gen_rand_strings(10)),
                                error_lines=tuple(gen_rand_strings(10)),
                                event_dicts=tuple(gen_rand_dicts(20)),
                                exception_msg=next(gen_rand_strings(1)) )


def gen_path_solver_results(cur_path, solving_session):
    for session_name in solving_session.gen_solving_session_names():
        child_path = cur_path + (session_name,)
        yield from gen_path_solver_results(child_path, solving_session.get_solving_session(session_name))
    for solver_result_name in solving_session.gen_solver_result_names():
        child_path = cur_path + (solver_result_name,)
        yield (child_path, solving_session.get_solver_result(solver_result_name))


def test_serialize_deserialize_solver_result():

    failed_solve = FailedSolve( log_lines=tuple(gen_rand_strings(10)),
                                output_lines=tuple(gen_rand_strings(10)),
                                error_lines=tuple(gen_rand_strings(10)),
                                event_dicts=tuple(gen_rand_dicts(20)),
                                exception_msg=next(gen_rand_strings(1)) )

    solution_tree = RandomValueFactory.create_solution_tree(tree_height=7,
                                                            range_size=169,
                                                            num_bet_sizes=1 )

    completed_solve = CompletedSolve(   log_lines=tuple(gen_rand_strings(10)),
                                        output_lines=tuple(gen_rand_strings(10)),
                                        error_lines=tuple(gen_rand_strings(10)),
                                        event_dicts=tuple(gen_rand_dicts(20)),
                                        solution_tree=solution_tree )
    # failed solve test
    with tempfile.TemporaryDirectory() as working_dir:
        working_path = pathlib.Path(working_dir)
        SolverResultSerializer.serialize_to_filesystem(working_dir, failed_solve)
        failed_solve_clone = SolverResultDeserializer.deserialize_from_filesystem(working_dir)
        assert failed_solve == failed_solve_clone
    # completed solve test
    with tempfile.TemporaryDirectory() as working_dir:
        working_path = pathlib.Path(working_dir)
        SolverResultSerializer.serialize_to_filesystem(working_dir, completed_solve)
        completed_solve_clone = SolverResultDeserializer.deserialize_from_filesystem(working_dir)
        assert completed_solve == completed_solve_clone



def test_create_solving_session():
    NUM_SOLVES = 10
    expected_session_tree = {}
    # make a random hierachy for the solver results
    for path_tuple, solver_result in zip(   gen_rand_paths(NUM_SOLVES, 4),
                                            gen_rand_solver_results(NUM_SOLVES)  ):
        result_name = next(gen_rand_strings(1))
        expected_session_tree[path_tuple + (result_name,)] = solver_result
    # create a solving session and check it
    with tempfile.TemporaryDirectory() as working_dir:
        solving_session = SolvingSession.create_empty(working_dir)
        for path_tuple, solver_result in expected_session_tree.items():
            cur_session = solving_session
            for path_elem in path_tuple[:-1]:
                try:
                    cur_session = cur_session.get_solving_session(path_elem)
                except ValueError:
                    cur_session = cur_session.create_solving_session(path_elem)
            cur_session.add_solver_result(path_tuple[-1], solver_result)
        # ensure it matches expected
        solving_session_clone = SolvingSession.create_from_path(working_dir)
        session_tree = dict(gen_path_solver_results((), solving_session_clone))
        assert session_tree == expected_session_tree