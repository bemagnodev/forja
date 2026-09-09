import logging
from unittest.mock import patch, MagicMock
import pytest
from api.services.sync_dispatcher import dispatch_sync


@patch("threading.Thread")
def test_dispatch_sync_creates_and_starts_daemon_thread(mock_thread_cls):
    """Testa se dispatch_sync instancia e inicia uma thread daemon com o nome esperado."""
    mock_thread_instance = MagicMock()
    mock_thread_cls.return_value = mock_thread_instance

    thread = dispatch_sync("sync_cf", "tourist")

    mock_thread_cls.assert_called_once()
    kwargs = mock_thread_cls.call_args.kwargs
    assert kwargs["name"] == "ForjaSyncThread-sync_cf-tourist"
    assert kwargs["daemon"] is True

    mock_thread_instance.start.assert_called_once()
    assert thread == mock_thread_instance


@patch("api.services.sync_dispatcher.call_command")
@patch("api.services.sync_dispatcher.close_old_connections")
def test_dispatch_sync_execution_target_success(mock_close_connections, mock_call_command):
    """Testa a execução interna do target da thread em caso de sucesso (fechando conexões antes e depois)."""
    with patch("threading.Thread") as mock_thread_cls:
        dispatch_sync("sync_atcoder", "tourist")
        target_fn = mock_thread_cls.call_args.kwargs["target"]

    target_fn()

    mock_call_command.assert_called_once_with("sync_atcoder", handle="tourist")
    assert mock_close_connections.call_count == 2


@patch("api.services.sync_dispatcher.call_command")
@patch("api.services.sync_dispatcher.close_old_connections")
@patch("api.services.sync_dispatcher.logger")
def test_dispatch_sync_execution_target_exception_handled(mock_logger, mock_close_connections, mock_call_command):
    """Testa se exceções no call_command são capturadas pelo logger sem vazar e se close_old_connections roda no finally."""
    mock_call_command.side_effect = RuntimeError("Erro simulado")

    with patch("threading.Thread") as mock_thread_cls:
        dispatch_sync("sync_cf", "tourist")
        target_fn = mock_thread_cls.call_args.kwargs["target"]

    target_fn()

    mock_call_command.assert_called_once_with("sync_cf", handle="tourist")
    mock_logger.exception.assert_called_once()
    assert mock_close_connections.call_count == 2
