import requests
import time
import hashlib
import secrets
import os
import re
import logging
import threading
from enum import Enum
from dataclasses import dataclass
from typing import List, Dict, Any, Optional
from urllib.parse import urlsplit, parse_qsl, urlencode, urlunsplit
from django.core.files import locks
from .cf_sync_runtime import _root

logger = logging.getLogger(__name__)
_api_lock = threading.Lock()


def _wait_for_api_slot(interval):
    """Serialize starts across threads/processes on this host, including failures."""
    with _api_lock:
        with (_root() / 'api-clock.lock').open('a+b') as file:
            if not locks.lock(file, locks.LOCK_EX):
                raise RuntimeError('Cannot coordinate Codeforces requests')
            try:
                file.seek(0)
                previous = file.read().decode('ascii')
                now = time.monotonic()
                if previous and now >= float(previous):
                    wait = interval - (now - float(previous))
                    if wait > 0:
                        time.sleep(wait)
                file.seek(0)
                file.truncate()
                file.write(str(time.monotonic()).encode('ascii'))
                file.flush()
            finally:
                locks.unlock(file)


def sanitize_sensitive_url(url_or_message: str) -> str:
    """
    Substitui os valores dos query params sensíveis (apiKey, apiSig, secret)
    por '[REDACTED]' para evitar vazamento em logs ou rastros de erro.
    """
    if not url_or_message:
        return ""

    # 1. Regex de substituição nos query params conhecidos
    pattern = r'((?:apiKey|apiSig|secret)=)[^&\s]+'
    sanitized = re.sub(pattern, r'\1[REDACTED]', str(url_or_message), flags=re.IGNORECASE)
    return sanitized


class CFErrorType(str, Enum):
    NONE = "NONE"
    PERMANENT = "PERMANENT"
    TRANSIENT = "TRANSIENT"


@dataclass
class CFResult:
    """
    Representação tipada do retorno de consultas à API do Codeforces.
    Permite aos serviços distinguir facilmente sucessos, erros permanentes
    (como Gym privado ou 400 Bad Request) e falhas transitórias (como 5xx e Timeout).
    """
    data: Optional[Any] = None
    status_code: Optional[int] = None
    error_type: CFErrorType = CFErrorType.NONE
    error_message: str = ""

    @property
    def is_success(self) -> bool:
        return self.error_type == CFErrorType.NONE and self.data is not None

    @property
    def is_permanent(self) -> bool:
        return self.error_type == CFErrorType.PERMANENT

    @property
    def is_transient(self) -> bool:
        return self.error_type == CFErrorType.TRANSIENT

    def __bool__(self) -> bool:
        return self.is_success


def _classify_error_comment(comment: str, status_code: Optional[int] = None) -> CFErrorType:
    """
    Centraliza a classificação de mensagens e status de erro da API do Codeforces.
    Categorias:
    - PERMANENT: contest explicitamente privado ou inexistente ('not visible', 'not found', 'wrong contest id').
    - TRANSIENT: rate limit, falhas de autenticação/assinatura (erro de config/tempo), falhas 5xx, timeouts
                 ou qualquer erro desconhecido (para evitar fallback precoce ou avanço incorreto de watermark).
    """
    comment_lower = (comment or "").lower()

    # 1. Rate limit (pode vir como 429, 400 ou em JSON com 200) -> TRANSIENT
    if any(term in comment_lower for term in ["limit exceeded", "rate limit", "too many requests"]):
        return CFErrorType.TRANSIENT

    # 2. Erros de autenticação, chaves ou dessincronização de horário -> TRANSIENT (não criar fallback de contest)
    if any(term in comment_lower for term in [
        "invalid api key", "wrong apisig", "incorrect signature", "time is out of sync", "invalid time",
        "apikey", "apisig"
    ]) and not any(perm in comment_lower for perm in ["is not visible", "contest not found", "wrong contest id"]):
        return CFErrorType.TRANSIENT

    # 3. Contest privado ou inexistente -> PERMANENT
    if any(term in comment_lower for term in [
        "is not visible", "not found", "contest not found", "wrong contest id", "no such contest", "handle not found"
    ]):
        return CFErrorType.PERMANENT

    # 4. Falhas transitórias explícitas de infraestrutura
    if status_code in [429, 500, 502, 503, 504]:
        return CFErrorType.TRANSIENT

    # 5. Erros desconhecidos/genéricos -> TRANSIENT (conservador: não cria fallback e retém watermark)
    return CFErrorType.TRANSIENT


