import requests
from bs4 import BeautifulSoup
from .base import BaseScraper
from .exceptions import UnparseableProblemException
from .images import mark_images

class AtCoderScraper(BaseScraper):
    def scrape(self, url: str) -> dict:
        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
        except requests.RequestException as e:
            raise UnparseableProblemException(f"Failed to fetch {url}: {e}")

        soup = BeautifulSoup(response.content, 'html.parser')
        task_statement = soup.find('div', id='task-statement')

        if not task_statement:
            raise UnparseableProblemException("Could not find div with id 'task-statement'")

        # Tentar pegar apenas o inglês
        lang_en = task_statement.find('span', class_='lang-en')
        container = lang_en if lang_en else task_statement
        images = mark_images(container, url)

        result = {
            "description": "",
            "constraints": "",
            "input_format": "",
            "output_format": ""
        }

        # Iterar sobre as seções
        sections = container.find_all('section')
        for section in sections:
            h3 = section.find('h3')
            if not h3:
                continue
            
            title = h3.text.strip().lower()
            
            # Remover o h3 do conteúdo para pegar só o texto
            h3.decompose()
            content = section.get_text(separator=' ', strip=True)

            if "problem statement" in title:
                result["description"] = content
            elif "constraints" in title:
                result["constraints"] = content
            elif title in ("input", "input format"):
                result["input_format"] = content
            elif title in ("output", "output format"):
                result["output_format"] = content

        # Se tudo ficou vazio, é possível que não parseamos direito
        if not any(result.values()):
            raise UnparseableProblemException("Could not extract any standard sections from AtCoder problem")

        if images:
            result["images"] = images
        return result
