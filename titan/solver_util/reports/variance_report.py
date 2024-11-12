from __future__ import annotations
import typing
import pathlib
import os
from titan.solver_util.solution_tree import (
    SolutionTree,
    SolutionTreeNode,
    StrategyOption,
    RaiseOption,
    FoldOption,
    CallOption,
    CheckOption
)
from titan.solver_util.preflop_solver.preflop_range_map import (
    PreflopRangeMap
)
from titan.solver_util.postflop_solver.postflop_range_map import (
    PostflopRangeMap
)



class _EvVarianceTableEntry:

    __slots__ = ('_hand', '_ev_matrix')

    def __init__(self, hand: str, ev_matrix: typing.Tuple[typing.Tuple[float, ...]]):
        self._hand = hand
        self._ev_matrix = ev_matrix

    def hand(self) -> str:
        return self._hand

    def ev_matrix(self) -> typing.Tuple[typing.Tuple[float, ...]]:
        return self._ev_matrix

    def __str__(self):
        num_options = len(self.ev_matrix()[0])
        min_evs = tuple(min(evs[i] for evs in self.ev_matrix())
                                    for i in range(num_options))
        max_evs = tuple(max(evs[i] for evs in self.ev_matrix())
                                    for i in range(num_options))
        ev_columns = '\t\t'.join((f"[{min_ev} ... {max_ev}] ".center(20) for min_ev, max_ev in zip(min_evs, max_evs)))
        return f"{self.hand().ljust(4)}\t\t{ev_columns}"

class _StrategyVarianceTableEntry:

    __slots__ = ('_hand', '_frequency_matrix')

    def __init__(self, hand: str, frequency_matrix: typing.Tuple[typing.Tuple[float, ...]]):
        self._hand = hand
        self._frequency_matrix = frequency_matrix

    def hand(self) -> str:
        return self._hand

    def frequency_matrix(self) -> typing.Tuple[typing.Tuple[float, ...]]:
        return self._frequency_matrix

    def __str__(self):
        num_options = len(self.frequency_matrix()[0])
        min_frequencies = tuple(min(frequencies[i] for frequencies in self.frequency_matrix())
                                    for i in range(num_options))
        max_frequencies = tuple(max(frequencies[i] for frequencies in self.frequency_matrix())
                                    for i in range(num_options))
        freq_columns = '\t\t'.join((f"[{min_freq * 100:>5.1f}% ... {max_freq * 100:>5.1f}%] ".center(20) for min_freq, max_freq in zip(min_frequencies, max_frequencies)))
        return f"{self.hand().ljust(4)}\t\t{freq_columns}"