class CodeforcesClient:
    """
    Cliente HTTP isolado para consumir a API oficial do Codeforces.
    Assina consultas de Gym via SHA-512; consultas públicas permanecem anônimas.
    Garante sanitização total de logs e tipagem de falhas (permanente vs transitória).
    """
    BASE_URL = "https://codeforces.com/api"

    def __init__(self, timeout: int = 15, sleep_time: float = 2, api_key: Optional[str] = None, api_secret: Optional[str] = None):
        self.timeout = timeout
        self.sleep_time = sleep_time
        self.session = requests.Session()
        self.api_key = api_key if api_key is not None else os.environ.get('CF_API_KEY')
        self.api_secret = api_secret if api_secret is not None else os.environ.get('CF_API_SECRET')

    def _make_request_result(self, endpoint: str, params: dict = None, *, authenticated=False) -> CFResult:
        url = f"{self.BASE_URL}/{endpoint}"
        
        if params is None:
            params = {}
        else:
            params = dict(params)
            
        _wait_for_api_slot(max(2, self.sleep_time))
        if authenticated and self.api_key and self.api_secret:
            params['apiKey'] = self.api_key
            params['time'] = str(int(time.time()))
            
            # Ordena params por chave e depois valor
            sorted_params = sorted(params.items(), key=lambda x: (x[0], str(x[1])))
            param_str = '&'.join([f"{k}={v}" for k, v in sorted_params])
            
            # Gera 6 caracteres hexadecimais aleatórios
            rand = secrets.token_hex(3)
            
            to_hash = f"{rand}/{endpoint}?{param_str}#{self.api_secret}"
            hash_val = hashlib.sha512(to_hash.encode('utf-8')).hexdigest()
            
            params['apiSig'] = f"{rand}{hash_val}"

        try:
            response = self.session.get(url, params=params, timeout=self.timeout)
            response.raise_for_status()
            data = response.json()
            if data.get('status') == 'OK':
                return CFResult(data=data.get('result'), status_code=response.status_code, error_type=CFErrorType.NONE)
            else:
                comment = data.get('comment', '')
                sanitized_comment = sanitize_sensitive_url(comment)
                print(f"[CodeforcesClient] O endpoint {endpoint} retornou Failed: {sanitized_comment}")

                err_type = _classify_error_comment(comment, status_code=response.status_code)
                return CFResult(status_code=response.status_code, error_type=err_type, error_message=sanitized_comment)

        except requests.HTTPError as e:
            status = e.response.status_code if e.response is not None else None
            sanitized_err = sanitize_sensitive_url(str(e))

            # Tenta extrair comment do JSON de erro da API do Codeforces
            comment = ""
            if e.response is not None:
                try:
                    err_json = e.response.json()
                    comment = err_json.get('comment', '')
                except Exception:
                    comment = e.response.text or ""

            sanitized_comment = sanitize_sensitive_url(comment)
            log_detail = f"{sanitized_err} | comment: {sanitized_comment}" if sanitized_comment else sanitized_err
            print(f"[CodeforcesClient] Erro de rede ou timeout acessando {endpoint}: {log_detail}")

            err_type = _classify_error_comment(comment, status_code=status)
            return CFResult(status_code=status, error_type=err_type, error_message=sanitized_comment or sanitized_err)

        except requests.RequestException as e:
            sanitized_err = sanitize_sensitive_url(str(e))
            print(f"[CodeforcesClient] Erro de rede ou timeout acessando {endpoint}: {sanitized_err}")
            return CFResult(status_code=None, error_type=CFErrorType.TRANSIENT, error_message=sanitized_err)

        except ValueError:
            return CFResult(error_type=CFErrorType.TRANSIENT, error_message="Invalid API JSON")

    def _make_request(self, endpoint: str, params: dict = None) -> Any:
        res = self._make_request_result(endpoint, params=params)
        return res.data

    def get_contests(self) -> List[Dict[str, Any]]:
        """ Retorna uma lista com metadata de todos os contests """
        result = self._make_request("contest.list")
        return result if result else []

    def get_problems(self) -> Dict[str, Any]:
        """ Retorna um dicionário com chaves 'problems' e 'problemStatistics' """
        result = self._make_request("problemset.problems")
        return result if result else {"problems": [], "problemStatistics": []}

    def get_user_submissions(self, handle: str, from_idx: int = 1, count: int = None) -> List[Dict[str, Any]]:
        """ Retorna todas as submissões de um usuário na plataforma (mais recente pro mais antigo) """
        result = self.get_user_submissions_result(handle, from_idx, count)
        return result.data if result.is_success else []

    def get_user_submissions_result(self, handle: str, from_idx: int = 1, count: int = None) -> CFResult:
        """Preserve the distinction between an empty public history and a failed page."""
        params = {"handle": handle, "from": from_idx}
        if count:
            params["count"] = count
        result = self._make_request_result("user.status", params)
        if result.is_success and not isinstance(result.data, list):
            return CFResult(error_type=CFErrorType.TRANSIENT, error_message="Invalid history format")
        return result

    def get_gym_standings_result(self, contest_id: str) -> CFResult:
        """Retorna CFResult com metadados e catálogo do Gym ou classificação do erro."""
        params = {"contestId": contest_id, "from": 1, "count": 1, "showUnofficial": True}
        return self._make_request_result("contest.standings", params, authenticated=True)

    def get_gym_standings(self, contest_id: str) -> Optional[Dict[str, Any]]:
        """Retorna metadata do Gym contest E a lista de todos os seus problemas."""
        res = self.get_gym_standings_result(contest_id)
        return res.data
