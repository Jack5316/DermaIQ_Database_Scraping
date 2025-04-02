#!/usr/bin/env python3
"""
Boots CSV Product Scraper

This script reads product URLs from boots.csv and scrapes detailed product information
using the single product scraper functionality from cosmetics_scraper.py.
"""

import os
import time
import random
import pandas as pd
import json
from datetime import datetime
from cosmetics_scraper import scrape_boots_product, save_to_csv

def read_product_urls_from_csv(csv_file):
    """
    Read product URLs from a CSV file with 'oct-link href' column.
    
    Args:
        csv_file (str): Path to the CSV file containing product URLs.
        
    Returns:
        list: A list of product URLs.
    """
    try:
        df = pd.read_csv(csv_file)
        
        # Check if 'oct-link href' column exists
        if 'oct-link href' in df.columns:
            # Extract URLs and remove duplicates
            product_urls = df['oct-link href'].dropna().unique().tolist()
            return product_urls
        else:
            print(f"Error: 'oct-link href' column not found in {csv_file}")
            return []
    except Exception as e:
        print(f"Error reading {csv_file}: {e}")
        return []

def scrape_product_list(product_urls, max_products=None, output_prefix="boots_scraped"):
    """
    Scrape a list of product URLs.
    
    Args:
        product_urls (list): List of product URLs to scrape.
        max_products (int, optional): Maximum number of products to scrape. None means no limit.
        output_prefix (str): The prefix for output files.
        
    Returns:
        list: A list of dictionaries containing product data.
    """
    # Create timestamp for unique filenames
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # Create data directory if it doesn't exist
    os.makedirs("data", exist_ok=True)
    
    # Output filenames
    csv_filename = f"data/{output_prefix}_{timestamp}.csv"
    json_filename = f"data/{output_prefix}_{timestamp}.json"
    
    # Limit the number of products if specified
    if max_products is not None:
        product_urls = product_urls[:max_products]
    
    print(f"Starting to scrape {len(product_urls)} products...")
    
    # Initialize list to store product data
    product_data_list = []
    
    # Scrape each product URL
    for i, url in enumerate(product_urls):
        try:
            print(f"Scraping product {i+1}/{len(product_urls)}: {url}")
            
            # Scrape the product
            product_data = scrape_boots_product(url)
            
            # Add to the list
            if product_data:
                product_data_list.append(product_data)
                
                # Save progress after every 5 products
                if (i + 1) % 5 == 0:
                    save_to_csv(product_data_list, csv_filename)
                    with open(json_filename, 'w', encoding='utf-8') as f:
                        json.dump(product_data_list, f, indent=2, ensure_ascii=False)
                    print(f"Progress saved: {i+1}/{len(product_urls)} products")
            
            # Random delay to avoid overloading the server
            delay = random.uniform(1, 3)
            time.sleep(delay)
            
        except Exception as e:
            print(f"Error scraping {url}: {e}")
    
    # Save final results
    save_to_csv(product_data_list, csv_filename)
    with open(json_filename, 'w', encoding='utf-8') as f:
        json.dump(product_data_list, f, indent=2, ensure_ascii=False)
    
    print(f"Scraping completed. {len(product_data_list)} products scraped.")
    print(f"Results saved to {csv_filename} and {json_filename}")
    
    return product_data_list, csv_filename, json_filename

def main():
    """Main function to run the scraper."""
    # Read product URLs from boots.csv
    csv_file = "boots.csv"
    product_urls = read_product_urls_from_csv(csv_file)
    
    if not product_urls:
        print(f"No product URLs found in {csv_file}")
        return
    
    print(f"Found {len(product_urls)} product URLs in {csv_file}")
    
    # Scrape the products
    product_data_list, csv_filename, json_filename = scrape_product_list(
        product_urls, 
        output_prefix="boots_products"
    )
    
    print(f"Scraping completed. Results saved to:")
    print(f"CSV: {csv_filename}")
    print(f"JSON: {json_filename}")

if __name__ == "__main__":
    main()
