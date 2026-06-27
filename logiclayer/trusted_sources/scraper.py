import requests
from bs4 import BeautifulSoup


def scrape_url_text(url: str) -> str:
    """Fetches a URL and extracts clean, readable text content using BeautifulSoup."""
    headers = {
        "User-Agent": "LogicLayerVerifier/1.0 (Educational Fact-Checking Guardrail App)"
    }
    try:
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code != 200:
            return ""

        soup = BeautifulSoup(response.text, "html.parser")

        # Strip non-content elements. noscript is the important addition here --
        # it's where "please enable JavaScript" fallback notices live, and
        # without stripping it, that boilerplate often wins the truncation
        # race over real content because it sits early in <body>.
        for tag in soup(["script", "style", "header", "footer", "nav",
                          "noscript", "aside", "form", "iframe", "svg"]):
            tag.extract()

        # Prefer a real content container if the page has one -- this avoids
        # picking up leftover boilerplate (cookie banners, sidebars, etc.)
        # that isn't caught by the tag-stripping above.
        main_content = soup.find("main") or soup.find("article") or soup.find(id="content")
        target = main_content if main_content else soup

        text = target.get_text(separator=" ")
        lines = (line.strip() for line in text.splitlines())
        chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
        clean_text = " ".join(chunk for chunk in chunks if chunk)

        return clean_text[:2000]
    except Exception as e:
        print(f"⚠️ Scraping error for {url}: {e}")
        return ""