"""Small, single-host CF sync coordinator; no durable queue or automatic retry.

OS locks are shared by web workers/CLI on the same filesystem and released on
process exit. JSON status is private and disposable: lost state means unknown,
never success. This does not coordinate multiple Render instances.
"""
from contextlib import contextmanager
from contextvars import ContextVar
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import threading
import uuid

from django.conf import settings
from django.core.files import locks
from django.core.management import call_command
from django.core.management.base import CommandError
from django.db import close_old_connections

_owns_sync = ContextVar('owns_cf_sync', default=False)


def _root():
    root = Path(getattr(settings, 'CF_SYNC_RUNTIME_DIR', settings.BASE_DIR / 'var' / 'cf_sync'))
    root.mkdir(parents=True, exist_ok=True)
    return root


def _try_lock():
    file = (_root() / 'sync.lock').open('a+b')
    if not locks.lock(file, locks.LOCK_EX | locks.LOCK_NB):
        file.close()
        return None
    return file


def _release(file):
    locks.unlock(file)
    file.close()


@contextmanager
def exclusive_cf_sync():
    if _owns_sync.get():
        yield
        return
    file = _try_lock()
    if file is None:
        raise CommandError('Uma sincronização Codeforces já está em execução. Aguarde.')
    token = _owns_sync.set(True)
    try:
        yield
    finally:
        _owns_sync.reset(token)
        _release(file)


def _path(handle):
    return _root() / (hashlib.sha256(handle.lower().encode()).hexdigest() + '.json')


def _write(handle, state):
    path = _path(handle)
    temporary = path.with_suffix('.' + uuid.uuid4().hex + '.tmp')
    try:
        temporary.write_text(json.dumps(state), encoding='utf-8')
        temporary.replace(path)
    finally:
        temporary.unlink(missing_ok=True)


def _read(handle, run_id):
    try:
        value = json.loads(_path(handle).read_text(encoding='utf-8'))
        if value.get('run_id') == run_id:
            return value
    except (OSError, ValueError, AttributeError):
        pass
    return {'state': 'unknown', 'message': 'Estado indisponível. Atualize os dados e tente sincronizar novamente.'}


def read_cf_sync(handle, run_id):
    state = _read(handle, run_id)
    if state['state'] == 'running':
        file = _try_lock()
        if file is not None:
            try:
                state = _read(handle, run_id)
                if state['state'] == 'running':
                    state = {**state, 'state': 'interrupted',
                             'message': 'Sincronização interrompida. Atualize os dados e tente novamente.'}
            finally:
                _release(file)
    return state


def start_cf_sync(handle):
    file = _try_lock()
    if file is None:
        return {'state': 'busy', 'message': 'Uma sincronização Codeforces já está em execução. Aguarde.'}
    state = {'run_id': uuid.uuid4().hex, 'state': 'running',
             'started_at': datetime.now(timezone.utc).isoformat(),
             'message': 'Sincronização iniciada. Aguarde a conclusão.'}

    def run():
        token = _owns_sync.set(True)
        final = dict(state)
        try:
            close_old_connections()
            outcome = call_command('sync_cf', handle=handle)
            if outcome == 'incomplete':
                final.update(state='failed', message='Sincronização incompleta. Progresso preservado; tente novamente mais tarde.')
            else:
                final.update(state='completed', message='Sincronização Codeforces concluída.')
        except Exception as error:
            # Never persist exception text, upstream bodies or signed URLs.
            final.update(state='failed', error_type=type(error).__name__,
                         message='Não foi possível concluir a sincronização. Progresso preservado; tente novamente mais tarde.')
        finally:
            try:
                final['finished_at'] = datetime.now(timezone.utc).isoformat()
                _write(handle, final)
            finally:
                _owns_sync.reset(token)
                try:
                    close_old_connections()
                finally:
                    _release(file)

    try:
        _write(handle, state)
        threading.Thread(target=run, name='ForjaSyncCF', daemon=True).start()
    except Exception:
        _release(file)
        raise
    return state
