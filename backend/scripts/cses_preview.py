import os
import json
import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv

# Carrega o token do .env
load_dotenv()
TOKEN = os.getenv('CSES_SESSION')

# Mapeamento Manual de Seções -> Tags do Codeforces (Padronização)
SECTION_TO_TAGS = {
    "Introductory Problems": ["implementation", "math"],
    "Sorting and Searching": ["sortings", "binary search", "two pointers"],
    "Dynamic Programming": ["dp"],
    "Graph Algorithms": ["graphs", "shortest paths", "dfs and similar"],
    "Range Queries": ["data structures", "trees"],
    "Tree Algorithms": ["trees", "dfs and similar"],
    "Mathematics": ["math", "number theory"],
    "String Algorithms": ["strings"],
    "Geometry": ["geometry"],
    "Advanced Techniques": ["bitmasks", "meet-in-the-middle"],
    "Additional Problems": ["ad-hoc"]
}

def run():
    if not TOKEN:
        print("ERRO: Token não encontrado no .env")
        return

    print("Iniciando varredura no CSES (Modo Leitura)...")
    
    url = "https://cses.fi/problemset/"
    cookies = {'PHPSESSID': TOKEN}
    
    try:
        response = requests.get(url, cookies=cookies, timeout=10)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # O CSES divide por <h2> (Títulos das seções) e <ul> (Listas de problemas)
        # Vamos iterar para pegar o par (Título -> Lista)
        
        content_div = soup.find('div', class_='content')
        if not content_div:
            print("Erro: Não achei a div de conteúdo. Token expirou?")
            return

        preview_data = []
        
        # Pega todos os H2 (Seções)
        sections = content_div.find_all('h2')
        
        for section in sections:
            section_name = section.text.strip()
            # A lista de tarefas é o próximo irmão 'ul' deste h2
            task_list = section.find_next_sibling('ul', class_='task-list')
            
            if not task_list: continue
            
            # Define as tags baseadas na seção
            tags = SECTION_TO_TAGS.get(section_name, ["cses"])
            
            tasks = task_list.find_all('li', class_='task')
            
            for task in tasks:
                link = task.find('a')
                name = link.text
                href = link['href']
                
                # Extraindo Estatísticas (Rating Implícito)
                # Formato: <span class="detail">157095 / 164381</span>
                detail = task.find('span', class_='detail')
                solve_count = 0
                if detail:
                    try:
                        # Pega o primeiro número ("157095")
                        solve_count = int(detail.text.split('/')[0].strip())
                    except:
                        pass

                # Extraindo Status
                icon = task.find('span', class_='task-score')
                status = "TODO"
                if 'full' in icon.get('class', []):
                    status = "OK"
                elif 'zero' in icon.get('class', []):
                    status = "WA"
                
                # Só adiciona se você tentou ou resolveu (opcional)
                if status != "TODO":
                    preview_data.append({
                        "section": section_name,
                        "problem": name,
                        "tags": tags,
                        "status": status,
                        "popularity": solve_count, # Vamos usar isso para estimar dificuldade!
                        "url": href
                    })

        # Salva em JSON para análise
        with open('cses_dump.json', 'w', encoding='utf-8') as f:
            json.dump(preview_data, f, indent=2, ensure_ascii=False)
            
        print(f"✅ Sucesso! {len(preview_data)} problemas encontrados.")
        print("📂 Verifique o arquivo 'cses_dump.json' gerado.")

    except Exception as e:
        print(f"Erro: {e}")

if __name__ == "__main__":
    run()