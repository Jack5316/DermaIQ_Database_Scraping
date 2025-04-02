import requests
from bs4 import BeautifulSoup
import json
import re
import pandas as pd
import time
import random
import os
from urllib.parse import urlparse, parse_qs
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime

# Configuration constants
MAX_WORKERS = 4  # Reduced from 5 to avoid being blocked
SAVE_INTERVAL = 10  # Save progress more frequently (was 20)
PRODUCT_LIMIT = None  # Limit number of products to scrape (set to None for all)
RETRY_ATTEMPTS = 3  # Number of retry attempts for failed requests
RETRY_DELAY = 3  # Increased delay between retry attempts (was 2)
MIN_DELAY = 1.0  # Minimum delay between requests
MAX_DELAY = 3.0  # Maximum delay between requests
RATE_LIMIT_PAUSE = 60  # Pause time in seconds if rate limited
MAX_RETRIES = 3

def extract_ingredients(soup):
    """
    Extract ingredients from the product page.
    
    Args:
        soup (BeautifulSoup): Parsed HTML content of the product page.
        
    Returns:
        str: Extracted ingredients text.
    """
    # First try specific ingredient sections by CSS selectors
    ingredients_selectors = [
        '.product-ingredients',
        '.ingredients-list',
        '.product-composition',
        '.composition-list',
        '[data-testid="ingredients"]',
        '[data-testid="product-ingredients"]',
        '.product-details-tile__product-info-section',
        '.product-info-block',
        '.product-details__description'
    ]
    
    # First try to find sections with ingredient headers
    ingredient_headers = soup.find_all(['h2', 'h3', 'h4', 'strong', 'b'], 
                                      string=lambda s: s and re.search(r'ingredients', s, re.IGNORECASE))
    
    for header in ingredient_headers:
        # Try to get the parent section
        parent = header.find_parent('div')
        if parent:
            # Get the text after the header
            header_text = header.get_text(strip=True)
            parent_text = parent.get_text(strip=True)
            
            # Extract the part after the header
            if header_text in parent_text:
                ingredients_text = parent_text[parent_text.index(header_text) + len(header_text):]
                # Clean up the text
                ingredients_text = ingredients_text.strip()
                ingredients_text = re.sub(r'^[:\.\s]+', '', ingredients_text)
                
                # Validate that this looks like ingredients (contains commas, chemical names)
                if ',' in ingredients_text and len(ingredients_text) > 20 and len(ingredients_text) < 3000:
                    return ingredients_text
        
        # Try to get the next sibling
        next_elem = header.find_next_sibling()
        if next_elem and next_elem.name in ['p', 'div', 'span', 'ul']:
            ingredients_text = next_elem.get_text(strip=True)
            if ',' in ingredients_text and len(ingredients_text) > 20 and len(ingredients_text) < 3000:
                return ingredients_text
    
    # Try specific selectors
    for selector in ingredients_selectors:
        ingredients_elems = soup.select(selector)
        for elem in ingredients_elems:
            # Check if this section contains the word "ingredients"
            if 'ingredients' in elem.text.lower():
                # Try to extract just the ingredients part
                ingredients_match = re.search(r'ingredients\s*:(.+?)(?:\.|$)', elem.text, re.IGNORECASE | re.DOTALL)
                if ingredients_match:
                    ingredients_text = ingredients_match.group(1).strip()
                    # Validate that this looks like ingredients
                    if ',' in ingredients_text and len(ingredients_text) > 20 and len(ingredients_text) < 3000:
                        return ingredients_text
                
                # If no specific pattern, check if the text is likely ingredients
                elem_text = elem.text.strip()
                if ',' in elem_text and len(elem_text) < 3000:
                    # Check if it has chemical names (common in ingredients)
                    chemical_pattern = r'\b(acid|extract|oil|butter|glycerin|water|aqua|alcohol|vitamin|sodium|potassium|calcium|zinc|iron|copper|magnesium)\b'
                    if re.search(chemical_pattern, elem_text, re.IGNORECASE):
                        return elem_text
    
    # Look for accordion sections that might contain ingredients
    accordion_items = soup.select('.accordion__item, .accordion-item, .product-accordion__item')
    for item in accordion_items:
        title_elem = item.select_one('.accordion__title, .accordion-title, .product-accordion__title')
        content_elem = item.select_one('.accordion__content, .accordion-content, .product-accordion__content')
        
        if title_elem and content_elem and 'ingredient' in title_elem.text.lower():
            content_text = content_elem.get_text(strip=True)
            if ',' in content_text and len(content_text) > 20 and len(content_text) < 3000:
                return content_text
    
    # Look for any paragraph that might contain ingredients
    for p in soup.find_all(['p', 'div']):
        p_text = p.get_text(strip=True)
        
        # Check if this paragraph has the ingredients pattern
        if re.search(r'ingredients\s*:', p_text, re.IGNORECASE) and ',' in p_text:
            # Extract the part after "ingredients:"
            ingredients_match = re.search(r'ingredients\s*:(.+)', p_text, re.IGNORECASE | re.DOTALL)
            if ingredients_match:
                ingredients_text = ingredients_match.group(1).strip()
                # Validate that this looks like ingredients
                if ',' in ingredients_text and len(ingredients_text) > 20 and len(ingredients_text) < 3000:
                    return ingredients_text
    
    # Look for structured data in JSON-LD
    json_ld_scripts = soup.find_all('script', {'type': 'application/ld+json'})
    for script in json_ld_scripts:
        try:
            data = json.loads(script.string)
            # Check various formats of structured data
            if isinstance(data, dict):
                # Check for ingredients in product schema
                if data.get('@type') == 'Product' and 'description' in data:
                    desc = data['description']
                    ingredients_match = re.search(r'ingredients\s*:(.+?)(?:\.|$)', desc, re.IGNORECASE | re.DOTALL)
                    if ingredients_match:
                        return ingredients_match.group(1).strip()
            elif isinstance(data, list):
                for item in data:
                    if isinstance(item, dict) and item.get('@type') == 'Product' and 'description' in item:
                        desc = item['description']
                        ingredients_match = re.search(r'ingredients\s*:(.+?)(?:\.|$)', desc, re.IGNORECASE | re.DOTALL)
                        if ingredients_match:
                            return ingredients_match.group(1).strip()
        except:
            continue
    
    # If all else fails, try a more aggressive approach for any text that looks like ingredients
    for elem in soup.find_all(['div', 'p', 'span']):
        elem_text = elem.get_text(strip=True)
        
        # Check if this text has characteristics of ingredients list
        if ',' in elem_text and 20 < len(elem_text) < 3000:
            # Common ingredients that indicate this is an ingredients list
            common_ingredients = [
                'aqua', 'water', 'glycerin', 'alcohol', 'parfum', 'fragrance', 
                'sodium', 'acid', 'extract', 'oil', 'butter', 'vitamin'
            ]
            
            # Count how many common ingredients are present
            matches = sum(1 for ing in common_ingredients if ing.lower() in elem_text.lower())
            
            # If at least 3 common ingredients are found, this is likely an ingredients list
            if matches >= 3:
                return elem_text
    
    return None


