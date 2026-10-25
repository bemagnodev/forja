"""Single Codeforces HTML parser, shared by live classification and datasets."""
from bs4 import BeautifulSoup
from .base import BaseScraper
from .exceptions import UnparseableProblemException
from .codeforces_http import fetch_codeforces_statement
from .images import mark_images


class CodeforcesScraper(BaseScraper):
    def scrape(self, url: str) -> dict:
        html = fetch_codeforces_statement(url)
        try:
            return self.parse_html(html, url)
        except ValueError as exc:
            raise UnparseableProblemException(str(exc)) from None

    @staticmethod
    def parse_html(html: str, source_url: str = "https://codeforces.com") -> dict:
        """Preserve mathematical source instead of destructively simplifying LaTeX."""
        soup = BeautifulSoup(html, "html.parser")
        root = soup.select_one("div.problem-statement")
        if root is None:
            raise ValueError("Missing statement; blocked or unsupported page")
        if root.find(["iframe", "script", "object"]):
            raise ValueError("statement image or embedded content requires review")

        images = mark_images(root, source_url)

        def text(node):
            return node.get_text("\n", strip=True) if node else ""

        # Description can span several direct children; never assume child index 1.
        description = "\n".join(
            text(child) for child in root.find_all(recursive=False)
            if child.name in ("div", "p", "ul", "ol") and not child.get("class")
        ).strip()
        result = {"description": description}
        for field, selector in (("input_format", ".input-specification"),
                                ("output_format", ".output-specification"),
                                ("notes", ".note")):
            result[field] = text(root.select_one(selector))
        for field, selector in (("time_limit", ".time-limit"), ("memory_limit", ".memory-limit")):
            node = root.select_one(selector)
            if node:
                for label in node.select(".property-title"):
                    label.decompose()
            result[field] = text(node)
        if any(not result[field] for field in ("description", "input_format", "output_format", "time_limit", "memory_limit")):
            raise ValueError("Incomplete statement")
        inputs = root.select(".sample-tests .input pre")
        outputs = root.select(".sample-tests .output pre")
        if not inputs or len(inputs) != len(outputs):
            raise ValueError("Missing or unpaired sample")
        result["testcases"] = [{"input": text(i), "output": text(o)} for i, o in zip(inputs, outputs)]
        title = root.select_one(".header .title")
        result["title"] = text(title)
        if images:
            result["images"] = images
        return result
