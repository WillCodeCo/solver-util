# solver-util

## Install

```
virtualenv .env
source .env/bin/activate
$ .env) pip install git+ssh://git@github.com/WillCodeCo/solver-util.git

```


## Scripts


```
...
```


## Run the tests

```
virtualenv .env
source .env/bin/activate
pip install -e .[test]
python -m pytest -s
```

## Brief documentation


### `ActionSequence` as paths to *spots* within a poker game tree

`ActionSequence` is a light wrapper around a `typing.Tuple[str]` type. It is used for referring to spots within the solution tree. They are used as paths.

For example, the path for the root spot is `ActionSequence(())`  or `ActionSequence.create_empty()`

Additionally, we can make use of a `create_from_string(...)`  convenience method as follows:

```
action_sequence = ActionSequence.create_from_string('ccfr100')
```

### `SolvedSpot` as the solver's result for a particular spot in the game tree

`SolvedSpot` is a representation of a solver result for a particular spot in the poker game tree. Each solved spot has the solver's strategy associated with it.

We can enumerate the possible options (`StrategyOption` type) open for the player to do, according to the solver's strategy, as follows:

```
options = some_solved_spot.strategy_options()

assert all((isinstance(opt, StrategyOption) for opt in options))
assert FoldOption() in options
assert (CheckOption() in options) or (CallOption() in options)

# and raise options too
for opt in options:
    if type(opt) != RaiseOption:
        continue
    assert opt.amount() > 0

```

We can examine the strategy matrix as follows:

```
strat_value  = some_solved_spot.strategy_matrix()[hand_idx][option_idx]

assert type(strat_value) == int 
```
- `hand_idx` represents the strategy for a particular hand in the range
- `option_idx` is the index of the `StrategyOption` in `some_solved_spot.strategy_options()`
- The strategy values are integers in the range `[0, 10000]`, and the sum of strategy values for the same hand will sum to a value close to but not exceeding `10000`

We can examine the EV matrix as follows:

```
ev_value = some_solved_spot.ev_matrix()[hand_idx][option_idx]

assert type(ev_value) == int
```
- `hand_idx` represents the strategy for a particular hand in the range
- `option_idx` is the index of the `StrategyOption` in `some_solved_spot.strategy_options()`
- The EV values are integers (negative or positive) representing the EV of the player performing the corresponding action.


We can also check to see if the `SolvedSpot` is a leaf node or not, i.e. whether it is a final spot due to the street being satisfied or the hand being over.

```
assert some_solved_spot.is_leaf_spot() in {True, False}
```

### `SolutionTree` encompasses the solver's result

The `SolutionTree` allows for querying and traversing the result of the solver.

**Retrieve a single node**
```
some_action_sequence = ActionSequence.create_from_string('ccf')
node = tree.get_node(ActionSequence.create_from_string(some_action_sequence))
```

**look at node's children**
```
for n in node.children():
    assert type(n.action_sequence()) == ActionSequence
```

**perform a path traversal from the root**
```
nodes = list(tree.gen_nodes_on_path())

# root node will be there
assert nodes[0] == tree.root_node()

# last node will be the one at the end of the path
assert nodes[-1] == tree.get_node(some_action_sequence)

assert len(nodes) == len(some_action_sequence) + 1  # plus 1 to include root

```

**perform a breadth-first traversal from the root**
```
nodes = list(tree.gen_nodes_in_bfs_traversal())

# first node should be root
assert nodes[0] == tree.root_node()

# print the leaf spots
for n in nodes:
    if n.is_leaf_spot():
        print(f"{node.action_sequence()} is a leaf !")
```

**Traverse the descendants of a node**
```
nodes = list(node.gen_descendants_on_path(some_action_sequence))

# first node is a child of node
assert nodes[0] != node
assert nodes[0].parent() == node
```

### `BlobTree` for serialization of `SolutionTree`

**Deserialize `BlobTreeNode`s from bytes**
```
from titan.solver_util.blob_tree.wire_protocol import (
    Deserializer as BlobTreeNodeDeserializer
)

async def gen_blob_tree_nodes():
    async for blob_bytes in get_some_blob_bytes():
        blob_tree_node, _ = BlobTreeNodeDeserializer.deserialize_blob_tree_node(blob_bytes)
        yield blob_tree_node
```

**Re-construct a `SolutionTree` from `BlobTreeNode`s**
```
from titan.solver_util.solution_tree import (
    SolutionTreeBuilder
)
from titan.solver_util.solution_tree.wire_protocol import (
    Deserializer as SolvedSpotDeserializer
)

ROOT_NODE_ID = 0

async def build_a_tree():

    builder = SolutionTreeBuilder()
    async for blob_tree_node in gen_blob_tree_nodes():
        solved_spot, _ = SolvedSpotDeserializer.deserialize_solved_spot(blob_tree_node.blob_bytes())
        
        # is root node ?
        if blob_tree_node.node_id() == ROOT_NODE_ID:
            builder.create_root_node(   node_id=blob_tree_node.node_id(),
                                        solved_spot=solved_spot  )
        else:
            builder.create_child_node(  node_id=blob_tree_node.node_id(),
                                        parent_node_id=blob_tree_node.parent_node_id(),
                                        action_string=blob_tree_node.child_id(),
                                        solved_spot=solved_spot )

    return builder.build_solution_tree()

```


### Working with `PreflopSolverProcessClient`

```
from titan.preflop_solver import (
    PreflopSolverProcessClient,
    PreflopSolverConfig,
)
from titan.solver_util import (
    ActionSequence
)

async def perform_a_solve():
    pass

```

### Working with `PostflopSolverProcessClient`

```
from titan.postflop_solver import (
    PostflopSolverProcessClient,
    PostflopSolverConfig,
)
from titan.solver_util import (
    ActionSequence
)

async def perform_a_solve():
    pass

```