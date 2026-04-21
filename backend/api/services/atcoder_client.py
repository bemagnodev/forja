import requests
import time
from typing import List, Dict, Any, Optional

class AtCoderClient:
    """
    Cliente HTTP isolado para consumir a API do Kenkoooo (AtCoder).
    Não deve conter lógica de regras de negócio ou referências ao banco de dados do Django.
    """
    API_URL = "https://kenkoooo.com/atcoder/atcoder-api/v3"
    RESOURCES_URL = "https://kenkoooo.com/atcoder/resources"

    def __init__(self, timeout: int = 10, sleep_time: float = 1.0):
        # A API Kenkoooo requer pelo menos 1s de delay entre calls grandes para não ser banido
        self.timeout = timeout
        self.sleep_time = sleep_time
        self.session = requests.Session()

    def _make_request(self, url: str, params: dict = None) -> Optional[Any]:
        """
        Método privado centralizado para lidar com TODAS as requisições HTTP.
        """
        try:
            response = self.session.get(url, params=params, timeout=self.timeout)
            response.raise_for_status()
            data = response.json()
            
            # Educação digital: Esperamos um pouco após cada sucesso
            time.sleep(self.sleep_time)
            return data
        except requests.RequestException as e:
            print(f"[AtCoderClient] Erro de rede ou timeout acessando {url}: {e}")
            return None

    def get_user_submissions(self, handle: str, from_epoch: int = 0) -> List[Dict[str, Any]]:
        """
        Busca de forma paginada todas as submissões de um usuário específico na API do Kenkoooo.
        A partir do epoch_second.
        """
        all_submissions = []
        current_epoch = from_epoch

        while True:
            url = f"{self.API_URL}/user/submissions"
            params = {
                'user': handle,
                'from_second': current_epoch
            }
            
            data = self._make_request(url, params=params)
                
            if not data:
                # Kenkoooo retorna None (erro) ou lista vazia quando atingimos o fim das submissões
                break
                
            all_submissions.extend(data)
            
            # Kenkoooo retorna as submissões ordenadas cronologicamente
            # O limit é usualmente 500, então pegamos o último epoch e somamos 1 para a próxima request
            # evitando loop infinito com o mesmo unix timestamp caso haja dezenas no exato segundo.
            last_epoch = data[-1].get('epoch_second', current_epoch)
            current_epoch = last_epoch + 1

            if len(data) < 500:
                # Como o limit padrao é 500 do response se for menor, terminamos
                break

        return all_submissions

    def get_contests(self) -> List[Dict[str, Any]]:
        """Busca o JSON estático de todos os contests do AtCoder no banco do Kenkoooo."""
        url = f"{self.RESOURCES_URL}/contests.json"
        result = self._make_request(url)
        return result if result is not None else []

    def get_problems(self) -> List[Dict[str, Any]]:
        """Busca o JSON estático com título e metadados de todos os problemas."""
        url = f"{self.RESOURCES_URL}/problems.json"
        result = self._make_request(url)
        return result if result is not None else []

    def get_problem_difficulties(self) -> Dict[str, int]:
        """
        Recupera as dificuldades formatadas O(1) do the Kenkoooo API.
        Aplica a fórmula do display oficial e normaliza a estatística 
        para a escala competitiva do Codeforces.
        """
        import math
        
        url = f"{self.RESOURCES_URL}/problem-models.json"
        try:
            data = self._make_request(url)
            # data formato: { "problem_id": {"difficulty": 344, ...}, ... }
            
            def normalize_atcoder_to_cf(rating: int) -> int:
                # 1. Cura Kenkoooo (Negativos/Baixos recebem boost exponencial atcoder)
                if rating < 400:
                    rating = int(400 / math.exp((400 - rating) / 400))
                
                # 2. Conversão Atcoder -> CF Baseado em faixas
                if rating < 400:
                    return int(800 + (rating * (300 / 400))) 
                elif rating < 1200:
                    return int(1100 + ((rating - 400) * (500 / 800)))
                elif rating < 2000:
                    return int(1600 + ((rating - 1200) * (500 / 800)))
                else:
                    return rating + 100

            difficulties = {}
            if data:
                for k, v in data.items():
                    diff = v.get('difficulty')
                    if diff is not None:
                        try:
                            difficulties[k] = normalize_atcoder_to_cf(int(diff))
                        except ValueError:
                            pass
            return difficulties
        except Exception as e:
            print(f"[AtCoderClient] Erro acessando difficulties: {e}")
            return {}
