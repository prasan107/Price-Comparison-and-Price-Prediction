from abc import ABC, abstractmethod
from playwright.async_api import async_playwright, Browser, BrowserContext
import random


USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:125.0) Gecko/20100101 Firefox/125.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_4) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 Safari/605.1.15",
]


class ScrapedProduct:
    """Standardised product dict returned by every scraper."""
    def __init__(self, name: str, price: float, url: str,
                 image_url: str, platform: str, search_query: str,
                 description: str = ""):
        self.name         = name.strip()
        self.price        = price
        self.url          = url
        self.image_url    = image_url
        self.platform     = platform      # "amazon" | "flipkart" | "blinkit" etc.
        self.search_query = search_query
        self.description  = description

    def to_dict(self) -> dict:
        return {
            "name":         self.name,
            "price":        self.price,
            "url":          self.url,
            "image_url":    self.image_url,
            "platform":     self.platform,
            "search_query": self.search_query,
            "description":  self.description,
        }


class BaseScraper(ABC):
    """
    Every platform scraper extends this class and implements search().
    Adding a new platform = create a new file + implement search(). Nothing else changes.
    """

    platform_name: str = "base"   # override in subclass

    async def _get_browser_context(self, playwright) -> tuple[Browser, BrowserContext]:
        """Shared browser launch config used by all scrapers."""
        browser = await playwright.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent=random.choice(USER_AGENTS),
            viewport={"width": 1280, "height": 720},
            locale="en-IN",
            timezone_id="Asia/Kolkata",
        )
        # Block images and fonts to speed up scraping
        await context.route(
            "**/*.{png,jpg,jpeg,gif,webp,svg,woff,woff2,ttf}",
            lambda route: route.abort()
            if route.request.resource_type in ("image", "font")
            else route.continue_()
        )
        return browser, context

    @abstractmethod
    async def search(self, query: str) -> list[ScrapedProduct]:
        """
        Scrape the platform for the given query.
        Must return a list of ScrapedProduct objects.
        Must never raise — return [] on failure.
        """
        pass