def scrape_boots_product(url, index=0, total=0):
    """
    Scrape product information from a Boots.com product page.
    
    Args:
        url (str): URL of the product page.
        index (int): Index of the product in the list.
        total (int): Total number of products to scrape.
        
    Returns:
        dict: Dictionary containing product information.
    """
    product_data = {
        'url': url,
        'product_name': None,
        'brand': None,
        'ingredients': None,
        'ingredients_count': None,
        'country_of_origin': None,
        'hazards_and_cautions': None,
        'how_to_use': None,
        'product_details': None,
        'scrape_timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    }
    
    # Initialize retry counter
    retries = 0
    
    while retries < MAX_RETRIES:
        try:
            # Print progress information
            if index > 0 and total > 0:
                print(f"[{index}/{total}] Fetching URL: {url} (Attempt {retries+1}/{MAX_RETRIES})")
            
            # Add a random delay to avoid rate limiting
            time.sleep(random.uniform(MIN_DELAY, MAX_DELAY))
            
            # Set headers to mimic a browser
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                'Accept-Language': 'en-US,en;q=0.9',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Referer': 'https://www.boots.com/',
                'Connection': 'keep-alive'
            }
            
            # Send request to the URL
            response = requests.get(url, headers=headers, timeout=30)
            
            # Check if we're being rate limited
            if response.status_code == 429:
                print(f"Rate limiting detected. Pausing for {RATE_LIMIT_PAUSE} seconds...")
                time.sleep(RATE_LIMIT_PAUSE)
                retries += 1
                continue
            
            # Check if the request was successful
            if response.status_code != 200:
                print(f"Failed to fetch {url}. Status code: {response.status_code}")
                retries += 1
                time.sleep(RETRY_DELAY)
                continue
            
            # Parse the HTML content
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Extract product name
            product_name_elem = soup.select_one('h1.product-details-tile__title')
            if product_name_elem:
                product_data['product_name'] = product_name_elem.text.strip()
            
            # Extract brand name
            brand_elem = soup.select_one('a.product-details-tile__brand')
            if brand_elem:
                product_data['brand'] = brand_elem.text.strip()
            
            # Extract ingredients
            product_data['ingredients'] = extract_ingredients(soup)
            if product_data['ingredients']:
                # Count the number of ingredients (roughly by splitting by commas)
                ingredients_text = product_data['ingredients']
                # Remove common non-ingredient text patterns
                ingredients_text = re.sub(r'ingredients:|\bingrédients:|\bingredients\b|:|\*|\+|\.', '', ingredients_text, flags=re.IGNORECASE)
                # Split by commas and count non-empty items
                ingredients_list = [ing.strip() for ing in ingredients_text.split(',') if ing.strip()]
                product_data['ingredients_count'] = len(ingredients_list)
                product_data['ingredients_list'] = ingredients_list
            
            # Extract country of origin
            country_patterns = [
                r'Made in ([A-Za-z\s]+)',
                r'Country of Origin:?\s*([A-Za-z\s]+)',
                r'Manufactured in ([A-Za-z\s]+)',
                r'Product of ([A-Za-z\s]+)',
                r'Produced in ([A-Za-z\s]+)'
            ]
            
            # Look for country of origin in product information sections
            product_info_sections = soup.select('.product-details-tile__product-info-section, .product-details__description, .product-info-block')
            for section in product_info_sections:
                section_text = section.get_text(strip=True)
                for pattern in country_patterns:
                    match = re.search(pattern, section_text, re.IGNORECASE)
                    if match:
                        product_data['country_of_origin'] = match.group(1).strip()
                        break
                if product_data['country_of_origin']:
                    break
            
            # Enhanced extraction for hazards and cautions
            hazards_section = None
            
            # Try multiple selectors for hazards and cautions
            hazard_selectors = [
                '.product-details-tile__product-info-section h3:contains("Hazards"), .product-details-tile__product-info-section h3:contains("Cautions"), .product-details-tile__product-info-section h3:contains("Warnings")',
                '.product-info-block h3:contains("Hazards"), .product-info-block h3:contains("Cautions"), .product-info-block h3:contains("Warnings")',
                '.product-details__description h3:contains("Hazards"), .product-details__description h3:contains("Cautions"), .product-details__description h3:contains("Warnings")'
            ]
            
            for selector in hazard_selectors:
                hazard_headers = soup.select(selector)
                if hazard_headers:
                    for header in hazard_headers:
                        # Get the parent section or the next sibling paragraph
                        parent_section = header.find_parent('div', class_=lambda c: c and ('section' in c.lower() or 'block' in c.lower()))
                        if parent_section:
                            # Remove the header text from the section text
                            section_text = parent_section.get_text(strip=True).replace(header.get_text(strip=True), '')
                            if section_text:
                                hazards_section = section_text
                                break
                        
                        # Try next sibling if parent approach didn't work
                        next_elem = header.find_next_sibling()
                        if next_elem and next_elem.name in ['p', 'div', 'span', 'ul']:
                            hazards_section = next_elem.get_text(strip=True)
                            break
                
                if hazards_section:
                    break
            
            # Also look for hazard-related keywords in any section
            if not hazards_section:
                hazard_keywords = ['caution', 'warning', 'hazard', 'danger', 'precaution', 'safety']
                for section in product_info_sections:
                    section_text = section.get_text(strip=True).lower()
                    for keyword in hazard_keywords:
                        if keyword in section_text:
                            # Extract the paragraph containing the keyword
                            paragraphs = section.find_all(['p', 'li', 'div'], string=lambda s: s and keyword in s.lower())
                            if paragraphs:
                                hazards_section = ' '.join([p.get_text(strip=True) for p in paragraphs])
                                break
                    if hazards_section:
                        break
            
            product_data['hazards_and_cautions'] = hazards_section
            
            # Enhanced extraction for how to use
            how_to_use_section = None
            
            # Try multiple selectors for how to use
            usage_selectors = [
                '.product-details-tile__product-info-section h3:contains("How to use"), .product-details-tile__product-info-section h3:contains("Directions"), .product-details-tile__product-info-section h3:contains("Application")',
                '.product-info-block h3:contains("How to use"), .product-info-block h3:contains("Directions"), .product-info-block h3:contains("Application")',
                '.product-details__description h3:contains("How to use"), .product-details__description h3:contains("Directions"), .product-details__description h3:contains("Application")'
            ]
            
            for selector in usage_selectors:
                usage_headers = soup.select(selector)
                if usage_headers:
                    for header in usage_headers:
                        # Get the parent section or the next sibling paragraph
                        parent_section = header.find_parent('div', class_=lambda c: c and ('section' in c.lower() or 'block' in c.lower()))
                        if parent_section:
                            # Remove the header text from the section text
                            section_text = parent_section.get_text(strip=True).replace(header.get_text(strip=True), '')
                            if section_text:
                                how_to_use_section = section_text
                                break
                        
                        # Try next sibling if parent approach didn't work
                        next_elem = header.find_next_sibling()
                        if next_elem and next_elem.name in ['p', 'div', 'span', 'ul']:
                            how_to_use_section = next_elem.get_text(strip=True)
                            break
                
                if how_to_use_section:
                    break
            
            # Also look for usage-related keywords in any section
            if not how_to_use_section:
                usage_keywords = ['apply', 'use', 'massage', 'directions', 'application']
                for section in product_info_sections:
                    section_text = section.get_text(strip=True).lower()
                    for keyword in usage_keywords:
                        if keyword in section_text:
                            # Extract the paragraph containing the keyword
                            paragraphs = section.find_all(['p', 'li', 'div'], string=lambda s: s and keyword in s.lower())
                            if paragraphs:
                                how_to_use_section = ' '.join([p.get_text(strip=True) for p in paragraphs])
                                break
                    if how_to_use_section:
                        break
            
            product_data['how_to_use'] = how_to_use_section
            
            # Enhanced extraction for product details
            product_details_section = None
            
            # Try multiple selectors for product details
            details_selectors = [
                '.product-details-tile__product-info-section h3:contains("Product details"), .product-details-tile__product-info-section h3:contains("Description"), .product-details-tile__product-info-section h3:contains("About")',
                '.product-info-block h3:contains("Product details"), .product-info-block h3:contains("Description"), .product-info-block h3:contains("About")',
                '.product-details__description h3:contains("Product details"), .product-details__description h3:contains("Description"), .product-details__description h3:contains("About")'
            ]
            
            for selector in details_selectors:
                details_headers = soup.select(selector)
                if details_headers:
                    for header in details_headers:
                        # Get the parent section or the next sibling paragraph
                        parent_section = header.find_parent('div', class_=lambda c: c and ('section' in c.lower() or 'block' in c.lower()))
                        if parent_section:
                            # Remove the header text from the section text
                            section_text = parent_section.get_text(strip=True).replace(header.get_text(strip=True), '')
                            if section_text:
                                product_details_section = section_text
                                break
                        
                        # Try next sibling if parent approach didn't work
                        next_elem = header.find_next_sibling()
                        if next_elem and next_elem.name in ['p', 'div', 'span', 'ul']:
                            product_details_section = next_elem.get_text(strip=True)
                            break
                
                if product_details_section:
                    break
            
            # If no specific product details section was found, use the general product description
            if not product_details_section:
                description_elem = soup.select_one('.product-details__description')
                if description_elem:
                    product_details_section = description_elem.get_text(strip=True)
            
            product_data['product_details'] = product_details_section
            
            # Check if we got meaningful data
            if product_data['product_name'] or product_data['brand'] or product_data['ingredients']:
                return product_data
            else:
                print(f"Failed to extract meaningful data from {url}")
                retries += 1
                time.sleep(RETRY_DELAY)
        
        except Exception as e:
            print(f"Error scraping {url}: {str(e)}")
            retries += 1
            time.sleep(RETRY_DELAY)
    
    return product_data


