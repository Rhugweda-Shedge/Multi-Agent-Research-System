from langchain.tools import tool
import requests
from bs4 import BeautifulSoup
from tavily import TavilyClient
import os
from dotenv import load_dotenv
from rich import print

load_dotenv(override=True)
tavily = TavilyClient(api_key=os.getenv("TAVILY_API_KEY"))

@tool
def web_search(query: str) -> str:
    """ Search the web for recent and reliable information on a topic. Returns Titles, URLs and Snippets of the search results. """
    try:
        results = tavily.search(query=query, max_results=5)
    except Exception as e:
        return f"Error searching the web: {str(e)}"

    out = []
    for r in results.get('results', []):
        out.append(
            f"Title: {r['title']}\nURL: {r['url']}\nSnippet: {r['content'][:300]}\n"
        )

    return "\n----\n".join(out) if out else "No results found."

# print(web_search.invoke("what are the recent news of nepal floods?"))

@tool
def scrape_url(url: str) -> str:
    """ Scrape the content of a web page. Returns the text content of the page. """
    try:
        response = requests.get(url, timeout=10, headers={"User-Agent": "Mozilla/5.0"})
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")

        for tag in soup(["script", "style", "nav", "footer"]):
            tag.decompose()
        return soup.get_text(separator=" ", strip=True)[:3000]

    except Exception as e:
        return f"Error scraping URL: {str(e)}"

# print(scrape_url.invoke("https://www.bbc.com/news/live/cwrk34rzx3z2t"))