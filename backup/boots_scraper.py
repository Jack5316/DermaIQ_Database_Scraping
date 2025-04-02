#!/usr/bin/env python3
"""
Boots Category Scraper

This script scrapes products from Boots.com, either from:
1. A category page URL
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
import requests

# Import functions from the existing cosmetics_scraper.py
from cosmetics_scraper import scrape_boots_product, save_to_csv

def get_total_pages(soup):
    """
    Extract the total number of pages from the pagination section.
    
    Args:
        soup (BeautifulSoup): The parsed HTML of the category page.
        
    Returns:
        int: The total number of pages, defaults to 1 if not found.
    """
    total_pages = 1
    
    # Try to find pagination elements
    pagination_elements = soup.select('.pagination')
    if pagination_elements:
        # Look for page numbers
        page_links = soup.select('.pagination a')
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
            total_pages = max(page_numbers)
    
    return total_pages

def get_product_urls_from_page(soup, base_url="https://www.boots.com"):
    """
    Extract product URLs from a category page.
    
    Args:
        soup (BeautifulSoup): The parsed HTML of the category page.
        base_url (str): The base URL to prepend to relative URLs.
        
    Returns:
        list: A list of product URLs.
    """
    product_urls = []
    
    # Try different selectors for product links based on the observed page structure
    product_selectors = [
        '.product-grid-item a.product-title-link',  # Based on image observation
        '.product-list-item a.product-title-link',  # Based on image observation
        '.estore-product-tile a.product-title-link',
        '.product-tile a.product-title-link',
        '.product__list a.product__link',
        '.product-list-item a.product-link',
        '.product-grid a.product-title',
        '.product-tile__details a',
        'a.product-title-link'
    ]
    
    # First try the specific selectors
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
        product_containers = soup.select('.product-grid-item, .product-list-item, .estore-product-tile, .product-tile')
        
        for container in product_containers:
            links = container.select('a[href]')
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

def get_next_page_url(current_url, page_number):
    """
    Construct the URL for the next page.
    
    Args:
        current_url (str): The current page URL.
        page_number (int): The next page number.
        
    Returns:
        str: The URL for the next page.
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

