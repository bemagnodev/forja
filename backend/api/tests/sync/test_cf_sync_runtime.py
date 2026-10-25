from unittest.mock import patch

import pytest

from api.services import cf_sync_runtime as runtime
from django.core.management.base import CommandError


@pytest.fixture(autouse=True)
def isolated_runtime(settings, tmp_path):
    settings.CF_SYNC_RUNTIME_DIR = tmp_path


def test_running_sync_rejects_second_handle_and_releases_after_completion():
    with patch.object(runtime.threading, 'Thread') as thread, \
         patch.object(runtime, 'close_old_connections'), \
         patch.object(runtime, 'call_command', return_value=None) as command:
        first = runtime.start_cf_sync('one')
        assert first['state'] == 'running'
        assert runtime.start_cf_sync('two')['state'] == 'busy'
        with pytest.raises(CommandError, match='já está em execução'):
            with runtime.exclusive_cf_sync():
                pytest.fail('CLI must not overlap the web sync')
        assert runtime.read_cf_sync('one', first['run_id'])['state'] == 'running'
        target = thread.call_args.kwargs['target']
        target()
        command.assert_called_once_with('sync_cf', handle='one')
        assert runtime.read_cf_sync('one', first['run_id'])['state'] == 'completed'
        assert runtime.start_cf_sync('two')['state'] == 'running'
        thread.call_args.kwargs['target']()


@pytest.mark.parametrize('outcome', [RuntimeError('secret=never-log-me'), 'incomplete'])
def test_failed_or_incomplete_command_reports_failure_without_secrets(outcome, caplog):
    with patch.object(runtime.threading, 'Thread') as thread, \
         patch.object(runtime, 'close_old_connections'), \
         patch.object(runtime, 'call_command') as command:
        if isinstance(outcome, Exception):
            command.side_effect = outcome
        else:
            command.return_value = outcome
        started = runtime.start_cf_sync('one')
        thread.call_args.kwargs['target']()
    state = runtime.read_cf_sync('one', started['run_id'])
    assert state['state'] == 'failed'
    assert 'never-log-me' not in str(state) + caplog.text
    assert runtime.read_cf_sync('two', started['run_id'])['state'] == 'unknown'


def test_lost_worker_is_interrupted_not_completed():
    # Process death leaves a running JSON but releases the OS lock.
    runtime._write('one', {'state': 'running', 'run_id': 'lost'})
    state = runtime.read_cf_sync('one', 'lost')
    assert state['state'] == 'interrupted'


def test_thread_start_failure_releases_sync_lock():
    with patch.object(runtime.threading, 'Thread') as thread:
        thread.return_value.start.side_effect = RuntimeError('cannot start')
        with pytest.raises(RuntimeError):
            runtime.start_cf_sync('one')
    with runtime.exclusive_cf_sync():
        pass
