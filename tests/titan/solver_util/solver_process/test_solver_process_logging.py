import logging
import os
import pathlib
import pytest
import time
import tempfile
import json
from titan.solver_util.solver_process import (
    SolverProcessLogging,
    StreamToFileRedirection
)
from multiprocessing import (
    Process
)


logger = SolverProcessLogging.get_logger(__name__)

class DummyProcess:

    @classmethod
    def timestamp(cls):
        return int(time.time()*1000)
        
    @classmethod
    def run_with_stdout(cls, log_directory: str, log_entries):
        SolverProcessLogging.setup_for_stream_output()
        for entry in log_entries:
            time.sleep(0.05)
            logger.info(entry)

    @classmethod
    def run_with_event_file_log(cls, log_directory: str, event_log_entries):
        # file paths to logs
        log_name = f"{cls.__name__.lower()}-{cls.timestamp()}"
        event_log_file_path = os.path.join(log_directory, log_name + '.events')
        txt_log_file_path = os.path.join(log_directory, log_name + '.log')
        # setup logger
        SolverProcessLogging.setup_for_file_output( txt_log_file_path=txt_log_file_path,
                                                    event_log_file_path=event_log_file_path )
        for event in event_log_entries:
            time.sleep(0.05)
            logger.event(event)

    @classmethod
    def run_with_txt_file_log(cls, log_directory: str, log_entries):
        # file paths to logs
        log_name = f"{cls.__name__.lower()}-{cls.timestamp()}"
        event_log_file_path = os.path.join(log_directory, log_name + '.events')
        txt_log_file_path = os.path.join(log_directory, log_name + '.log')
        # setup logger
        SolverProcessLogging.setup_for_file_output( txt_log_file_path=txt_log_file_path,
                                                    event_log_file_path=event_log_file_path )
        for entry in log_entries:
            time.sleep(0.05)
            logger.error(entry)


    @classmethod
    def run_with_txt_file_log_rewriting(cls, log_directory: str, log_entries):
        # file paths to logs
        log_name = f"{cls.__name__.lower()}-{cls.timestamp()}"
        event_log_file_path = os.path.join(log_directory, log_name + '.events')
        txt_log_file_path = os.path.join(log_directory, log_name + '.log')
        for entry in log_entries:
            # setup logger
            SolverProcessLogging.setup_for_file_output( txt_log_file_path=txt_log_file_path,
                                                        event_log_file_path=event_log_file_path )
            logger.info(entry)
            time.sleep(0.2)



def test_solver_process_stream_log():
    TXT_LOG_ENTRIES = tuple(f'hello {i}' for i in range(10))

    with tempfile.TemporaryDirectory() as working_dir:
        stream_out_path = os.path.join(working_dir, 'stdout.txt')        
        with StreamToFileRedirection.create_for_stdout(stream_out_path) as stdout_redirect:
            with StreamToFileRedirection.create_for_stderr(stream_out_path) as stderr_redirect:
                
                process = Process( target=DummyProcess.run_with_stdout,
                                    args=(working_dir, TXT_LOG_ENTRIES) )
                process.start()
                process.join()
        with open(stream_out_path, 'r') as f:
            contents = f.read()
        for entry in TXT_LOG_ENTRIES:
            assert entry in contents


def test_solver_process_event_log():
    EVENT_LOG_ENTRIES = tuple({'type': 'count', 'value': i} for i in range(10))
    with tempfile.TemporaryDirectory() as working_dir:               
        process = Process( target=DummyProcess.run_with_event_file_log,
                            args=(working_dir, EVENT_LOG_ENTRIES) )
        process.start()
        process.join()
        # check
        event_log_path = next(p for p in pathlib.Path(working_dir).glob('*.events'))
        #
        expected_events = list(EVENT_LOG_ENTRIES)
        with open(event_log_path, 'r') as f:
            for line in f.readlines():
                assert json.loads(line)['event'] == expected_events[0]
                expected_events.pop(0)

def test_solver_process_txt_log():
    TXT_LOG_ENTRIES = tuple(f'hello {i}' for i in range(10))

    with tempfile.TemporaryDirectory() as working_dir:
        process = Process( target=DummyProcess.run_with_txt_file_log,
                            args=(working_dir, TXT_LOG_ENTRIES) )
        process.start()
        process.join()
        # check
        txt_log_path = next(p for p in pathlib.Path(working_dir).glob('*.log'))
        with open(txt_log_path, 'r') as f:
            contents = f.read()
        for entry in TXT_LOG_ENTRIES:
            assert entry in contents




def test_solver_process_rewrites_log():
    TXT_LOG_ENTRIES = tuple(f'hello {i}' for i in range(10))

    with tempfile.TemporaryDirectory() as working_dir:
        process = Process(  target=DummyProcess.run_with_txt_file_log_rewriting,
                            args=(working_dir, TXT_LOG_ENTRIES) )
        process.start()

        expected_log_entries = [entry for entry in TXT_LOG_ENTRIES]

        file_contents = None
        for i, expected_log_entry in enumerate(TXT_LOG_ENTRIES):

            logger.info(f"Waiting to read `{expected_log_entry}`")

            last_file_contents = file_contents
            for attempt in range(1000):
                try:
                    txt_log_path = next(p for p in pathlib.Path(working_dir).glob('*.log'))
                    with open(txt_log_path, 'r') as f:
                        file_contents = f.read()

                    if not file_contents.endswith('\n'):
                        file_contents = None
                except:
                    file_contents = None
                if file_contents and file_contents != last_file_contents:
                    logger.info(f"read new {file_contents}")
                    break
                time.sleep(0.01)
            else:
                pytest.fail(f"Failed to read a change in the file contents !")


            # log should match the expected entry
            assert expected_log_entry in file_contents
            # check that file contents represents a single entry
            assert sum(1 for log_entry in TXT_LOG_ENTRIES if log_entry in file_contents) == 1

        # wait for process
        process.join()
