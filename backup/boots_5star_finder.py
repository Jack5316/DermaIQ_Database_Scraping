#!/usr/bin/env python3
"""
Script to find and extract URLs for all 5-star rated skincare products from Boots.com.
This script focuses specifically on locating product elements on the page.
"""

import os
import sys
import asyncio
import logging
import traceback
from datetime import datetime
from playwright.async_api import async_playwright
from bs4 import BeautifulSoup

# Configure logging
os.makedirs("logs", exist_ok=True)
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
log_file = f"logs/boots_5star_finder_{timestamp}.log"

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("boots_5star_finder")

# URL for 5-star skincare products
FIVE_STAR_URL = "https://www.boots.com/beauty/skincare/skincare-all-skincare?criteria.roundedReviewScore=5"

async def find_5star_product_urls():
    """Find all 5-star skincare product URLs."""
    logger.info(f"Starting to find 5-star product URLs from {FIVE_STAR_URL}")
    
    # Create necessary directories
    os.makedirs("screenshots", exist_ok=True)
    os.makedirs("data", exist_ok=True)
    
    try:
        async with async_playwright() as p:
            # Launch browser
            browser = await p.chromium.launch(headless=False)
            context = await browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
                viewport={"width": 1280, "height": 800}
            )
            page = await context.new_page()
            
            # Navigate to the 5-star products page
            logger.info(f"Navigating to {FIVE_STAR_URL}")
            await page.goto(FIVE_STAR_URL, wait_until="networkidle")
            
            # Take a screenshot of the initial page
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
            
            # Try different selectors for product elements
            product_selectors = [
                '.product-grid .product-tile',
                '.product-list-item',
                '.product-card',
                '.product',
                '[data-test="product-tile"]',
                '.product-grid-item',
                '.product-item',
                '.plp-grid__item'
            ]
            
            # Check each selector
            for selector in product_selectors:
                try:
                    logger.info(f"Trying selector: {selector}")
                    products = await page.query_selector_all(selector)
                    if products:
                        logger.info(f"Found {len(products)} products with selector: {selector}")
                        # Take a screenshot with this selector
                        await page.screenshot(path=f"screenshots/products_with_{selector.replace('.', '_').replace('[', '_').replace(']', '_')}.png")
                        break
                except Exception as e:
                    logger.warning(f"Error with selector {selector}: {str(e)}")
            
            # Try to find the total number of products
            try:
                # Common selectors for product count
                count_selectors = [
                    '.plp__results-count',
                    '.product-count',
                    '.results-count',
                    '[data-test="product-count"]',
                    '.total-items'
                ]
                
                for selector in count_selectors:
                    count_element = await page.query_selector(selector)
                    if count_element:
                        count_text = await count_element.text_content()
                        logger.info(f"Found count element with text: {count_text}")
                        break
            except Exception as e:
                logger.warning(f"Error finding product count: {str(e)}")
            
            # Scroll down to load all products
            logger.info("Starting to scroll to load all products")
            
            # Take screenshots at different scroll positions
            for i in range(1, 11):
                logger.info(f"Scrolling to position {i*10}%")
                await page.evaluate(f"window.scrollTo(0, document.body.scrollHeight * {i/10})")
                await page.wait_for_timeout(2000)
                await page.screenshot(path=f"screenshots/scroll_position_{i*10}percent.png")
            
            # Scroll back to top
            await page.evaluate("window.scrollTo(0, 0)")
            await page.wait_for_timeout(1000)
            
            # Try to click "Load more" or similar buttons
            load_more_selectors = [
                'button.load-more',
                'button.show-more',
                'button[data-test="load-more"]',
                'button:has-text("Load more")',
                'button:has-text("Show more")'
            ]
            
            for selector in load_more_selectors:
                try:
                    button = await page.query_selector(selector)
                    if button:
                        logger.info(f"Found load more button with selector: {selector}")
                        await button.screenshot(path=f"screenshots/load_more_button.png")
                        await button.click()
                        await page.wait_for_timeout(3000)
                        await page.screenshot(path="screenshots/after_load_more.png")
                        break
                except Exception as e:
                    logger.warning(f"Error with load more button {selector}: {str(e)}")
            
            # Get page HTML for analysis
            content = await page.content()
            with open("data/page_content.html", "w", encoding="utf-8") as f:
                f.write(content)
            logger.info("Saved page content to data/page_content.html")
            
            # Use BeautifulSoup to analyze the page
            soup = BeautifulSoup(content, 'html.parser')
            
            # Try to find product links with BeautifulSoup
            product_urls = set()
            
            # Look for anchor tags with product-related attributes or classes
            link_selectors = [
                'a.product-title',
                'a.product-name',
                'a.product-link',
                'a[data-test="product-link"]',
                '.product a',
                '.product-tile a',
                '.product-card a'
            ]
            
            for selector in link_selectors:
                links = soup.select(selector)
                logger.info(f"Found {len(links)} links with selector: {selector}")
                
                for link in links:
                    if 'href' in link.attrs:
                        href = link['href']
                        
                        # Ensure it's a full URL
                        if href.startswith('/'):
                            href = f"https://www.boots.com{href}"
                        
                        # Check if it looks like a product URL
                        if '/product/' in href or '/skincare/' in href:
                            product_urls.add(href)
                            logger.info(f"Added product URL: {href}")
            
            # If we still haven't found any products, try a more general approach
            if not product_urls:
                logger.info("Trying a more general approach to find product URLs")
                
                # Look for all links on the page
                all_links = soup.find_all('a')
                logger.info(f"Found {len(all_links)} links on the page")
                
                for link in all_links:
                    if 'href' in link.attrs:
                        href = link['href']
                        
                        # Ensure it's a full URL
                        if href.startswith('/'):
                            href = f"https://www.boots.com{href}"
                        
                        # Check if it looks like a product URL
                        if '/product/' in href or '/skincare/' in href:
                            product_urls.add(href)
                            logger.info(f"Added product URL: {href}")
            
            # Save URLs to file
            if product_urls:
                url_file = f"data/boots_5star_urls_{timestamp}.txt"
                with open(url_file, 'w') as f:
                    for url in product_urls:
                        f.write(f"{url}\n")
                
                logger.info(f"Saved {len(product_urls)} product URLs to {url_file}")
            else:
                logger.error("No product URLs found")
            
            # Close browser
            await browser.close()
            
            return product_urls
    
    except Exception as e:
        logger.error(f"Error finding 5-star product URLs: {str(e)}")
        logger.error(traceback.format_exc())
        return set()

async def main():
    """Main function."""
    try:
        # Find 5-star product URLs
        product_urls = await find_5star_product_urls()
        
        if product_urls:
            logger.info(f"Successfully found {len(product_urls)} 5-star product URLs")
            return 0
        else:
            logger.error("Failed to find any 5-star product URLs")
            return 1
    
    except Exception as e:
        logger.error(f"Error in main: {str(e)}")
        logger.error(traceback.format_exc())
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