class _StrategyVarianceTable:

    __slots__ = ('_strategy_options', '_entries')

    MAX_FREQUENCY = 10000

    def __init__(self, strategy_options: typing.Tuple[StrategyOption, ...], entries: typing.Tuple[_StrategyVarianceTableEntry, ...]):
        self._strategy_options = strategy_options
        self._entries = entries

    def strategy_options(self) -> typing.Tuple[StrategyOption, ...]:
        return self._strategy_options

    def entries(self) -> typing.Tuple[_StrategyTableEntry, ...]:
        return self._entries

    def is_leaf(self) -> bool:
        return len(self._entries) == 0

    def __str__(self):
        if self.is_leaf():
            return f"(No strategy variance table available)"
        header_items = ('HAND', ) + tuple(str(opt).center(20) for opt in self.strategy_options())
        spacer_row = "-" * 25 * len(header_items)
        header_row = '\t\t'.join(header_items)
        rows = '\n'.join(str(entry) for entry in self.entries())
        return header_row + '\n' + spacer_row + '\n' + rows


    @classmethod
    def create_from_solution_tree_nodes(cls, solution_tree_nodes: typing.Tuple[SolutionTreeNode, ...]):
        if not solution_tree_nodes:
            raise ValueError((  f"Could not call {cls.__name__}.create_from_solution_tree_nodes() " +
                                f"without any solution_tree_nodes !"  ))
        elif any(sn.solved_spot().strategy_options() != solution_tree_nodes[0].solved_spot().strategy_options()
                    for sn in solution_tree_nodes):
            raise ValueError((  f"Could not call {cls.__name__}.create_from_solution_tree_nodes() " +
                                f"with solution_tree_nodes that have different strategy options !"  ))
        elif any(sn.solved_spot().strategy_matrix().shape() != solution_tree_nodes[0].solved_spot().strategy_matrix().shape()
                    for sn in solution_tree_nodes):
            raise ValueError((  f"Could not call {cls.__name__}.create_from_solution_tree_nodes() " +
                                f"with solution_tree_nodes that have different shaped strategy matrices !"  ))
        elif solution_tree_nodes[0].solved_spot().is_leaf_spot():
            return cls( strategy_options=(),
                        entries=() )
        elif solution_tree_nodes[0].solved_spot().strategy_matrix().shape()[0] == PreflopRangeMap.RANGE_SIZE:          
            options = solution_tree_nodes[0].solved_spot().strategy_options()
            entries = (_StrategyVarianceTableEntry( hand=PreflopRangeMap.hand_for_index(i),
                                                    frequency_matrix=tuple(tuple(sn.solved_spot().strategy_matrix().values()[i] / cls.MAX_FREQUENCY
                                                                            for sn in solution_tree_nodes))) for i in range(PreflopRangeMap.RANGE_SIZE))
            return cls( strategy_options=options,
                        entries=tuple(entries) )
        elif solution_tree_nodes[0].solved_spot().strategy_matrix().shape()[0] == PostflopRangeMap.RANGE_SIZE:
            options = solution_tree_nodes[0].solved_spot().strategy_options()
            entries = (_StrategyVarianceTableEntry( hand=PostflopRangeMap.hand_for_index(i),
                                                    frequency_matrix=tuple(tuple(sn.solved_spot().strategy_matrix().values()[i] / cls.MAX_FREQUENCY
                                                                            for sn in solution_tree_nodes))) for i in range(PostflopRangeMap.RANGE_SIZE))
            return cls( strategy_options=options,
                        entries=tuple(entries) )
        else:
            raise ValueError((  f"Could not call {cls.__name__}.create_from_solution_tree_nodes() " +
                                f"with weirdly shaped strategy_matrix: {solution_tree_nodes[0].solved_spot().strategy_matrix().shape()}!"  ))


