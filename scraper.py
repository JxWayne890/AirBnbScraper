import requests
from bs4 import BeautifulSoup

def scrape_site(url):
    try:
        response = requests.get(url, timeout=10)
        soup = BeautifulSoup(response.text, "html.parser")
        title = soup.title.string if soup.title else "No Title Found"
        return {"title": title, "url": url}
    except Exception as e:
        return {"error": str(e)}
