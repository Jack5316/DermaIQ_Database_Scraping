#!/usr/bin/env python3
"""
Boots Scraper v2

A more robust scraper for Boots.com that adapts to the current website structure.
Uses Playwright for browser automation and handles dynamic content loading.
"""

import os
import time
import random
import re
import json
import argparse
import pandas as pd
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse
from bs4 import BeautifulSoup
import asyncio
from playwright.async_api import async_playwright, TimeoutError

# Set up logging
import logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("boots_scraper.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def save_to_csv(product_data_list, filename='boots_products.csv'):
    """
    Save the product data to a CSV file.
    
    Args:
        product_data_list (list): List of product data dictionaries.
        filename (str): The name of the CSV file.
    """
    if not product_data_list:
        logger.warning("No product data to save.")
        return
    
    # Convert list of dictionaries to DataFrame
    df = pd.DataFrame(product_data_list)
    
    # Save to CSV
    df.to_csv(filename, index=False, encoding='utf-8')
    logger.info(f"Data saved to {filename}")

async def scrape_boots_product(page, url):
    """
    Scrape product information from a Boots.com product page using Playwright.
    
    Args:
        page (Page): Playwright page object.
        url (str): The URL of the product page.
        
    Returns:
        dict: A dictionary containing the scraped product information.
    """
    # Initialize the product data dictionary
    product_data = {
        'url': url,
        'source': 'Boots',
        'product_name': None,
        'brand': None,
        'price': None,
        'rating': None,
        'review_count': None,
        'ingredients': None,
        'hazards_and_cautions': None,
        'product_details': None,
        'how_to_use': None,
        'country_of_origin': None
    }
    
    # Extract product ID from URL if possible
    product_id_match = re.search(r'(\d+)(?:[^/]*)?$', url)
    if product_id_match:
        product_data['product_id'] = product_id_match.group(1)
    
    try:
        # Navigate to the URL
        logger.info(f"Navigating to: {url}")
        response = await page.goto(url, wait_until="domcontentloaded", timeout=60000)
        
        # Check if the page was successfully loaded
        if response and response.status >= 400:
            logger.error(f"Failed to load page. Status code: {response.status}")
            return product_data
        
        # Accept cookies if the banner appears
        try:
            cookie_button = await page.query_selector('button:has-text("Accept All Cookies"), .cookie-banner__button, #onetrust-accept-btn-handler')
            if cookie_button:
                await cookie_button.click()
                logger.info("Accepted cookies")
                await page.wait_for_timeout(1000)  # Wait for the banner to disappear
        except Exception as e:
            logger.warning(f"Error handling cookie banner: {str(e)}")
        
        # Wait for the product content to load
        try:
            await page.wait_for_selector('h1, .product-title, [data-test="product-title"], .pdp-main', timeout=10000)
        except Exception as e:
            logger.warning(f"Error waiting for product title selector: {str(e)}")
        
        # Check if we got a 404 page
        page_title = await page.title()
        page_content = await page.content()
        if "Page not found" in page_title or "Page not found" in page_content:
            logger.error(f"Page not found (404) for URL: {url}")
            return product_data
        
        # Wait for product information to load
        try:
            await page.wait_for_load_state("networkidle", timeout=10000)
        except Exception as e:
            logger.warning(f"Warning: Page load state timeout: {str(e)}")
        
        # Take a screenshot for debugging
        os.makedirs("screenshots", exist_ok=True)
        screenshot_path = f"screenshots/{product_data['product_id'] if product_data.get('product_id') else 'unknown'}.png"
        await page.screenshot(path=screenshot_path)
        logger.info(f"Screenshot saved to {screenshot_path}")
        
        # Get the page content
        content = await page.content()
        soup = BeautifulSoup(content, 'html.parser')
        
        # Extract product name
        try:
            # Try multiple selectors for product name
            selectors = [
                'h1.product-title', 
                '.product-name h1', 
                '[data-test="product-title"]',
                'h1',
                '.product__title',
                '.product-detail__title',
                '.pdp-main h1'
            ]
            
            for selector in selectors:
                name_element = await page.query_selector(selector)
                if name_element:
                    product_data['product_name'] = (await name_element.text_content()).strip()
                    break
            
            if not product_data['product_name']:
                # Try with BeautifulSoup if Playwright selectors failed
                for selector in selectors:
                    name_element = soup.select_one(selector)
                    if name_element:
                        product_data['product_name'] = name_element.text.strip()
                        break
        except Exception as e:
            logger.error(f"Error extracting product name: {str(e)}")
        
        # Extract brand
        try:
            # Try multiple selectors for brand
            brand_selectors = [
                '.brand-name', 
                '.product-brand', 
                '[data-test="product-brand"]',
                '.product__brand',
                '.product-detail__brand',
                '.brand'
            ]
            
            for selector in brand_selectors:
                brand_element = await page.query_selector(selector)
                if brand_element:
                    product_data['brand'] = (await brand_element.text_content()).strip()
                    break
            
            if not product_data['brand'] and product_data['product_name']:
                # Try to extract brand from product name
                brand_match = re.match(r'^([A-Za-z0-9\s]+)', product_data['product_name'])
                if brand_match:
                    potential_brand = brand_match.group(1).strip()
                    if len(potential_brand.split()) <= 3:  # Most brands are 1-3 words
                        product_data['brand'] = potential_brand
        except Exception as e:
            logger.error(f"Error extracting brand: {str(e)}")
        
        # Extract price
        try:
            # Try multiple selectors for price
            price_selectors = [
                '.product-price', 
                '.price', 
                '[data-test="product-price"]',
                '.product__price',
                '.product-detail__price',
                '.price-info',
                '.current-price'
            ]
            
            for selector in price_selectors:
                price_element = await page.query_selector(selector)
                if price_element:
                    price_text = (await price_element.text_content()).strip()
                    # Extract price using regex to handle different formats
                    price_match = re.search(r'£(\d+\.\d+)', price_text)
                    if price_match:
                        product_data['price'] = price_match.group(1)
                    else:
                        product_data['price'] = price_text
                    break
        except Exception as e:
            logger.error(f"Error extracting price: {str(e)}")
        
        # Click on any tab or button that might reveal more product information
        tab_buttons = [
            "Ingredients", 
            "Product Information", 
            "Product Details",
            "How to use", 
            "Warnings", 
            "Description"
        ]
        
        for tab_text in tab_buttons:
            try:
                # Try to find buttons or tabs with this text
                button = await page.query_selector(f'button:text("{tab_text}"), [role="tab"]:text("{tab_text}")')
                if button:
                    await button.click()
                    logger.info(f"Clicked on tab: {tab_text}")
                    await page.wait_for_timeout(1000)  # Wait for content to load
            except Exception as e:
                logger.warning(f"Error clicking tab {tab_text}: {str(e)}")
        
        # After clicking tabs, get updated page content
        content = await page.content()
        soup = BeautifulSoup(content, 'html.parser')
        
        # Extract ingredients
        try:
            # Look for sections that might contain ingredients
            ingredients_selectors = [
                '.ingredients', 
                '#ingredients',
                '[data-test="ingredients"]',
                '.product-ingredients',
                '.product-info__ingredients',
                '.pdp-info-section:contains("Ingredients")',
                'div[id*="ingredients"]',
                'section[id*="ingredients"]',
                'div[class*="ingredients"]',
                'section[class*="ingredients"]'
            ]
            
            for selector in ingredients_selectors:
                try:
                    ingredients_element = soup.select_one(selector)
                    if ingredients_element:
                        product_data['ingredients'] = ingredients_element.text.strip()
                        logger.info("Found ingredients")
                        break
                except Exception as e:
                    logger.warning(f"Error with ingredients selector {selector}: {str(e)}")
            
            # If still not found, try looking for headings followed by content
            if not product_data['ingredients']:
                headings = soup.find_all(['h2', 'h3', 'h4', 'strong', 'b'])
                for heading in headings:
                    if 'ingredient' in heading.text.lower():
                        # Get the next sibling paragraph or div
                        next_elem = heading.find_next(['p', 'div', 'span'])
                        if next_elem:
                            product_data['ingredients'] = next_elem.text.strip()
                            logger.info("Found ingredients after heading")
                            break
            
            # If still not found, try looking in the entire page text
            if not product_data['ingredients']:
                page_text = soup.get_text()
                ingredients_pattern = r'(?:ingredients|ingredient list|what\'s in it)[:\s]+(.*?)(?:\n\n|\.|$)'
                ingredients_match = re.search(ingredients_pattern, page_text, re.IGNORECASE | re.DOTALL)
                if ingredients_match:
                    product_data['ingredients'] = ingredients_match.group(1).strip()
                    logger.info("Found ingredients using regex")
        except Exception as e:
            logger.error(f"Error extracting ingredients: {str(e)}")
        
        # Extract product details
        try:
            # Look for sections that might contain product details
            details_selectors = [
                '.product-details', 
                '#product-details',
                '[data-test="product-details"]',
                '.product-info__details',
                '.pdp-info-section:contains("Details")',
                '.pdp-info-section:contains("Description")',
                'div[id*="details"]',
                'section[id*="details"]',
                'div[class*="details"]',
                'section[class*="details"]',
                '.description',
                '#description'
            ]
            
            for selector in details_selectors:
                try:
                    details_element = soup.select_one(selector)
                    if details_element:
                        product_data['product_details'] = details_element.text.strip()
                        logger.info("Found product details")
                        break
                except Exception as e:
                    logger.warning(f"Error with details selector {selector}: {str(e)}")
            
            # If still not found, try looking for headings followed by content
            if not product_data['product_details']:
                headings = soup.find_all(['h2', 'h3', 'h4', 'strong', 'b'])
                for heading in headings:
                    if any(keyword in heading.text.lower() for keyword in ['detail', 'description', 'about']):
                        # Get the next sibling paragraph or div
                        next_elem = heading.find_next(['p', 'div', 'span'])
                        if next_elem:
                            product_data['product_details'] = next_elem.text.strip()
                            logger.info("Found product details after heading")
                            break
        except Exception as e:
            logger.error(f"Error extracting product details: {str(e)}")
        
        # Extract how to use
        try:
            # Look for sections that might contain how to use information
            how_to_use_selectors = [
                '.how-to-use', 
                '#how-to-use',
                '[data-test="how-to-use"]',
                '.product-info__how-to-use',
                '.pdp-info-section:contains("How to use")',
                '.pdp-info-section:contains("Directions")',
                'div[id*="how-to-use"]',
                'section[id*="how-to-use"]',
                'div[class*="how-to-use"]',
                'section[class*="how-to-use"]',
                '.directions',
                '#directions'
            ]
            
            for selector in how_to_use_selectors:
                try:
                    how_to_use_element = soup.select_one(selector)
                    if how_to_use_element:
                        product_data['how_to_use'] = how_to_use_element.text.strip()
                        logger.info("Found how to use")
                        break
                except Exception as e:
                    logger.warning(f"Error with how to use selector {selector}: {str(e)}")
            
            # If still not found, try looking for headings followed by content
            if not product_data['how_to_use']:
                headings = soup.find_all(['h2', 'h3', 'h4', 'strong', 'b'])
                for heading in headings:
                    if any(keyword in heading.text.lower() for keyword in ['how to use', 'directions', 'application']):
                        # Get the next sibling paragraph or div
                        next_elem = heading.find_next(['p', 'div', 'span'])
                        if next_elem:
                            product_data['how_to_use'] = next_elem.text.strip()
                            logger.info("Found how to use after heading")
                            break
            
            # If still not found, try looking in the entire page text
            if not product_data['how_to_use']:
                page_text = soup.get_text()
                how_to_use_pattern = r'(?:how to use|directions|application)[:\s]+(.*?)(?:\n\n|\.|$)'
                how_to_use_match = re.search(how_to_use_pattern, page_text, re.IGNORECASE | re.DOTALL)
                if how_to_use_match:
                    product_data['how_to_use'] = how_to_use_match.group(1).strip()
                    logger.info("Found how to use using regex")
        except Exception as e:
            logger.error(f"Error extracting how to use: {str(e)}")
        
        # Extract hazards and cautions
        try:
            # Look for sections that might contain hazards and cautions
            hazards_selectors = [
                '.hazards', 
                '#hazards',
                '.warnings',
                '#warnings',
                '[data-test="warnings"]',
                '.product-info__hazards',
                '.pdp-info-section:contains("Warnings")',
                '.pdp-info-section:contains("Cautions")',
                'div[id*="warnings"]',
                'section[id*="warnings"]',
                'div[class*="warnings"]',
                'section[class*="warnings"]',
                '.cautions',
                '#cautions'
            ]
            
            for selector in hazards_selectors:
                try:
                    hazards_element = soup.select_one(selector)
                    if hazards_element:
                        product_data['hazards_and_cautions'] = hazards_element.text.strip()
                        logger.info("Found hazards and cautions")
                        break
                except Exception as e:
                    logger.warning(f"Error with hazards selector {selector}: {str(e)}")
            
            # If still not found, try looking for headings followed by content
            if not product_data['hazards_and_cautions']:
                headings = soup.find_all(['h2', 'h3', 'h4', 'strong', 'b'])
                for heading in headings:
                    if any(keyword in heading.text.lower() for keyword in ['warning', 'caution', 'hazard', 'safety']):
                        # Get the next sibling paragraph or div
                        next_elem = heading.find_next(['p', 'div', 'span'])
                        if next_elem:
                            product_data['hazards_and_cautions'] = next_elem.text.strip()
                            logger.info("Found hazards and cautions after heading")
                            break
            
            # If still not found, try looking in the entire page text
            if not product_data['hazards_and_cautions']:
                page_text = soup.get_text()
                hazards_pattern = r'(?:warnings|cautions|hazards|safety precautions)[:\s]+(.*?)(?:\n\n|\.|$)'
                hazards_match = re.search(hazards_pattern, page_text, re.IGNORECASE | re.DOTALL)
                if hazards_match:
                    product_data['hazards_and_cautions'] = hazards_match.group(1).strip()
                    logger.info("Found hazards and cautions using regex")
        except Exception as e:
            logger.error(f"Error extracting hazards and cautions: {str(e)}")
        
        # Extract country of origin
        try:
            # Look for country of origin in the page text
            page_text = soup.get_text()
            country_patterns = [
                r'(?:country of origin|made in|origin)[:\s]+([A-Za-z\s]+)',
                r'(?:manufactured in|produced in)[:\s]+([A-Za-z\s]+)'
            ]
            
            for pattern in country_patterns:
                country_match = re.search(pattern, page_text, re.IGNORECASE)
                if country_match:
                    product_data['country_of_origin'] = country_match.group(1).strip()
                    logger.info("Found country of origin")
                    break
        except Exception as e:
            logger.error(f"Error extracting country of origin: {str(e)}")
        
        # Check if we successfully extracted the product name
        if product_data['product_name']:
            logger.info(f"Successfully scraped: {product_data['product_name']}")
        else:
            logger.warning(f"Failed to extract meaningful data from {url}")
        
        return product_data
    
    except Exception as e:
        logger.error(f"Error scraping product {url}: {str(e)}")
        return product_data

async def find_product_urls(page, category_url=None, max_products=10):
    """
    Find product URLs from the Boots website.
    
    Args:
        page (Page): Playwright page object.
        category_url (str): The URL of the category page to scrape.
        max_products (int): Maximum number of products to find.
        
    Returns:
        list: A list of product URLs.
    """
    product_urls = []
    
    if not category_url:
        # Default to skincare products
        category_url = "https://www.boots.com/beauty/skincare/skincare-all-skincare"
    
    try:
        logger.info(f"Navigating to category page: {category_url}")
        await page.goto(category_url, wait_until="domcontentloaded", timeout=60000)
        
        # Accept cookies if the banner appears
        try:
            cookie_button = await page.query_selector('button:has-text("Accept All Cookies"), .cookie-banner__button, #onetrust-accept-btn-handler')
            if cookie_button:
                await cookie_button.click()
                logger.info("Accepted cookies")
                await page.wait_for_timeout(1000)  # Wait for the banner to disappear
        except Exception as e:
            logger.warning(f"Error handling cookie banner: {str(e)}")
        
        # Take a screenshot of the category page
        os.makedirs("screenshots", exist_ok=True)
        await page.screenshot(path="screenshots/category_page.png")
        logger.info("Screenshot saved to screenshots/category_page.png")
        
        # Scroll down to load more products
        logger.info("Scrolling to load more products...")
        for _ in range(5):  # Scroll a few times to load more products
            await page.evaluate('window.scrollBy(0, 800)')
            await page.wait_for_timeout(1000)  # Wait for content to load
        
        # Get the page content
        content = await page.content()
        soup = BeautifulSoup(content, 'html.parser')
        
        # Find all product cards/tiles on the page
        product_cards = soup.select('.product-card, .product-tile, .product-item, [data-product-id], [data-productid], .product')
        logger.info(f"Found {len(product_cards)} potential product cards on the page")
        
        # Extract links from product cards
        for card in product_cards:
            # Find the link in the card
            link = card.find('a', href=True)
            if link:
                href = link.get('href')
                if href:
                    # Ensure it's an absolute URL
                    if href.startswith('/'):
                        href = f"https://www.boots.com{href}"
                    
                    # Check if it looks like a product URL (not a category)
                    if is_product_url(href):
                        if href not in product_urls:
                            product_urls.append(href)
                            logger.info(f"Found product URL from card: {href}")
                            
                            if len(product_urls) >= max_products:
                                break
        
        # If we didn't find enough products from cards, look for all links
        if len(product_urls) < max_products:
            logger.info("Looking for product links in all page links...")
            links = soup.find_all('a', href=True)
            logger.info(f"Found {len(links)} links on the page")
            
            for link in links:
                href = link.get('href')
                if href:
                    # Ensure it's an absolute URL
                    if href.startswith('/'):
                        href = f"https://www.boots.com{href}"
                    
                    # Check if it looks like a product URL
                    if is_product_url(href):
                        if href not in product_urls:
                            product_urls.append(href)
                            logger.info(f"Found product URL: {href}")
                            
                            if len(product_urls) >= max_products:
                                break
        
        # If we still didn't find enough products, try searching
        if len(product_urls) < max_products:
            logger.info("Not enough products found, trying search...")
            search_terms = ["skincare", "face cream", "moisturizer", "serum", "cleanser"]
            
            for term in search_terms[:2]:  # Limit to first 2 search terms
                if len(product_urls) >= max_products:
                    break
                
                try:
                    # Go to the main page
                    await page.goto("https://www.boots.com", wait_until="domcontentloaded", timeout=30000)
                    
                    # Try to find the search input
                    search_input = await page.query_selector('#search, input[type="search"], [placeholder*="Search"]')
                    if search_input:
                        # Enter search term
                        await search_input.fill(term)
                        await search_input.press("Enter")
                        logger.info(f"Searching for: {term}")
                        
                        # Wait for results to load
                        await page.wait_for_timeout(5000)
                        
                        # Take a screenshot of search results
                        await page.screenshot(path=f"screenshots/search_{term}.png")
                        logger.info(f"Screenshot saved to screenshots/search_{term}.png")
                        
                        # Scroll down to load more products
                        for _ in range(3):
                            await page.evaluate('window.scrollBy(0, 800)')
                            await page.wait_for_timeout(1000)
                        
                        # Get links from search results
                        content = await page.content()
                        soup = BeautifulSoup(content, 'html.parser')
                        
                        # Try to find product cards first
                        product_cards = soup.select('.product-card, .product-tile, .product-item, [data-product-id], [data-productid], .product')
                        for card in product_cards:
                            link = card.find('a', href=True)
                            if link:
                                href = link.get('href')
                                if href:
                                    # Ensure it's an absolute URL
                                    if href.startswith('/'):
                                        href = f"https://www.boots.com{href}"
                                    
                                    # Check if it looks like a product URL
                                    if is_product_url(href):
                                        if href not in product_urls:
                                            product_urls.append(href)
                                            logger.info(f"Found product URL from search card: {href}")
                                            
                                            if len(product_urls) >= max_products:
                                                break
                        
                        # If we still need more, look at all links
                        if len(product_urls) < max_products:
                            links = soup.find_all('a', href=True)
                            for link in links:
                                href = link.get('href')
                                if href:
                                    # Ensure it's an absolute URL
                                    if href.startswith('/'):
                                        href = f"https://www.boots.com{href}"
                                    
                                    # Check if it looks like a product URL
                                    if is_product_url(href):
                                        if href not in product_urls:
                                            product_urls.append(href)
                                            logger.info(f"Found product URL from search: {href}")
                                            
                                            if len(product_urls) >= max_products:
                                                break
                except Exception as e:
                    logger.error(f"Error searching for {term}: {str(e)}")
        
        # If we still don't have enough products, try browsing specific subcategories
        if len(product_urls) < max_products:
            subcategories = [
                "https://www.boots.com/beauty/skincare/face-skincare/face-moisturisers",
                "https://www.boots.com/beauty/skincare/face-skincare/face-serums",
                "https://www.boots.com/beauty/skincare/face-skincare/cleansers-toners"
            ]
            
            for subcategory in subcategories:
                if len(product_urls) >= max_products:
                    break
                
                try:
                    logger.info(f"Navigating to subcategory: {subcategory}")
                    await page.goto(subcategory, wait_until="domcontentloaded", timeout=30000)
                    
                    # Scroll down to load more products
                    for _ in range(3):
                        await page.evaluate('window.scrollBy(0, 800)')
                        await page.wait_for_timeout(1000)
                    
                    # Get links from subcategory
                    content = await page.content()
                    soup = BeautifulSoup(content, 'html.parser')
                    
                    # Try to find product cards first
                    product_cards = soup.select('.product-card, .product-tile, .product-item, [data-product-id], [data-productid], .product')
                    for card in product_cards:
                        link = card.find('a', href=True)
                        if link:
                            href = link.get('href')
                            if href:
                                # Ensure it's an absolute URL
                                if href.startswith('/'):
                                    href = f"https://www.boots.com{href}"
                                
                                # Check if it looks like a product URL
                                if is_product_url(href):
                                    if href not in product_urls:
                                        product_urls.append(href)
                                        logger.info(f"Found product URL from subcategory card: {href}")
                                        
                                        if len(product_urls) >= max_products:
                                            break
                    
                    # If we still need more, look at all links
                    if len(product_urls) < max_products:
                        links = soup.find_all('a', href=True)
                        for link in links:
                            href = link.get('href')
                            if href:
                                # Ensure it's an absolute URL
                                if href.startswith('/'):
                                    href = f"https://www.boots.com{href}"
                                
                                # Check if it looks like a product URL
                                if is_product_url(href):
                                    if href not in product_urls:
                                        product_urls.append(href)
                                        logger.info(f"Found product URL from subcategory: {href}")
                                        
                                        if len(product_urls) >= max_products:
                                            break
                except Exception as e:
                    logger.error(f"Error browsing subcategory {subcategory}: {str(e)}")
    
    except Exception as e:
        logger.error(f"Error finding product URLs: {str(e)}")
    
    logger.info(f"Found {len(product_urls)} product URLs")
    return product_urls

def is_product_url(url):
    """
    Check if a URL is likely to be a product page rather than a category page.
    
    Args:
        url (str): The URL to check.
        
    Returns:
        bool: True if the URL is likely a product page, False otherwise.
    """
    # Exclude obvious category pages
    if any(category in url for category in [
        '/skincare-all-skincare',
        '/new-in-skincare',
        '/korean-skincare',
        '/category/',
        '/brands/',
        '/offers/',
        '/advice/',
        '/inspiration/'
    ]):
        return False
    
    # Exclude URLs with query parameters (typically filters or sorting)
    if '?' in url:
        return False
    
    # Check for patterns that suggest it's a product page
    product_indicators = [
        # Product URLs often have numeric IDs
        re.search(r'/[a-z0-9-]+-\d+$', url),
        re.search(r'/p/\d+', url),
        re.search(r'/product/\d+', url),
        # Product URLs often have specific product names with hyphens
        re.search(r'/[a-z0-9-]+-[a-z0-9-]+-[a-z0-9-]+-\d+', url),
        # Some product URLs have specific formats
        '/beauty/skincare/' in url and len(url.split('/')) >= 6
    ]
    
    return any(product_indicators)

async def scrape_products(product_urls, max_products=None, output_file="boots_products.csv"):
    """
    Scrape product information from a list of product URLs.
    
    Args:
        product_urls (list): List of product URLs to scrape.
        max_products (int): Maximum number of products to scrape.
        output_file (str): Output CSV file name.
        
    Returns:
        list: A list of dictionaries containing product data.
    """
    if max_products and len(product_urls) > max_products:
        product_urls = product_urls[:max_products]
    
    logger.info(f"Scraping {len(product_urls)} product URLs")
    
    product_data_list = []
    
    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(headless=False)
        context = await browser.new_context(
            viewport={"width": 1280, "height": 800},
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        )
        page = await context.new_page()
        
        for i, url in enumerate(product_urls):
            logger.info(f"\n{'='*50}\nScraping product {i+1}/{len(product_urls)}: {url}\n{'='*50}")
            
            # Add a random delay between requests
            delay = random.uniform(1.5, 3.0)
            logger.info(f"Waiting {delay:.2f} seconds...")
            await asyncio.sleep(delay)
            
            product_data = await scrape_boots_product(page, url)
            product_data_list.append(product_data)
        
        await browser.close()
    
    # Save the data to CSV
    save_to_csv(product_data_list, output_file)
    
    return product_data_list

async def main_async():
    """
    Main async function to run the scraper.
    """
    parser = argparse.ArgumentParser(description='Scrape products from Boots.com')
    parser.add_argument('--category', type=str, help='Category URL to scrape')
    parser.add_argument('--file', type=str, help='File containing product URLs to scrape')
    parser.add_argument('--urls', nargs='+', help='Product URLs to scrape')
    parser.add_argument('--max-products', type=int, default=10, help='Maximum number of products to scrape')
    parser.add_argument('--output', type=str, default='boots_products.csv', help='Output CSV file')
    parser.add_argument('--headless', action='store_true', help='Run browser in headless mode')
    
    args = parser.parse_args()
    
    # Set up Playwright
    async with async_playwright() as playwright:
        # Launch the browser
        browser = await playwright.chromium.launch(headless=args.headless)
        context = await browser.new_context(
            viewport={"width": 1280, "height": 800},
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        )
        page = await context.new_page()
        
        product_urls = []
        
        # Determine the source of product URLs
        if args.urls:
            # Use directly provided URLs
            product_urls = args.urls
            logger.info(f"Using {len(product_urls)} product URLs provided as command-line arguments")
        
        elif args.file:
            # Read URLs from file
            with open(args.file, 'r') as f:
                product_urls = [line.strip() for line in f if line.strip()]
            logger.info(f"Read {len(product_urls)} product URLs from file: {args.file}")
        
        else:
            # Find product URLs from the website
            category_url = args.category if args.category else "https://www.boots.com/beauty/skincare/skincare-all-skincare"
            product_urls = await find_product_urls(page, category_url, args.max_products)
        
        await browser.close()
        
        if not product_urls:
            logger.error("No product URLs found. Exiting.")
            return
        
        # Scrape the products
        product_data_list = await scrape_products(product_urls, args.max_products, args.output)
        
        # Print summary
        logger.info(f"\nScraping completed. Scraped {len(product_data_list)} products.")
        logger.info(f"Data saved to {args.output}")
        
        # Print success rate
        success_count = sum(1 for product in product_data_list if product['product_name'] is not None)
        if product_urls:
            success_rate = (success_count / len(product_urls)) * 100
            logger.info(f"Success rate: {success_rate:.2f}% ({success_count}/{len(product_urls)})")

def main():
    """
    Main function to run the scraper.
    """
    asyncio.run(main_async())

if __name__ == "__main__":
    main()
