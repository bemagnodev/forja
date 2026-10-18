"""Small, private input review report; never embed external page markup."""
import html
import json
from urllib.parse import urlsplit

from bs4 import BeautifulSoup


def render_review(manifest: dict, sources: dict[str, str]) -> str:
    articles = []
    for item in manifest["items"]:
        root = BeautifulSoup(sources[item["key"]], "html.parser").select_one("div.problem-statement")
        if root is None:
            raise ValueError("Missing problem-statement for review")
        for node in root.select("script, style, nav, meta, link, input, form, button, iframe, object, noscript, [hidden]"):
            if node.parent is not None:
                node.decompose()
        source_text = root.get_text("\n", strip=True)
        url = item["source_url"]
        try:
            parts = urlsplit(url)
            safe_url = parts.scheme == "https" and parts.netloc == "codeforces.com"
        except ValueError:
            safe_url = False
        link = f'<a href="{html.escape(url, quote=True)}" rel="noreferrer">Original</a>' if safe_url else "Original indisponível"
        prepared = json.dumps(item["input"], ensure_ascii=False, indent=2)
        articles.append(
            f'<article><h2>{html.escape(item["key"])}</h2>{link}'
            f'<p>Hash: <code>{html.escape(item["input_hash"])}</code></p>'
            '<p>rating, tags, título e contest não entram no payload.</p>'
            '<div class="columns"><section><h3>Texto-fonte do enunciado</h3>'
            f'<pre>{html.escape(source_text)}</pre></section>'
            f'<section><h3>Entrada preparada</h3><pre>{html.escape(prepared)}</pre></section></div></article>'
        )
    return (
        '<!doctype html><html lang="pt-BR"><meta charset="utf-8">'
        '<title>AI Lab — revisão privada</title>'
        '<style>body{font:16px sans-serif;margin:2rem}.columns{display:grid;grid-template-columns:1fr 1fr;gap:1rem}'
        'pre{white-space:pre-wrap;overflow-wrap:anywhere}article{border-top:1px solid #aaa}'
        '@media(max-width:800px){.columns{grid-template-columns:1fr}}</style>'
        '<h1>Revisão privada dos enunciados</h1>' + "".join(articles) + '</html>'
    )
