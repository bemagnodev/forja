import requests
from bs4 import BeautifulSoup, Tag
from .base import BaseScraper
from .exceptions import UnparseableProblemException

class CSESScraper(BaseScraper):
    def scrape(self, url: str) -> dict:
        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
        except requests.RequestException as e:
            raise UnparseableProblemException(f"Failed to fetch {url}: {e}")

        soup = BeautifulSoup(response.content, 'html.parser')
        content_div = soup.find('div', class_='content')

        if not content_div:
            raise UnparseableProblemException("Could not find div with class 'content'")

        result = {
            "title": soup.title.string.replace("CSES - ", "") if soup.title else "",
            "time_limit": "",
            "memory_limit": "",
            "description": "",
            "constraints": "",
            "input_format": "",
            "output_format": ""
        }

        # Extrair limites
        constraints_ul = content_div.find('ul', class_='task-constraints')
        if constraints_ul:
            for li in constraints_ul.find_all('li'):
                text = li.get_text()
                if "Time limit:" in text:
                    result["time_limit"] = text.replace("Time limit:", "").strip()
                elif "Memory limit:" in text:
                    result["memory_limit"] = text.replace("Memory limit:", "").strip()

        # Extrair descrição (elementos antes do primeiro h1)
        # e outras seções (baseadas no id dos h1)
        current_section = "description"
        section_content = {
            "description": [],
            "input": [],
            "output": [],
            "constraints": [],
            "example": []
        }

        for child in content_div.children:
            if not isinstance(child, Tag):
                continue
            
            # Ignorar scripts, inputs escondidos e a lista de restrições (já parseada)
            if child.name in ['script', 'input', 'title'] or (child.name == 'ul' and 'task-constraints' in child.get('class', [])):
                continue

            if child.name == 'h1':
                # Trocar de seção
                header_id = child.get('id', '')
                if header_id in section_content:
                    current_section = header_id
                else:
                    # Fallback para o texto do h1 se id não for um dos esperados
                    title = child.get_text().strip().lower()
                    if "input" in title: current_section = "input"
                    elif "output" in title: current_section = "output"
                    elif "constraint" in title: current_section = "constraints"
                    else: current_section = title
                continue
            
            if current_section in section_content:
                section_content[current_section].append(child.get_text(separator=' ', strip=True))

        result["description"] = " ".join(section_content.get("description", []))
        result["input_format"] = " ".join(section_content.get("input", []))
        result["output_format"] = " ".join(section_content.get("output", []))
        result["constraints"] = " ".join(section_content.get("constraints", []))

        if not any(result[k] for k in ["description", "input_format", "output_format"]):
            raise UnparseableProblemException("Could not extract main sections from CSES problem")

        return result
