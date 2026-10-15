import subprocess
import sys
import json
import asyncio
from scrapers.base import BaseScraper, ScrapedProduct


FLIPKART_SCRIPT = """
import sys, json, random, re
from playwright.sync_api import sync_playwright

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
]

DETAIL_PAGE_LIMIT = 6

SKIP_TEXTS = {
    "add to compare", "currently unavailable", "add to cart",
    "buy now", "view details", "sponsored", "assured",
    "compare", "wishlist", "seller", "delivery", "free delivery"
}

def extract_price(text):
    match = re.search(r"[\u20b9]\\s?([\\d,]+)", text)
    if not match:
        return None
    try:
        return float(match.group(1).replace(",", ""))
    except:
        return None

def is_valid_name(name: str) -> bool:
    if not name or len(name) < 5:
        return False
    if name.lower().strip() in SKIP_TEXTS:
        return False
    if len(name.split()) <= 2 and not any(c.isdigit() for c in name):
        return False
    return True

def fetch_detail_description(context, url):
    # Visit a Flipkart product page and pull the 'Highlights' bullets.
    if url == "N/A":
        return None
    try:
        page = context.new_page()
        page.goto(url, wait_until="domcontentloaded", timeout=20000)
        page.wait_for_timeout(800)

        parts = []
        # Strategy 1: known highlight-list class patterns (Flipkart rotates these often)
        for sel in ["div._2418kt li", "div._7eSDEz li", "ul._1xgFaf li", "div.aMaAEs li"]:
            loc = page.locator(sel)
            cnt = loc.count()
            if cnt > 0:
                for j in range(min(cnt, 6)):
                    t = loc.nth(j).inner_text().strip()
                    if t and len(t) > 5:
                        parts.append(t)
                if parts:
                    break

        # Strategy 2: fall back to XPath — first <ul> after any 'Highlight' text on the page
        if not parts:
            try:
                xp = page.locator(
                    "xpath=//*[contains(text(),'Highlight')]/following::ul[1]/li"
                )
                cnt = xp.count()
                for j in range(min(cnt, 6)):
                    t = xp.nth(j).inner_text().strip()
                    if t and len(t) > 5:
                        parts.append(t)
            except:
                pass

        page.close()
        if parts:
            return " | ".join(parts[:5])[:400]
    except Exception as e:
        print(f"[Flipkart] detail page failed for {url[:60]}: {e}", file=sys.stderr)
        try:
            page.close()
        except:
            pass
    return None

def scrape(query):
    url = f"https://www.flipkart.com/search?q={query}&otracker=search"
    results = []
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent=random.choice(USER_AGENTS),
            viewport={"width": 1280, "height": 720},
            locale="en-IN",
        )
        page = context.new_page()
        try:
            page.goto(url, wait_until="domcontentloaded", timeout=60000)
            try:
                close_btn = page.locator("button._2KpZ6l._2doB4z")
                if close_btn.count() > 0:
                    close_btn.first.click()
            except:
                pass
        except Exception as e:
            print(f"[Flipkart] load failed: {e}", file=sys.stderr)
            browser.close()
            print(json.dumps([]))
            return

        page.wait_for_timeout(2000)
        products = page.locator("div[data-id]")
        count = products.count()
        print(f"[Flipkart] {count} containers", file=sys.stderr)

        for i in range(min(count, 20)):
            p = products.nth(i)

            if p.locator("a").count() == 0:
                continue

            link = None
            all_links = p.locator("a")
            for j in range(all_links.count()):
                href = all_links.nth(j).get_attribute("href") or ""
                if "/p/" in href or (href.startswith("/") and len(href) > 10):
                    link = href
                    break
            if not link:
                link = p.locator("a").first.get_attribute("href")
            full_url = f"https://www.flipkart.com{link}" if link else "N/A"

            name = ""
            title_links = p.locator("a[title]")
            if title_links.count() > 0:
                for j in range(title_links.count()):
                    candidate = title_links.nth(j).get_attribute("title") or ""
                    if is_valid_name(candidate):
                        name = candidate
                        break

            if not name:
                lines = [l.strip() for l in p.inner_text().split("\\n") if l.strip()]
                for line in lines:
                    if is_valid_name(line):
                        name = line[:200]
                        break

            if not name:
                continue

            img_loc = p.locator("img")
            img = img_loc.first.get_attribute("src") if img_loc.count() > 0 else ""

            # Lightweight fallback description from the search card itself
            desc = ""
            lines = [l.strip() for l in p.inner_text().split("\\n") if l.strip()]
            found_name = False
            for line in lines:
                if not found_name:
                    if line == name:
                        found_name = True
                    continue
                if line == name:
                    continue
                if extract_price(line) is not None and len(line) < 15:
                    continue
                if line.lower() in SKIP_TEXTS:
                    continue
                if len(line) < 4:
                    continue
                desc = line[:200]
                break

            price = extract_price(p.inner_text())
            if price is None:
                continue

            results.append({
                "name": name.strip(), "price": price, "url": full_url,
                "image_url": img or "https://via.placeholder.com/150",
                "description": desc,
                "platform": "flipkart", "search_query": query
            })

        print(f"[Flipkart] {len(results)} parsed from search page", file=sys.stderr)

        # Second pass: visit detail pages for the top N results to get real highlight bullets
        for idx in range(min(len(results), DETAIL_PAGE_LIMIT)):
            better_desc = fetch_detail_description(context, results[idx]["url"])
            if better_desc:
                results[idx]["description"] = better_desc
                print(f"[Flipkart] Got detail description for: {results[idx]['name'][:40]}", file=sys.stderr)

        browser.close()
    print(json.dumps(results))

scrape(sys.argv[1])
"""


class FlipkartScraper(BaseScraper):
    platform_name = "flipkart"

    async def search(self, query: str) -> list[ScrapedProduct]:
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._run_subprocess, query)

    def _run_subprocess(self, query: str) -> list[ScrapedProduct]:
        try:
            import os
            child_env = os.environ.copy()
            child_env["PYTHONIOENCODING"] = "utf-8"
            result = subprocess.run(
                [sys.executable, "-c", FLIPKART_SCRIPT, query],
                capture_output=True, text=True, timeout=150,
                encoding="utf-8", errors="replace", env=child_env
            )
            if result.stderr:
                print(f"[Flipkart] stderr:\n{result.stderr[-2000:]}")
            lines = [l for l in result.stdout.strip().splitlines() if l.strip()]
            if not lines:
                print("[Flipkart] No stdout output.")
                return []
            data = json.loads(lines[-1])
            products = [
                ScrapedProduct(
                    name=d["name"], price=d["price"], url=d["url"],
                    image_url=d["image_url"], platform=d["platform"],
                    search_query=d["search_query"],
                    description=d.get("description", "")
                ) for d in data
            ]
            print(f"[Flipkart] Returning {len(products)} products")
            return products
        except subprocess.TimeoutExpired:
            print("[Flipkart] Timed out")
            return []
        except Exception as e:
            print(f"[Flipkart] Error: {e}")
            return []