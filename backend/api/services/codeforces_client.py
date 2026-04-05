import requests
import time
from typing import List, Dict, Any, Optional

class CodeforcesClient:
    """
    Cliente HTTP isolado para consumir a API oficial do Codeforces.
    Zero acoplamento com Regras de Negócio ou DB Django.
    """
    BASE_URL = "https://codeforces.com/api"

    def __init__(self, timeout: int = 15, sleep_time: float = 0.5):
        self.timeout = timeout
        self.sleep_time = sleep_time
        self.session = requests.Session()

    def _make_request(self, endpoint: str, params: dict = None) -> Any:
        url = f"{self.BASE_URL}/{endpoint}"
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
