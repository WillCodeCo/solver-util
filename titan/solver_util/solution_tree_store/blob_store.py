from __future__ import annotations
import typing
import pathlib
import shutil
import gzip
import logging

logger = logging.getLogger(__name__)


class BlobStore:
    
    COMPRESS_LEVEL = 1

    @classmethod
    def ensure_directories_are_created(cls, path: pathlib.Path):
        path.mkdir(parents=True, exist_ok=True)

    @classmethod
    def remove_empty_dirs_on_path(cls, path: pathlib.Path, limit_path: pathlib.Path):
        if not path.is_dir():
            raise ValueError(f"remove_dir_if_empty expects a path to a directory !")
        elif path == limit_path:
            raise ValueError(f"remove_dir_if_empty expects a path that is a descendant of limit_path")
        is_empty = (not any(path.iterdir()))
        if is_empty:
            path.rmdir()
            if path.parent != limit_path:
                cls.remove_empty_dirs_on_path(path=path.parent, limit_path=limit_path)

    @classmethod
    def _path_to_blob(cls, store_path: pathlib.Path, blob_prefix: str, blob_key: str) -> pathlib.Path:
        return store_path / blob_prefix / blob_key[0:4] / blob_key[4:6] / blob_key[6:8] / blob_key

    @classmethod
    def _path_to_compressed_blob(cls, store_path: pathlib.Path, blob_prefix: str, blob_key: str) -> pathlib.Path:
        return cls._path_to_blob(store_path, blob_prefix, blob_key).with_suffix('.gz')

    @classmethod
    def get_blob_path(cls, store_path: pathlib.Path, blob_prefix: str, blob_key: str) -> bytes:
        if cls._path_to_compressed_blob(store_path, blob_prefix, blob_key).is_file():
            return cls._path_to_compressed_blob(store_path, blob_prefix, blob_key)
        elif cls._path_to_blob(store_path, blob_prefix, blob_key).is_file():
            return cls._path_to_blob(store_path, blob_prefix, blob_key)
        else:
            raise ValueError(f"{cls.__name__}.get_blob_path(...) Failed because no blob was found for blob_key `{blob_key}` !")

    @classmethod
    def does_blob_exist(cls, store_path: pathlib.Path, blob_prefix: str, blob_key: str) -> bool:
        try:
            blob_path = cls.get_blob_path(store_path, blob_prefix, blob_key)
            return True
        except ValueError:
            return False

    @classmethod
    def gen_blob_keys(cls, store_path: pathlib.Path, blob_prefix: str) -> typing.Iterator[str]:
        root_path = (store_path / blob_prefix)
        for p in root_path.rglob('*'):
            if p.is_dir():
                continue
            file_name = p.stem
            if cls.get_blob_path(store_path, blob_prefix, file_name) == p:
                yield file_name

    @classmethod
    def open_blob(cls, store_path: pathlib.Path, blob_prefix: str, blob_key: str) -> typing.BinaryIO:
        blob_path = cls.get_blob_path(store_path, blob_prefix, blob_key)
        if blob_path.suffix == '.gz':
            return gzip.open(blob_path, 'rb')
        else:
            return open(blob_path, 'rb')

    @classmethod
    def get_blob_bytes(cls, store_path: pathlib.Path, blob_prefix: str, blob_key: str) -> bytes:
        with cls.open_blob(store_path=store_path, blob_prefix=blob_prefix, blob_key=blob_key) as f:
            return f.read()

    @classmethod
    def copy_blob(cls, store_path: pathlib.Path, blob_prefix: str, blob_key: str, dest_file_path: pathlib.Path):
        if BlobStore.does_blob_exist(   store_path=store_path,
                                        blob_prefix=blob_prefix,
                                        blob_key=blob_key  ):
            logger.info(f"Skipping copy_blob `{blob_key}` since it already exists !")
            return
        # otherwise
        try:
            blob_path = cls.get_blob_path(store_path, blob_prefix, blob_key)
            shutil.copyfile(blob_path, dest_file_path)
        except IOError:
            raise ValueError(f"{cls.__name__}.copy_blob(...) Failed when copying blob `{blob_path}` to `{dest_file_path}`")

    @classmethod
    def add_blob_from_bytes(cls, store_path: pathlib.Path, blob_prefix: str, blob_key: str, blob_bytes: bytes):
        if BlobStore.does_blob_exist(   store_path=store_path,
                                        blob_prefix=blob_prefix,
                                        blob_key=blob_key  ):
            logger.info(f"Skipping add_blob_from_bytes `{blob_key}` since it already exists !")
            return
        # otherwise
        try:
            cls.ensure_directories_are_created(cls._path_to_blob(store_path, blob_prefix, blob_key).parent)
            with open(cls._path_to_blob(store_path, blob_prefix, blob_key), 'wb') as f:
                f.write(blob_bytes)
        except IOError:
            raise ValueError(f"{cls.__name__}.add_blob(...) Failed when adding blob bytes to `{cls._path_to_blob(store_path, blob_prefix, blob_key)}`")

    @classmethod
    def add_compressed_blob_from_bytes(cls, store_path: pathlib.Path, blob_prefix: str, blob_key: str, blob_bytes: bytes):
        try:
            blob_path = cls._path_to_compressed_blob(store_path, blob_prefix, blob_key)
            if blob_path.is_file():
                logger.info(f"Skipping add_compressed_blob_from_bytes `{blob_key}` since it already exists !")
                return
            cls.ensure_directories_are_created(blob_path.parent)
            with gzip.open(blob_path, 'wb', compresslevel=cls.COMPRESS_LEVEL) as f:
                f.write(blob_bytes)
        except IOError:
            raise ValueError(f"{cls.__name__}.add_compressed_blob_from_bytes(...) Failed when adding blob bytes to `{blob_path}`")

    @classmethod
    def add_blob_from_path(cls, store_path: pathlib.Path, blob_prefix: str, blob_key: str, src_blob_path: pathlib.Path):
        try:
            dest_blob_path = cls._path_to_blob(store_path, blob_prefix, blob_key)
            if dest_blob_path.is_file():
                logger.info(f"Skipping add_blob_from_path `{blob_key}` since it already exists !")
                return
            cls.ensure_directories_are_created(dest_blob_path.parent)
            shutil.copyfile(src_blob_path, dest_blob_path)
        except IOError:
            raise ValueError(f"{cls.__name__}.add_blob_from_path(...) Failed when adding blob `{src_blob_path}` to `{dest_blob_path}`")

    @classmethod
    def add_compressed_blob_from_path(cls, store_path: pathlib.Path, blob_prefix: str, blob_key: str, src_blob_path: pathlib.Path):
        try:
            dest_blob_path = cls._path_to_compressed_blob(store_path, blob_prefix, blob_key)
            if dest_blob_path.is_file():
                logger.info(f"Skipping add_compressed_blob_from_path `{blob_key}` since it already exists !")
                return
            cls.ensure_directories_are_created(dest_blob_path.parent)
            with open(src_blob_path, 'rb') as f_in:
                with gzip.open(dest_blob_path, 'wb', compresslevel=cls.COMPRESS_LEVEL) as f_out:
                    shutil.copyfileobj(f_in, f_out)
        except IOError:
            raise ValueError(f"{cls.__name__}.add_compressed_blob_from_path(...) Failed when adding blob `{src_blob_path}` to `{dest_blob_path}`")


    @classmethod
    def delete_blob(cls, store_path: pathlib.Path, blob_prefix: str, blob_key: str):
        p_compressed = cls._path_to_compressed_blob(store_path, blob_prefix, blob_key)
        p = cls._path_to_blob(store_path, blob_prefix, blob_key)
        if p_compressed.is_file():
            p_compressed.unlink()
        if p.is_file():
            p.unlink()
        cls.remove_empty_dirs_on_path(path=p.parent, limit_path=(store_path / blob_prefix))


    @classmethod
    def ensure_valid_store_path(cls, store_path: pathlib.Path):
        try:
            assert store_path.is_dir()
            assert all(p.is_dir() for p in store_path.iterdir()), f"Only sub-directories expected in root of store_path"
        except AssertionError as e:
            raise ValueError(f"Invalid store_path for {cls.__name__} : {e}")

    @classmethod
    def is_empty(cls, store_path: pathlib.Path) -> bool:
        cls.ensure_valid_store_path(store_path)
        return (not any(store_path.iterdir()))

    @classmethod
    def create_blob_key_from_bytes(cls, blob_bytes: bytes) -> str:
        m = hashlib.sha256()
        m.update(blob_bytes)
        return m.hexdigest()

    @classmethod
    def create_blob_key_from_path(cls, blob_path: pathlib.Path) -> str:
        with open(blob_path, 'rb') as f:
            return cls.create_blob_key_from_bytes(f.read())