def read_product_urls_from_boots_csv(csv_file='Boots_Skincare.csv'):
    """
    Read product URLs from Boots_Skincare.csv file with 'oct-link href 2' column.
    
    Args:
        csv_file (str): Path to the CSV file containing product URLs.
        
    Returns:
        list: A list of product URLs.
    """
    try:
        print(f"Reading CSV file: {csv_file}")
        # Check if file exists
        if not os.path.exists(csv_file):
            print(f"Error: File {csv_file} does not exist")
            return []
            
        # Print file size for debugging
        file_size = os.path.getsize(csv_file)
        print(f"File size: {file_size} bytes")
        
        # Try to read the first few lines of the file for debugging
        print("First few lines of the CSV file:")
        with open(csv_file, 'r', encoding='utf-8', errors='ignore') as f:
            for i, line in enumerate(f):
                if i < 3:  # Print first 3 lines
                    print(f"Line {i+1}: {line.strip()}")
                else:
                    break
        
        df = pd.read_csv(csv_file)
        
        # Print column names for debugging
        print(f"CSV columns: {', '.join(df.columns)}")
        
        # Check if 'oct-link href 2' column exists
        if 'oct-link href 2' in df.columns:
            print("Found 'oct-link href 2' column")
            # Extract URLs and remove duplicates
            product_urls = df['oct-link href 2'].dropna().unique().tolist()
            print(f"Extracted {len(product_urls)} unique URLs")
            # Print first few URLs for debugging
            for i, url in enumerate(product_urls[:3]):
                print(f"Sample URL {i+1}: {url}")
            return product_urls
        else:
            print(f"Error: 'oct-link href 2' column not found in {csv_file}")
            # Try alternative column names
            possible_columns = [col for col in df.columns if 'oct-link' in col.lower() and 'href' in col.lower()]
            if possible_columns:
                print(f"Found alternative columns: {possible_columns}")
                product_urls = df[possible_columns[0]].dropna().unique().tolist()
                print(f"Extracted {len(product_urls)} unique URLs from {possible_columns[0]}")
                return product_urls
            return []
    except Exception as e:
        print(f"Error reading {csv_file}: {e}")
        # Print traceback for debugging
        import traceback
        traceback.print_exc()
        return []


