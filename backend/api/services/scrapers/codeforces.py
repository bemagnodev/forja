import re
import requests
from bs4 import BeautifulSoup
from .base import BaseScraper
from .exceptions import UnparseableProblemException

# Mapeamento dos comandos LaTeX mais comuns em problemas do CF para Unicode
LATEX_REPLACEMENTS = [
    (r'\\ldots', '...'),
    (r'\\cdots', '...'),
    (r'\\dots',  '...'),
    (r'\\oplus', '⊕'),
    (r'\\leq',   '≤'),
    (r'\\geq',   '≥'),
    (r'\\neq',   '≠'),
    (r'\\lt',    '<'),
    (r'\\gt',    '>'),
    (r'\\le',    '≤'),
    (r'\\ge',    '≥'),
    (r'\\times', '×'),
    (r'\\cdot',  '·'),
    (r'\\lfloor', '⌊'),
    (r'\\rfloor', '⌋'),
    (r'\\lceil',  '⌈'),
    (r'\\rceil',  '⌉'),
    (r'\\infty',  '∞'),
    (r'\\sum',    'Σ'),
    (r'\\sqrt\{([^}]+)\}', r'√(\1)'),
    (r'\\frac\{([^}]+)\}\{([^}]+)\}', r'(\1)/(\2)'),
    (r'\\left[|(]', ''),
    (r'\\right[|)]', ''),
    (r'\\[a-zA-Z]+', ''),   # remove outros comandos LaTeX desconhecidos
    (r'\{|\}',   ''),       # remove chaves soltas
]

def _clean_latex(text: str) -> str:
    """Remove delimitadores LaTeX e converte símbolos para Unicode legível."""
    # Remove delimitadores $$$...$$$, $$...$$, $...$
    text = re.sub(r'\$\$\$(.+?)\$\$\$', r'\1', text, flags=re.DOTALL)
    text = re.sub(r'\$\$(.+?)\$\$',     r'\1', text, flags=re.DOTALL)
    text = re.sub(r'\$(.+?)\$',         r'\1', text, flags=re.DOTALL)
    # Aplica substituições de símbolos
    for pattern, replacement in LATEX_REPLACEMENTS:
        text = re.sub(pattern, replacement, text)
    # Colapsa espaços duplos resultantes da limpeza
    text = re.sub(r'  +', ' ', text)
    return text.strip()

def _parse_limit_value(raw: str, keyword: str) -> str:
    """
    Extrai apenas o valor numérico + unidade de strings como
    'time limit per test2 seconds' → '2 seconds'
    'memory limit per test256 megabytes' → '256 megabytes'
    """
    # Remove o prefixo de texto fixo que o CF inclui antes do valor
    cleaned = raw.replace(keyword, '').strip()
    return cleaned if cleaned else raw


class CodeforcesScraper(BaseScraper):
    CF_API_BASE = "https://codeforces.com/api"



    def scrape(self, url: str) -> dict:
        response = requests.get(url, timeout=10)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, 'html.parser')

        problem_statement = soup.find('div', class_='problem-statement')
        if not problem_statement:
            raise UnparseableProblemException(
                "No problem-statement div found. Possibly an iframe or PDF."
            )

        header = problem_statement.find('div', class_='header')

        # Extrai título
        title = ""
        if header and header.find('div', class_='title'):
            title = header.find('div', class_='title').text.strip()

        # Extrai e limpa os limites (remove o prefixo de texto do CF)
        time_limit = ""
        if header and header.find('div', class_='time-limit'):
            time_limit = _parse_limit_value(
                header.find('div', class_='time-limit').text.strip(),
                "time limit per test"
            )

        memory_limit = ""
        if header and header.find('div', class_='memory-limit'):
            memory_limit = _parse_limit_value(
                header.find('div', class_='memory-limit').text.strip(),
                "memory limit per test"
            )

        # Descrição: segundo div direto dentro do problem-statement
        description_divs = problem_statement.find_all('div', recursive=False)
        raw_description = (
            description_divs[1].get_text(strip=True, separator='\n')
            if len(description_divs) > 1 else ""
        )
        description = _clean_latex(raw_description)

        # Formato de entrada
        input_format_div = problem_statement.find('div', class_='input-specification')
        input_format = _clean_latex(
            input_format_div.get_text(strip=True, separator='\n') if input_format_div else ""
        )

        # Formato de saída
        output_format_div = problem_statement.find('div', class_='output-specification')
        output_format = _clean_latex(
            output_format_div.get_text(strip=True, separator='\n') if output_format_div else ""
        )

        # Casos de teste de exemplo
        sample_tests_div = problem_statement.find('div', class_='sample-tests')
        testcases = []
        if sample_tests_div:
            samples = sample_tests_div.find_all('div', class_='sample-test')
            if samples:
                inputs  = samples[0].find_all('div', class_='input')
                outputs = samples[0].find_all('div', class_='output')
                for i in range(min(len(inputs), len(outputs))):
                    inp = inputs[i].find('pre').get_text(strip=True, separator='\n')  if inputs[i].find('pre')  else ""
                    out = outputs[i].find('pre').get_text(strip=True, separator='\n') if outputs[i].find('pre') else ""
                    testcases.append({"input": inp, "output": out})

        # Notas
        note_div = problem_statement.find('div', class_='note')
        notes = _clean_latex(note_div.get_text(strip=True, separator='\n') if note_div else "")

        return {
            "title":            title,
            "time_limit":       time_limit,
            "memory_limit":     memory_limit,
            "description":      description,
            "input_format":     input_format,
            "output_format":    output_format,
            "testcases":        testcases,
            "notes":            notes,
        }
