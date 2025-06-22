from fastapi import FastAPI, Request
from playwright.async_api import async_playwright

app = FastAPI()

@app.get("/")
async def root():
    return {"message": "Scraper is alive"}

@app.post("/scrape")
async def scrape(request: Request):
    data = await request.json()
    url = data.get("url")

    if not url:
        return {"error": "Missing 'url' in request"}

    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()
        await page.goto(url)

        content = await page.content()
        title = await page.title()

        await browser.close()

        return {
            "title": title,
            "html": content[:2000]  # Only return first 2000 chars
        }
