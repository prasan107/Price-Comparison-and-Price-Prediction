import subprocess
import sys
import json
import asyncio
from scrapers.base import BaseScraper, ScrapedProduct


AMAZON_SCRIPT = r"""
import sys, json, random, re
from playwright.sync_api import sync_playwright

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
]

DETAIL_PAGE_LIMIT = 6

# Words that are NEVER in Amazon listing titles even for genuine products
# These are brand names or generic words — don't require them to match
IGNORE_IN_MATCH = {
    "samsung", "apple", "boat", "mi", "oneplus", "realme", "vivo", "oppo",
    "motorola", "nokia", "asus", "lenovo", "sony", "lg", "philips",
    "mobile", "phone", "smartphone",
}

# Brand sub-brands / product lines — if user types brand, also accept these
BRAND_ALIASES = {
    "boat":    ["aavante", "stone", "astra", "nirvana", "bassheads", "rockerz"],
    "oneplus": ["nord"],
    "mi":      ["xiaomi", "redmi", "poco"],
}

ACCESSORY_KEYWORDS = [
    "charger", "cable", "case", "cover", "screen protector", "tempered glass",
    "adapter", "earphone", "earbud", "power bank", "stand", "holder",
    "wallet", "pouch", "skin", "wrap", "sticker", "lens protector",
    "mfi certified", "type c to", "usb-c to", "lightning to",
]

def extract_price_from_text(text):
    for pat in [r"[\u20b9]\s?([\d,]+\.?\d*)", r"([\d,]+)\s?(?:rupees?|INR)"]:
        m = re.search(pat, text)
        if m:
            try:
                return float(m.group(1).replace(",","").strip())
            except:
                pass
    return None

def is_accessory(name):
    name_lower = name.lower()
    return any(kw in name_lower for kw in ACCESSORY_KEYWORDS)

def is_relevant(name, query):
    name_lower  = name.lower()
    query_lower = query.lower()

    # Strategy 1: exact phrase match
    if query_lower in name_lower:
        return True

    query_words = query_lower.split()

    # Strategy 2: brand aliases
    for brand, aliases in BRAND_ALIASES.items():
        if brand in query_words:
            if any(alias in name_lower for alias in aliases):
                return True

    # Strategy 3: filter significant words
    sig_words = [
        w for w in query_words
        if len(w) > 2 and w not in IGNORE_IN_MATCH
    ]

    if not sig_words:
        return True

    # Separate model-specific words (s24, a55, 16e)
    # from generic words (galaxy, ultra, pro)
    GENERIC_WORDS = {"galaxy", "ultra", "pro", "plus", "max", "mini", "air",
                     "note", "tab", "lite", "edge", "fold", "flip"}

    model_words   = [w for w in sig_words if w not in GENERIC_WORDS]
    generic_words = [w for w in sig_words if w in GENERIC_WORDS]

    # If query has model-specific words (s24, iphone16),
    # ALL of them must appear in the product name
    if model_words:
        return all(w in name_lower for w in model_words)

    # If query is only generic words, at least one must match
    return any(w in name_lower for w in generic_words)
def fetch_detail_description(context, url):
    try:
        page = context.new_page()
        page.goto(url, wait_until="domcontentloaded", timeout=20000)
        page.wait_for_timeout(500)
        bullets_loc = page.locator("#feature-bullets ul.a-unordered-list li span.a-list-item")
        count = bullets_loc.count()
        parts = []
        for j in range(min(count, 5)):
            t = bullets_loc.nth(j).inner_text().strip()
            if t and len(t) > 5 and "report an issue" not in t.lower():
                parts.append(t)
        page.close()
        if parts:
            return " | ".join(parts)[:400]
    except Exception as e:
        print(f"[Amazon] detail page failed for {url[:60]}: {e}", file=sys.stderr)
        try:
            page.close()
        except:
            pass
    return None

def scrape(query):
    url = f"https://www.amazon.in/s?k={query}"
    results = []
    with sync_playwright() as pw:
        try:
            browser = pw.chromium.launch(headless=True, args=["--disable-blink-features=AutomationControlled"])
        except Exception:
            browser = pw.chromium.launch(headless=True)

        context = browser.new_context(
            user_agent=random.choice(USER_AGENTS),
            viewport={"width": 1280, "height": 720},
            locale="en-IN",
            extra_http_headers={"Accept-Language": "en-IN,en;q=0.9"},
        )
        context.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        page = context.new_page()

        try:
            for attempt in range(3):
                try:
                    page.goto(url, wait_until="domcontentloaded", timeout=60000)
                    break
                except Exception as e:
                    print(f"[Amazon] goto attempt {attempt+1} failed: {e}", file=sys.stderr)
                    if attempt == 2:
                        raise
                    page.wait_for_timeout(2000)

            page.wait_for_timeout(1500)
            title = page.title()
            print(f"[Amazon] Page title: {title}", file=sys.stderr)

            if "robot" in title.lower() or page.locator("form[action*='validateCaptcha']").count() > 0:
                print("[Amazon] CAPTCHA detected", file=sys.stderr)
                browser.close()
                print(json.dumps([]))
                return

            page.wait_for_selector("div.s-main-slot", timeout=15000)
        except Exception as e:
            print(f"[Amazon] load failed: {e}", file=sys.stderr)
            browser.close()
            print(json.dumps([]))
            return

        products = page.locator("div.s-main-slot div.s-result-item[data-component-type='s-search-result']")
        count = products.count()
        print(f"[Amazon] {count} raw items", file=sys.stderr)

        for i in range(min(count, 20)):
            p = products.nth(i)

            candidates = []
            for sel in ["h2 a span", "h2 span", "[data-cy='title-recipe'] span", "span.a-size-medium"]:
                loc = p.locator(sel)
                for j in range(loc.count()):
                    txt = loc.nth(j).inner_text().strip()
                    if txt and len(txt) > 3:
                        candidates.append(txt)
            if not candidates:
                continue
            name = max(candidates, key=len)

            if is_accessory(name):
                print(f"[Amazon] Skipping accessory: {name[:50]}", file=sys.stderr)
                continue

            if not is_relevant(name, query):
                print(f"[Amazon] Skipping irrelevant: {name[:50]}", file=sys.stderr)
                continue

            link_loc = p.locator("h2 a")
            rel = link_loc.first.get_attribute("href") if link_loc.count() > 0 else None
            if not rel:
                any_link = p.locator("a.a-link-normal[href*='/dp/']")
                if any_link.count() > 0:
                    rel = any_link.first.get_attribute("href")
            if not rel:
                continue
            full_url = rel if rel.startswith("http") else f"https://www.amazon.in{rel}"

            img_loc = p.locator("img.s-image")
            img = img_loc.first.get_attribute("src") if img_loc.count() > 0 else ""

            desc = ""
            for desc_sel in [
                "div.a-section ul.a-unordered-list li span.a-list-item",
                "span.a-color-secondary",
                "div.a-row.a-size-base span",
            ]:
                desc_loc = p.locator(desc_sel)
                if desc_loc.count() > 0:
                    parts = []
                    for j in range(min(desc_loc.count(), 3)):
                        t = desc_loc.nth(j).inner_text().strip()
                        if t and len(t) > 5:
                            parts.append(t)
                    if parts:
                        desc = " | ".join(parts)[:300]
                        break

            price = None
            loc1 = p.locator("span.a-price > span.a-offscreen")
            if loc1.count() > 0:
                for j in range(loc1.count()):
                    raw = loc1.nth(j).inner_text().replace(",","").strip()
                    cleaned = re.sub(r"[^\d.]", "", raw)
                    if cleaned:
                        try:
                            price = float(cleaned)
                            break
                        except:
                            pass

            if price is None:
                whole_loc = p.locator("span.a-price-whole")
                if whole_loc.count() > 0:
                    raw = whole_loc.first.inner_text().replace(",","").strip().rstrip(".")
                    cleaned = re.sub(r"[^\d]", "", raw)
                    if cleaned:
                        try:
                            frac = 0.0
                            frac_loc = p.locator("span.a-price-fraction")
                            if frac_loc.count() > 0:
                                frac_raw = frac_loc.first.inner_text().strip()
                                frac = float(f"0.{frac_raw}") if frac_raw.isdigit() else 0.0
                            price = float(cleaned) + frac
                        except:
                            pass

            if price is None:
                aria_loc = p.locator("span[aria-label*='\u20b9']")
                if aria_loc.count() > 0:
                    price = extract_price_from_text(aria_loc.first.get_attribute("aria-label") or "")

            if price is None:
                price = extract_price_from_text(p.inner_text())

            if price is None or price <= 0:
                print(f"[Amazon] No price for: {name[:40]}", file=sys.stderr)
                continue

            results.append({
                "name": name, "price": price, "url": full_url,
                "image_url": img or "https://via.placeholder.com/150",
                "description": desc,
                "platform": "amazon", "search_query": query
            })

        print(f"[Amazon] {len(results)} parsed from search page", file=sys.stderr)

        for idx in range(min(len(results), DETAIL_PAGE_LIMIT)):
            better_desc = fetch_detail_description(context, results[idx]["url"])
            if better_desc:
                results[idx]["description"] = better_desc
                print(f"[Amazon] Got detail description for: {results[idx]['name'][:40]}", file=sys.stderr)

        browser.close()
    print(json.dumps(results))

scrape(sys.argv[1])
"""


class AmazonScraper(BaseScraper):
    platform_name = "amazon"

    async def search(self, query: str) -> list[ScrapedProduct]:
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._run_subprocess, query)

    def _run_subprocess(self, query: str) -> list[ScrapedProduct]:
        try:
            import os
            child_env = os.environ.copy()
            child_env["PYTHONIOENCODING"] = "utf-8"
            result = subprocess.run(
                [sys.executable, "-c", AMAZON_SCRIPT, query],
                capture_output=True, text=True, timeout=150,
                encoding="utf-8", errors="replace", env=child_env
            )
            if result.stderr:
                print(f"[Amazon] stderr:\n{result.stderr[-2500:]}")
            lines = [l for l in result.stdout.strip().splitlines() if l.strip()]
            if not lines:
                print("[Amazon] No stdout output.")
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
            print(f"[Amazon] Returning {len(products)} products")
            return products
        except subprocess.TimeoutExpired:
            print("[Amazon] Timed out")
            return []
        except Exception as e:
            print(f"[Amazon] Error: {e}")
            return []