class _EvVarianceTable:

    def __init__(self, strategy_options: typing.Tuple[StrategyOption, ...], entries: typing.Tuple[_EvVarianceTableEntry, ...]):
        self._strategy_options = strategy_options
        self._entries = entries

    def strategy_options(self) -> typing.Tuple[StrategyOption, ...]:
        return self._strategy_options

    def entries(self) -> typing.Tuple[_EvVarianceTableEntry, ...]:
        return self._entries

    def is_leaf(self) -> bool:
        return len(self._entries) == 0

    def __str__(self):
        if self.is_leaf():
            return f"(No EV variance table available)"
        header_items = ('HAND', ) + tuple(str(opt).center(20) for opt in self.strategy_options())
        spacer_row = "-" * 25 * len(header_items)
        header_row = '\t\t'.join(header_items)
        rows = '\n'.join(str(entry) for entry in self.entries())
        return header_row + '\n' + spacer_row + '\n' + rows

    @classmethod
    def create_from_solution_tree_nodes(cls, solution_tree_nodes: typing.Tuple[SolutionTreeNode, ...]):
        if not solution_tree_nodes:
            raise ValueError((  f"Could not call {cls.__name__}.create_from_solution_tree_nodes() " +
                                f"without any solution_tree_nodes !"  ))
        elif any(sn.solved_spot().strategy_options() != solution_tree_nodes[0].solved_spot().strategy_options()
                    for sn in solution_tree_nodes):
            raise ValueError((  f"Could not call {cls.__name__}.create_from_solution_tree_nodes() " +
                                f"with solution_tree_nodes that have different strategy options !"  ))
        elif any(sn.solved_spot().ev_matrix().shape() != solution_tree_nodes[0].solved_spot().ev_matrix().shape()
                    for sn in solution_tree_nodes):
            raise ValueError((  f"Could not call {cls.__name__}.create_from_solution_tree_nodes() " +
                                f"with solution_tree_nodes that have different shaped EV matrices !"  ))
        elif solution_tree_nodes[0].solved_spot().is_leaf_spot():
            return cls( strategy_options=(),
                        entries=() )
        elif solution_tree_nodes[0].solved_spot().ev_matrix().shape()[0] == PreflopRangeMap.RANGE_SIZE:          
            options = solution_tree_nodes[0].solved_spot().strategy_options()
            entries = (_EvVarianceTableEntry(   hand=PreflopRangeMap.hand_for_index(i),
                                                ev_matrix=tuple(tuple(sn.solved_spot().ev_matrix().values()[i]
                                                                        for sn in solution_tree_nodes))) for i in range(PreflopRangeMap.RANGE_SIZE))
            return cls( strategy_options=options,
                        entries=tuple(entries) )
        elif solution_tree_nodes[0].solved_spot().ev_matrix().shape()[0] == PostflopRangeMap.RANGE_SIZE:
            options = solution_tree_nodes[0].solved_spot().strategy_options()
            entries = (_EvVarianceTableEntry(   hand=PostflopRangeMap.hand_for_index(i),
                                                ev_matrix=tuple(tuple(sn.solved_spot().ev_matrix().values()[i]
                                                                        for sn in solution_tree_nodes))) for i in range(PostflopRangeMap.RANGE_SIZE))
            return cls( strategy_options=options,
                        entries=tuple(entries) )
        else:
            raise ValueError((  f"Could not call {cls.__name__}.create_from_solution_tree_nodes() " +
                                f"with weirdly shaped ev_matrix !"  ))


class _ReportNode:

    __slots__ = (   '_strategy_variance_table',
                    '_ev_variance_table',
                    '_children'  )


    def __init__(self, strategy_variance_table: _StrategyTable, ev_variance_table: _EvVarianceTable, children: typing.Dict[str, _ReportNode]):
        self._strategy_variance_table = strategy_variance_table
        self._ev_variance_table = ev_variance_table
        self._children = dict(children)

    def strategy_variance_table(self) -> _StrategyVarianceTable:
        return self._strategy_variance_table

    def ev_variance_table(self) -> _EvVarianceTable:
        return self._ev_variance_table

    def children(self) -> typing.Dict[str, _ReportNode]:
        return self._children

    def has_child(self, child_name: str) -> bool:
        return (child_name in self._children)

    def add_child(self, child_name: str, child_report_node: _ReportNode):
        if self.has_child(child_name):
            raise ValueError(f"Cannot add_child() in {self.__class__.__name__} since child_name `{child_name}` already exists !")
        self._children[child_name] = child_report_node

    def gen_nodes_bfs(self):
        to_visit = [(None, self)]
        while to_visit:
            name, cur_node = to_visit.pop(0)
            for child_name, child_report_node in cur_node.children().items():
                to_visit.append((child_name, child_report_node))
            yield (name, cur_node)

    def save_to_filesystem(self, path: str):
        cur_path = pathlib.Path(path)
        if not cur_path.is_dir():
            raise ValueError(f"Cannot call {self.__class__.__name__}.save_to_filesystem() for a path `{path}` that does not represent a directory")
        # save strategy variance table
        with open(cur_path / 'strategy-variance.txt', 'w') as f:
            f.write(str(self.strategy_variance_table()))
        # save EV variance table
        with open(cur_path / 'ev-variance.txt', 'w') as f:
            f.write(str(self.ev_variance_table()))
        # recurse down for children
        for child_name, child_node in self.children().items():
            # make a directory for child
            child_path = (cur_path / child_name)
            if not child_path.is_dir():
                child_path.mkdir()
            child_node.save_to_filesystem(child_path)

    @classmethod
    def create_from_solution_tree_nodes(cls, solution_tree_nodes: typing.Tuple[SolutionTreeNode, ...], children: typing.Dict[str, _ReportNode]):
        return cls( strategy_variance_table=_StrategyVarianceTable.create_from_solution_tree_nodes(solution_tree_nodes),
                    ev_variance_table=_EvVarianceTable.create_from_solution_tree_nodes(solution_tree_nodes),
                    children={} )



