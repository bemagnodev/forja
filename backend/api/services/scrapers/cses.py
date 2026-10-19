import requests
from bs4 import BeautifulSoup, Tag
from .base import BaseScraper, sample_text
from .exceptions import UnparseableProblemException, fetch_statement
from .images import mark_images

class CSESScraper(BaseScraper):
    def scrape(self, url: str) -> dict:
        response = fetch_statement(url, requests.get)

        soup = BeautifulSoup(response.content, 'html.parser')
        content_div = soup.find('div', class_='content')

        if not content_div:
            raise UnparseableProblemException("Could not find div with class 'content'")
        images = mark_images(content_div, url)

        result = {
            "title": soup.title.get_text().replace("CSES - ", "") if soup.title else "",
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

        body = content_div.select_one('.md') or content_div
        samples = []
        for child in body.children:
            if not isinstance(child, Tag):
                continue
            
            # Ignorar scripts, inputs escondidos e a lista de restrições (já parseada)
            if child.name in ['script', 'input', 'title', 'style', 'link'] or (child.name == 'ul' and 'task-constraints' in child.get('class', [])):
                continue

            if child.name in ('h1', 'h2', 'h3'):
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
                    elif 'example' in title: current_section = 'example'
                    else: current_section = title
                continue
            
            if current_section in section_content:
                if current_section == 'example':
                    samples.extend([child] if child.name == 'pre' else child.find_all('pre'))
                section_content[current_section].append(child.get_text(separator=' ', strip=True))

        result["description"] = " ".join(section_content.get("description", []))
        result["input_format"] = " ".join(section_content.get("input", []))
        result["output_format"] = " ".join(section_content.get("output", []))
        result["constraints"] = " ".join(section_content.get("constraints", []))

        if not any(result[k] for k in ["description", "input_format", "output_format"]):
            raise UnparseableProblemException("Could not extract main sections from CSES problem")

        if len(samples) % 2:
            raise UnparseableProblemException('Unpaired samples')
        if samples:
            values = [sample_text(pre) for pre in samples]
            result['testcases'] = [{'input': values[i], 'output': values[i+1]} for i in range(0, len(values), 2)]

        if images:
            result["images"] = images
        return result
