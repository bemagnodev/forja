import requests
import re
from bs4 import BeautifulSoup
from .base import BaseScraper, sample_text
from .exceptions import UnparseableProblemException, fetch_statement
from .images import mark_images

class AtCoderScraper(BaseScraper):
    def scrape(self, url: str) -> dict:
        response = fetch_statement(url, requests.get)

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
        samples = {}
        sections = container.find_all('section')
        for section in sections:
            h3 = section.find('h3')
            if not h3:
                continue
            
            title = h3.text.strip().lower()
            sample = re.fullmatch(r'sample (input|output)\s+(\d+)', title)
            if sample:
                pre = section.find('pre')
                if pre is None:
                    raise UnparseableProblemException('Missing sample content')
                pair = samples.setdefault(int(sample[2]), {})
                if sample[1] in pair:
                    raise UnparseableProblemException('Duplicate sample')
                pair[sample[1]] = sample_text(pre)
                continue
            
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

        if any(set(pair) != {'input', 'output'} for pair in samples.values()):
            raise UnparseableProblemException('Unpaired samples')
        if samples:
            result['testcases'] = [samples[number] for number in sorted(samples)]

        if images:
            result["images"] = images
        return result
