"""Mark visual content in text without fetching or interpreting image bytes."""
from urllib.parse import urljoin, urlsplit


def mark_images(root, source_url):
    images = []
    for node in root.find_all(["img", "svg"]):
        position = len(images) + 1
        url = urljoin(source_url, node.get("src", "")) if node.name == "img" else ""
        # Inline/data images remain unprocessed; do not retain their payload.
        if urlsplit(url).scheme not in ("http", "https"):
            url = ""
        title = node.find("title") if node.name == "svg" else None
        alt = node.get("alt", "") if node.name == "img" else (title.get_text() if title else "")
        images.append({"url": url, "alt": alt, "position": position})
        node.replace_with(f"[image:{position}]")
    return images
