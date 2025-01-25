from fastapi import FastAPI, Request
from contextlib import asynccontextmanager
from typing import Set
import logging
from src.scraper import WebScraper
from src.schema import CrawlSchema
import uvicorn

# Configure logging
logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)

active_scrapers: Set[WebScraper] = set()

@asynccontextmanager
async def lifespan(app: FastAPI):
    logging.info("Application starting up")
    yield
    logging.info("Application shutting down - cleaning up resources")
    for scraper in active_scrapers.copy():
        try:
            await scraper.close()
        except Exception as e:
            logging.error(f"Error closing scraper: {str(e)[:100]}")
    active_scrapers.clear()

app = FastAPI(lifespan=lifespan)

@app.post("/crawl")
async def crawl(body: CrawlSchema):
    """Endpoint for initiating website crawling"""
    scraper = WebScraper()
    active_scrapers.add(scraper)
    try:
        product_urls = await scraper.crawl_websites(body.domains)
        return {"product_urls": product_urls}
    finally:
        try:
            await scraper.close()
            active_scrapers.remove(scraper)
        except Exception as e:
            logging.error(f"Error cleaning up scraper: {str(e)[:100]}")

@app.get("/")
async def health_check():
    return {"status": "ok", "active_scrapers": len(active_scrapers)}

if __name__ == '__main__':
    uvicorn.run(app, port=5005, host="0.0.0.0")