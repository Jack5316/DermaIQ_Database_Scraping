#!/usr/bin/env python3
"""
Direct scraper for Boots.com 5-star skincare products.
This script uses a more direct approach to extract product information by navigating
to the skincare category and filtering for 5-star products.
"""

import os
import sys
import time
import random
import json
import asyncio
import logging
import argparse
import traceback
from datetime import datetime
import pandas as pd
from bs4 import BeautifulSoup
from playwright.async_api import async_playwright

# Configure logging
os.makedirs("logs", exist_ok=True)
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
log_file = f"logs/boots_5star_direct_scraper_{timestamp}.log"

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Base URL for Boots skincare products
BASE_URL = "https://www.boots.com/beauty/skincare/skincare-all-skincare"
FIVE_STAR_URL = f"{BASE_URL}?criteria.roundedReviewScore=5"

async def random_delay(min_seconds=1, max_seconds=5):
    """Wait for a random amount of time to avoid detection."""
    delay = random.uniform(min_seconds, max_seconds)
    logger.info(f"Waiting {delay:.2f} seconds before request...")
    await asyncio.sleep(delay)

async def get_all_skincare_products(headless=True, max_products=None):
    """Get all skincare products from Boots.com."""
    logger.info("Getting all skincare products")
    
    # Create necessary directories
    os.makedirs("screenshots", exist_ok=True)
    os.makedirs("data", exist_ok=True)
    
    product_data = []
    
    try:
        async with async_playwright() as p:
            # Launch browser
            browser = await p.chromium.launch(headless=headless)
            context = await browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
                viewport={"width": 1280, "height": 800}
            )
            page = await context.new_page()
            
            # Navigate to the skincare products page
            await random_delay()
            logger.info(f"Navigating to {BASE_URL}")
            await page.goto(BASE_URL, wait_until="networkidle")
            
            # Take a screenshot of the initial page
            if not headless:
                await page.screenshot(path="screenshots/initial_page.png")
                logger.info("Took screenshot of initial page")
            
            # Handle cookie consent if present
            try:
                logger.info("Checking for cookie consent dialog")
                consent_button = await page.query_selector('button#onetrust-accept-btn-handler')
                if consent_button:
                    logger.info("Found cookie consent dialog, accepting cookies")
                    await consent_button.click()
                    await page.wait_for_timeout(2000)  # Wait for dialog to disappear
            except Exception as e:
                logger.warning(f"Error handling cookie consent: {str(e)}")
            
            # Apply 5-star filter
            logger.info("Applying 5-star filter")
            
            # Method 1: Try to click on 5-star filter
            try:
                star_filter_selectors = [
                    'input[value="5"]',
                    'input[name="criteria.roundedReviewScore"][value="5"]',
                    'label:has-text("5 stars")',
                    '[data-test="filter-rating-5"]'
                ]
                
                filter_clicked = False
                for selector in star_filter_selectors:
                    filter_element = await page.query_selector(selector)
                    if filter_element:
                        logger.info(f"Found 5-star filter with selector: {selector}")
                        await filter_element.click()
                        await page.wait_for_timeout(5000)  # Wait for page to update
                        filter_clicked = True
                        break
                
                if not filter_clicked:
                    logger.warning("Could not find 5-star filter to click, using direct URL")
                    await page.goto(FIVE_STAR_URL, wait_until="networkidle")
            except Exception as e:
                logger.warning(f"Error clicking 5-star filter: {str(e)}")
                logger.info("Using direct URL for 5-star products")
                await page.goto(FIVE_STAR_URL, wait_until="networkidle")
            
            # Take a screenshot after applying filter
            if not headless:
                await page.screenshot(path="screenshots/after_filter.png")
                logger.info("Took screenshot after applying filter")
            
            # Get the current URL to confirm we're on the 5-star page
            current_url = page.url
            logger.info(f"Current URL: {current_url}")
            
            # Scroll down to load all products
            logger.info("Scrolling to load all products")
            
            # Calculate the number of scrolls needed (assuming ~24 products per page)
            total_products = 285  # Default value
            products_per_page = 24
            num_scrolls = (total_products // products_per_page) + 1
            
            for i in range(num_scrolls):
                logger.info(f"Scroll {i+1}/{num_scrolls}")
                await page.evaluate("window.scrollBy(0, window.innerHeight)")
                await page.wait_for_timeout(2000)
                
                # Try clicking "Load more" button if present
                try:
                    load_more_selectors = [
                        'button.load-more',
                        'button.show-more',
                        'button[data-test="load-more"]',
                        'button:has-text("Load more")',
                        'button:has-text("Show more")'
                    ]
                    
                    for selector in load_more_selectors:
                        load_more = await page.query_selector(selector)
                        if load_more:
                            logger.info(f"Found load more button with selector: {selector}")
                            await load_more.click()
                            await page.wait_for_timeout(5000)  # Wait for new products to load
                            break
                except Exception as e:
                    logger.warning(f"Error clicking load more button: {str(e)}")
            
            # Take a screenshot after scrolling
            if not headless:
                await page.screenshot(path="screenshots/after_scrolling.png")
                logger.info("Took screenshot after scrolling")
            
            # Extract product information directly from the page
            logger.info("Extracting product information")
            
            # Method 1: Try to extract product cards
            product_card_selectors = [
                '.product-grid .product-tile',
                '.product-list-item',
                '.product-card',
                '.product',
                '[data-test="product-tile"]',
                '.product-grid-item',
                '.product-item',
                '.plp-grid__item',
                '.product-list__item',
                '.product-tile'
            ]
            
            for selector in product_card_selectors:
                product_cards = await page.query_selector_all(selector)
                logger.info(f"Found {len(product_cards)} product cards with selector: {selector}")
                
                if product_cards:
                    for i, card in enumerate(product_cards):
                        if max_products and i >= max_products:
                            break
                        
                        try:
                            # Extract product information
                            product_info = {}
                            
                            # URL
                            link = await card.query_selector('a')
                            if link:
                                href = await link.get_attribute('href')
                                if href:
                                    if href.startswith('/'):
                                        href = f"https://www.boots.com{href}"
                                    product_info['url'] = href
                            
                            # Name
                            name_element = await card.query_selector('.product-title, .product-name, h3')
                            if name_element:
                                product_info['name'] = await name_element.text_content()
                            
                            # Brand
                            brand_element = await card.query_selector('.product-brand, .brand')
                            if brand_element:
                                product_info['brand'] = await brand_element.text_content()
                            
                            # Price
                            price_element = await card.query_selector('.product-price, .price')
                            if price_element:
                                product_info['price'] = await price_element.text_content()
                            
                            # Rating
                            rating_element = await card.query_selector('.rating, .product-rating')
                            if rating_element:
                                product_info['rating'] = await rating_element.text_content()
                            
                            # Add to product data
                            if product_info.get('url'):
                                product_data.append(product_info)
                                logger.info(f"Added product: {product_info.get('name', 'Unknown')} - {product_info.get('url')}")
                        except Exception as e:
                            logger.warning(f"Error extracting product info from card {i+1}: {str(e)}")
                    
                    break  # Break after finding a working selector
            
            # Method 2: If no product cards found, try to extract product links directly
            if not product_data:
                logger.info("No product cards found, trying to extract product links directly")
                
                # Get all links on the page
                all_links = await page.query_selector_all('a')
                logger.info(f"Found {len(all_links)} links on the page")
                
                product_links = []
                for link in all_links:
                    try:
                        href = await link.get_attribute('href')
                        if href and ('/product/' in href or '/skincare/' in href):
                            if href.startswith('/'):
                                href = f"https://www.boots.com{href}"
                            
                            # Check if it's a product link (not a category)
                            if '/product/' in href:
                                product_links.append(href)
                    except Exception as e:
                        continue
                
                # Remove duplicates
                product_links = list(set(product_links))
                logger.info(f"Found {len(product_links)} unique product links")
                
                # Create basic product data
                for url in product_links:
                    product_data.append({'url': url})
            
            # Method 3: If still no product data, try to extract from page HTML
            if not product_data:
                logger.info("No product data found, trying to extract from page HTML")
                
                # Get page HTML
                content = await page.content()
                soup = BeautifulSoup(content, 'html.parser')
                
                # Look for product links
                product_links = []
                for a in soup.find_all('a', href=True):
                    href = a['href']
                    if '/product/' in href:
                        if href.startswith('/'):
                            href = f"https://www.boots.com{href}"
                        product_links.append(href)
                
                # Remove duplicates
                product_links = list(set(product_links))
                logger.info(f"Found {len(product_links)} unique product links from HTML")
                
                # Create basic product data
                for url in product_links:
                    product_data.append({'url': url})
            
            # Method 4: Try to extract from network requests
            if not product_data:
                logger.info("No product data found, trying to extract from network requests")
                
                # Enable request interception
                await page.route('**/*', lambda route: route.continue_())
                
                # Reload the page
                await page.reload(wait_until="networkidle")
                
                # Get all requests
                requests = await page.context.all_requests
                
                # Look for API requests that might contain product data
                api_requests = [req for req in requests if 
                               '/api/' in req.url or 
                               '.json' in req.url or 
                               'graphql' in req.url]
                
                logger.info(f"Found {len(api_requests)} potential API requests")
                
                # Try to extract product data from API responses
                for req in api_requests:
                    try:
                        response = await req.response()
                        if response:
                            body = await response.text()
                            if 'product' in body.lower():
                                logger.info(f"Found potential product data in response from: {req.url}")
                                
                                # Try to parse JSON
                                try:
                                    data = json.loads(body)
                                    
                                    # Look for product data in the response
                                    if isinstance(data, dict):
                                        if 'products' in data:
                                            products = data['products']
                                            logger.info(f"Found {len(products)} products in API response")
                                            
                                            for product in products:
                                                if isinstance(product, dict):
                                                    product_info = {}
                                                    
                                                    # Extract product information
                                                    if 'url' in product:
                                                        product_info['url'] = product['url']
                                                    elif 'productUrl' in product:
                                                        product_info['url'] = product['productUrl']
                                                    
                                                    if 'name' in product:
                                                        product_info['name'] = product['name']
                                                    elif 'productName' in product:
                                                        product_info['name'] = product['productName']
                                                    
                                                    if 'brand' in product:
                                                        product_info['brand'] = product['brand']
                                                    elif 'brandName' in product:
                                                        product_info['brand'] = product['brandName']
                                                    
                                                    if 'price' in product:
                                                        product_info['price'] = product['price']
                                                    
                                                    # Add to product data if it has a URL
                                                    if product_info.get('url'):
                                                        product_data.append(product_info)
                                except Exception as e:
                                    logger.warning(f"Error parsing JSON from response: {str(e)}")
                    except Exception as e:
                        logger.warning(f"Error processing request: {str(e)}")
            
            # Save product data to file
            if product_data:
                # Save as JSON
                json_file = f"data/boots_5star_products_{timestamp}.json"
                with open(json_file, 'w') as f:
                    json.dump(product_data, f, indent=2)
                logger.info(f"Saved {len(product_data)} products to {json_file}")
                
                # Save as CSV
                csv_file = f"data/boots_5star_products_{timestamp}.csv"
                pd.DataFrame(product_data).to_csv(csv_file, index=False)
                logger.info(f"Saved {len(product_data)} products to {csv_file}")
                
                # Save URLs to text file
                url_file = f"data/boots_5star_urls_{timestamp}.txt"
                with open(url_file, 'w') as f:
                    for product in product_data:
                        if 'url' in product:
                            f.write(f"{product['url']}\n")
                logger.info(f"Saved product URLs to {url_file}")
            else:
                logger.error("No product data found")
            
            # Close browser
            await browser.close()
            
            return product_data
    
    except Exception as e:
        logger.error(f"Error getting skincare products: {str(e)}")
        logger.error(traceback.format_exc())
        return product_data

async def scrape_product_details(product_data, headless=True, screenshot_dir=None):
    """Scrape detailed information for each product."""
    logger.info(f"Scraping details for {len(product_data)} products")
    
    # Create necessary directories
    if screenshot_dir:
        os.makedirs(screenshot_dir, exist_ok=True)
    
    detailed_data = []
    
    try:
        async with async_playwright() as p:
            # Launch browser
            browser = await p.chromium.launch(headless=headless)
            context = await browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
                viewport={"width": 1280, "height": 800}
            )
            page = await context.new_page()
            
            # Handle cookie consent
            try:
                await page.goto("https://www.boots.com", wait_until="networkidle")
                logger.info("Checking for cookie consent dialog")
                consent_button = await page.query_selector('button#onetrust-accept-btn-handler')
                if consent_button:
                    logger.info("Found cookie consent dialog, accepting cookies")
                    await consent_button.click()
                    await page.wait_for_timeout(2000)
            except Exception as e:
                logger.warning(f"Error handling cookie consent: {str(e)}")
            
            # Process each product
            for i, product in enumerate(product_data):
                logger.info(f"Processing product {i+1}/{len(product_data)}")
                
                if 'url' not in product:
                    logger.warning(f"Product {i+1} has no URL, skipping")
                    detailed_data.append(product)
                    continue
                
                url = product['url']
                logger.info(f"Scraping product: {url}")
                
                try:
                    # Navigate to the product page
                    await random_delay()
                    await page.goto(url, wait_until="networkidle")
                    
                    # Take screenshot if directory is provided
                    if screenshot_dir:
                        product_id = url.split('/')[-1].split('?')[0]
                        screenshot_path = os.path.join(screenshot_dir, f"{product_id}.png")
                        await page.screenshot(path=screenshot_path)
                        logger.info(f"Saved screenshot to {screenshot_path}")
                    
                    # Extract product information
                    
                    # Product name
                    try:
                        name_selectors = [
                            'h1.product-details__name',
                            '.product-title',
                            '.product-name',
                            'h1[data-test="product-name"]',
                            'h1'
                        ]
                        
                        for selector in name_selectors:
                            name_element = await page.query_selector(selector)
                            if name_element:
                                product['name'] = await name_element.text_content()
                                logger.info(f"Found product name: {product['name']}")
                                break
                    except Exception as e:
                        logger.warning(f"Error extracting product name: {str(e)}")
                    
                    # Brand
                    try:
                        brand_selectors = [
                            '.product-details__brand',
                            '.product-brand',
                            '[data-test="product-brand"]',
                            '.brand'
                        ]
                        
                        for selector in brand_selectors:
                            brand_element = await page.query_selector(selector)
                            if brand_element:
                                product['brand'] = await brand_element.text_content()
                                logger.info(f"Found brand: {product['brand']}")
                                break
                    except Exception as e:
                        logger.warning(f"Error extracting brand: {str(e)}")
                    
                    # Price
                    try:
                        price_selectors = [
                            '.product-details__price',
                            '.product-price',
                            '[data-test="product-price"]',
                            '.price'
                        ]
                        
                        for selector in price_selectors:
                            price_element = await page.query_selector(selector)
                            if price_element:
                                product['price'] = await price_element.text_content()
                                logger.info(f"Found price: {product['price']}")
                                break
                    except Exception as e:
                        logger.warning(f"Error extracting price: {str(e)}")
                    
                    # Description
                    try:
                        description_selectors = [
                            '.product-details__description',
                            '.product-description',
                            '[data-test="product-description"]',
                            '.description'
                        ]
                        
                        for selector in description_selectors:
                            description_element = await page.query_selector(selector)
                            if description_element:
                                product['description'] = await description_element.text_content()
                                logger.info(f"Found description (truncated): {product['description'][:50]}...")
                                break
                    except Exception as e:
                        logger.warning(f"Error extracting description: {str(e)}")
                    
                    # Ingredients
                    try:
                        # First try to find and click an "Ingredients" tab or button
                        ingredient_tab_selectors = [
                            'button:has-text("Ingredients")',
                            'a:has-text("Ingredients")',
                            'div[data-tab="ingredients"]',
                            '#tab-ingredients'
                        ]
                        
                        for selector in ingredient_tab_selectors:
                            tab = await page.query_selector(selector)
                            if tab:
                                logger.info(f"Found ingredients tab with selector: {selector}")
                                await tab.click()
                                await page.wait_for_timeout(1000)
                                break
                        
                        # Now try to extract the ingredients
                        ingredient_selectors = [
                            '.product-details__ingredients',
                            '.product-ingredients',
                            '[data-test="product-ingredients"]',
                            '.ingredients',
                            '#ingredients'
                        ]
                        
                        for selector in ingredient_selectors:
                            ingredients_element = await page.query_selector(selector)
                            if ingredients_element:
                                product['ingredients'] = await ingredients_element.text_content()
                                logger.info(f"Found ingredients (truncated): {product['ingredients'][:50]}...")
                                break
                    except Exception as e:
                        logger.warning(f"Error extracting ingredients: {str(e)}")
                    
                    # Get page HTML for further analysis
                    content = await page.content()
                    soup = BeautifulSoup(content, 'html.parser')
                    
                    # Extract any additional information that might be available
                    
                    # Product ID/SKU
                    try:
                        sku_elements = soup.select('[data-test="product-sku"], .product-sku, .sku')
                        if sku_elements:
                            product['sku'] = sku_elements[0].text.strip()
                            logger.info(f"Found SKU: {product['sku']}")
                    except Exception as e:
                        logger.warning(f"Error extracting SKU: {str(e)}")
                    
                    # Rating
                    try:
                        rating_elements = soup.select('.rating, .product-rating, [data-test="product-rating"]')
                        if rating_elements:
                            product['rating'] = rating_elements[0].text.strip()
                            logger.info(f"Found rating: {product['rating']}")
                    except Exception as e:
                        logger.warning(f"Error extracting rating: {str(e)}")
                    
                    # Review count
                    try:
                        review_count_elements = soup.select('.review-count, .product-review-count, [data-test="product-review-count"]')
                        if review_count_elements:
                            product['review_count'] = review_count_elements[0].text.strip()
                            logger.info(f"Found review count: {product['review_count']}")
                    except Exception as e:
                        logger.warning(f"Error extracting review count: {str(e)}")
                    
                    # Country of origin
                    try:
                        country_elements = soup.select('.country-of-origin, [data-test="country-of-origin"]')
                        if country_elements:
                            product['country_of_origin'] = country_elements[0].text.strip()
                            logger.info(f"Found country of origin: {product['country_of_origin']}")
                    except Exception as e:
                        logger.warning(f"Error extracting country of origin: {str(e)}")
                    
                    # How to use
                    try:
                        how_to_use_elements = soup.select('.how-to-use, [data-test="how-to-use"]')
                        if how_to_use_elements:
                            product['how_to_use'] = how_to_use_elements[0].text.strip()
                            logger.info(f"Found how to use (truncated): {product['how_to_use'][:50]}...")
                    except Exception as e:
                        logger.warning(f"Error extracting how to use: {str(e)}")
                    
                    # Hazards and cautions
                    try:
                        hazards_elements = soup.select('.hazards, .cautions, [data-test="hazards-cautions"]')
                        if hazards_elements:
                            product['hazards_cautions'] = hazards_elements[0].text.strip()
                            logger.info(f"Found hazards and cautions (truncated): {product['hazards_cautions'][:50]}...")
                    except Exception as e:
                        logger.warning(f"Error extracting hazards and cautions: {str(e)}")
                    
                    # Add timestamp
                    product['timestamp'] = datetime.now().isoformat()
                    
                    # Add to detailed data
                    detailed_data.append(product)
                    
                    # Save progress after each product
                    progress_file = f"data/boots_5star_detailed_{timestamp}.csv"
                    pd.DataFrame(detailed_data).to_csv(progress_file, index=False)
                    logger.info(f"Saved progress to {progress_file}")
                    
                except Exception as e:
                    logger.error(f"Error scraping product {url}: {str(e)}")
                    logger.error(traceback.format_exc())
                    product['error'] = str(e)
                    detailed_data.append(product)
            
            # Close browser
            await browser.close()
            
            return detailed_data
    
    except Exception as e:
        logger.error(f"Error scraping product details: {str(e)}")
        logger.error(traceback.format_exc())
        return detailed_data