def save_to_csv(product_data_list, filename='cosmetics_database.csv'):
    """
    Save the product data to a CSV file.
    
    Args:
        product_data_list (list): List of product data dictionaries.
        filename (str): The name of the CSV file.
    """
    if not product_data_list:
        print("No data to save")
        return
    
    # Create a deep copy of the data to avoid modifying the original
    product_data_copy = []
    for product in product_data_list:
        product_copy = product.copy()
        # Convert ingredients_list to string if it exists
        if 'ingredients_list' in product_copy and product_copy['ingredients_list'] is not None:
            product_copy['ingredients_list'] = ', '.join(product_copy['ingredients_list'])
        product_data_copy.append(product_copy)
    
    df = pd.DataFrame(product_data_copy)
    df.to_csv(filename, index=False)
    print(f"Data saved to {filename} ({len(product_data_list)} products)")


def save_to_json(product_data_list, filename='cosmetics_database.json'):
    """
    Save the product data to a JSON file.
    
    Args:
        product_data_list (list): List of product data dictionaries.
        filename (str): The name of the JSON file.
    """
    if not product_data_list:
        print("No data to save")
        return
    
    # Convert to a serializable format
    serializable_data = []
    for product in product_data_list:
        # Create a copy to avoid modifying the original
        serializable_product = {k: v for k, v in product.items()}
        
        # Convert ingredients_list to strings if needed
        if 'ingredients_list' in serializable_product:
            serializable_product['ingredients_list'] = [str(ingredient) for ingredient in serializable_product.get('ingredients_list', [])]
        
        serializable_data.append(serializable_product)
    
    with open(filename, 'w') as f:
        json.dump(serializable_data, f, indent=4)
    print(f"Data also saved to {filename}")


