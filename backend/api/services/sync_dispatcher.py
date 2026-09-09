import logging
import threading
from django.core.management import call_command
from django.db import close_old_connections

logger = logging.getLogger(__name__)


def dispatch_sync(command_name: str, handle: str) -> threading.Thread:
    """
    Despacha a execução de um comando de sincronização em segundo plano (background thread).
    Fechando conexões antigas do ORM no início e término para garantir isolamento de threads.
    """
    def run_sync():
        close_old_connections()
        try:
            call_command(command_name, handle=handle)
        except Exception as e:
            logger.exception("Erro ao executar %s em background para handle '%s': %s", command_name, handle, e)
        finally:
            close_old_connections()

    thread = threading.Thread(
        target=run_sync,
        name=f"ForjaSyncThread-{command_name}-{handle}",
        daemon=True
    )
    thread.start()
    return thread
