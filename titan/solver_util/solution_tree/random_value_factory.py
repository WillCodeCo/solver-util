import random
import typing
from numpy import typing as npt    
import numpy as np
from titan.solver_util.spot_models import (
    ActionSequence
)
from titan.solver_util.solution_tree.types import (
    StrategyOption,
    CheckOption,
    CallOption,
    FoldOption,
    RaiseOption,
    RangeMatrix,
    SolvedSpot,
    SolutionTreeNode,
    SolutionTree
)
from titan.solver_util.solution_tree.solution_tree_builder import (
    SolutionTreeBuilderException,
    SolutionTreeBuilder
)


class RandomValueFactory:

    ALREADY_FOLDED_RATIO = 0.1

    @classmethod
    def create_raise_option(cls):
        amount = random.randint(1, 10000)
        pot_size_ratio_bps = amount // 50 # for no reason
        return RaiseOption(amount, pot_size_ratio_bps)

    @classmethod
    def create_strategy_options(cls, can_check: bool, num_bet_sizes: int):
        raise_options = set()
        while len(raise_options) < num_bet_sizes:
            raise_options.add(cls.create_raise_option())
        raise_options = sorted(list(raise_options), key=lambda option: option.amount())
        if can_check:
            return (FoldOption(), CheckOption()) + tuple(raise_options)
        else:
            return (FoldOption(), CallOption()) + tuple(raise_options)

    @classmethod
    def create_range_matrix(cls, num_options: int, range_size: int):
        shape = (range_size, num_options)
        return RangeMatrix(np.random.randint(-100000, 100000, shape))


    @classmethod
    def create_strategy_matrix(cls, num_options: int, range_size: int):
        shape = (range_size, num_options)
        # rows must sum to 1.0
        matrix = np.random.rand(*shape).astype(np.float32)
        matrix = matrix/matrix.sum(axis=1)[:,None]
        matrix = (matrix * 10000)
        matrix = np.around(matrix, decimals=0).astype(np.int32)
        # amount of rounding error correction needed to sum properly
        correct_matrix = -(matrix.sum(axis=1) - 10000)
        delta_matrix = np.zeros(shape=shape)
        delta_matrix[np.arange(range_size), matrix.argmax(axis=1)] = correct_matrix[np.arange(range_size)]
        matrix = matrix + delta_matrix
        # choose some random rows to have a sum of 0
        random_rows = np.random.randint(0, range_size, (int(range_size * cls.ALREADY_FOLDED_RATIO),))
        matrix[random_rows] = np.zeros(shape=(num_options,))
        return RangeMatrix(matrix)

    @classmethod
    def create_ev_matrix(cls, num_options: int, range_size: int):
        return cls.create_range_matrix(num_options, range_size)

    @classmethod
    def create_solved_spot(cls, can_check: bool, num_bet_sizes: int, range_size: int):
        options = cls.create_strategy_options(can_check, num_bet_sizes)
        strategy_matrix = cls.create_strategy_matrix(   num_options=len(options),
                                                        range_size=range_size  )
        ev_matrix = cls.create_ev_matrix(   num_options=len(options),
                                            range_size=range_size  )
        return SolvedSpot(options, strategy_matrix, ev_matrix)

    @classmethod
    def create_leaf_solved_spot(cls):
        return SolvedSpot((), RangeMatrix.create_empty(), RangeMatrix.create_empty())



    @classmethod
    def create_children_for_options(cls, builder: SolutionTreeBuilder, parent_node_id: int,
                                                                options: typing.Iterable[StrategyOption],
                                                                node_ids: typing.Iterator[int],
                                                                depths: typing.Tuple[int],
                                                                range_size: int,
                                                                num_bet_sizes: int):
        for option in options:
            node_id = next(node_ids)
            # is leaf node
            if len(depths) == 1:
                builder.create_child_node(  node_id=node_id,
                                            parent_node_id=parent_node_id,
                                            action_string=option.action_string(),
                                            solved_spot=cls.create_leaf_solved_spot()  )
            else:
                solved_spot = cls.create_solved_spot(   can_check=random.choice([True, False]),
                                                        num_bet_sizes=num_bet_sizes,
                                                        range_size=range_size  )
                builder.create_child_node(  node_id=node_id,
                                            parent_node_id=parent_node_id,
                                            action_string=option.action_string(),
                                            solved_spot=solved_spot  )
                cls.create_children_for_options(builder=builder,
                                                parent_node_id=node_id,
                                                options=solved_spot.strategy_options(),
                                                node_ids=node_ids,
                                                depths=depths[1:],
                                                range_size=range_size,
                                                num_bet_sizes=num_bet_sizes)



    @classmethod
    def create_solution_tree(cls, tree_height: int, range_size: int, num_bet_sizes: int):
        num_children = num_bet_sizes + 2 # FOLD + Call/Check + bets/raise
        num_nodes = sum(num_children**depth for depth in range(tree_height+1))
        node_ids = (node_id for node_id in range(num_nodes))
        depths = tuple(range(tree_height+1))
        # make a builder
        builder = SolutionTreeBuilder()
        # create root node
        root_node_id = next(node_ids)
        root_solved_spot = cls.create_solved_spot(  can_check=False,
                                                    num_bet_sizes=num_bet_sizes,
                                                    range_size=range_size  )
        node = builder.create_root_node(node_id=root_node_id,
                                        solved_spot=root_solved_spot)
        # create the rest of the tree
        cls.create_children_for_options(builder=builder,
                                        parent_node_id=root_node_id,
                                        options=node.strategy_options(),
                                        node_ids=node_ids,
                                        depths=depths[1:],
                                        range_size=range_size,
                                        num_bet_sizes=num_bet_sizes)
        return builder.build_solution_tree()


    @classmethod
    def create_solution_tree_from_path(cls, tree_height: int,
                                            range_size: int,
                                            num_bet_sizes: int,
                                            action_sequence: ActionSequence):
        if len(action_sequence) > tree_height:
            raise ValueError(f"Cannot create a solution tree smaller than the length of the path")
        # make a builder
        builder = SolutionTreeBuilder()
        # iterate through the prefixes of action sequence
        for path_len, node_action_sequence in enumerate(action_sequence.gen_prefixes()):
            if path_len == 0:
                # root node ?
                builder.create_root_node(   node_id=path_len,
                                            solved_spot=cls.create_solved_spot( can_check=False,
                                                                                num_bet_sizes=num_bet_sizes,
                                                                                range_size=range_size  )   )
            elif path_len == tree_height:
                # last node, make a leaf !
                builder.create_child_node(  node_id=path_len,
                                            parent_node_id=(path_len - 1),
                                            action_string=str(node_action_sequence[-1]),
                                            solved_spot=cls.create_leaf_solved_spot()  )
            else:
                # try to make sensible choices for available actions
                if node_action_sequence == action_sequence:
                    can_check = random.choice([True, False])
                elif action_sequence[path_len] == 'x':
                    can_check = True
                elif action_sequence[path_len] == 'c':
                    can_check = False
                else:
                    can_check = random.choice([True, False])
                solved_spot = cls.create_solved_spot(   can_check=can_check,
                                                        num_bet_sizes=num_bet_sizes,
                                                        range_size=range_size  )
                builder.create_child_node(  node_id=path_len,
                                            parent_node_id=(path_len - 1),
                                            action_string=str(node_action_sequence[-1]),
                                            solved_spot=solved_spot  )
        return builder.build_solution_tree()