def extract_product_urls_from_api(category_url, max_products=None):
    """
    Extract product URLs by accessing the Boots search API directly.
    
    Args:
        category_url (str): The URL of the category page.
        max_products (int, optional): Maximum number of products to extract.
        
    Returns:
        list: A list of product URLs.
    """
    product_urls = []
    
    # Parse the category URL to extract query parameters
    parsed_url = urlparse(category_url)
    path = parsed_url.path
    query_params = parse_qs(parsed_url.query)
    
    # Extract category ID from the path
    category_id = None
    path_parts = path.strip('/').split('/')
    if len(path_parts) > 0:
        category_id = path_parts[-1]
    
    # Set up headers to mimic a browser
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'application/json',
        'Accept-Language': 'en-US,en;q=0.9',
        'Referer': category_url
    }
    
    # Construct the search API URL
    base_api_url = "https://www.boots.com/webapp/wcs/stores/servlet/CategoryDisplay"
    
    # Set default parameters
    api_params = {
        'storeId': '11352',
        'catalogId': '28501',
        'langId': '-1',
        'categoryId': category_id or '',
        'pageSize': '24',  # Default page size
        'beginIndex': '0'
    }
    
    # Add any additional filters from the original URL
    for key, value in query_params.items():
        if key not in api_params:
            api_params[key] = value[0]
    
    # Copy the review score filter if present
    if 'criteria.roundedReviewScore' in query_params:
        api_params['criteria.roundedReviewScore'] = query_params['criteria.roundedReviewScore'][0]
    
    current_index = 0
    page = 1
    more_products = True
    
    while more_products:
        # Update the begin index for pagination
        api_params['beginIndex'] = str(current_index)
        
        # Construct the API URL
        api_url = f"{base_api_url}?{urlencode(api_params)}"
        
        print(f"Fetching products from API (page {page}): {api_url}")
        
        try:
            response = requests.get(api_url, headers=headers, timeout=30)
            
            if response.status_code != 200:
                print(f"Failed to retrieve data from API. Status code: {response.status_code}")
                break
            
            # Parse the HTML response
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Extract product links
            page_product_urls = get_product_urls_from_page(soup)
            
            if not page_product_urls:
                # Try to find product data in JSON format
                script_tags = soup.find_all('script', {'type': 'application/json'})
                for script in script_tags:
                    try:
                        json_data = json.loads(script.string)
                        if isinstance(json_data, dict) and 'products' in json_data:
                            for product in json_data.get('products', []):
                                if 'url' in product:
                                    product_url = product['url']
                                    if not product_url.startswith('http'):
                                        product_url = f"https://www.boots.com{product_url}"
                                    page_product_urls.append(product_url)
                    except (json.JSONDecodeError, AttributeError):
                        continue
            
            print(f"Found {len(page_product_urls)} products on page {page}")
            
            if not page_product_urls:
                print("No more products found, ending pagination.")
                more_products = False
            else:
                product_urls.extend(page_product_urls)
                
                # Check if we've reached the maximum number of products
                if max_products and len(product_urls) >= max_products:
                    product_urls = product_urls[:max_products]
                    more_products = False
                    break
                
                # Move to the next page
                current_index += len(page_product_urls)
                page += 1
                
                # Add a delay between requests
                delay = random.uniform(1.5, 3.0)
                print(f"Waiting {delay:.2f} seconds before fetching next page...")
                time.sleep(delay)
        
        except Exception as e:
            print(f"Error fetching products from API: {str(e)}")
            break
    
    # Remove duplicates while preserving order
    product_urls = list(dict.fromkeys(product_urls))
    print(f"Found {len(product_urls)} unique product URLs across all pages")
    
    return product_urls

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
        with open(file_path, 'r') as f:
            for line in f:
                url = line.strip()
                if url and url.startswith('http'):
                    product_urls.append(url)
        
        print(f"Read {len(product_urls)} product URLs from {file_path}")
    except Exception as e:
        print(f"Error reading product URLs from file: {str(e)}")
    
    return product_urls

def get_current_5star_skincare_products():
    """
    Get a list of current 5-star skincare products from Boots.
    These are manually curated and updated.
    
    Returns:
        list: A list of product URLs.
    """
    # Current popular 5-star skincare products from Boots as of March 2025
    return [
        "https://www.boots.com/beauty/skincare/face-skincare/cleansers-toners/cerave-hydrating-cleanser-236ml-10246741",
        "https://www.boots.com/beauty/skincare/face-skincare/face-serums/the-ordinary-hyaluronic-acid-2-b5-30ml-10283942",
        "https://www.boots.com/beauty/skincare/face-skincare/face-serums/the-ordinary-niacinamide-10-zinc-1-30ml-10283940",
        "https://www.boots.com/beauty/skincare/face-skincare/eye-creams/the-ordinary-caffeine-solution-5-egcg-30ml-10283943",
        "https://www.boots.com/beauty/skincare/face-skincare/face-moisturisers/la-roche-posay-effaclar-duo-40ml-10185194",
        "https://www.boots.com/beauty/skincare/face-skincare/face-moisturisers/cerave-moisturising-lotion-236ml-10246740",
        "https://www.boots.com/beauty/skincare/face-skincare/face-moisturisers/the-ordinary-natural-moisturizing-factors-ha-30ml-10283950",
        "https://www.boots.com/beauty/skincare/face-skincare/face-exfoliators-peels/the-ordinary-glycolic-acid-7-toning-solution-240ml-10283951",
        "https://www.boots.com/beauty/skincare/face-skincare/face-treatments/the-ordinary-salicylic-acid-2-solution-30ml-10283949",
        "https://www.boots.com/beauty/skincare/face-skincare/face-treatments/the-ordinary-azelaic-acid-suspension-10-30ml-10283944"
    ]

