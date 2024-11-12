from __future__ import annotations
import typing
import pathlib
import gzip
import json
import hashlib
import tempfile
import logging
import time
from titan.solver_util.solution_tree_store.blob_store import (
    BlobStore
)
from titan.solver_util.solution_tree_store.types import (
    SolverType,
    SolutionTreeMeta,
    SolutionTreeStoreIndexEntry,
    SolutionTreeStoreIndex
)
from titan.solver_util.solution_tree_store.solution_tree_reader import (
    SolutionTreeReader
)
from titan.solver_util.solution_tree_store.solution_tree_writer import (
    SolutionTreeWriter
)

logger = logging.getLogger(__name__)


class SolutionTreeStoreIndexFactory:

    @classmethod
    def create_preflop_entry(cls, solution_tree_meta: SolutionTreeMeta, solver_config_dict: dict) -> SolutionTreeStoreIndexEntry:
        index_key = SolutionTreeStoreIndex.create_preflop_index_key(is_path_solve=solution_tree_meta.is_path_solve(),
                                                                    action_sequence=solution_tree_meta.action_sequence(),
                                                                    solver_config_dict=solver_config_dict)
        return SolutionTreeStoreIndexEntry( index_key=index_key,
                                            solution_tree_key=solution_tree_meta.solution_tree_key(),
                                            solver_config_key=solution_tree_meta.solver_config_key() )

    @classmethod
    def create_postflop_entry(cls, solution_tree_meta: SolutionTreeMeta, solver_config_dict: dict) -> SolutionTreeStoreIndexEntry:
        index_key = SolutionTreeStoreIndex.create_postflop_index_key(is_path_solve=solution_tree_meta.is_path_solve(),
                                                                    action_sequence=solution_tree_meta.action_sequence(),
                                                                    solver_config_dict=solver_config_dict)
        return SolutionTreeStoreIndexEntry( index_key=index_key,
                                            solution_tree_key=solution_tree_meta.solution_tree_key(),
                                            solver_config_key=solution_tree_meta.solver_config_key() )

    @classmethod
    def create(cls, store_path: pathlib.Path) -> SolutionTreeStoreIndex:
        result = SolutionTreeStoreIndex.create_empty()
        for i, solution_tree_meta in enumerate(SolutionTreeStoreImpl.gen_solution_tree_metas(store_path)):
            logger.info(f"Indexing solution_tree_meta #{i}")
            if solution_tree_meta.solver_type() == SolverType.PREFLOP:

                solver_config_dict = SolutionTreeStoreImpl.get_preflop_solver_config_dict(  store_path=store_path,
                                                                                            key=solution_tree_meta.solver_config_key()  )
                entry = cls.create_preflop_entry(solution_tree_meta, solver_config_dict)
            elif solution_tree_meta.solver_type() == SolverType.POSTFLOP:
                solver_config_dict = SolutionTreeStoreImpl.get_postflop_solver_config_dict( store_path=store_path,
                                                                                            key=solution_tree_meta.solver_config_key() )
                entry = cls.create_postflop_entry(solution_tree_meta, solver_config_dict)
            else:
                raise ValueError(f"{cls.__name__}.create failed due to unexpected value for solver_type `{solution_tree_meta.solver_type()}` !")
            result.add_entry(entry)
        return result


