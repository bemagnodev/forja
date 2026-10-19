from abc import ABC, abstractmethod


def sample_text(pre):
    """Keep sample whitespace and explicit HTML line breaks."""
    for br in pre.find_all('br'):
        br.replace_with('\n')
    return pre.get_text().replace('\r\n', '\n').strip('\n')

class BaseScraper(ABC):
    @abstractmethod
    def scrape(self, url: str) -> dict:
        pass