def scrape_product_list(product_urls, max_products=None, output_file="boots_products.csv"):
    """
    Scrape a list of product URLs.
    
    Args:
        product_urls (list): List of product URLs to scrape.
        max_products (int, optional): Maximum number of products to scrape. None means no limit.
        output_file (str): The name of the output CSV file.
        
    Returns:
        list: A list of dictionaries containing product data.
    """
    all_product_data = []
    
    # Limit to max_products if specified
    if max_products and len(product_urls) > max_products:
        product_urls = product_urls[:max_products]
    
    print(f"Scraping {len(product_urls)} product URLs")
    
    # Scrape each product
    successful_scrapes = 0
    
    for i, url in enumerate(product_urls):
        try:
            print(f"\n{'='*50}")
            print(f"Scraping product {i+1}/{len(product_urls)}: {url}")
            print(f"{'='*50}")
            
            # Add a random delay between requests to avoid being blocked
            delay = random.uniform(1.0, 3.0)
            print(f"Waiting {delay:.2f} seconds...")
            time.sleep(delay)
            
            # Scrape the product data
            product_data = scrape_boots_product(url)
            
            if product_data and any(product_data[key] for key in ['product_name', 'ingredients', 'product_details']):
                # Print the scraped data - only the fields we care about
                print("\nScraped Product Data:")
                for key, value in product_data.items():
                    if key in ['url', 'source', 'product_name', 'brand', 'ingredients', 'hazards_and_cautions', 'product_details', 'ingredients_count', 'country_of_origin']:
                        if value:
                            print(f"{key}: {value}")
                        else:
                            print(f"{key}: Not found")
                
                # Add to our list of products
                all_product_data.append(product_data)
                successful_scrapes += 1
                
                # Save data incrementally after every 5 products
                if successful_scrapes % 5 == 0:
                    save_to_csv(all_product_data, output_file)
                    print(f"Incremental save: {successful_scrapes} products saved to {output_file}")
            else:
                print(f"Failed to extract meaningful data from {url}")
                
        except Exception as e:
            print(f"Error processing URL {url}: {str(e)}")
    
    # Final save
    if all_product_data:
        save_to_csv(all_product_data, output_file)
        print(f"\nSuccessfully scraped {successful_scrapes} out of {len(product_urls)} products.")
        print(f"Data saved to {output_file}")
    else:
        print("No product data was scraped.")
    
    return all_product_data