class SolutionTreeStoreImpl:
    
    INDEX_COMPRESS_LEVEL = 1
    INDEX_PREFIX = 'index'
    SOLUTION_TREE_PREFIX = 'solution-tree'
    SOLUTION_TREE_META_PREFIX = 'solution-tree-meta'
    PREFLOP_SOLVER_CONFIG_PREFIX = 'preflop-solver-config'
    POSTFLOP_SOLVER_CONFIG_PREFIX = 'postflop-solver-config'

    @classmethod
    def ensure_valid_store_path(cls, store_path: pathlib.Path):
        try:
            assert store_path.is_dir()
            BlobStore.ensure_valid_store_path(store_path)
        except AssertionError as e:
            raise ValueError(f"Invalid store_path for {cls.__name__} : {e}")

    @classmethod
    def is_empty(cls, store_path: pathlib.Path) -> bool:
        cls.ensure_valid_store_path(store_path)
        return BlobStore.is_empty(store_path)

    @classmethod
    def create_index(cls, store_path: pathlib.Path) -> SolutionTreeStoreIndex:
        return SolutionTreeStoreIndexFactory.create(store_path)

    @classmethod
    def get_solution_tree(cls, store_path: pathlib.Path, key: str) -> SolutionTree:
        return SolutionTreeReader.read_compressed(BlobStore.get_blob_path(store_path, cls.SOLUTION_TREE_PREFIX, key))

    @classmethod
    def get_solution_tree_meta(cls, store_path: pathlib.Path, key: str) -> SolutionTreeMeta:
        return SolutionTreeMeta.create_from_dict(json.loads(BlobStore.get_blob_bytes(store_path, cls.SOLUTION_TREE_META_PREFIX, key)))

    @classmethod
    def get_preflop_solver_config_dict(cls, store_path: pathlib.Path, key: str) -> dict:
        return json.loads(BlobStore.get_blob_bytes(store_path, cls.PREFLOP_SOLVER_CONFIG_PREFIX, key))

    @classmethod
    def get_postflop_solver_config_dict(cls, store_path: pathlib.Path, key: str) -> dict:
        return json.loads(BlobStore.get_blob_bytes(store_path, cls.POSTFLOP_SOLVER_CONFIG_PREFIX, key))

    @classmethod
    def get_solution_tree_store_index(cls, store_path: pathlib.Path, key: str) -> dict:
        return SolutionTreeStoreIndex.create_from_dict(json.loads(BlobStore.get_blob_bytes(store_path, cls.INDEX_PREFIX, key)))

    @classmethod
    def gen_solution_tree_metas(cls, store_path: pathlib.Path) -> typing.Iterator[SolutionTreeMeta]:
        for key in BlobStore.gen_blob_keys(store_path, cls.SOLUTION_TREE_META_PREFIX):
            yield cls.get_solution_tree_meta(store_path=store_path, key=key)

    @classmethod
    def gen_solution_tree_store_indexes(cls, store_path: pathlib.Path) -> typing.Iterator[SolutionTreeStoreIndex]:
        for key in BlobStore.gen_blob_keys(store_path, cls.INDEX_PREFIX):
            yield cls.get_solution_tree_store_index(store_path=store_path, key=key)

    @classmethod
    def compute_file_hash(cls, file_obj) -> str:
        h  = hashlib.sha256()
        b  = bytearray(128*1024)
        mv = memoryview(b)
        while n := file_obj.readinto(mv):
            h.update(mv[:n])
        return h.hexdigest()

    @classmethod
    def compute_file_hash_from_path(cls, some_file_path: pathlib.Path) -> str:
        with open(some_file_path, 'rb', buffering=0) as f:
            return cls.compute_file_hash(f)


    @classmethod
    def compute_dict_hash(cls, some_dict: dict) -> str:
        m = hashlib.sha256()
        m.update(json.dumps(some_dict, sort_keys=True).encode('ascii'))
        return m.hexdigest()

    @classmethod
    def add_preflop_solution_tree_from_path(cls, store_path: pathlib.Path, solver_config_dict: dict,
                                                                    action_sequence: ActionSequence,
                                                                    is_path_solve: bool,
                                                                    solution_tree_path: pathlib.Path) -> SolutionTreeStoreIndexEntry:
        config_key = cls.compute_dict_hash(solver_config_dict)
        solution_tree_key = cls.compute_file_hash_from_path(solution_tree_path)       
        solution_tree_meta = SolutionTreeMeta.create_for_preflop(   is_path_solve=is_path_solve,
                                                                    action_sequence=action_sequence,
                                                                    solver_config_key=config_key,
                                                                    solution_tree_key=solution_tree_key  )
        BlobStore.add_compressed_blob_from_path(store_path=store_path,
                                                blob_prefix=cls.SOLUTION_TREE_PREFIX,
                                                blob_key=solution_tree_key,
                                                src_blob_path=solution_tree_path)
        BlobStore.add_compressed_blob_from_bytes(store_path=store_path,
                                                blob_prefix=cls.PREFLOP_SOLVER_CONFIG_PREFIX,
                                                blob_key=config_key,
                                                blob_bytes=json.dumps(solver_config_dict).encode('ascii'))
        BlobStore.add_blob_from_bytes(  store_path=store_path,
                                        blob_prefix=cls.SOLUTION_TREE_META_PREFIX,
                                        blob_key=solution_tree_meta.hash(),
                                        blob_bytes=json.dumps(solution_tree_meta.serialize_to_dict()).encode('ascii')  )
        # return info useful for indexes
        index_key = SolutionTreeStoreIndex.create_preflop_index_key(is_path_solve=is_path_solve,
                                                                    action_sequence=action_sequence,
                                                                    solver_config_dict=solver_config_dict)
        return SolutionTreeStoreIndexEntry( index_key=index_key,
                                            solution_tree_key=solution_tree_key,
                                            solver_config_key=config_key )


    @classmethod
    def add_postflop_solution_tree_from_path(cls, store_path: pathlib.Path, solver_config_dict: dict,
                                                                    action_sequence: ActionSequence,
                                                                    is_path_solve: bool,
                                                                    solution_tree_path: pathlib.Path):
        config_key = cls.compute_dict_hash(solver_config_dict)
        solution_tree_key = cls.compute_file_hash_from_path(solution_tree_path)       
        solution_tree_meta = SolutionTreeMeta.create_for_postflop(  is_path_solve=is_path_solve,
                                                                    action_sequence=action_sequence,
                                                                    solver_config_key=config_key,
                                                                    solution_tree_key=solution_tree_key  )
        BlobStore.add_compressed_blob_from_path(store_path=store_path,
                                                blob_prefix=cls.SOLUTION_TREE_PREFIX,
                                                blob_key=solution_tree_key,
                                                src_blob_path=solution_tree_path)
        BlobStore.add_compressed_blob_from_bytes(store_path=store_path,
                                                blob_prefix=cls.POSTFLOP_SOLVER_CONFIG_PREFIX,
                                                blob_key=config_key,
                                                blob_bytes=json.dumps(solver_config_dict).encode('ascii'))
        BlobStore.add_blob_from_bytes(  store_path=store_path,
                                        blob_prefix=cls.SOLUTION_TREE_META_PREFIX,
                                        blob_key=solution_tree_meta.hash(),
                                        blob_bytes=json.dumps(solution_tree_meta.serialize_to_dict()).encode('ascii')  )
        # return info useful for indexes
        index_key = SolutionTreeStoreIndex.create_postflop_index_key(is_path_solve=is_path_solve,
                                                                    action_sequence=action_sequence,
                                                                    solver_config_dict=solver_config_dict)
        return SolutionTreeStoreIndexEntry( index_key=index_key,
                                            solution_tree_key=solution_tree_key,
                                            solver_config_key=config_key )

    @classmethod
    def add_preflop_solution_tree(cls, store_path: pathlib.Path, solver_config_dict: dict,
                                                                    action_sequence: ActionSequence,
                                                                    is_path_solve: bool,
                                                                    solution_tree: SolutionTree):
        tmp_file = tempfile.NamedTemporaryFile(delete=False)
        tmp_file.close()
        tmp_file_path = pathlib.Path(tmp_file.name)
        try:            
            SolutionTreeWriter.write(tmp_file_path, solution_tree)
            return cls.add_preflop_solution_tree_from_path( store_path=store_path,
                                                            solver_config_dict=solver_config_dict,
                                                            action_sequence=action_sequence,
                                                            is_path_solve=is_path_solve,
                                                            solution_tree_path=tmp_file_path )
        finally:
            tmp_file_path.unlink()

    @classmethod
    def add_postflop_solution_tree(cls, store_path: pathlib.Path, solver_config_dict: dict,
                                                                    action_sequence: ActionSequence,
                                                                    is_path_solve: bool,
                                                                    solution_tree: SolutionTree):
        tmp_file = tempfile.NamedTemporaryFile(delete=False)
        tmp_file.close()
        tmp_file_path = pathlib.Path(tmp_file.name)
        try:            
            SolutionTreeWriter.write(tmp_file_path, solution_tree)
            return cls.add_postflop_solution_tree_from_path(store_path=store_path,
                                                            solver_config_dict=solver_config_dict,
                                                            action_sequence=action_sequence,
                                                            is_path_solve=is_path_solve,
                                                            solution_tree_path=tmp_file_path)
        finally:
            tmp_file_path.unlink()



    @classmethod
    def add_solution_tree_store_index(cls, store_path: pathlib.Path, solution_tree_store_index: SolutionTreeStoreIndex):
        index_dict = solution_tree_store_index.serialize_to_dict()
        index_key = cls.compute_dict_hash(index_dict)
        BlobStore.add_compressed_blob_from_bytes(store_path=store_path,
                                                blob_prefix=cls.INDEX_PREFIX,
                                                blob_key=index_key,
                                                blob_bytes=json.dumps(index_dict).encode('ascii'))

    @classmethod
    def delete_solution_tree_store_index(cls, store_path: pathlib.Path, solution_tree_store_index: SolutionTreeStoreIndex):
        index_dict = solution_tree_store_index.serialize_to_dict()
        index_key = cls.compute_dict_hash(index_dict)
        BlobStore.delete_blob(  store_path=store_path,
                                blob_prefix=cls.INDEX_PREFIX,
                                blob_key=index_key  )

    @classmethod
    def load_and_merge_indexes(cls, store_path: pathlib.Path) -> SolutionTreeStoreIndex:
        all_indexes = tuple(cls.gen_solution_tree_store_indexes(store_path))
        if not all_indexes:
            raise ValueError(f"Failed to load_and_merge_indexes(), none were found !")
        return SolutionTreeStoreIndex.merge(*all_indexes)

    @classmethod
    def remove_small_indexes(cls, store_path: pathlib.Path, size_threshold: int):
        for index in tuple(cls.gen_solution_tree_store_indexes(store_path)):
            if index.size() < size_threshold:
                cls.delete_solution_tree_store_index(store_path=store_path, solution_tree_store_index=index)