def save_product_data(product_data_list, output_file):
    """
    Save product data to both CSV and JSON formats.
    
    Args:
        product_data_list (list): List of product data dictionaries.
        output_file (str): Base name for output files (without extension).
    """
    # Save to CSV
    save_to_csv(product_data_list, output_file)
    
    # Save to JSON
    json_file = output_file.replace('.csv', '') + '.json'
    with open(json_file, 'w') as f:
        json.dump(product_data_list, f, indent=2)
    
    print(f"Data saved to {output_file} ({len(product_data_list)} products)")
    print(f"Data also saved to {json_file}")


def save_progress(product_data_list, prefix="_progress"):
    """
    Save progress to both CSV and JSON files.
    
    Args:
        product_data_list (list): List of product data dictionaries.
        prefix (str): Prefix to add to filenames.
    """
    save_to_csv(product_data_list, f"cosmetics_database{prefix}.csv")
    save_to_json(product_data_list, f"cosmetics_database{prefix}.json")


def main():
    """Main function to orchestrate the scraping process."""
    print("Starting Boots.com cosmetics scraper")
    
    # Read product URLs from CSV file
    product_urls = read_product_urls_from_boots_csv()
    
    if not product_urls:
        print("No product URLs found. Exiting.")
        return
    
    print(f"Starting to scrape {len(product_urls)} products")
    
    # Create a directory for error logs if it doesn't exist
    error_dir = "error_logs"
    if not os.path.exists(error_dir):
        os.makedirs(error_dir)
    
    # Create a log file for failed URLs
    failed_urls_log = os.path.join(error_dir, f"failed_urls_{int(time.time())}.txt")
    redirects_log = os.path.join(error_dir, f"redirects_{int(time.time())}.txt")
    
    # Load progress if available
    progress_file = 'cosmetics_database_progress.json'
    all_product_data = []
    processed_urls = set()
    
    if os.path.exists(progress_file):
        try:
            with open(progress_file, 'r') as f:
                all_product_data = json.load(f)
                print(f"Loaded {len(all_product_data)} products from progress file")
                
                # Process existing data to add ingredients_list field if missing
                for product in all_product_data:
                    if 'ingredients' in product and product['ingredients'] and 'ingredients_list' not in product:
                        ingredients_text = product['ingredients']
                        # Clean up the text
                        ingredients_text = re.sub(r'ingredients:|\bingrédients:|\bingredients\b|:|\*|\+|\.', '', ingredients_text, flags=re.IGNORECASE)
                        # Split by commas and count non-empty items
                        ingredients_list = [ing.strip() for ing in ingredients_text.split(',') if ing.strip()]
                        product['ingredients_count'] = len(ingredients_list)
                        product['ingredients_list'] = ingredients_list
                
                # Track which URLs have already been processed
                processed_urls = {product['url'] for product in all_product_data if 'url' in product}
                
                # Create a backup of the progress file
                backup_file = f'cosmetics_database_progress_backup_{int(time.time())}.json'
                with open(backup_file, 'w') as backup_f:
                    json.dump(all_product_data, backup_f, indent=2)
                print(f"Created backup of progress file: {backup_file}")
        except Exception as e:
            print(f"Error loading progress file: {str(e)}")
            print("Starting from scratch")
            all_product_data = []
            processed_urls = set()
    
    # Filter out already processed URLs
    remaining_urls = [url for url in product_urls if url not in processed_urls]
    print(f"Remaining URLs to scrape: {len(remaining_urls)}")
    
    # Track failed URLs for retry
    failed_urls = []
    redirect_urls = []
    
    # Scrape products using ThreadPoolExecutor for concurrency
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        # Submit scraping tasks
        future_to_url = {
            executor.submit(scrape_boots_product, url, i+1, len(remaining_urls)): url 
            for i, url in enumerate(remaining_urls)
        }
        
        # Process completed tasks
        for i, future in enumerate(as_completed(future_to_url)):
            url = future_to_url[future]
            try:
                product_data = future.result()
                
                # Check if we got meaningful data
                if product_data and (product_data.get('product_name') or product_data.get('brand') or product_data.get('ingredients')):
                    all_product_data.append(product_data)
                else:
                    # Check if this is a redirect URL
                    if "webapp/wcs/stores/servlet/ProductDisplay" in url:
                        redirect_urls.append(url)
                        with open(redirects_log, 'a') as f:
                            f.write(f"{url}\n")
                    else:
                        failed_urls.append(url)
                        with open(failed_urls_log, 'a') as f:
                            f.write(f"{url}\n")
                
                # Save progress at regular intervals
                if (i + 1) % SAVE_INTERVAL == 0:
                    save_product_data(all_product_data, 'cosmetics_database_progress.csv')
                    print(f"Progress: {i+1}/{len(remaining_urls)} URLs processed, {len(all_product_data)} successful")
                
                # Check for rate limiting
                if i > 0 and i % 100 == 0:
                    print(f"Processed {i} URLs. Pausing briefly to avoid rate limiting...")
                    time.sleep(RATE_LIMIT_PAUSE / 3)  # Shorter pause for regular intervals
                
            except Exception as e:
                print(f"Error processing result for {url}: {str(e)}")
                failed_urls.append(url)
                with open(failed_urls_log, 'a') as f:
                    f.write(f"{url} - Error: {str(e)}\n")
    
    # Save final results
    save_product_data(all_product_data, 'cosmetics_database.csv')
    
    # Save to JSON as well
    with open('cosmetics_database.json', 'w') as f:
        json.dump(all_product_data, f, indent=2)
    
    print(f"\nFinished scraping. Successfully scraped {len(all_product_data)} products.")
    print(f"Failed URLs: {len(failed_urls)}")
    print(f"Redirect URLs: {len(redirect_urls)}")
    
    # Generate summary of the data
    generate_data_summary(all_product_data)
    
    # If there are failed URLs, try to retry them with a different approach
    if failed_urls or redirect_urls:
        print("\nAttempting to retry failed URLs with alternative approach...")
        retry_failed_urls(failed_urls, redirect_urls, all_product_data)


