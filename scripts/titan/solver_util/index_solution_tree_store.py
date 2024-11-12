from __future__ import annotations
import typing
import pathlib
import logging
import argparse
from titan.solver_util.solution_tree_store import (
    SolutionTreeStore
)


logger = logging.getLogger(__name__)



class ArgValidator:

    @classmethod
    def ensure_valid_store_dir_path(cls, store_dir: str):
        store_path = pathlib.Path(store_dir)
        SolutionTreeStore.ensure_valid_store_path(store_path)
        assert not SolutionTreeStore.is_empty(store_path), f"Cannot index an empty store !"


class IndexScript:

    @classmethod
    def rebuild_index(cls, store_dir: str):
        store_path = pathlib.Path(store_dir)
        store = SolutionTreeStore.create_from_directory_and_rebuild_index(store_path=store_path)


def main():
    parser = argparse.ArgumentParser(description="Index Solution Tree Store")
    parser.add_argument("-s", "--store-dir", type=str, default=None, required=False, help="Path to solution tree store")
    args = parser.parse_args()

    # configure the logger
    logging.basicConfig(level=logging.INFO)

    try:
        ArgValidator.ensure_valid_store_dir_path(args.store_dir)
        IndexScript.rebuild_index(store_dir=args.store_dir)
    except Exception as e:
        print(f"Failed due to exception: {e}")
        raise


if __name__ == "__main__"   :
    main()


