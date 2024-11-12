from __future__ import annotations
import typing
import pathlib
import tempfile
import gzip
import shutil
import json
import logging
import os
import argparse
from titan.solver_util.spot_models import (
    ActionSequence,
)
from titan.solver_util.solution_tree import (
    SolutionTree,
)
from titan.solver_util.solution_tree_store import (
    SolutionTreeStore
)


logger = logging.getLogger(__name__)



class ArgValidator:

    @classmethod
    def ensure_valid_store_dir_path(cls, store_dir: str):
        store_path = pathlib.Path(store_dir)
        assert not store_path.is_file(), f"store_dir `{store_dir}` is a path to a file not a directory !"
        assert store_path.is_dir(), f"store_dir `{store_dir}` is not a valid directory"
        is_empty = not any(store_path.iterdir())
        assert not is_empty, f"store_dir `{store_dir}` is empty !"

    @classmethod
    def ensure_valid_output_dir(cls, output_dir: str, force_overwrite: bool):
        output_path = pathlib.Path(output_dir)
        assert not output_path.is_file(), f"{output_dir} is a path to a file not a directory !"
        assert output_path.is_dir(), f"{output_dir} is not a valid directory"
        is_empty = not any(output_path.iterdir())
        assert is_empty or force_overwrite, f"{output_dir} is not empty. User the -f flag to overwrite"


class MigrationScript:

    @classmethod
    def clear_output_dir(cls, output_dir):
        for p in pathlib.Path(output_dir).iterdir():
            logger.info(f"Deleting `{p}`")
            if p.is_dir():
                shutil.rmtree(p, ignore_errors=True)
            else:
                os.remove(p)
                

    @classmethod
    def migrate(cls, store_dir: str, output_dir: str):
        old_store_path = pathlib.Path(store_dir)
        new_store_path = pathlib.Path(output_dir)

        store = SolutionTreeStore.create_empty(store_path=new_store_path)

        for gz_file_path in old_store_path.rglob('*.gz'):
            logger.info(f"Extracting `{gz_file_path}` ...")
            #
            key_file_path = gz_file_path.parent / 'key.json'
            # extract compressed solution tree
            tmp_file = tempfile.NamedTemporaryFile(delete=False)
            tmp_file_path = pathlib.Path(tmp_file.name)
            with gzip.open(gz_file_path, 'rb') as f_in:
                with open(tmp_file_path, 'wb') as f_out:
                    shutil.copyfileobj(f_in, f_out)
            tmp_file.close()
            logger.info(f"Extracted `{gz_file_path}` to `{tmp_file_path}`")
            # load the key json
            key_dict = None
            with open(key_file_path, 'r') as f:
                key_dict = json.loads(f.read())
            if (not key_dict):
                raise ValueError(f"Invalid key.json at path `{key_file_path}`")
            # add to new store
            if key_dict['solver_type'] == 'PREFLOP':
                store.add_preflop_solution_tree_from_path(  solver_config_dict=key_dict['solver_config'],
                                                            action_sequence=ActionSequence.create_from_string(key_dict['action_sequence']),
                                                            is_path_solve=(key_dict['solve_mode'] == 'PATH_SOLVE'),
                                                            solution_tree_path=tmp_file_path )
            elif key_dict['solver_type'] == 'POSTFLOP':
                store.add_postflop_solution_tree_from_path( solver_config_dict=key_dict['solver_config'],
                                                            action_sequence=ActionSequence.create_from_string(key_dict['action_sequence']),
                                                            is_path_solve=(key_dict['solve_mode'] == 'PATH_SOLVE'),
                                                            solution_tree_path=tmp_file_path  )
            else:
                raise ValueError(f"Invalid solver_type `{key_dict['solver_type']}`")
            # clean up
            tmp_file_path.unlink()
        # save index to file
        store.save_index()



def main():
    parser = argparse.ArgumentParser(description="Migrate Solution Tree Store")
    parser.add_argument("-s", "--store-dir", type=str, default=None, required=False, help="Path to previous version solution tree store")
    parser.add_argument("-o", "--output-dir", type=str, required=True, help="Path to output directory")
    parser.add_argument("-f", "--force-overwrite", action='store_true', default=False, required=False, help="Force overwrite of output dir")
    args = parser.parse_args()

    # configure the logger
    logging.basicConfig(level=logging.INFO)

    try:
        if args.output_dir == args.store_dir:
            raise ValueError(f"The output-dir should not be the same as the store-dir !")
        ArgValidator.ensure_valid_output_dir(args.output_dir, args.force_overwrite)
        ArgValidator.ensure_valid_store_dir_path(args.store_dir)
        if args.force_overwrite:
            MigrationScript.clear_output_dir(args.output_dir)
        MigrationScript.migrate(store_dir=args.store_dir,
                                output_dir=args.output_dir)
    except Exception as e:
        print(f"Failed due to exception: {e}")
        raise


if __name__ == "__main__"   :
    main()


