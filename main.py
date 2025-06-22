from fastapi import FastAPI, Query
from pydantic import BaseModel
from playwright.sync_api import sync_playwright

app = FastAPI()

class ScrapeResult(BaseModel):
    url: str
    text: str

@app.get("/scrape", response_model=ScrapeResult)
def scrape_page(url: str = Query(...)):
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(url, timeout=60000)
        content = page.locator("body").inner_text()
        browser.close()
        return {"url": url, "text": content}
