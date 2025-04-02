#!/usr/bin/env python3
"""
Boots.com Product Extractor

This script is designed to extract product information from Boots.com, focusing on 5-star rated
skincare products. It uses a targeted approach to navigate the website and extract detailed
product information including ingredients, country of origin, hazards and cautions, how to use,
and other product details.
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
log_file = f"logs/boots_product_extractor_{timestamp}.log"

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Base URLs
BASE_URL = "https://www.boots.com"
SKINCARE_URL = f"{BASE_URL}/beauty/skincare/skincare-all-skincare"
FIVE_STAR_URL = f"{SKINCARE_URL}?criteria.roundedReviewScore=5"

# Product URLs for testing (if needed)
TEST_PRODUCT_URLS = [
    "https://www.boots.com/beauty/skincare/face-skincare/cleansers-and-toners/no7-radiant-results-revitalising-cleansing-wipes-30s-10263822",
    "https://www.boots.com/beauty/skincare/face-skincare/face-serums/no7-laboratories-firming-booster-serum-30ml-10263820",
    "https://www.boots.com/beauty/skincare/face-skincare/face-moisturisers-and-creams/no7-protect-and-perfect-intense-advanced-day-cream-spf15-50ml-10263818"
]

async def random_delay(min_seconds=1, max_seconds=5):
    """Wait for a random amount of time to avoid detection."""
    delay = random.uniform(min_seconds, max_seconds)
    logger.info(f"Waiting {delay:.2f} seconds before request...")
    await asyncio.sleep(delay)

async def setup_browser(headless=True):
    """Set up the browser with appropriate settings."""
    logger.info("Setting up browser")
    
    playwright = await async_playwright().start()
    browser = await playwright.chromium.launch(headless=headless)
    context = await browser.new_context(
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
        viewport={"width": 1280, "height": 800}
    )
    
    # Create a new page
    page = await context.new_page()
    
    # Handle cookie consent
    try:
        await page.goto(BASE_URL, wait_until="networkidle")
        logger.info("Checking for cookie consent dialog")
        consent_button = await page.query_selector('button#onetrust-accept-btn-handler')
        if consent_button:
            logger.info("Found cookie consent dialog, accepting cookies")
            await consent_button.click()
            await page.wait_for_timeout(2000)
    except Exception as e:
        logger.warning(f"Error handling cookie consent: {str(e)}")
    
    return playwright, browser, context, page

async def extract_product_urls_from_page(page):
    """Extract product URLs from the current page."""
    logger.info("Extracting product URLs from current page")
    
    product_urls = []
    
    try:
        # Method 1: Look for product cards and extract URLs
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
            '.product-tile',
            'article.product',
            'div[data-component="product"]',
            'li.product'
        ]
        
        for selector in product_card_selectors:
            product_cards = await page.query_selector_all(selector)
            logger.info(f"Found {len(product_cards)} product cards with selector: {selector}")
            
            if product_cards:
                for card in product_cards:
                    try:
                        # Extract URL from the card
                        link = await card.query_selector('a')
                        if link:
                            href = await link.get_attribute('href')
                            if href:
                                if href.startswith('/'):
                                    href = f"{BASE_URL}{href}"
                                
                                # Check if it's a product URL
                                if '/product/' in href or '/beauty/skincare/' in href:
                                    product_urls.append(href)
                                    logger.info(f"Found product URL: {href}")
                    except Exception as e:
                        logger.warning(f"Error extracting URL from product card: {str(e)}")
                
                # If we found product cards with this selector, no need to try others
                if product_urls:
                    break
        
        # Method 2: If no product cards found, look for product links directly
        if not product_urls:
            logger.info("No product cards found, looking for product links directly")
            
            # Get all links on the page
            content = await page.content()
            soup = BeautifulSoup(content, 'html.parser')
            
            # Look for product links
            for a in soup.find_all('a', href=True):
                href = a['href']
                if '/product/' in href or ('/beauty/skincare/' in href and not href.endswith('skincare')):
                    if href.startswith('/'):
                        href = f"{BASE_URL}{href}"
                    
                    product_urls.append(href)
                    logger.info(f"Found product URL: {href}")
        
        # Remove duplicates
        product_urls = list(set(product_urls))
        logger.info(f"Found {len(product_urls)} unique product URLs")
        
        return product_urls
    
    except Exception as e:
        logger.error(f"Error extracting product URLs: {str(e)}")
        logger.error(traceback.format_exc())
        return product_urls

async def find_all_5star_product_urls(headless=True):
    """Find all 5-star skincare product URLs."""
    logger.info(f"Finding all 5-star skincare product URLs from {FIVE_STAR_URL}")
    
    # Create necessary directories
    os.makedirs("screenshots", exist_ok=True)
    os.makedirs("data", exist_ok=True)
    
    product_urls = []
    
    try:
        # Set up browser
        playwright, browser, context, page = await setup_browser(headless=headless)
        
        try:
            # Navigate to the 5-star products page
            await random_delay()
            logger.info(f"Navigating to {FIVE_STAR_URL}")
            await page.goto(FIVE_STAR_URL, wait_until="networkidle")
            
            # Take a screenshot of the initial page
            if not headless:
                await page.screenshot(path="screenshots/initial_page.png")
                logger.info("Took screenshot of initial page")
            
            # Check if we're on the correct page
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
            
            # Extract product URLs from the page
            page_product_urls = await extract_product_urls_from_page(page)
            product_urls.extend(page_product_urls)
            
            # If no product URLs found, try using test URLs
            if not product_urls and TEST_PRODUCT_URLS:
                logger.warning("No product URLs found, using test URLs")
                product_urls = TEST_PRODUCT_URLS
            
            # Save URLs to file
            if product_urls:
                url_file = f"data/boots_5star_urls_{timestamp}.txt"
                with open(url_file, 'w') as f:
                    for url in product_urls:
                        f.write(f"{url}\n")
                
                logger.info(f"Saved {len(product_urls)} product URLs to {url_file}")
            else:
                logger.error("No product URLs found")
        
        finally:
            # Close browser
            await browser.close()
            await playwright.stop()
        
        return product_urls
    
    except Exception as e:
        logger.error(f"Error finding 5-star product URLs: {str(e)}")
        logger.error(traceback.format_exc())
        return product_urls

async def scrape_product_details(url, page, screenshot_dir=None):
    """Scrape detailed information for a single product."""
    logger.info(f"Scraping product details: {url}")
    
    product_data = {
        'url': url,
        'timestamp': datetime.now().isoformat()
    }
    
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
                    product_data['name'] = await name_element.text_content()
                    logger.info(f"Found product name: {product_data['name']}")
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
                    product_data['brand'] = await brand_element.text_content()
                    logger.info(f"Found brand: {product_data['brand']}")
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
                    product_data['price'] = await price_element.text_content()
                    logger.info(f"Found price: {product_data['price']}")
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
                    product_data['description'] = await description_element.text_content()
                    logger.info(f"Found description (truncated): {product_data['description'][:50]}...")
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
                    product_data['ingredients'] = await ingredients_element.text_content()
                    logger.info(f"Found ingredients (truncated): {product_data['ingredients'][:50]}...")
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
                product_data['sku'] = sku_elements[0].text.strip()
                logger.info(f"Found SKU: {product_data['sku']}")
        except Exception as e:
            logger.warning(f"Error extracting SKU: {str(e)}")
        
        # Rating
        try:
            rating_elements = soup.select('.rating, .product-rating, [data-test="product-rating"]')
            if rating_elements:
                product_data['rating'] = rating_elements[0].text.strip()
                logger.info(f"Found rating: {product_data['rating']}")
        except Exception as e:
            logger.warning(f"Error extracting rating: {str(e)}")
        
        # Review count
        try:
            review_count_elements = soup.select('.review-count, .product-review-count, [data-test="product-review-count"]')
            if review_count_elements:
                product_data['review_count'] = review_count_elements[0].text.strip()
                logger.info(f"Found review count: {product_data['review_count']}")
        except Exception as e:
            logger.warning(f"Error extracting review count: {str(e)}")
        
        # Country of origin
        try:
            country_elements = soup.select('.country-of-origin, [data-test="country-of-origin"]')
            if country_elements:
                product_data['country_of_origin'] = country_elements[0].text.strip()
                logger.info(f"Found country of origin: {product_data['country_of_origin']}")
        except Exception as e:
            logger.warning(f"Error extracting country of origin: {str(e)}")
        
        # How to use
        try:
            how_to_use_elements = soup.select('.how-to-use, [data-test="how-to-use"]')
            if how_to_use_elements:
                product_data['how_to_use'] = how_to_use_elements[0].text.strip()
                logger.info(f"Found how to use (truncated): {product_data['how_to_use'][:50]}...")
        except Exception as e:
            logger.warning(f"Error extracting how to use: {str(e)}")
        
        # Hazards and cautions
        try:
            hazards_elements = soup.select('.hazards, .cautions, [data-test="hazards-cautions"]')
            if hazards_elements:
                product_data['hazards_cautions'] = hazards_elements[0].text.strip()
                logger.info(f"Found hazards and cautions (truncated): {product_data['hazards_cautions'][:50]}...")
        except Exception as e:
            logger.warning(f"Error extracting hazards and cautions: {str(e)}")
        
        return product_data
    
    except Exception as e:
        logger.error(f"Error scraping product {url}: {str(e)}")
        logger.error(traceback.format_exc())
        product_data['error'] = str(e)
        return product_data

async def process_product_batch(product_urls, batch_index, batch_size, headless=True, screenshot_dir=None):
    """Process a batch of product URLs."""
    logger.info(f"Processing batch {batch_index + 1} with {len(product_urls)} products")
    
    start_idx = batch_index * batch_size
    end_idx = min(start_idx + batch_size, len(product_urls))
    batch_urls = product_urls[start_idx:end_idx]
    
    batch_data = []
    
    try:
        # Set up browser
        playwright, browser, context, page = await setup_browser(headless=headless)
        
        try:
            # Process each product in the batch
            for i, url in enumerate(batch_urls):
                try:
                    logger.info(f"Processing product {start_idx + i + 1}/{len(product_urls)}: {url}")
                    product_data = await scrape_product_details(url, page, screenshot_dir)
                    batch_data.append(product_data)
                    
                    # Save batch data after each product to avoid losing progress
                    batch_file = f"data/boots_5star_batch_{batch_index + 1}_{timestamp}.csv"
                    pd.DataFrame(batch_data).to_csv(batch_file, index=False)
                    logger.info(f"Saved batch data to {batch_file}")
                    
                except Exception as e:
                    logger.error(f"Error processing product {url}: {str(e)}")
                    logger.error(traceback.format_exc())
                    batch_data.append({'url': url, 'error': str(e)})
        
        finally:
            # Close browser
            await browser.close()
            await playwright.stop()
    
    except Exception as e:
        logger.error(f"Error processing batch {batch_index + 1}: {str(e)}")
        logger.error(traceback.format_exc())
    
    return batch_data

async def main():
    """Main function to run the scraper."""
    parser = argparse.ArgumentParser(description="Boots Product Extractor")
    parser.add_argument("--headless", action="store_true", help="Run browser in headless mode")
    parser.add_argument("--max-products", type=int, help="Maximum number of products to scrape")
    parser.add_argument("--batch-size", type=int, default=10, help="Number of products to process in each batch")
    parser.add_argument("--resume-from", type=int, default=0, help="Resume from a specific product index")
    parser.add_argument("--data-dir", default="data", help="Directory to save data files")
    parser.add_argument("--screenshot-dir", default="screenshots", help="Directory to save screenshots")
    parser.add_argument("--urls-file", help="File containing product URLs to scrape (one URL per line)")
    parser.add_argument("--test", action="store_true", help="Use test product URLs")
    args = parser.parse_args()
    
    logger.info(f"Starting Boots Product Extractor")
    logger.info(f"Command line arguments: {args}")
    
    # Create necessary directories
    os.makedirs(args.data_dir, exist_ok=True)
    os.makedirs(args.screenshot_dir, exist_ok=True)
    
    try:
        # Get product URLs
        if args.urls_file and os.path.exists(args.urls_file):
            logger.info(f"Loading product URLs from {args.urls_file}")
            with open(args.urls_file, 'r') as f:
                product_urls = [line.strip() for line in f if line.strip()]
            logger.info(f"Loaded {len(product_urls)} product URLs from file")
        elif args.test:
            logger.info("Using test product URLs")
            product_urls = TEST_PRODUCT_URLS
            logger.info(f"Loaded {len(product_urls)} test product URLs")
        else:
            logger.info("Finding 5-star product URLs")
            product_urls = await find_all_5star_product_urls(headless=args.headless)
            logger.info(f"Found {len(product_urls)} 5-star product URLs")
        
        if not product_urls:
            logger.error("No product URLs to process")
            return 1
        
        # Limit the number of products if specified
        if args.max_products and len(product_urls) > args.max_products:
            logger.info(f"Limiting to {args.max_products} products")
            product_urls = product_urls[:args.max_products]
        
        # Calculate number of batches
        num_products = len(product_urls)
        start_idx = args.resume_from
        num_batches = (num_products - start_idx + args.batch_size - 1) // args.batch_size
        
        logger.info(f"Processing {num_products} products in {num_batches} batches of size {args.batch_size}")
        logger.info(f"Starting from product index {start_idx}")
        
        # Process products in batches
        all_data = []
        
        for batch_idx in range(start_idx // args.batch_size, num_batches):
            logger.info(f"Starting batch {batch_idx + 1}/{num_batches}")
            
            batch_data = await process_product_batch(
                product_urls, 
                batch_idx, 
                args.batch_size, 
                headless=args.headless, 
                screenshot_dir=args.screenshot_dir
            )
            
            all_data.extend(batch_data)
            
            # Save all data after each batch
            all_data_file = os.path.join(args.data_dir, f"boots_5star_products_{timestamp}.csv")
            pd.DataFrame(all_data).to_csv(all_data_file, index=False)
            logger.info(f"Saved all data to {all_data_file}")
            
            # Save progress file
            progress_file = os.path.join(args.data_dir, "scraping_progress.txt")
            with open(progress_file, 'w') as f:
                f.write(f"timestamp: {datetime.now().isoformat()}\n")
                f.write(f"total_products: {num_products}\n")
                f.write(f"processed_products: {min((batch_idx + 1) * args.batch_size, num_products)}\n")
                f.write(f"next_batch_index: {batch_idx + 1}\n")
            logger.info(f"Updated progress file")
        
        logger.info(f"Scraping completed. Processed {len(all_data)} products.")
        return 0
    
    except Exception as e:
        logger.error(f"Error in main: {str(e)}")
        logger.error(traceback.format_exc())
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