def generate_data_summary(product_data_list):
    """
    Generate a summary of the scraped data.
    
    Args:
        product_data_list (list): List of product data dictionaries.
    """
    if not product_data_list:
        print("No data to summarize")
        return
    
    total_products = len(product_data_list)
    
    # Count products with each field
    fields_count = {
        'product_name': 0,
        'brand': 0,
        'ingredients': 0,
        'hazards_and_cautions': 0,
        'product_details': 0,
        'country_of_origin': 0,
        'how_to_use': 0
    }
    
    # Count unique brands
    brands = set()
    
    # Count products with ingredients
    products_with_ingredients = 0
    total_ingredients = 0
    
    for product in product_data_list:
        for field in fields_count:
            if product.get(field):
                fields_count[field] += 1
        
        if product.get('brand'):
            brands.add(product['brand'])
        
        # Fixed bug: Safely handle ingredients_count which might be None
        ingredients_count = product.get('ingredients_count')
        if ingredients_count and isinstance(ingredients_count, (int, float)) and ingredients_count > 0:
            products_with_ingredients += 1
            total_ingredients += ingredients_count
    
    # Calculate average ingredients per product
    avg_ingredients = total_ingredients / products_with_ingredients if products_with_ingredients > 0 else 0
    
    # Print summary
    print("\n" + "="*50)
    print("DATA SUMMARY")
    print("="*50)
    print(f"Total products scraped: {total_products}")
    print(f"Unique brands: {len(brands)}")
    print("\nField coverage:")
    for field, count in fields_count.items():
        percentage = (count / total_products) * 100
        print(f"  {field}: {count} ({percentage:.1f}%)")
    
    print(f"\nProducts with ingredients: {products_with_ingredients} ({(products_with_ingredients / total_products) * 100:.1f}%)")
    print(f"Average ingredients per product: {avg_ingredients:.1f}")
    print("="*50)
    
    # Save summary to file
    with open('data_summary.txt', 'w') as f:
        f.write("DATA SUMMARY\n")
        f.write(f"Total products scraped: {total_products}\n")
        f.write(f"Unique brands: {len(brands)}\n\n")
        f.write("Field coverage:\n")
        for field, count in fields_count.items():
            percentage = (count / total_products) * 100
            f.write(f"  {field}: {count} ({percentage:.1f}%)\n")
        
        f.write(f"\nProducts with ingredients: {products_with_ingredients} ({(products_with_ingredients / total_products) * 100:.1f}%)\n")
        f.write(f"Average ingredients per product: {avg_ingredients:.1f}\n")
    
    print("Summary saved to data_summary.txt")