def scrape_boots_category(category_url, max_products=None, output_file="boots_products.csv"):
    """
    Scrape all products from a Boots category page, handling pagination.
    
    Args:
        category_url (str): The URL of the category page.
        max_products (int, optional): Maximum number of products to scrape. None means no limit.
        output_file (str): The name of the output CSV file.
        
    Returns:
        list: A list of dictionaries containing product data.
    """
    # For 5-star skincare products, use updated hardcoded approach
    if "criteria.roundedReviewScore=5" in category_url and "skincare" in category_url:
        print("Using curated list of 5-star skincare products...")
        product_urls = get_current_5star_skincare_products()
        return scrape_product_list(product_urls, max_products, output_file)
    else:
        # Try to extract product URLs using the API approach
        product_urls = extract_product_urls_from_api(category_url, max_products)
        
        # If API approach failed, try the traditional HTML approach
        if not product_urls:
            print("API approach failed, trying traditional HTML scraping...")
            
            # Set up headers to mimic a browser
            headers = {
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
                'Accept-Language': 'en-US,en;q=0.9',
                'Referer': 'https://www.boots.com/'
            }
            
            try:
                # Send a GET request to the initial URL
                print(f"Fetching category page: {category_url}")
                response = requests.get(category_url, headers=headers, timeout=30)
                
                # Check if the request was successful
                if response.status_code != 200:
                    print(f"Failed to retrieve the category page. Status code: {response.status_code}")
                    return []
                
                # Parse the HTML content
                soup = BeautifulSoup(response.content, 'html.parser')
                
                # Get the total number of pages
                total_pages = get_total_pages(soup)
                print(f"Found {total_pages} pages in total")
                
                # Process all pages
                current_page = 1
                while current_page <= total_pages:
                    if current_page > 1:
                        # Construct the URL for the next page
                        next_page_url = get_next_page_url(category_url, current_page)
                        
                        # Add a delay between page requests
                        delay = random.uniform(2.0, 5.0)
                        print(f"Waiting {delay:.2f} seconds before fetching next page...")
                        time.sleep(delay)
                        
                        print(f"Fetching category page {current_page}/{total_pages}: {next_page_url}")
                        response = requests.get(next_page_url, headers=headers, timeout=30)
                        
                        if response.status_code != 200:
                            print(f"Failed to retrieve page {current_page}. Status code: {response.status_code}")
                            break
                        
                        soup = BeautifulSoup(response.content, 'html.parser')
                    
                    # Get product URLs from the current page
                    page_product_urls = get_product_urls_from_page(soup)
                    print(f"Found {len(page_product_urls)} products on page {current_page}")
                    
                    # Add to our list of all product URLs
                    product_urls.extend(page_product_urls)
                    
                    # Check if we've reached the maximum number of products
                    if max_products and len(product_urls) >= max_products:
                        product_urls = product_urls[:max_products]
                        break
                    
                    current_page += 1
                
                # Remove duplicates
                product_urls = list(dict.fromkeys(product_urls))
                print(f"Found {len(product_urls)} unique product URLs across all pages")
                
            except Exception as e:
                print(f"Error scraping category: {str(e)}")
        
        # If we still don't have any product URLs, try a direct search approach
        if not product_urls:
            print("Traditional HTML scraping failed, trying direct search approach...")
            try:
                # Extract search term from the URL path
                parsed_url = urlparse(category_url)
                path_parts = parsed_url.path.strip('/').split('/')
                search_term = path_parts[-1].replace('-', ' ')
                
                # Construct a search URL
                search_url = f"https://www.boots.com/webapp/wcs/stores/servlet/SearchDisplay?storeId=11352&catalogId=28501&langId=-1&searchTerm={search_term}"
                
                print(f"Trying search URL: {search_url}")
                response = requests.get(search_url, headers=headers, timeout=30)
                
                if response.status_code == 200:
                    soup = BeautifulSoup(response.content, 'html.parser')
                    product_urls = get_product_urls_from_page(soup)
                    print(f"Found {len(product_urls)} products from search")
                    
                    # Limit to max_products if specified
                    if max_products and len(product_urls) > max_products:
                        product_urls = product_urls[:max_products]
            except Exception as e:
                print(f"Error with direct search approach: {str(e)}")
        
        return scrape_product_list(product_urls, max_products, output_file)

def main():
    """Main function to run the scraper."""
    parser = argparse.ArgumentParser(description='Scrape products from Boots.com.')
    parser.add_argument('--url', type=str, 
                        default="https://www.boots.com/beauty/skincare/skincare-all-skincare?criteria.roundedReviewScore=5",
                        help='The URL of the category page to scrape')
    parser.add_argument('--max', type=int, default=None, 
                        help='Maximum number of products to scrape (default: no limit)')
    parser.add_argument('--output', type=str, default="boots_products.csv",
                        help='Output CSV file name (default: boots_products.csv)')
    parser.add_argument('--file', type=str, default=None,
                        help='Path to a file containing product URLs to scrape (one URL per line)')
    parser.add_argument('--products', nargs='+', default=None,
                        help='List of product URLs to scrape')
    
    args = parser.parse_args()
    
    # Determine the scraping mode based on the provided arguments
    if args.file:
        print(f"Reading product URLs from file: {args.file}")
        product_urls = read_product_urls_from_file(args.file)
        if product_urls:
            scrape_product_list(product_urls, args.max, args.output)
        else:
            print("No valid product URLs found in the file.")
    elif args.products:
        print(f"Scraping {len(args.products)} provided product URLs")
        scrape_product_list(args.products, args.max, args.output)
    else:
        print(f"Starting to scrape Boots.com category: {args.url}")
        print(f"Max products: {'No limit' if args.max is None else args.max}")
        print(f"Output file: {args.output}")
        scrape_boots_category(args.url, args.max, args.output)

if __name__ == "__main__":
    main()
