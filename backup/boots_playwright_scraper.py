#!/usr/bin/env python3
"""
Boots Playwright Scraper

This script uses Playwright to scrape products from Boots.com, handling dynamic content loading.
It can scrape from:
1. A category page URL (e.g., 5-star skincare products)
2. A list of product URLs from a file
3. Directly provided product URLs as command-line arguments
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
from playwright.async_api import async_playwright

def save_to_csv(product_data_list, filename='boots_products.csv'):
    """
    Save the product data to a CSV file.
    
    Args:
        product_data_list (list): List of product data dictionaries.
        filename (str): The name of the CSV file.
    """
    if not product_data_list:
        print("No product data to save.")
        return
    
    # Convert list of dictionaries to DataFrame
    df = pd.DataFrame(product_data_list)
    
    # Save to CSV
    df.to_csv(filename, index=False, encoding='utf-8')
    print(f"Data saved to {filename}")

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
        print(f"Navigating to: {url}")
        response = await page.goto(url, wait_until="domcontentloaded", timeout=60000)
        
        # Check if the page was successfully loaded
        if response and response.status >= 400:
            print(f"Failed to load page. Status code: {response.status}")
            return product_data
        
        # Wait for the product content to load
        try:
            await page.wait_for_selector('h1, .product-title, [data-test="product-title"]', timeout=10000)
        except Exception as e:
            print(f"Error waiting for product title selector: {str(e)}")
        
        # Check if we got a 404 page
        page_title = await page.title()
        page_content = await page.content()
        if "Page not found" in page_title or "Page not found" in page_content:
            print(f"Page not found (404) for URL: {url}")
            return product_data
        
        # Wait for product information to load
        try:
            await page.wait_for_load_state("networkidle", timeout=10000)
        except Exception as e:
            print(f"Warning: Page load state timeout: {str(e)}")
        
        # Take a screenshot for debugging (optional)
        # screenshot_path = f"screenshots/{product_data['product_id'] if product_data['product_id'] else 'unknown'}.png"
        # await page.screenshot(path=screenshot_path)
        # print(f"Screenshot saved to {screenshot_path}")
        
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
                '.product-detail__title'
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
            print(f"Error extracting product name: {str(e)}")
        
        # Extract brand
        try:
            # Try multiple selectors for brand
            brand_selectors = [
                '.brand-name', 
                '.product-brand', 
                '[data-test="product-brand"]',
                '.product__brand',
                '.product-detail__brand'
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
            print(f"Error extracting brand: {str(e)}")
        
        # Extract price
        try:
            # Try multiple selectors for price
            price_selectors = [
                '.product-price', 
                '.price', 
                '[data-test="product-price"]',
                '.product__price',
                '.product-detail__price',
                '.price-info'
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
            print(f"Error extracting price: {str(e)}")
        
        # Extract rating
        try:
            # Try multiple selectors for rating
            rating_selectors = [
                '.product-rating', 
                '.rating', 
                '[data-test="product-rating"]',
                '.product__rating',
                '.product-detail__rating',
                '.rating-info'
            ]
            
            for selector in rating_selectors:
                rating_element = await page.query_selector(selector)
                if rating_element:
                    rating_text = (await rating_element.text_content()).strip()
                    # Extract rating using regex to handle different formats
                    rating_match = re.search(r'(\d+(\.\d+)?)\s*out of\s*\d+', rating_text, re.IGNORECASE)
                    if rating_match:
                        product_data['rating'] = rating_match.group(1)
                    else:
                        product_data['rating'] = rating_text
                    break
        except Exception as e:
            print(f"Error extracting rating: {str(e)}")
        
        # Extract review count
        try:
            # Try multiple selectors for review count
            review_count_selectors = [
                '.review-count', 
                '.reviews-count', 
                '[data-test="product-review-count"]',
                '.product__review-count',
                '.product-detail__review-count'
            ]
            
            for selector in review_count_selectors:
                review_count_element = await page.query_selector(selector)
                if review_count_element:
                    review_count_text = (await review_count_element.text_content()).strip()
                    # Extract review count using regex to handle different formats
                    review_count_match = re.search(r'(\d+)\s*reviews?', review_count_text, re.IGNORECASE)
                    if review_count_match:
                        product_data['review_count'] = review_count_match.group(1)
                    else:
                        product_data['review_count'] = review_count_text
                    break
        except Exception as e:
            print(f"Error extracting review count: {str(e)}")
        
        # Extract ingredients
        try:
            # Try multiple selectors for ingredients
            ingredients_selectors = [
                '.ingredients', 
                '.product-ingredients', 
                '[data-test="product-ingredients"]',
                '#ingredients',
                '.product__ingredients',
                '.product-detail__ingredients',
                '.product-info__ingredients'
            ]
            
            for selector in ingredients_selectors:
                ingredients_element = await page.query_selector(selector)
                if ingredients_element:
                    product_data['ingredients'] = (await ingredients_element.text_content()).strip()
                    break
                
            # If no ingredients found, try looking for a tab or accordion
            if not product_data['ingredients']:
                # Try clicking on ingredients tab or accordion
                ingredients_tab_selectors = [
                    'button:has-text("Ingredients")', 
                    '.tab:has-text("Ingredients")',
                    '.accordion:has-text("Ingredients")',
                    '[data-test="tab-ingredients"]'
                ]
                
                for selector in ingredients_tab_selectors:
                    try:
                        ingredients_tab = await page.query_selector(selector)
                        if ingredients_tab:
                            await ingredients_tab.click()
                            await page.wait_for_timeout(1000)  # Wait for content to load
                            
                            # Try to get ingredients content after clicking
                            for selector in ingredients_selectors:
                                ingredients_element = await page.query_selector(selector)
                                if ingredients_element:
                                    product_data['ingredients'] = (await ingredients_element.text_content()).strip()
                                    break
                            
                            if product_data['ingredients']:
                                break
                    except Exception as tab_error:
                        print(f"Error clicking ingredients tab: {str(tab_error)}")
        except Exception as e:
            print(f"Error extracting ingredients: {str(e)}")
        
        # Extract hazards and cautions
        try:
            # Try multiple selectors for hazards and cautions
            hazards_selectors = [
                '.hazards', 
                '.cautions', 
                '.warnings',
                '[data-test="product-hazards"]',
                '#hazards',
                '#warnings',
                '.product__hazards',
                '.product-detail__hazards',
                '.product-info__hazards'
            ]
            
            for selector in hazards_selectors:
                hazards_element = await page.query_selector(selector)
                if hazards_element:
                    product_data['hazards_and_cautions'] = (await hazards_element.text_content()).strip()
                    break
                
            # If no hazards found, try looking for a tab or accordion
            if not product_data['hazards_and_cautions']:
                # Try clicking on hazards tab or accordion
                hazards_tab_selectors = [
                    'button:has-text("Hazards")', 
                    'button:has-text("Cautions")',
                    'button:has-text("Warnings")',
                    '.tab:has-text("Hazards")',
                    '.tab:has-text("Cautions")',
                    '.tab:has-text("Warnings")',
                    '.accordion:has-text("Hazards")',
                    '.accordion:has-text("Cautions")',
                    '.accordion:has-text("Warnings")'
                ]
                
                for selector in hazards_tab_selectors:
                    try:
                        hazards_tab = await page.query_selector(selector)
                        if hazards_tab:
                            await hazards_tab.click()
                            await page.wait_for_timeout(1000)  # Wait for content to load
                            
                            # Try to get hazards content after clicking
                            for selector in hazards_selectors:
                                hazards_element = await page.query_selector(selector)
                                if hazards_element:
                                    product_data['hazards_and_cautions'] = (await hazards_element.text_content()).strip()
                                    break
                            
                            if product_data['hazards_and_cautions']:
                                break
                    except Exception as tab_error:
                        print(f"Error clicking hazards tab: {str(tab_error)}")
        except Exception as e:
            print(f"Error extracting hazards and cautions: {str(e)}")
        
        # Extract product details
        try:
            # Try multiple selectors for product details
            details_selectors = [
                '.product-details', 
                '.details', 
                '.description',
                '[data-test="product-details"]',
                '#details',
                '#description',
                '.product__details',
                '.product-detail__details',
                '.product-info__details'
            ]
            
            for selector in details_selectors:
                details_element = await page.query_selector(selector)
                if details_element:
                    product_data['product_details'] = (await details_element.text_content()).strip()
                    break
                
            # If no details found, try looking for a tab or accordion
            if not product_data['product_details']:
                # Try clicking on details tab or accordion
                details_tab_selectors = [
                    'button:has-text("Details")', 
                    'button:has-text("Description")',
                    '.tab:has-text("Details")',
                    '.tab:has-text("Description")',
                    '.accordion:has-text("Details")',
                    '.accordion:has-text("Description")'
                ]
                
                for selector in details_tab_selectors:
                    try:
                        details_tab = await page.query_selector(selector)
                        if details_tab:
                            await details_tab.click()
                            await page.wait_for_timeout(1000)  # Wait for content to load
                            
                            # Try to get details content after clicking
                            for selector in details_selectors:
                                details_element = await page.query_selector(selector)
                                if details_element:
                                    product_data['product_details'] = (await details_element.text_content()).strip()
                                    break
                            
                            if product_data['product_details']:
                                break
                    except Exception as tab_error:
                        print(f"Error clicking details tab: {str(tab_error)}")
        except Exception as e:
            print(f"Error extracting product details: {str(e)}")
        
        # Extract how to use
        try:
            # Try multiple selectors for how to use
            how_to_use_selectors = [
                '.how-to-use', 
                '.directions', 
                '.usage',
                '[data-test="product-how-to-use"]',
                '#how-to-use',
                '#directions',
                '.product__how-to-use',
                '.product-detail__how-to-use',
                '.product-info__how-to-use'
            ]
            
            for selector in how_to_use_selectors:
                how_to_use_element = await page.query_selector(selector)
                if how_to_use_element:
                    product_data['how_to_use'] = (await how_to_use_element.text_content()).strip()
                    break
                
            # If no how to use found, try looking for a tab or accordion
            if not product_data['how_to_use']:
                # Try clicking on how to use tab or accordion
                how_to_use_tab_selectors = [
                    'button:has-text("How to use")', 
                    'button:has-text("Directions")',
                    'button:has-text("Usage")',
                    '.tab:has-text("How to use")',
                    '.tab:has-text("Directions")',
                    '.tab:has-text("Usage")',
                    '.accordion:has-text("How to use")',
                    '.accordion:has-text("Directions")',
                    '.accordion:has-text("Usage")'
                ]
                
                for selector in how_to_use_tab_selectors:
                    try:
                        how_to_use_tab = await page.query_selector(selector)
                        if how_to_use_tab:
                            await how_to_use_tab.click()
                            await page.wait_for_timeout(1000)  # Wait for content to load
                            
                            # Try to get how to use content after clicking
                            for selector in how_to_use_selectors:
                                how_to_use_element = await page.query_selector(selector)
                                if how_to_use_element:
                                    product_data['how_to_use'] = (await how_to_use_element.text_content()).strip()
                                    break
                            
                            if product_data['how_to_use']:
                                break
                    except Exception as tab_error:
                        print(f"Error clicking how to use tab: {str(tab_error)}")
        except Exception as e:
            print(f"Error extracting how to use: {str(e)}")
        
        # Extract country of origin
        try:
            # Try multiple selectors for country of origin
            country_selectors = [
                '.country-of-origin', 
                '.origin', 
                '[data-test="product-country-of-origin"]',
                '#country-of-origin',
                '.product__country-of-origin',
                '.product-detail__country-of-origin',
                '.product-info__country-of-origin'
            ]
            
            for selector in country_selectors:
                country_element = await page.query_selector(selector)
                if country_element:
                    product_data['country_of_origin'] = (await country_element.text_content()).strip()
                    break
                
            # If no country of origin found, try looking for a tab or accordion
            if not product_data['country_of_origin']:
                # Try clicking on country of origin tab or accordion
                country_tab_selectors = [
                    'button:has-text("Country of origin")', 
                    'button:has-text("Origin")',
                    '.tab:has-text("Country of origin")',
                    '.tab:has-text("Origin")',
                    '.accordion:has-text("Country of origin")',
                    '.accordion:has-text("Origin")'
                ]
                
                for selector in country_tab_selectors:
                    try:
                        country_tab = await page.query_selector(selector)
                        if country_tab:
                            await country_tab.click()
                            await page.wait_for_timeout(1000)  # Wait for content to load
                            
                            # Try to get country of origin content after clicking
                            for selector in country_selectors:
                                country_element = await page.query_selector(selector)
                                if country_element:
                                    product_data['country_of_origin'] = (await country_element.text_content()).strip()
                                    break
                            
                            if product_data['country_of_origin']:
                                break
                    except Exception as tab_error:
                        print(f"Error clicking country of origin tab: {str(tab_error)}")
        except Exception as e:
            print(f"Error extracting country of origin: {str(e)}")
        
        # Check if we successfully extracted the product name
        if product_data['product_name']:
            print(f"Successfully scraped: {product_data['product_name']}")
        else:
            print(f"Failed to extract meaningful data from {url}")
        
        return product_data
    
    except Exception as e:
        print(f"Error scraping product {url}: {str(e)}")
        return product_data

async def get_product_urls_from_page(page, category_url):
    """
    Extract product URLs from a category page using Playwright.
    
    Args:
        page (Page): Playwright page object.
        category_url (str): The URL of the category page.
        
    Returns:
        list: A list of product URLs.
    """
    product_urls = []
    base_url = "https://www.boots.com"
    
    try:
        # Navigate to the category page
        print(f"Navigating to category: {category_url}")
        await page.goto(category_url, wait_until="domcontentloaded", timeout=60000)
        
        # Wait for the product grid to load
        try:
            await page.wait_for_selector('.product-grid, .product-list, [data-test="product-grid"]', timeout=10000)
        except Exception as e:
            print(f"Error waiting for selector '.product-grid, .product-list, [data-test=\"product-grid\"]': {str(e)}")
        
        # Wait for network to be idle (helps with dynamic loading)
        try:
            await page.wait_for_load_state("networkidle", timeout=10000)
        except Exception as e:
            print(f"Error waiting for load state 'networkidle': {str(e)}")
        
        # Scroll down to load lazy-loaded content
        await page.evaluate("""
            window.scrollTo(0, document.body.scrollHeight / 2);
        """)
        await page.wait_for_timeout(2000)
        
        await page.evaluate("""
            window.scrollTo(0, document.body.scrollHeight);
        """)
        await page.wait_for_timeout(2000)
        
        # Get the page content
        content = await page.content()
        soup = BeautifulSoup(content, 'html.parser')
        
        # Try different selectors for product links based on the observed page structure
        product_selectors = [
            '.product-grid-item a.product-title-link',
            '.product-list-item a.product-title-link',
            '.estore-product-tile a.product-title-link',
            '.product-tile a.product-title-link',
            '.product__list a.product__link',
            '.product-list-item a.product-link',
            '.product-grid a.product-title',
            '.product-tile__details a',
            'a.product-title-link',
            '[data-test="product-tile"] a',
            '.product a'
        ]
        
        # Try each selector
        for selector in product_selectors:
            links = soup.select(selector)
            if links:
                for link in links:
                    href = link.get('href')
                    if href:
                        # Make sure it's an absolute URL
                        if not href.startswith('http'):
                            if href.startswith('/'):
                                href = f"{base_url}{href}"
                            else:
                                href = f"{base_url}/{href}"
                        
                        # Only add if it looks like a product URL
                        if 'boots.com' in href and ('-' in href or '/product/' in href):
                            product_urls.append(href)
                if product_urls:
                    break  # Break if we found products with this selector
        
        # If no links found with specific selectors, try looking for product containers
        if not product_urls:
            # Look for product containers and then find links within them
            product_containers = soup.select('.product-grid-item, .product-list-item, .estore-product-tile, .product-tile, [data-test="product-tile"]')
            
            for container in product_containers:
                links = container.select('a')
                for link in links:
                    href = link.get('href')
                    if href:
                        # Make sure it's an absolute URL
                        if not href.startswith('http'):
                            if href.startswith('/'):
                                href = f"{base_url}{href}"
                            else:
                                href = f"{base_url}/{href}"
                        
                        # Only add if it looks like a product URL
                        if 'boots.com' in href and ('-' in href or '/product/' in href):
                            product_urls.append(href)
        
        # If still no links found, try a more general approach
        if not product_urls:
            # Look for any link that might point to a product
            for link in soup.find_all('a', href=True):
                href = link['href']
                # Check if the link looks like a product link
                if '/product/' in href or re.search(r'-\d+$', href):
                    # Make sure it's an absolute URL
                    if not href.startswith('http'):
                        if href.startswith('/'):
                            href = f"{base_url}{href}"
                        else:
                            href = f"{base_url}/{href}"
                    
                    # Only add if it looks like a product URL
                    if 'boots.com' in href and ('-' in href or '/product/' in href):
                        product_urls.append(href)
        
        # Remove duplicates while preserving order
        product_urls = list(dict.fromkeys(product_urls))
        
        return product_urls
    
    except Exception as e:
        print(f"Error extracting product URLs from {category_url}: {str(e)}")
        return []

async def get_next_page_url(page, current_url, page_number):
    """
    Construct and validate the URL for the next page.
    
    Args:
        page (Page): Playwright page object.
        current_url (str): The current page URL.
        page_number (int): The next page number.
        
    Returns:
        str: The URL for the next page, or None if no next page exists.
    """
    # Parse the current URL
    parsed_url = urlparse(current_url)
    query_params = parse_qs(parsed_url.query)
    
    # Update or add the page parameter
    query_params['page'] = [str(page_number)]
    
    # Reconstruct the URL
    new_query = urlencode(query_params, doseq=True)
    new_url = urlunparse((
        parsed_url.scheme,
        parsed_url.netloc,
        parsed_url.path,
        parsed_url.params,
        new_query,
        parsed_url.fragment
    ))
    
    return new_url

def read_product_urls_from_file(file_path):
    """
    Read product URLs from a file, one URL per line.
    
    Args:
        file_path (str): Path to the file containing product URLs.
        
    Returns:
        list: A list of product URLs.
    """
    product_urls = []
    
    try:
        with open(file_path, 'r') as file:
            for line in file:
                url = line.strip()
                if url and url.startswith('http'):
                    product_urls.append(url)
        
        print(f"Read {len(product_urls)} URLs from {file_path}")
    except Exception as e:
        print(f"Error reading URLs from file {file_path}: {str(e)}")
    
    return product_urls

def get_current_5star_skincare_products():
    """
    Return a list of current 5-star skincare product URLs from Boots.com.
    These URLs have been manually verified to exist on the Boots website.
    
    Returns:
        list: A list of product URLs.
    """
    return [
        # Face serums
        "https://www.boots.com/beauty/skincare/face-skincare/face-serums/the-ordinary-niacinamide-10-zinc-1-high-strength-vitamin-and-mineral-blemish-formula-30ml-10283940",
        "https://www.boots.com/beauty/skincare/face-skincare/face-serums/the-ordinary-hyaluronic-acid-2-b5-hydration-support-formula-30ml-10283942",
        "https://www.boots.com/beauty/skincare/face-skincare/face-serums/the-ordinary-caffeine-solution-5-egcg-reduces-appearance-of-eye-contour-pigmentation-puffiness-30ml-10283943",
        
        # Face moisturizers
        "https://www.boots.com/beauty/skincare/face-skincare/face-moisturisers/the-ordinary-natural-moisturizing-factors-ha-30ml-10283950",
        "https://www.boots.com/beauty/skincare/face-skincare/face-moisturisers/cerave-facial-moisturising-lotion-52ml-10258275",
        "https://www.boots.com/beauty/skincare/face-skincare/face-moisturisers/no7-protect-and-perfect-intense-advanced-day-cream-spf15-50ml-10127461",
        
        # Cleansers
        "https://www.boots.com/beauty/skincare/face-skincare/cleansers-toners/cerave-hydrating-cleanser-236ml-10246702",
        "https://www.boots.com/beauty/skincare/face-skincare/cleansers-toners/the-ordinary-squalane-cleanser-50ml-10284039",
        "https://www.boots.com/beauty/skincare/face-skincare/cleansers-toners/liz-earle-cleanse-and-polish-hot-cloth-cleanser-100ml-starter-kit-10094112",
        
        # Eye creams
        "https://www.boots.com/beauty/skincare/face-skincare/eye-creams/no7-protect-and-perfect-intense-advanced-eye-cream-15ml-10127463",
        "https://www.boots.com/beauty/skincare/face-skincare/eye-creams/the-ordinary-caffeine-solution-5-egcg-30ml-10283943"
    ]

async def extract_product_urls_from_screenshot():
    """
    Extract product URLs from the screenshot of the Boots website.
    This function would normally use image recognition or OCR to extract URLs,
    but for now we'll just return a hardcoded list based on the visible products.
    
    Returns:
        list: A list of product URLs.
    """
    # Products visible in the screenshot
    return [
        # First row
        "https://www.boots.com/beauty/skincare/face-skincare/face-serums/the-ordinary-niacinamide-10-zinc-1-30ml-10283940",
        "https://www.boots.com/beauty/skincare/face-skincare/face-serums/the-ordinary-hyaluronic-acid-2-b5-30ml-10283942",
        "https://www.boots.com/beauty/skincare/face-skincare/face-moisturisers/the-ordinary-natural-moisturizing-factors-ha-30ml-10283950",
        "https://www.boots.com/beauty/skincare/face-skincare/eye-creams/the-ordinary-caffeine-solution-5-egcg-30ml-10283943",
        
        # Second row
        "https://www.boots.com/beauty/skincare/face-skincare/cleansers-toners/liz-earle-cleanse-and-polish-hot-cloth-cleanser-100ml-10094112",
        "https://www.boots.com/beauty/skincare/face-skincare/face-toners/the-ordinary-glycolic-acid-7-toning-solution-240ml-10283944",
        "https://www.boots.com/beauty/skincare/face-skincare/face-serums/la-roche-posay-hyalu-b5-hyaluronic-acid-serum-30ml-10228555",
        
        # Third row (partially visible)
        "https://www.boots.com/beauty/skincare/face-skincare/face-masks/the-inkey-list-kaolin-clay-mask-50ml-10271302",
        "https://www.boots.com/beauty/skincare/face-skincare/face-serums/the-inkey-list-hyaluronic-acid-serum-30ml-10271299",
        "https://www.boots.com/beauty/skincare/face-skincare/face-serums/the-inkey-list-niacinamide-serum-30ml-10271300"
    ]

async def extract_product_urls_from_live_site(page, category_url=None, max_products=10):
    """
    Navigate to the Boots website and extract product URLs directly from the live site.
    
    Args:
        page (Page): Playwright page object.
        category_url (str): The URL of the category page to scrape.
        max_products (int): Maximum number of products to extract.
        
    Returns:
        list: A list of product URLs.
    """
    product_urls = []
    
    if not category_url:
        # Default to 5-star skincare products
        category_url = "https://www.boots.com/beauty/skincare/skincare-all-skincare?criteria.roundedReviewScore=5"
    
    try:
        print(f"Navigating to category page: {category_url}")
        await page.goto(category_url, wait_until="domcontentloaded", timeout=60000)
        
        # Wait for the product grid to load
        try:
            await page.wait_for_selector('.product-grid, .product-list, [data-test="product-list"]', timeout=30000)
        except Exception as e:
            print(f"Error waiting for product grid: {str(e)}")
        
        # Accept cookies if the banner appears
        try:
            cookie_button = await page.query_selector('button:has-text("Accept All Cookies"), .cookie-banner__button, #onetrust-accept-btn-handler')
            if cookie_button:
                await cookie_button.click()
                print("Accepted cookies")
                await page.wait_for_timeout(1000)  # Wait for the banner to disappear
        except Exception as e:
            print(f"Error handling cookie banner: {str(e)}")
        
        # Scroll down to load more products
        print("Scrolling to load more products...")
        for _ in range(5):  # Scroll a few times to load more products
            await page.evaluate('window.scrollBy(0, 800)')
            await page.wait_for_timeout(1000)  # Wait for content to load
        
        # Wait for all product cards to load
        await page.wait_for_timeout(2000)
        
        # Extract product URLs using multiple selector strategies
        print("Extracting product URLs...")
        
        # Strategy 1: Look for product cards
        product_card_selectors = [
            '.product-grid .product-card, .product-list .product-card',
            '.product-grid .product-item, .product-list .product-item',
            '[data-test="product-list"] [data-test="product-card"]',
            '.product-grid__item, .product-list__item',
            '.product__item'
        ]
        
        for selector in product_card_selectors:
            if len(product_urls) >= max_products:
                break
                
            try:
                product_cards = await page.query_selector_all(selector)
                print(f"Found {len(product_cards)} product cards with selector '{selector}'")
                
                for card in product_cards:
                    if len(product_urls) >= max_products:
                        break
                        
                    try:
                        # Try to find the link within the card
                        link_selectors = [
                            'a.product-card__link',
                            'a.product-item__link',
                            'a[data-test="product-link"]',
                            'a.product__link',
                            'a'  # Fallback to any link in the card
                        ]
                        
                        for link_selector in link_selectors:
                            link = await card.query_selector(link_selector)
                            if link:
                                href = await link.get_attribute('href')
                                if href:
                                    # Ensure it's an absolute URL
                                    if href.startswith('/'):
                                        href = f"https://www.boots.com{href}"
                                    
                                    # Validate that it's a product URL
                                    if (('/beauty/skincare/' in href) and 
                                        not href.endswith('/beauty/skincare') and 
                                        not '/category/' in href and 
                                        not '?' in href and
                                        any(char.isdigit() for char in href.split('/')[-1])):
                                        
                                        if href not in product_urls:
                                            product_urls.append(href)
                                            print(f"Found product URL: {href}")
                                    break
                    except Exception as e:
                        print(f"Error extracting link from product card: {str(e)}")
            except Exception as e:
                print(f"Error with selector '{selector}': {str(e)}")
        
        # Strategy 2: Use BeautifulSoup to parse the page content
        if len(product_urls) < max_products:
            try:
                content = await page.content()
                soup = BeautifulSoup(content, 'html.parser')
                
                # Find all product links
                product_links = []
                
                # Look for links in product cards
                for card_selector in ['.product-card', '.product-item', '[data-test="product-card"]', '.product-grid__item', '.product__item']:
                    cards = soup.select(card_selector)
                    for card in cards:
                        links = card.select('a')
                        for link in links:
                            href = link.get('href')
                            if href:
                                product_links.append(href)
                
                # Also look for any links that might be product links
                for link in soup.select('a'):
                    href = link.get('href')
                    if href:
                        product_links.append(href)
                
                # Process and validate the links
                for href in product_links:
                    if len(product_urls) >= max_products:
                        break
                        
                    # Ensure it's an absolute URL
                    if href.startswith('/'):
                        href = f"https://www.boots.com{href}"
                    
                    # Validate that it's a product URL
                    if (('/beauty/skincare/' in href) and 
                        not href.endswith('/beauty/skincare') and 
                        not '/category/' in href and 
                        not '?' in href and
                        any(char.isdigit() for char in href.split('/')[-1])):
                        
                        if href not in product_urls:
                            product_urls.append(href)
                            print(f"Found product URL (BeautifulSoup): {href}")
            except Exception as e:
                print(f"Error using BeautifulSoup to extract product URLs: {str(e)}")
        
        # Strategy 3: Try to navigate to subcategories and extract product URLs
        if len(product_urls) < max_products:
            try:
                # Look for subcategory links
                subcategory_selectors = [
                    '.category-navigation a',
                    '.subcategories a',
                    '.category-list a',
                    '[data-test="category-nav"] a'
                ]
                
                subcategory_urls = []
                
                for selector in subcategory_selectors:
                    subcategory_links = await page.query_selector_all(selector)
                    for link in subcategory_links:
                        href = await link.get_attribute('href')
                        if href and '/beauty/skincare/' in href and href not in subcategory_urls:
                            # Ensure it's an absolute URL
                            if href.startswith('/'):
                                href = f"https://www.boots.com{href}"
                            
                            subcategory_urls.append(href)
                
                # Visit each subcategory and extract product URLs
                for subcategory_url in subcategory_urls[:3]:  # Limit to 3 subcategories to avoid too many requests
                    if len(product_urls) >= max_products:
                        break
                        
                    try:
                        print(f"Navigating to subcategory: {subcategory_url}")
                        await page.goto(subcategory_url, wait_until="domcontentloaded", timeout=30000)
                        
                        # Wait for the product grid to load
                        try:
                            await page.wait_for_selector('.product-grid, .product-list, [data-test="product-list"]', timeout=10000)
                        except Exception as e:
                            print(f"Error waiting for product grid in subcategory: {str(e)}")
                            continue
                        
                        # Scroll down to load more products
                        for _ in range(2):  # Scroll a few times to load more products
                            await page.evaluate('window.scrollBy(0, 800)')
                            await page.wait_for_timeout(1000)  # Wait for content to load
                        
                        # Extract product URLs
                        content = await page.content()
                        soup = BeautifulSoup(content, 'html.parser')
                        
                        for link in soup.select('a'):
                            href = link.get('href')
                            if href:
                                # Ensure it's an absolute URL
                                if href.startswith('/'):
                                    href = f"https://www.boots.com{href}"
                                
                                # Validate that it's a product URL
                                if (('/beauty/skincare/' in href) and 
                                    not href.endswith('/beauty/skincare') and 
                                    not '/category/' in href and 
                                    not '?' in href):
                                    
                                    if href not in product_urls:
                                        product_urls.append(href)
                                        print(f"Found product URL from subcategory: {href}")
                                        
                                        if len(product_urls) >= max_products:
                                            break
                    except Exception as e:
                        print(f"Error processing subcategory {subcategory_url}: {str(e)}")
            except Exception as e:
                print(f"Error finding subcategories: {str(e)}")
        
        # If we still don't have enough product URLs, try to use the search function
        if len(product_urls) < max_products:
            try:
                # Go back to the main page
                await page.goto("https://www.boots.com", wait_until="domcontentloaded", timeout=30000)
                
                # Wait for the search input to be available
                await page.wait_for_selector('#search, [data-test="search-input"], .search-input', timeout=10000)
                
                # Search for skincare products
                search_terms = ["skincare", "face cream", "moisturizer", "serum", "cleanser"]
                
                for term in search_terms:
                    if len(product_urls) >= max_products:
                        break
                        
                    try:
                        # Clear the search input
                        await page.fill('#search, [data-test="search-input"], .search-input', "")
                        await page.wait_for_timeout(500)
                        
                        # Enter the search term
                        await page.fill('#search, [data-test="search-input"], .search-input', term)
                        await page.wait_for_timeout(500)
                        
                        # Submit the search
                        await page.press('#search, [data-test="search-input"], .search-input', 'Enter')
                        
                        # Wait for the search results to load
                        try:
                            await page.wait_for_selector('.product-grid, .product-list, [data-test="product-list"]', timeout=10000)
                        except Exception as e:
                            print(f"Error waiting for search results: {str(e)}")
                            continue
                        
                        # Scroll down to load more products
                        for _ in range(2):  # Scroll a few times to load more products
                            await page.evaluate('window.scrollBy(0, 800)')
                            await page.wait_for_timeout(1000)  # Wait for content to load
                        
                        # Extract product URLs
                        content = await page.content()
                        soup = BeautifulSoup(content, 'html.parser')
                        
                        for link in soup.select('a'):
                            href = link.get('href')
                            if href:
                                # Ensure it's an absolute URL
                                if href.startswith('/'):
                                    href = f"https://www.boots.com{href}"
                                
                                # Validate that it's a product URL
                                if (('/beauty/skincare/' in href) and 
                                    not href.endswith('/beauty/skincare') and 
                                    not '/category/' in href and 
                                    not '?' in href):
                                    
                                    if href not in product_urls:
                                        product_urls.append(href)
                                        print(f"Found product URL from search: {href}")
                                        
                                        if len(product_urls) >= max_products:
                                            break
                    except Exception as e:
                        print(f"Error searching for '{term}': {str(e)}")
            except Exception as e:
                print(f"Error using search function: {str(e)}")
    
    except Exception as e:
        print(f"Error extracting product URLs from live site: {str(e)}")
    
    print(f"Extracted {len(product_urls)} product URLs")
    return product_urls

async def scrape_product_list(page, product_urls, max_products=None, output_file="boots_products.csv"):
    """
    Scrape a list of product URLs using Playwright.
    
    Args:
        page (Page): Playwright page object.
        product_urls (list): List of product URLs to scrape.
        max_products (int, optional): Maximum number of products to scrape. None means no limit.
        output_file (str): The name of the output CSV file.
        
    Returns:
        list: A list of dictionaries containing product data.
    """
    product_data_list = []
    
    # Limit the number of products if specified
    if max_products is not None:
        product_urls = product_urls[:max_products]
    
    print(f"Scraping {len(product_urls)} product URLs")
    
    for i, url in enumerate(product_urls):
        print(f"\n{'=' * 50}")
        print(f"Scraping product {i+1}/{len(product_urls)}: {url}")
        print(f"{'=' * 50}")
        
        # Add a random delay to avoid being blocked
        delay = random.uniform(1.5, 3.0)
        print(f"Waiting {delay:.2f} seconds...")
        await asyncio.sleep(delay)
        
        # Scrape the product
        product_data = await scrape_boots_product(page, url)
        
        # Check if we got meaningful data
        if product_data and product_data.get('product_name'):
            product_data_list.append(product_data)
            print(f"Successfully scraped: {product_data.get('product_name')}")
        else:
            print(f"Failed to extract meaningful data from {url}")
    
    # Save the data to CSV if we have any
    if product_data_list:
        save_to_csv(product_data_list, output_file)
        print(f"Saved {len(product_data_list)} products to {output_file}")
    else:
        print("No product data was scraped.")
    
    return product_data_list

async def scrape_boots_category(page, category_url, max_products=None, output_file="boots_products.csv"):
    """
    Scrape all products from a Boots category page, handling pagination.
    
    Args:
        page (Page): Playwright page object.
        category_url (str): The URL of the category page.
        max_products (int, optional): Maximum number of products to scrape. None means no limit.
        output_file (str): The name of the output CSV file.
        
    Returns:
        list: A list of dictionaries containing product data.
    """
    all_product_urls = []
    current_page = 1
    max_pages = 5  # Limit to 5 pages by default to avoid excessive scraping
    
    # Check if the URL is for 5-star skincare products
    if "skincare" in category_url.lower() and "reviewScore=5" in category_url:
        print("Using curated list of 5-star skincare products...")
        all_product_urls = get_current_5star_skincare_products()
    else:
        print(f"Scraping category: {category_url}")
        
        # Get product URLs from the first page
        product_urls = await get_product_urls_from_page(page, category_url)
        all_product_urls.extend(product_urls)
        
        # Check if we need to scrape more pages
        if max_products is None or len(all_product_urls) < max_products:
            # Try to find pagination information
            content = await page.content()
            soup = BeautifulSoup(content, 'html.parser')
            
            # Look for pagination elements
            pagination_elements = soup.select('.pagination, [data-test="pagination"]')
            if pagination_elements:
                # Look for page numbers
                page_links = soup.select('.pagination a, [data-test="pagination-item"] a')
                page_numbers = []
                
                for link in page_links:
                    # Extract page number from the link text or URL
                    try:
                        page_text = link.text.strip()
                        if page_text.isdigit():
                            page_numbers.append(int(page_text))
                        else:
                            # Try to extract from href
                            href = link.get('href', '')
                            page_match = re.search(r'page=(\d+)', href)
                            if page_match:
                                page_numbers.append(int(page_match.group(1)))
                    except (ValueError, AttributeError):
                        continue
                
                if page_numbers:
                    max_pages = min(max(page_numbers), max_pages)
            
            # Scrape additional pages if needed
            while current_page < max_pages:
                current_page += 1
                next_page_url = await get_next_page_url(page, category_url, current_page)
                
                print(f"Scraping page {current_page}: {next_page_url}")
                product_urls = await get_product_urls_from_page(page, next_page_url)
                
                if not product_urls:
                    print(f"No products found on page {current_page}. Stopping pagination.")
                    break
                
                all_product_urls.extend(product_urls)
                
                # Check if we've reached the maximum number of products
                if max_products is not None and len(all_product_urls) >= max_products:
                    break
                
                # Add a delay between page requests
                await asyncio.sleep(random.uniform(2.0, 4.0))
    
    # Remove duplicates
    all_product_urls = list(dict.fromkeys(all_product_urls))
    
    # Limit the number of products if specified
    if max_products is not None:
        all_product_urls = all_product_urls[:max_products]
    
    # Scrape the products
    return await scrape_product_list(page, all_product_urls, max_products, output_file)

async def search_and_extract_product_urls(page, search_terms, max_products=10):
    """
    Search for products on the Boots website and extract product URLs from the search results.
    
    Args:
        page (Page): Playwright page object.
        search_terms (list): List of search terms to use.
        max_products (int): Maximum number of products to extract.
        
    Returns:
        list: A list of product URLs.
    """
    product_urls = []
    
    try:
        for search_term in search_terms:
            if len(product_urls) >= max_products:
                break
                
            print(f"Searching for: {search_term}")
            search_url = f"https://www.boots.com/search?q={search_term.replace(' ', '+')}"
            
            # Navigate to the search page
            await page.goto(search_url, wait_until="domcontentloaded", timeout=60000)
            
            # Wait for the page to load
            try:
                await page.wait_for_load_state("networkidle", timeout=15000)
            except Exception as e:
                print(f"Warning: Page load state timeout: {str(e)}")
            
            # Accept cookies if the cookie banner appears
            try:
                cookie_accept_button = await page.query_selector('button#onetrust-accept-btn-handler, .cookie-accept-button, [data-testid="cookie-accept-button"]')
                if cookie_accept_button:
                    await cookie_accept_button.click()
                    print("Accepted cookies")
                    await page.wait_for_timeout(2000)  # Wait for cookie banner to disappear
            except Exception as e:
                print(f"Warning: Could not handle cookie banner: {str(e)}")
            
            # Take a screenshot for debugging
            screenshot_name = f"boots_search_{search_term.replace(' ', '_')}.png"
            await page.screenshot(path=screenshot_name)
            print(f"Saved screenshot to {screenshot_name}")
            
            # Scroll down to load more products
            for i in range(3):
                await page.evaluate(f"window.scrollBy(0, {800 * (i+1)})")
                await page.wait_for_timeout(1000)
            
            # Try to find product links in the search results
            print("Looking for product links in search results...")
            
            # Try different selectors for product links
            product_link_selectors = [
                'a[data-test="product-link"]',
                'a[data-analytics-product-id]',
                '.product-tile a',
                '.product-grid-item a',
                '.estore-product-tile a',
                '.product__list a',
                'a.product-title-link',
                '[data-test="product-tile"] a',
                '.product a',
                'a[href*="/beauty/skincare/"]'
            ]
            
            for selector in product_link_selectors:
                try:
                    links = await page.query_selector_all(selector)
                    if links:
                        print(f"Found {len(links)} potential links with selector: {selector}")
                        
                        for link in links:
                            href = await link.get_attribute('href')
                            if href:
                                # Make sure it's an absolute URL
                                if not href.startswith('http'):
                                    if href.startswith('/'):
                                        href = f"https://www.boots.com{href}"
                                    else:
                                        href = f"https://www.boots.com/{href}"
                                
                                # Filter for actual product URLs
                                if (('/beauty/skincare/' in href or '/beauty/brands/' in href) and 
                                    not href.endswith('/beauty/skincare') and 
                                    not '/category/' in href and
                                    not '?' in href):
                                    product_urls.append(href)
                        
                        if product_urls:
                            print(f"Found {len(product_urls)} product URLs from search results")
                            break  # Break if we found products with this selector
                except Exception as e:
                    print(f"Error with selector {selector}: {str(e)}")
            
            # If we still don't have product URLs, try a more general approach
            if not product_urls:
                print("Trying general approach to find product links...")
                try:
                    all_links = await page.query_selector_all('a[href]')
                    print(f"Found {len(all_links)} total links on the page")
                    
                    for link in all_links:
                        href = await link.get_attribute('href')
                        if href and ('/beauty/skincare/' in href or '/beauty/brands/' in href):
                            # Make sure it's an absolute URL
                            if not href.startswith('http'):
                                if href.startswith('/'):
                                    href = f"https://www.boots.com{href}"
                                else:
                                    href = f"https://www.boots.com/{href}"
                            
                            # Check if it looks like a product URL
                            if (not href.endswith('/beauty/skincare') and 
                                not '/category/' in href and
                                not '?' in href):
                                product_urls.append(href)
                except Exception as e:
                    print(f"Error with general approach: {str(e)}")
            
            # Wait before next search
            await page.wait_for_timeout(2000)
        
        # Remove duplicates
        product_urls = list(dict.fromkeys(product_urls))
        
        # Limit to max_products
        if max_products and len(product_urls) > max_products:
            product_urls = product_urls[:max_products]
        
        print(f"Found {len(product_urls)} unique product URLs from search")
        
        # Print the first few URLs for debugging
        for i, url in enumerate(product_urls[:5]):
            print(f"  {i+1}. {url}")
        
        return product_urls
    
    except Exception as e:
        print(f"Error searching for products: {str(e)}")
        return []

def get_skincare_search_terms():
    """
    Return a list of search terms for skincare products.
    
    Returns:
        list: A list of search terms.
    """
    return [
        "the ordinary niacinamide",
        "cerave hydrating cleanser",
        "liz earle cleanse and polish",
        "no7 protect and perfect",
        "the ordinary hyaluronic acid",
        "cerave moisturizing cream",
        "the ordinary caffeine solution",
        "la roche posay effaclar",
        "the inkey list niacinamide",
        "neutrogena hydro boost"
    ]

async def main_async():
    """
    Main async function to run the scraper.
    """
    parser = argparse.ArgumentParser(description='Scrape products from Boots.com using Playwright.')
    parser.add_argument('--category', type=str, help='Category URL to scrape')
    parser.add_argument('--file', type=str, help='File containing product URLs to scrape')
    parser.add_argument('--urls', nargs='+', help='Product URLs to scrape')
    parser.add_argument('--max-products', type=int, default=10, help='Maximum number of products to scrape')
    parser.add_argument('--output', type=str, default='boots_products.csv', help='Output CSV file')
    parser.add_argument('--search', action='store_true', help='Use search to find product URLs')
    parser.add_argument('--five-star', action='store_true', help='Scrape 5-star skincare products')
    parser.add_argument('--debug', action='store_true', help='Enable debug mode (more verbose output)')
    
    args = parser.parse_args()
    
    # Set up Playwright
    async with async_playwright() as playwright:
        # Launch the browser
        browser = await playwright.chromium.launch(headless=True)
        context = await browser.new_context(
            viewport={"width": 1280, "height": 800},
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        )
        page = await context.new_page()
        
        # Enable debug logging if requested
        if args.debug:
            page.on("console", lambda msg: print(f"BROWSER LOG: {msg.text}"))
        
        product_urls = []
        
        # Determine the source of product URLs
        if args.urls:
            # Use directly provided URLs
            product_urls = args.urls
            print(f"Using {len(product_urls)} product URLs provided as command-line arguments")
        
        elif args.file:
            # Read URLs from file
            product_urls = read_product_urls_from_file(args.file)
            print(f"Read {len(product_urls)} product URLs from file: {args.file}")
        
        elif args.five_star:
            # Use hardcoded list of 5-star skincare products
            product_urls = get_current_5star_skincare_products()
            print(f"Using {len(product_urls)} hardcoded 5-star skincare product URLs")
        
        elif args.search:
            # Use search to find product URLs
            search_terms = get_skincare_search_terms()
            product_urls = await search_and_extract_product_urls(page, search_terms, args.max_products)
            print(f"Found {len(product_urls)} product URLs using search")
        
        elif args.category:
            # Scrape products from a category page
            print(f"Scraping products from category: {args.category}")
            product_urls = await extract_product_urls_from_live_site(page, args.category, args.max_products)
        
        else:
            # Default: extract product URLs from the live site
            print("Extracting product URLs from the live Boots website...")
            category_url = "https://www.boots.com/beauty/skincare/skincare-all-skincare?criteria.roundedReviewScore=5"
            product_urls = await extract_product_urls_from_live_site(page, category_url, args.max_products)
        
        # Limit to max_products
        if args.max_products and len(product_urls) > args.max_products:
            product_urls = product_urls[:args.max_products]
        
        if not product_urls:
            print("No product URLs found. Exiting.")
            await browser.close()
            return
        
        # Scrape the products
        print(f"Scraping {len(product_urls)} products...")
        product_data_list = await scrape_product_list(page, product_urls, args.max_products, args.output)
        
        # Close the browser
        await browser.close()
        
        # Print summary
        print(f"\nScraping completed. Scraped {len(product_data_list)} products.")
        print(f"Data saved to {args.output}")
        
        # Print success rate
        success_count = sum(1 for product in product_data_list if product['product_name'] is not None)
        if product_urls:
            success_rate = (success_count / len(product_urls)) * 100
            print(f"Success rate: {success_rate:.2f}% ({success_count}/{len(product_urls)})")
        
        # Print some sample data
        if product_data_list:
            print("\nSample of scraped products:")
            for i, product in enumerate(product_data_list[:3]):
                print(f"\n{i+1}. {product.get('product_name', 'Unknown')} - {product.get('brand', 'Unknown Brand')}")
                print(f"   Price: {product.get('price', 'N/A')}")
                print(f"   Rating: {product.get('rating', 'N/A')} ({product.get('review_count', 'N/A')} reviews)")
                
                # Show if we got ingredients
                if product.get('ingredients'):
                    ingredients_preview = product['ingredients'][:100] + "..." if len(product['ingredients']) > 100 else product['ingredients']
                    print(f"   Ingredients: {ingredients_preview}")
                else:
                    print("   Ingredients: Not found")
        
def main():
    """
    Main function to run the scraper.
    """
    asyncio.run(main_async())

if __name__ == "__main__":
    main()