def retry_failed_urls(failed_urls, redirect_urls, all_product_data):
    """
    Retry failed URLs with an alternative approach.
    
    Args:
        failed_urls (list): List of URLs that failed to scrape.
        redirect_urls (list): List of redirect URLs that failed to scrape.
        all_product_data (list): List of all product data scraped so far.
    """
    # Combine all URLs that need to be retried
    urls_to_retry = failed_urls + redirect_urls
    
    if not urls_to_retry:
        return
    
    print(f"Retrying {len(urls_to_retry)} failed URLs with alternative approach")
    
    # Use a more aggressive approach for retries
    successful_retries = 0
    
    for i, url in enumerate(urls_to_retry):
        print(f"[Retry {i+1}/{len(urls_to_retry)}] {url}")
        
        try:
            # Use a longer timeout and different user agent for retries
            headers = {
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/15.4 Safari/605.1.15',
                'Accept-Language': 'en-US,en;q=0.9',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Referer': 'https://www.boots.com/beauty',
                'Connection': 'keep-alive',
                'Cache-Control': 'no-cache',
                'Pragma': 'no-cache'
            }
            
            # Add a longer delay for retries
            time.sleep(random.uniform(MAX_DELAY, MAX_DELAY * 2))
            
            # Handle redirects manually for redirect URLs
            if "webapp/wcs/stores/servlet/ProductDisplay" in url:
                # Extract product ID from query parameters
                parsed_url = urlparse(url)
                query_params = parse_qs(parsed_url.query)
                
                if 'productId' in query_params:
                    product_id = query_params['productId'][0]
                    # Construct a direct URL using the product ID
                    direct_url = f"https://www.boots.com/product/{product_id}"
                    print(f"  Trying direct URL: {direct_url}")
                    
                    response = requests.get(direct_url, headers=headers, timeout=45, allow_redirects=True)
                    
                    # If redirected, use the final URL
                    if response.history:
                        url = response.url
                        print(f"  Redirected to: {url}")
            
            # Try to scrape with a longer timeout
            product_data = scrape_with_extended_timeout(url, headers)
            
            if product_data and (product_data.get('product_name') or product_data.get('brand') or product_data.get('ingredients')):
                all_product_data.append(product_data)
                successful_retries += 1
                print(f"  Successfully scraped on retry!")
            else:
                print(f"  Failed to extract data on retry")
        
        except Exception as e:
            print(f"  Error during retry: {str(e)}")
        
        # Add a pause every few retries to avoid rate limiting
        if (i + 1) % 5 == 0:
            print(f"Pausing briefly to avoid rate limiting...")
            time.sleep(RATE_LIMIT_PAUSE / 2)
    
    print(f"\nRetry complete. Successfully recovered {successful_retries} out of {len(urls_to_retry)} failed URLs.")
    
    # Save the updated data
    save_to_csv(all_product_data, 'cosmetics_database_with_retries.csv')
    
    with open('cosmetics_database_with_retries.json', 'w') as f:
        json.dump(all_product_data, f, indent=2)
    
    # Generate updated summary
    generate_data_summary(all_product_data)


