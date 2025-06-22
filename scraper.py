from bs4 import BeautifulSoup
import requests

def scrape_website(url):
    try:
        res = requests.get(url, timeout=10)
        soup = BeautifulSoup(res.text, 'html.parser')

        # Extract structured sections
        title = soup.title.string if soup.title else "No Title"
        meta_desc = soup.find('meta', attrs={'name': 'description'})
        meta_desc = meta_desc['content'] if meta_desc else "No meta description"

        # Look for content-heavy divs or sections
        paragraphs = soup.find_all('p')
        content_text = ' '.join(p.get_text() for p in paragraphs[:10])  # Adjust for depth

        # Look for keywords in headers or section titles
        about = soup.find(string=lambda t: t and "about" in t.lower())
        services = soup.find(string=lambda t: t and "service" in t.lower())

        return {
            "title": title,
            "description": meta_desc,
            "content_snippet": content_text.strip(),
            "has_about_section": bool(about),
            "has_services_section": bool(services),
            "url": url
        }

    except Exception as e:
        return {"error": str(e), "url": url}
