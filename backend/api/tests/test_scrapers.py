import pytest
import responses
from api.services.scrapers.exceptions import UnparseableProblemException
from api.services.scrapers.codeforces import CodeforcesScraper

# HTML padrão de um problema do CF, incluindo propriedades aninhadas como o site real
SAMPLE_HTML = """
<div class="problem-statement">
    <div class="header">
        <div class="title">A. Test Problem</div>
        <div class="time-limit"><div class="property-title">time limit per test</div>2 seconds</div>
        <div class="memory-limit"><div class="property-title">memory limit per test</div>256 megabytes</div>
    </div>
    <div>
        <p>Array $$$a$$$ of length $$$n$$$, find $$$x \\leq k$$$.</p>
    </div>
    <div class="input-specification">
        <p>Input format with $$$n \\leq 10^5$$$.</p>
    </div>
    <div class="output-specification">
        <p>Output format.</p>
    </div>
    <div class="sample-tests">
        <div class="sample-test">
            <div class="input"><pre>1</pre></div>
            <div class="output"><pre>2</pre></div>
        </div>
    </div>
    <div class="note">
        <p>Note with $$$x \\oplus y$$$.</p>
    </div>
</div>
"""


@responses.activate
def test_codeforces_scraper_success():
    """
    Cenário: O scraper acessa um problema válido do CF com HTML padrão.
    Resultado Esperado: Dicionário com campos formatados (sem prefixo de limite)
    e LaTeX convertido para Unicode. Não inclui métricas de submissions.
    """
    responses.add(responses.GET, "https://codeforces.com/problemset/problem/1/A", body=SAMPLE_HTML, status=200)

    scraper = CodeforcesScraper()
    result = scraper.scrape("https://codeforces.com/problemset/problem/1/A")

    # Limites devem ter só o valor + unidade, sem o prefixo "time limit per test"
    assert result["time_limit"] == "2 seconds"
    assert result["memory_limit"] == "256 megabytes"

    # LaTeX deve ser removido do texto
    assert "$$$" not in result["description"]
    assert "\\leq" not in result["input_format"]
    assert "≤" in result["input_format"]  # convertido para Unicode
    assert "⊕" in result["notes"]         # \oplus → ⊕

    # Campos básicos
    assert result["title"] == "A. Test Problem"
    assert len(result["testcases"]) == 1

    # total_solved foi removido — garantir que não existe no retorno
    assert "total_solved" not in result


@responses.activate
def test_codeforces_scraper_unparseable():
    """
    Cenário: O Codeforces retorna uma página sem a div problem-statement (ex: iframe de PDF de Gym).
    Resultado Esperado: Scraper lança UnparseableProblemException imediatamente (fail-fast).
    """
    responses.add(
        responses.GET,
        "https://codeforces.com/problemset/problem/1/B",
        body="<div>No problem statement here</div>",
        status=200,
    )

    scraper = CodeforcesScraper()
    with pytest.raises(UnparseableProblemException):
        scraper.scrape("https://codeforces.com/problemset/problem/1/B")

ATCODER_SAMPLE_HTML = """
<html>
<body>
    <div id="task-statement">
        <span class="lang-en">
            <div class="part">
                <section>
                    <h3>Problem Statement</h3>
                    <p>Find the sum of $A$ and $B$.</p>
                </section>
            </div>
            <div class="part">
                <section>
                    <h3>Constraints</h3>
                    <ul><li>$1 \leq A, B \leq 100$</li></ul>
                </section>
            </div>
            <div class="part">
                <section>
                    <h3>Input</h3>
                    <p>Input is given from Standard Input in the following format:</p>
                    <pre>$A$ $B$</pre>
                </section>
            </div>
            <div class="part">
                <section>
                    <h3>Output</h3>
                    <p>Print the answer.</p>
                </section>
            </div>
        </span>
        <span class="lang-ja">
            <div class="part">
                <section>
                    <h3>問題文</h3>
                    <p>$A$ と $B$ の和を求めてください。</p>
                </section>
            </div>
        </span>
    </div>
</body>
</html>
"""