def scrape_with_extended_timeout(url, headers):
    """
    Scrape a product with extended timeout and more aggressive error handling.
    
    Args:
        url (str): URL of the product page.
        headers (dict): HTTP headers to use.
        
    Returns:
        dict: Dictionary containing product information.
    """
    product_data = {
        'url': url,
        'product_name': None,
        'brand': None,
        'ingredients': None,
        'ingredients_count': None,
        'country_of_origin': None,
        'hazards_and_cautions': None,
        'how_to_use': None,
        'product_details': None,
        'scrape_timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    }
    
    try:
        # Use a longer timeout for problematic URLs
        response = requests.get(url, headers=headers, timeout=45)
        
        # Check if the request was successful
        if response.status_code != 200:
            print(f"  Failed to fetch {url}. Status code: {response.status_code}")
            return product_data
        
        # Parse the HTML content
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Try multiple approaches to extract data
        
        # 1. Extract product name with multiple selectors
        product_name_selectors = [
            'h1.product-details-tile__title',
            'h1.product-title',
            'h1.product-name',
            'h1.product__title',
            'title'  # Fallback to page title
        ]
        
        for selector in product_name_selectors:
            product_name_elem = soup.select_one(selector)
            if product_name_elem:
                product_name = product_name_elem.text.strip()
                # Clean up title if using page title
                if selector == 'title':
                    product_name = re.sub(r'\s*\|\s*Boots.*$', '', product_name)
                product_data['product_name'] = product_name
                break
        
        # 2. Extract brand with multiple selectors
        brand_selectors = [
            'a.product-details-tile__brand',
            '.product-brand',
            '.brand-name',
            '.product-info__brand'
        ]
        
        for selector in brand_selectors:
            brand_elem = soup.select_one(selector)
            if brand_elem:
                product_data['brand'] = brand_elem.text.strip()
                break
        
        # If brand not found, try to extract from product name
        if not product_data['brand'] and product_data['product_name']:
            # Common pattern: Brand - Product Name
            brand_match = re.match(r'^([^-]+)\s*-\s*.+', product_data['product_name'])
            if brand_match:
                product_data['brand'] = brand_match.group(1).strip()
            elif 'boots' in product_data['product_name'].lower():
                product_data['brand'] = 'Boots'
        
        # 3. Extract ingredients with our enhanced function
        product_data['ingredients'] = extract_ingredients(soup)
        
        if product_data['ingredients']:
            # Count the number of ingredients
            ingredients_text = product_data['ingredients']
            ingredients_text = re.sub(r'ingredients:|\bingrédients:|\bingredients\b|:|\*|\+|\.', '', ingredients_text, flags=re.IGNORECASE)
            ingredients_list = [ing.strip() for ing in ingredients_text.split(',') if ing.strip()]
            product_data['ingredients_count'] = len(ingredients_list)
            product_data['ingredients_list'] = ingredients_list
        
        # 4. Extract other fields using the same approach as in scrape_boots_product
        # (This would be the same code as in the main scrape_boots_product function)
        
        return product_data
        
    except Exception as e:
        print(f"  Error in extended scraping: {str(e)}")
        return product_data


if __name__ == "__main__":
    main()
