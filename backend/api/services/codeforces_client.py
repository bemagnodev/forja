import requests
import time
import hashlib
import secrets
import os
from typing import List, Dict, Any, Optional

class CodeforcesClient:
    """
    Cliente HTTP isolado para consumir a API oficial do Codeforces.
    Suporta autenticação automática via SHA-512 se CF_API_KEY for definida.
    """
    BASE_URL = "https://codeforces.com/api"

    def __init__(self, timeout: int = 15, sleep_time: float = 0.5):
        self.timeout = timeout
        self.sleep_time = sleep_time
        self.session = requests.Session()
        self.api_key = os.environ.get('CF_API_KEY')
        self.api_secret = os.environ.get('CF_API_SECRET')

    def _make_request(self, endpoint: str, params: dict = None) -> Any:
        url = f"{self.BASE_URL}/{endpoint}"
        
        if params is None:
            params = {}
            
        if self.api_key and self.api_secret:
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
                time.sleep(self.sleep_time)  
                return data.get('result')
            else:
                print(f"[CodeforcesClient] O endpoint {endpoint} retornou Failed: {data.get('comment')}")
                return None
        except requests.RequestException as e:
            print(f"[CodeforcesClient] Erro de rede ou timeout acessando {endpoint}: {e}")
            return None

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
        params = {"handle": handle, "from": from_idx}
        if count:
            params["count"] = count
        result = self._make_request("user.status", params)
        return result if result else []

    def get_gym_standings(self, contest_id: str) -> Optional[Dict[str, Any]]:
        """Retorna metadata do Gym contest E a lista de todos os seus problemas."""
        params = {"contestId": contest_id, "from": 1, "count": 1, "showUnofficial": True}
        result = self._make_request("contest.standings", params)
        return result