async def main():
    """Main function to run the scraper."""
    parser = argparse.ArgumentParser(description="Boots 5-Star Direct Scraper")
    parser.add_argument("--headless", action="store_true", help="Run browser in headless mode")
    parser.add_argument("--max-products", type=int, help="Maximum number of products to scrape")
    parser.add_argument("--data-dir", default="data", help="Directory to save data files")
    parser.add_argument("--screenshot-dir", default="screenshots", help="Directory to save screenshots")
    parser.add_argument("--skip-details", action="store_true", help="Skip scraping detailed product information")
    parser.add_argument("--product-file", help="JSON file containing product data to scrape details for")
    args = parser.parse_args()
    
    logger.info(f"Starting Boots 5-star direct scraper")
    logger.info(f"Command line arguments: {args}")
    
    # Create necessary directories
    os.makedirs(args.data_dir, exist_ok=True)
    os.makedirs(args.screenshot_dir, exist_ok=True)
    
    try:
        # Get product data
        if args.product_file and os.path.exists(args.product_file):
            logger.info(f"Loading product data from {args.product_file}")
            with open(args.product_file, 'r') as f:
                product_data = json.load(f)
            logger.info(f"Loaded {len(product_data)} products from file")
        else:
            logger.info("Getting skincare products")
            product_data = await get_all_skincare_products(headless=args.headless, max_products=args.max_products)
            logger.info(f"Found {len(product_data)} products")
        
        if not product_data:
            logger.error("No product data found")
            return 1
        
        # Scrape detailed product information
        if not args.skip_details:
            logger.info("Scraping detailed product information")
            detailed_data = await scrape_product_details(
                product_data, 
                headless=args.headless, 
                screenshot_dir=args.screenshot_dir
            )
            logger.info(f"Scraped details for {len(detailed_data)} products")
            
            # Save final data
            final_file = os.path.join(args.data_dir, f"boots_5star_final_{timestamp}.csv")
            pd.DataFrame(detailed_data).to_csv(final_file, index=False)
            logger.info(f"Saved final data to {final_file}")
        
        logger.info("Scraping completed successfully")
        return 0
    
    except Exception as e:
        logger.error(f"Error in main: {str(e)}")
        logger.error(traceback.format_exc())
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