class SolutionTreeStore:

    __slots__ = (   '_store_path',
                    '_index'  )

    def __init__(self, store_path: pathlib.Path, index: SolutionTreeStoreIndex):
        self._store_path = store_path
        self._index = index

    def store_path(self) -> str:
        return self._store_path

    def index(self) -> SolutionTreeStoreIndex:
        return self._index

    def add_preflop_solution_tree_from_path(self, solver_config_dict: dict, action_sequence: ActionSequence,
                                                                                        is_path_solve: bool,
                                                                                        solution_tree_path: pathlib.Path):
        index_entry = SolutionTreeStoreImpl.add_preflop_solution_tree_from_path(store_path=self.store_path(),
                                                                                solver_config_dict=solver_config_dict,
                                                                                action_sequence=action_sequence,
                                                                                is_path_solve=is_path_solve,
                                                                                solution_tree_path=solution_tree_path)
        # save in index
        self._index.add_entry(index_entry)

    def add_postflop_solution_tree_from_path(self, solver_config_dict: dict, action_sequence: ActionSequence,
                                                                                        is_path_solve: bool,
                                                                                        solution_tree_path: pathlib.Path):
        index_entry = SolutionTreeStoreImpl.add_postflop_solution_tree_from_path(   store_path=self.store_path(),
                                                                                    solver_config_dict=solver_config_dict,
                                                                                    action_sequence=action_sequence,
                                                                                    is_path_solve=is_path_solve,
                                                                                    solution_tree_path=solution_tree_path  )
        # save in index
        self._index.add_entry(index_entry)



    def add_preflop_solution_tree(self, solver_config_dict: dict, action_sequence: ActionSequence,
                                                                            is_path_solve: bool,
                                                                            solution_tree: SolutionTree):
        index_entry = SolutionTreeStoreImpl.add_preflop_solution_tree_from_path(store_path=self.store_path(),
                                                                                solver_config_dict=solver_config_dict,
                                                                                action_sequence=action_sequence,
                                                                                is_path_solve=is_path_solve,
                                                                                solution_tree=solution_tree)
        # save in index
        self._index.add_entry(index_entry)

    def add_postflop_solution_tree(self, solver_config_dict: dict, action_sequence: ActionSequence,
                                                                            is_path_solve: bool,
                                                                            solution_tree: SolutionTree):
        index_entry = SolutionTreeStoreImpl.add_postflop_solution_tree( store_path=self.store_path(),
                                                                        solver_config_dict=solver_config_dict,
                                                                        action_sequence=action_sequence,
                                                                        is_path_solve=is_path_solve,
                                                                        solution_tree=solution_tree )
        # save in index
        self._index.add_entry(index_entry)


    def save_index(self):
        SolutionTreeStoreImpl.add_solution_tree_store_index(store_path=self.store_path(), solution_tree_store_index=self.index())

    def rebuild_index(self):
        self._index = SolutionTreeStoreImpl.create_index(store_path=self.store_path())

    def clean_up_indexes(self):
        SolutionTreeStoreImpl.remove_small_indexes(store_path=self.store_path(), size_threshold=self.index().size())

    def get_solution_tree(self, key: str) -> SolutionTree:
        return SolutionTreeStoreImpl.get_solution_tree(store_path=self.store_path(), key=key)

    def get_solution_tree_meta(self, key: str) -> SolutionTreeMeta:
        return SolutionTreeStoreImpl.get_solution_tree_meta(store_path=self.store_path(), key=key)

    def get_preflop_solver_config_dict(self, key: str) -> dict:
        return SolutionTreeStoreImpl.get_preflop_solver_config_dict(store_path=self.store_path(), key=key)

    def get_postflop_solver_config_dict(self, key: str) -> dict:
        return SolutionTreeStoreImpl.get_postflop_solver_config_dict(store_path=self.store_path(), key=key)

    def gen_solution_tree_metas(self) -> typing.Iterator[SolutionTreeMeta]:
        yield from SolutionTreeStoreImpl.gen_solution_tree_metas(store_path=self.store_path())

    @classmethod
    def ensure_valid_store_path(cls, store_path: pathlib.Path):
        SolutionTreeStoreImpl.ensure_valid_store_path(store_path)

    @classmethod
    def is_empty(cls, store_path: pathlib.Path):
        SolutionTreeStoreImpl.is_empty(store_path)


    @classmethod
    def create_from_directory(cls, store_path: pathlib.Path) -> SolutionTreeStore:
        return cls( store_path=store_path,
                    index=SolutionTreeStoreImpl.load_and_merge_indexes(store_path) )

    @classmethod
    def create_empty(cls, store_path: pathlib.Path) -> SolutionTreeStore:
        try:
            index = SolutionTreeStoreImpl.load_and_merge_indexes(store_path)
        except ValueError:
            index = None
        if index:
            raise ValueError(f"Cannot create empty {cls.__name__} in directory where there is an existing index file !")
        dir_is_empty = (not any(store_path.iterdir()))
        if not store_path.is_dir():
            raise ValueError(f"Cannot create empty {cls.__name__} in non-directory `{store_path}` !")
        if not dir_is_empty:
            raise ValueError(f"Cannot create empty {cls.__name__} in non-empty directory `{store_path}` !")
        return cls( store_path=store_path,
                    index=SolutionTreeStoreIndex.create_empty() )


    @classmethod
    def create_from_directory_and_rebuild_index(cls, store_path: pathlib.Path) -> SolutionTreeStore:
        result = cls(   store_path=store_path,
                        index=SolutionTreeStoreIndex.create_empty()  )
        result.rebuild_index()
        result.save_index()
        return result