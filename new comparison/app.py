from flask import Flask, render_template, request
import asyncio
from playwright.async_api import async_playwright
import random
import pandas as pd

app = Flask(__name__)


# Function to get a random user agent
def get_random_user_agent():
    user_agents = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.1 Safari/605.1.15"
    ]
    return random.choice(user_agents)


# Scrape Amazon Function
async def scrape_amazon(search_term):
    url = f'https://www.amazon.in/s?k={search_term}'
    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent=get_random_user_agent(),
            viewport={"width": 1280, "height": 720}
        )
        page = await context.new_page()

        try:
            await page.goto(url, wait_until='load', timeout=60000)  # 60 seconds timeout
        except Exception as e:
            print(f"Error loading Amazon page: {e}")
            await browser.close()
            return []

        results = []
        products = page.locator('div.s-main-slot div.s-result-item')
        count = await products.count()
        print(f"Found {count} Amazon products.")

        for i in range(count):
            product = products.nth(i)

            # --- Extract Name ---
            name_locator = product.locator('h2 a span')
            name = await name_locator.first.inner_text() if await name_locator.count() > 0 else (
                                                                                                    await product.inner_text())[
                                                                                                :100]

            relative_url = await product.locator('a.a-link-normal').first.get_attribute(
                'href') if await product.locator('a.a-link-normal').count() > 0 else None
            full_url = f"https://www.amazon.in{relative_url}" if relative_url else 'N/A'

            image_locator = product.locator('img.s-image')
            image_url = await image_locator.first.get_attribute(
                'src') if await image_locator.count() > 0 else 'https://via.placeholder.com/150'

            price_text = await product.locator(
                'span.a-price > span.a-offscreen').first.inner_text() if await product.locator(
                'span.a-price > span.a-offscreen').count() > 0 else 'N/A'
            price = None
            if price_text != 'N/A':
                try:
                    price = float(price_text.replace('₹', '').replace(',', '').strip())
                except:
                    price = None

            if price:
                results.append({
                    'product_name': name,
                    'product_url': full_url,
                    'image_url': image_url,
                    'price': price,
                })

        await browser.close()
        return results


# Scrape Flipkart Function
async def scrape_flipkart(search_term):
    url = f'https://www.flipkart.com/search?q={search_term}'
    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent=get_random_user_agent()
        )
        page = await context.new_page()

        try:
            await page.goto(url, wait_until='domcontentloaded', timeout=60000)  # 60 seconds timeout
        except Exception as e:
            print(f"Error loading Flipkart page: {e}")
            await browser.close()
            return []

        await page.wait_for_timeout(3000)  # Wait 3 seconds for any lazy-loaded content

        results = []
        products = page.locator('div[data-id]')  # Locator for products
        count = await products.count()
        print(f"Found {count} Flipkart products.")

        for i in range(count):
            product = products.nth(i)

            if await product.locator("a").count() == 0:
                continue

            title = await product.locator("div").first.inner_text()  # Get product title
            link = await product.locator("a").first.get_attribute("href")  # Get product link
            full_url = f"https://www.flipkart.com{link}" if link else "N/A"
            image_url = await product.locator("img").first.get_attribute("src") or "https://via.placeholder.com/150"

            # Use the provided CSS selector to get the price
            price_text = ""
            try:
                price_locator = product.locator('div.Nx9bqj._4b5DiR')
                price_text = await price_locator.inner_text()  # Extract price text
            except Exception as e:
                print(f"Error extracting price for Flipkart product: {e}")
                price_text = ""

            # Ensure we have valid price text
            try:
                price = float(price_text.replace("₹", "").replace(",", "").strip()) if price_text else 0.0
            except ValueError:
                price = 0.0

            # Append the result
            results.append({
                "product_name": title,
                "product_url": full_url,
                "image_url": image_url,
                "price": price
            })

        await browser.close()
        return results


# Function to save results in Excel
def save_results_to_excel(amazon_results, flipkart_results):
    # Create DataFrame for Amazon products
    amazon_df = pd.DataFrame(amazon_results)

    # Create DataFrame for Flipkart products
    flipkart_df = pd.DataFrame(flipkart_results)

    # Save the results to an Excel file
    with pd.ExcelWriter('product_search_results.xlsx', engine='openpyxl') as writer:
        amazon_df.to_excel(writer, sheet_name='Amazon Products', index=False)
        flipkart_df.to_excel(writer, sheet_name='Flipkart Products', index=False)

    print("Results saved to 'product_search_results.xlsx'")


# Flask route for home page (search form)
@app.route('/')
def index():
    return render_template('index.html')


# Flask route for handling the search and displaying results
@app.route('/search', methods=['POST'])
def search():
    search_term = request.form['search_term']
    if search_term:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        amazon_results = loop.run_until_complete(scrape_amazon(search_term))
        flipkart_results = loop.run_until_complete(scrape_flipkart(search_term))

        # Save the results in Excel
        save_results_to_excel(amazon_results, flipkart_results)

        return render_template('result.html', amazon_results=amazon_results, flipkart_results=flipkart_results)

    return render_template('index.html', error="Please enter a valid search term.")


if __name__ == '__main__':
    app.run(debug=True)