class VarianceStreetReport:


    def __init__(self, root_report_node: _ReportNode):
        self._root_report_node = root_report_node

    def root_report_node(self):
        return self._root_report_node

    def gen_nodes_bfs(self):
        yield from self.root_report_node().gen_nodes_bfs()

    def save_to_filesystem(self, path: str):
        self.root_report_node().save_to_filesystem(path)


    @classmethod
    def create(cls, solution_trees: typing.Tuple[SolutionTree]) -> VarianceStreetReport:
        root_report_node = None
        report_node_lookup = {}
        node_generators = [st.gen_nodes_in_bfs_traversal() for st in solution_trees]
        for solution_tree_nodes in zip(*node_generators):
            report_node = _ReportNode.create_from_solution_tree_nodes(  solution_tree_nodes=solution_tree_nodes,
                                                                        children={}  )
            action_sequence = solution_tree_nodes[0].action_sequence()
            report_node_lookup[action_sequence] = report_node
            if root_report_node is not None:
                parent_report_node = report_node_lookup[action_sequence[:-1]]
                child_name = str(action_sequence[-1])
                parent_report_node.add_child(child_name, report_node)
            else:
                root_report_node = report_node
        if not root_report_node:
            raise ValueError(f"Cannot call {cls.__name__}.create() without any solution_trees !")
        return root_report_node




class VarianceReport:

    __slots__ = ('_variance_street_reports',)

    def __init__(self, variance_street_reports: typing.Tuple[VarianceStreetReport, ...]):
        self._variance_street_reports = variance_street_reports

    def save_to_filesystem(self, path: str):
        sub_report_names = ('preflop', 'flop', 'turn', 'river')
        cur_path = pathlib.Path(path)
        for sub_report_name, report in zip(sub_report_names, self._variance_street_reports):
            child_path = (cur_path / sub_report_name)
            if not child_path.is_dir():
                child_path.mkdir()
            report.save_to_filesystem(child_path)


    @classmethod
    def create(cls, hand_history: HandHistory, preflop_solution_trees: typing.Tuple[SolutionTree, ...],
                                                flop_solution_trees: typing.Tuple[SolutionTree, ...],
                                                turn_solution_trees: typing.Tuple[SolutionTree, ...],
                                                river_solution_trees: typing.Tuple[SolutionTree, ...]) -> VarianceReport:

        if not preflop_solution_trees:
            raise ValueError(f"Cannot call {cls.__name__}.create() without any preflop_solution_trees !")
        elif not flop_solution_trees:
            return cls(variance_street_reports=(VarianceStreetReport.create(preflop_solution_trees),))
        elif not turn_solution_trees:
            return cls(variance_street_reports=(VarianceStreetReport.create(preflop_solution_trees),
                                                VarianceStreetReport.create(flop_solution_trees)))
        elif not river_solution_trees:
            return cls(variance_street_reports=(VarianceStreetReport.create(preflop_solution_trees),
                                                VarianceStreetReport.create(flop_solution_trees),
                                                VarianceStreetReport.create(turn_solution_trees)))
        else:
            return cls(variance_street_reports=(    VarianceStreetReport.create(preflop_solution_trees),
                                                    VarianceStreetReport.create(flop_solution_trees),
                                                    VarianceStreetReport.create(turn_solution_trees),
                                                    VarianceStreetReport.create(river_solution_trees) ))