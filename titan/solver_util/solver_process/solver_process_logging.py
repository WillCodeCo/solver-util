import sys
import os
import logging
import json
import time

class _Encoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, set):
            return tuple(o)
        return super().default(o)

class _JsonLogEntry:
    __slots__ = ('_fields',)

    def __init__(self, fields: dict):
        self._fields = fields

    def __str__(self):
        return _Encoder().encode(self._fields)


class _JsonEntryFilter(logging.Filter):
    def filter(self, record):
        return type(record.msg) == _JsonLogEntry


class _TextEntryFilter(logging.Filter):
    def filter(self, record):
        return type(record.msg) == str

class SolverProcessLogger:

    __slots__ = ('_logger',)

    def __init__(self, logger: logging.Logger):
        self._logger = logger

    @classmethod
    def timestamp(cls):
        return int(time.time()*1000)

    def debug(self, msg, *args, **kwargs):
        self._logger.debug(msg, *args, **kwargs)

    def info(self, msg, *args, **kwargs):
        self._logger.info(msg, *args, **kwargs)

    def warning(self, msg, *args, **kwargs):
        self._logger.warning(msg, *args, **kwargs)

    def error(self, msg, *args, **kwargs):
        self._logger.error(msg, *args, **kwargs)

    def event(self, event_fields: dict):
        self._logger.info(_JsonLogEntry({   'source': self._logger.name,
                                            'timestamp': self.timestamp(),
                                            'event': event_fields     }))


class SolverProcessLogging:
    
    _cache = {}

    @classmethod
    def get_logger(cls, logger_name) -> logging.Logger:
        try:
            return cls._cache[logger_name]
        except KeyError:
            result = SolverProcessLogger(logging.getLogger(logger_name))
            cls._cache[logger_name] = result
            return result

    @classmethod
    def clear_handlers(cls):
        root_logger = logging.getLogger()
        for handler in list(root_logger.handlers):
            root_logger.removeHandler(handler)
            handler.close()

    @classmethod
    def setup_for_stream_output(cls):
        cls.clear_handlers()
        # event logs to stout
        event_log_handler = logging.StreamHandler(sys.stdout)
        event_log_handler.addFilter(_JsonEntryFilter())
        event_log_formatter = logging.Formatter("[EVENT]:${message}", style='$')
        event_log_handler.setFormatter(event_log_formatter)
        # normal logs
        txt_log_handler = logging.StreamHandler(sys.stdout)
        txt_log_handler.addFilter(_TextEntryFilter())
        txt_log_formatter = logging.Formatter("${asctime}:${levelname}:${name}:${message}", style='$')
        txt_log_handler.setFormatter(txt_log_formatter)
        # setup handlers
        root_logger = logging.getLogger()
        root_logger.addHandler(event_log_handler)
        root_logger.addHandler(txt_log_handler)


    @classmethod
    def setup_for_file_output(cls, event_log_file_path: str, txt_log_file_path: str):
        cls.clear_handlers()
        # event log
        event_log_handler = logging.FileHandler(event_log_file_path, mode='w')
        event_log_handler.addFilter(_JsonEntryFilter())
        # normal logs
        txt_log_handler = logging.FileHandler(txt_log_file_path, mode='w')
        txt_log_handler.addFilter(_TextEntryFilter())
        log_formatter = logging.Formatter("${asctime}:${levelname}:${name}:${message}", style='$')
        txt_log_handler.setFormatter(log_formatter)
        # setup handlers
        root_logger = logging.getLogger()
        root_logger.addHandler(event_log_handler)
        root_logger.addHandler(txt_log_handler)