@responses.activate
def test_atcoder_scraper_success():
    """
    Cenário: Acessa problema do AtCoder. Deve focar no lang-en e extrair as seções.
    Resultado Esperado: Dicionário contendo description, constraints, input_format, e output_format sem texto em japonês.
    """
    from api.services.scrapers.atcoder import AtCoderScraper
    
    responses.add(
        responses.GET, 
        "https://atcoder.jp/contests/abc300/tasks/abc300_a", 
        body=ATCODER_SAMPLE_HTML, 
        status=200
    )

    scraper = AtCoderScraper()
    result = scraper.scrape("https://atcoder.jp/contests/abc300/tasks/abc300_a")

    assert "Find the sum" in result["description"]
    assert "問題文" not in result["description"]
    assert "Constraints" not in result["constraints"] # deve pegar só o inner content
    assert "1 \leq A, B \leq 100" in result["constraints"] or "1 ≤ A, B ≤ 100" in result["constraints"]
    assert "Input is given" in result["input_format"]
    assert "Print the answer" in result["output_format"]


@responses.activate
def test_atcoder_scraper_unparseable():
    from api.services.scrapers.atcoder import AtCoderScraper
    
    responses.add(
        responses.GET,
        "https://atcoder.jp/contests/abc300/tasks/abc300_b",
        body="<div>No task statement</div>",
        status=200,
    )

    scraper = AtCoderScraper()
    with pytest.raises(UnparseableProblemException):
        scraper.scrape("https://atcoder.jp/contests/abc300/tasks/abc300_b")

CSES_SAMPLE_HTML = """
<html>
<body>
    <div class="content">
        <ul class="task-constraints">
            <li><b>Time limit:</b> 1.00 s</li>
            <li><b>Memory limit:</b> 512 MB</li>
        </ul>
        <input type="hidden" name="course" value="problemset">
        <p>Consider an algorithm.</p>
        <p>Your task is to simulate the execution.</p>
        <h1 id="input">Input</h1>
        <p>The only input line contains an integer n.</p>
        <h1 id="output">Output</h1>
        <p>Print a line that contains all values.</p>
        <h1 id="constraints">Constraints</h1>
        <ul><li>$1 \\le n \\le 10^6$</li></ul>
        <h1 id="example">Example</h1>
        <p>Input:</p><pre>3</pre>
        <p>Output:</p><pre>3 10 5 16 8 4 2 1</pre>
    </div>
</body>
</html>
"""

@responses.activate
def test_cses_scraper_success():
    """
    Cenário: Acessa problema do CSES.
    Resultado Esperado: Dicionário contendo description, constraints, input_format, e output_format baseados nos headers h1 e tags ul.
    """
    from api.services.scrapers.cses import CSESScraper
    
    responses.add(
        responses.GET, 
        "https://cses.fi/problemset/task/1068", 
        body=CSES_SAMPLE_HTML, 
        status=200
    )

    scraper = CSESScraper()
    result = scraper.scrape("https://cses.fi/problemset/task/1068")

    # Time/Memory limits
    assert "1.00 s" in result["time_limit"]
    assert "512 MB" in result["memory_limit"]

    # Conteúdo principal
    assert "Consider an algorithm." in result["description"]
    assert "simulate the execution." in result["description"]
    assert "The only input line contains" in result["input_format"]
    assert "Print a line that contains" in result["output_format"]
    assert "1 \le n \le 10^6" in result["constraints"] or "1 ≤ n ≤ 10^6" in result["constraints"]

@responses.activate
def test_cses_scraper_unparseable():
    from api.services.scrapers.cses import CSESScraper
    
    responses.add(
        responses.GET,
        "https://cses.fi/problemset/task/9999",
        body="<div>No content class</div>",
        status=200,
    )

    scraper = CSESScraper()
    with pytest.raises(UnparseableProblemException):
        scraper.scrape("https://cses.fi/problemset/task/9999")
