#!/usr/bin/env python3
"""
Boots Advanced Scraper

A comprehensive scraper for Boots.com skincare products that extracts detailed product information
for a cosmetics database. Features include:
- Navigation through site structure starting from /beauty/skincare
- Extraction of product details, ingredients, and specifications
- Headers rotation and user-agent spoofing
- Random delays between requests
- Error handling with exponential backoff retries
- Session management with cookies handling
- Respect for robots.txt
- Proxy rotation capability
- Ingredient parsing and standardization
"""

import os
import re
import json
import time
import random
import logging
import argparse
import asyncio
import urllib.robotparser
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse, urljoin
from datetime import datetime
from typing import Dict, List, Set, Any, Optional, Union

import pandas as pd
from bs4 import BeautifulSoup
from playwright.async_api import async_playwright, Browser, Page, Playwright, TimeoutError as PlaywrightTimeoutError, Response

# Ingredient standardization constants
INGREDIENT_STANDARDIZATION = {
    # Common ingredient name variations
    "aqua": "Water",
    "water": "Water",
    "glycerin": "Glycerin",
    "glycerine": "Glycerin",
    "sodium chloride": "Sodium Chloride",
    "salt": "Sodium Chloride",
    "tocopherol": "Vitamin E",
    "tocopheryl acetate": "Vitamin E Acetate",
    "retinol": "Vitamin A",
    "retinyl palmitate": "Vitamin A Palmitate",
    "ascorbic acid": "Vitamin C",
    "sodium ascorbyl phosphate": "Vitamin C Derivative",
    "niacinamide": "Vitamin B3",
    "panthenol": "Provitamin B5",
    "sodium hyaluronate": "Hyaluronic Acid",
    "hyaluronic acid": "Hyaluronic Acid",
    "aloe barbadensis leaf juice": "Aloe Vera",
    "aloe vera": "Aloe Vera",
    "butyrospermum parkii butter": "Shea Butter",
    "shea butter": "Shea Butter",
    "cocos nucifera oil": "Coconut Oil",
    "coconut oil": "Coconut Oil",
    "simmondsia chinensis seed oil": "Jojoba Oil",
    "jojoba oil": "Jojoba Oil",
    "rosa canina fruit oil": "Rosehip Oil",
    "rosehip oil": "Rosehip Oil",
    "argania spinosa kernel oil": "Argan Oil",
    "argan oil": "Argan Oil",
    "sodium laureth sulfate": "Sodium Laureth Sulfate (SLES)",
    "sodium lauryl sulfate": "Sodium Lauryl Sulfate (SLS)",
    "parfum": "Fragrance",
    "fragrance": "Fragrance",
    "ci": "Color Index",
}

# Common ingredient prefixes
INGREDIENT_PREFIXES = [
    "sodium",
    "potassium",
    "magnesium",
    "calcium",
    "zinc",
    "iron",
    "copper",
    "manganese",
    "aluminum",
    "titanium",
    "silica",
    "hydrogenated",
    "hydrolyzed",
    "polyethylene",
    "polysorbate",
    "peg",
    "ppg",
    "cetyl",
    "cetearyl",
    "stearyl",
    "lauryl",
    "myristyl",
    "caprylic",
    "glyceryl",
]

# Common ingredient suffixes
INGREDIENT_SUFFIXES = [
    "extract",
    "oil",
    "butter",
    "wax",
    "acid",
    "alcohol",
    "glucoside",
    "glycol",
    "sulfate",
    "phosphate",
    "stearate",
    "palmitate",
    "benzoate",
    "salicylate",
    "caprylate",
    "sorbate",
    "glycinate",
    "citrate",
]

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("boots_scraper.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Base URLs
BASE_URL = "https://www.boots.com"
SKINCARE_BASE_URL = "https://www.boots.com/beauty/skincare"

# User agents for rotation
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.1 Safari/605.1.15",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:89.0) Gecko/20100101 Firefox/89.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.114 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.114 Safari/537.36",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 14_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0 Mobile/15E148 Safari/604.1",
    "Mozilla/5.0 (iPad; CPU OS 14_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0 Mobile/15E148 Safari/604.1",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36 Edg/91.0.864.59"
]

# List of proxies (replace with your actual proxies)
PROXIES = [
    # Format: "http://username:password@ip:port"
    # Example: "http://user:pass@123.45.67.89:8080"
]

class RobotsChecker:
    """Class to check if URLs are allowed by robots.txt"""
    
    def __init__(self, base_url: str):
        """
        Initialize the robots checker.
        
        Args:
            base_url: Base URL of the website
        """
        self.parser = urllib.robotparser.RobotFileParser()
        robots_url = urljoin(base_url, "/robots.txt")
        self.parser.set_url(robots_url)
        
        try:
            self.parser.read()
            logger.info(f"Read robots.txt from {robots_url}")
        except Exception as e:
            logger.warning(f"Error reading robots.txt: {str(e)}")
    
    def is_allowed(self, url: str, user_agent: str = "*") -> bool:
        """
        Check if a URL is allowed by robots.txt.
        
        Args:
            url: URL to check
            user_agent: User agent to check for
            
        Returns:
            True if the URL is allowed, False otherwise
        """
        try:
            return self.parser.can_fetch(user_agent, url)
        except Exception as e:
            logger.warning(f"Error checking robots.txt for {url}: {str(e)}")
            # If there's an error, assume it's allowed
            return True

class BootsScraper:
    """Main scraper class for Boots.com skincare products"""
    
    def __init__(self, 
                 headless: bool = True, 
                 use_proxies: bool = False,
                 respect_robots: bool = True,
                 max_retries: int = 3,
                 min_delay: float = 2.0,
                 max_delay: float = 10.0,
                 screenshot_dir: str = "screenshots",
                 data_dir: str = "data",
                 cache_dir: str = "cache"):
        """
        Initialize the Boots scraper.
        
        Args:
            headless: Whether to run the browser in headless mode
            use_proxies: Whether to use proxy rotation
            respect_robots: Whether to respect robots.txt
            max_retries: Maximum number of retries for failed requests
            min_delay: Minimum delay between requests in seconds
            max_delay: Maximum delay between requests in seconds
            screenshot_dir: Directory to save screenshots
            data_dir: Directory to save data
            cache_dir: Directory to cache responses
        """
        self.headless = headless
        self.use_proxies = use_proxies
        self.respect_robots = respect_robots
        self.max_retries = max_retries
        self.min_delay = min_delay
        self.max_delay = max_delay
        self.screenshot_dir = screenshot_dir
        self.data_dir = data_dir
        self.cache_dir = cache_dir
        
        self.browser = None
        self.context = None
        self.page = None
        self.robots_checker = RobotsChecker(BASE_URL) if respect_robots else None
        self.current_user_agent = random.choice(USER_AGENTS)
        self.current_proxy = None if not use_proxies else random.choice(PROXIES) if PROXIES else None
        
        # Track visited URLs to avoid duplicates
        self.visited_urls = set()
        self.product_urls = set()
        self.category_urls = set()
        
        # Track scraped data
        self.products_data = []
        self.ingredients_data = []
        
        # Statistics
        self.stats = {
            "pages_visited": 0,
            "products_found": 0,
            "products_scraped": 0,
            "errors": 0,
            "retries": 0,
            "start_time": None,
            "end_time": None,
            "requests_made": 0
        }
    
    async def setup_browser(self) -> None:
        """Set up the Playwright browser with appropriate settings."""
        playwright = await async_playwright().start()
        
        # Browser launch options
        browser_options = {
            "headless": self.headless
        }
        
        # Add proxy if enabled and available
        if self.use_proxies and self.current_proxy:
            browser_options["proxy"] = {
                "server": self.current_proxy
            }
        
        self.browser = await playwright.chromium.launch(**browser_options)
        
        # Context options with user agent
        context_options = {
            "viewport": {"width": 1280, "height": 800},
            "user_agent": self.current_user_agent
        }
        
        self.context = await self.browser.new_context(**context_options)
        self.page = await self.context.new_page()
        
        # Set default timeout
        self.page.set_default_timeout(30000)
        
        # Set up event listeners
        self.page.on("response", self._handle_response)
        
        logger.info(f"Browser set up with user agent: {self.current_user_agent}")
        if self.current_proxy:
            logger.info(f"Using proxy: {self.current_proxy}")
    
    async def _handle_response(self, response: Response) -> None:
        """Handle response events for caching and analysis."""
        if response.status >= 400:
            logger.warning(f"Received error status {response.status} for URL: {response.url}")
        else:
            logger.debug(f"Received status {response.status} for URL: {response.url}")
        
        # Update statistics
        self.stats["requests_made"] += 1
        if response.status >= 400:
            self.stats["errors"] += 1
        
        # Cache successful responses for product pages
        if response.status == 200 and "/beauty/skincare/" in response.url and response.request.method == "GET":
            try:
                # Only cache text responses (HTML, JSON, etc.)
                content_type = response.headers.get("content-type", "")
                if "text/html" in content_type or "application/json" in content_type:
                    url_hash = hash(response.url)
                    cache_path = os.path.join(self.cache_dir, f"{url_hash}.html")
                    
                    # Save response to cache
                    with open(cache_path, "wb") as f:
                        f.write(await response.body())
                    
                    logger.debug(f"Cached response for URL: {response.url}")
            except Exception as e:
                logger.error(f"Error caching response: {str(e)}")
    
    async def rotate_user_agent(self) -> None:
        """Rotate the user agent for the next request."""
        previous_agent = self.current_user_agent
        
        # Ensure we get a different user agent
        while self.current_user_agent == previous_agent and len(USER_AGENTS) > 1:
            self.current_user_agent = random.choice(USER_AGENTS)
        
        # Update the browser context
        if self.context:
            await self.context.set_extra_http_headers({
                "User-Agent": self.current_user_agent
            })
            
        logger.debug(f"Rotated user agent to: {self.current_user_agent}")
    
    async def rotate_proxy(self) -> None:
        """Rotate the proxy for the next request."""
        if not self.use_proxies or not PROXIES:
            return
        
        previous_proxy = self.current_proxy
        
        # Ensure we get a different proxy
        while self.current_proxy == previous_proxy and len(PROXIES) > 1:
            self.current_proxy = random.choice(PROXIES)
        
        # We need to recreate the browser context for proxy changes
        if self.browser:
            if self.context:
                await self.context.close()
            
            context_options = {
                "viewport": {"width": 1280, "height": 800},
                "user_agent": self.current_user_agent
            }
            
            if self.current_proxy:
                context_options["proxy"] = {
                    "server": self.current_proxy
                }
            
            self.context = await self.browser.new_context(**context_options)
            self.page = await self.context.new_page()
            
            # Set default timeout
            self.page.set_default_timeout(30000)
            
            # Set up event listeners
            self.page.on("response", self._handle_response)
            
            logger.debug(f"Rotated proxy to: {self.current_proxy}")
    
    async def navigate_with_retry(self, url: str, max_retries: int = None) -> Optional[bool]:
        """
        Navigate to a URL with retry logic and exponential backoff.
        
        Args:
            url: The URL to navigate to
            max_retries: Maximum number of retries, defaults to self.max_retries
            
        Returns:
            True if navigation was successful, None otherwise
        """
        if max_retries is None:
            max_retries = self.max_retries
        
        # Check if URL is allowed by robots.txt
        if self.respect_robots and self.robots_checker and not self.robots_checker.is_allowed(url):
            logger.warning(f"URL not allowed by robots.txt: {url}")
            return None
        
        # Add random delay between requests
        delay = random.uniform(self.min_delay, self.max_delay)
        logger.info(f"Waiting {delay:.2f} seconds before request...")
        await asyncio.sleep(delay)
        
        # Try to navigate with retries
        for attempt in range(max_retries + 1):
            try:
                # Rotate user agent and proxy occasionally
                if random.random() < 0.3:  # 30% chance to rotate
                    await self.rotate_user_agent()
                
                if self.use_proxies and random.random() < 0.2:  # 20% chance to rotate
                    await self.rotate_proxy()
                
                # Navigate to the URL
                response = await self.page.goto(
                    url, 
                    wait_until="domcontentloaded", 
                    timeout=60000
                )
                
                # Handle cookies if needed
                await self._handle_cookies()
                
                # Wait for network to be relatively idle
                await self.page.wait_for_load_state("networkidle", timeout=10000)
                
                # Update statistics
                self.stats["pages_visited"] += 1
                self.visited_urls.add(url)
                
                # Take a screenshot if needed
                url_hash = hash(url)
                screenshot_path = os.path.join(self.screenshot_dir, f"{url_hash}.png")
                await self.page.screenshot(path=screenshot_path)
                
                return True
                
            except Exception as e:
                self.stats["errors"] += 1
                
                if attempt < max_retries:
                    self.stats["retries"] += 1
                    backoff_time = 2 ** attempt * random.uniform(1, 3)
                    logger.warning(f"Error navigating to {url}: {str(e)}. Retrying in {backoff_time:.2f} seconds (attempt {attempt + 1}/{max_retries})")
                    await asyncio.sleep(backoff_time)
                else:
                    logger.error(f"Failed to navigate to {url} after {max_retries} retries: {str(e)}")
                    return None
    
    async def _handle_cookies(self) -> None:
        """Handle cookie consent banners on the page."""
        try:
            # Try different selectors for cookie banners
            cookie_selectors = [
                'button:has-text("Accept All Cookies")', 
                '.cookie-banner__button', 
                '#onetrust-accept-btn-handler',
                '[aria-label="Accept cookies"]',
                '[data-testid="cookie-accept-all"]'
            ]
            
            for selector in cookie_selectors:
                try:
                    # Try to find buttons or tabs with this text
                    cookie_button = await self.page.query_selector(selector)
                    if cookie_button:
                        await cookie_button.click()
                        logger.info("Accepted cookies")
                        await self.page.wait_for_timeout(1000)  # Wait for banner to disappear
                        return
                except Exception:
                    continue
        except Exception as e:
            logger.warning(f"Error handling cookie banner: {str(e)}")

    async def find_category_urls(self) -> Set[str]:
        """
        Find skincare category URLs from the Boots website.
        
        Returns:
            Set of category URLs
        """
        logger.info("Finding category URLs")
        
        # Start with the base skincare URL
        skincare_url = urljoin(BASE_URL, "/beauty/skincare")
        
        # Navigate to the skincare page
        success = await self.navigate_with_retry(skincare_url)
        if not success:
            logger.error(f"Failed to navigate to {skincare_url}")
            return set()
        
        # Wait for the page to load
        await self.page.wait_for_load_state("networkidle")
        
        # Get the page content
        content = await self.page.content()
        soup = BeautifulSoup(content, 'html.parser')
        
        # Find category links
        category_urls = set()
        
        # Look for category links in the navigation menu
        category_selectors = [
            'a[href*="/beauty/skincare/"]',
            '.category-navigation a[href*="/beauty/skincare/"]',
            '.nav-menu a[href*="/beauty/skincare/"]',
            '.menu a[href*="/beauty/skincare/"]'
        ]
        
        for selector in category_selectors:
            links = soup.select(selector)
            for link in links:
                href = link.get('href')
                if href and '/beauty/skincare/' in href and not href.endswith('/beauty/skincare/'):
                    # Make sure it's an absolute URL
                    if href.startswith('/'):
                        href = urljoin(BASE_URL, href)
                    
                    # Check if the URL is allowed by robots.txt
                    if self.robots_checker and not self.robots_checker.is_allowed(href):
                        logger.info(f"Skipping disallowed URL: {href}")
                        continue
                    
                    category_urls.add(href)
                    logger.debug(f"Found category URL: {href}")
        
        # If we didn't find any category URLs, try a different approach
        if not category_urls:
            # Try to find links with specific patterns
            all_links = soup.find_all('a', href=True)
            for link in all_links:
                href = link.get('href')
                if href and '/beauty/skincare/' in href and not href.endswith('/beauty/skincare/'):
                    # Make sure it's an absolute URL
                    if href.startswith('/'):
                        href = urljoin(BASE_URL, href)
                    
                    # Check if the URL is allowed by robots.txt
                    if self.robots_checker and not self.robots_checker.is_allowed(href):
                        logger.info(f"Skipping disallowed URL: {href}")
                        continue
                    
                    category_urls.add(href)
                    logger.debug(f"Found category URL: {href}")
        
        # Add the main skincare categories if we still don't have any
        if not category_urls:
            default_categories = [
                "/beauty/skincare/cleanse-and-tone",
                "/beauty/skincare/moisturisers",
                "/beauty/skincare/serums-and-oils",
                "/beauty/skincare/eye-care",
                "/beauty/skincare/face-masks",
                "/beauty/skincare/lip-care"
            ]
            
            for category in default_categories:
                url = urljoin(BASE_URL, category)
                
                # Check if the URL is allowed by robots.txt
                if self.robots_checker and not self.robots_checker.is_allowed(url):
                    logger.info(f"Skipping disallowed URL: {url}")
                    continue
                
                category_urls.add(url)
                logger.debug(f"Added default category URL: {url}")
        
        # Update statistics
        self.stats["categories_found"] = len(category_urls)
        self.category_urls.update(category_urls)
        
        logger.info(f"Found {len(category_urls)} category URLs")
        return category_urls
    
    async def find_product_urls(self, category_url: str, max_products: int = None) -> Set[str]:
        """
        Find product URLs from a category page.
        
        Args:
            category_url: The category page URL
            max_products: Maximum number of products to find
            
        Returns:
            Set of product URLs
        """
        logger.info(f"Finding product URLs from category: {category_url}")
        
        # Navigate to the category page
        response = await self.navigate_with_retry(category_url)
        if not response:
            logger.error(f"Failed to navigate to {category_url}")
            return set()
        
        # Scroll down to load more products
        logger.info("Scrolling to load more products...")
        for _ in range(5):  # Scroll a few times to load more products
            await self.page.evaluate('window.scrollBy(0, 800)')
            await self.page.wait_for_timeout(1000)  # Wait for content to load
        
        # Get the page content
        content = await self.page.content()
        soup = BeautifulSoup(content, 'html.parser')
        
        # Find product URLs
        product_urls = set()
        
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
                        href = urljoin(BASE_URL, href)
                    
                    # Check if it looks like a product URL (not a category)
                    if self.is_product_url(href):
                        product_urls.add(href)
                        logger.debug(f"Found product URL from card: {href}")
                        
                        if max_products and len(product_urls) >= max_products:
                            break
        
        # If we didn't find enough products from cards, look for all links
        if not max_products or len(product_urls) < max_products:
            logger.info("Looking for product links in all page links...")
            links = soup.find_all('a', href=True)
            
            for link in links:
                href = link.get('href')
                if href:
                    # Ensure it's an absolute URL
                    if href.startswith('/'):
                        href = urljoin(BASE_URL, href)
                    
                    # Check if it looks like a product URL
                    if self.is_product_url(href) and href not in product_urls:
                        product_urls.add(href)
                        logger.debug(f"Found product URL: {href}")
                        
                        if max_products and len(product_urls) >= max_products:
                            break
        
        # Update the set of product URLs
        self.product_urls.update(product_urls)
        self.stats["products_found"] += len(product_urls)
        
        logger.info(f"Found {len(product_urls)} product URLs from category: {category_url}")
        return product_urls
    
    def is_product_url(self, url: str) -> bool:
        """
        Check if a URL is a product URL.
        
        Args:
            url: URL to check
            
        Returns:
            True if it's a product URL, False otherwise
        """
        # Parse the URL
        parsed_url = urlparse(url)
        
        # Check the path pattern
        path = parsed_url.path
        
        # Product URLs typically end with a product code (numeric)
        if re.search(r'/\d+$', path):
            return True
        
        # Product URLs often have a specific format with product name and code
        if re.search(r'/[a-z0-9-]+-\d+$', path):
            return True
        
        # Check for common product URL patterns
        product_patterns = [
            r'/beauty/skincare/[^/]+/[^/]+$',  # /beauty/skincare/category/product
            r'/[^/]+/[^/]+/\d+$',              # /brand/product/code
            r'/product/[^/]+$',                # /product/name
        ]
        
        for pattern in product_patterns:
            if re.search(pattern, path):
                return True
        
        return False
    
    async def scrape_product(self, url: str) -> Dict[str, Any]:
        """
        Scrape detailed product information from a product page.
        
        Args:
            url: The product page URL
            
        Returns:
            Dictionary containing the scraped product information
        """
        logger.info(f"Scraping product: {url}")
        
        # Initialize product data
        product_data = {
            "product_url": url,
            "product_id": self._extract_product_id(url),
            "product_name": "",
            "brand": "",
            "price": None,
            "original_price": None,
            "discount": None,
            "rating": None,
            "review_count": None,
            "product_details": "",
            "ingredients": "",
            "ingredients_list": [],
            "key_ingredients": [],
            "how_to_use": "",
            "hazards_and_cautions": "",
            "country_of_origin": "",
            "specifications": {},
            "scrape_date": datetime.now().isoformat()
        }
        
        # Navigate to the product page
        max_attempts = 3
        for attempt in range(max_attempts):
            try:
                success = await self.navigate_with_retry(url)
                if not success:
                    logger.error(f"Failed to navigate to {url} after multiple retries")
                    return product_data
                
                # Wait for the page to load
                await self.page.wait_for_load_state("networkidle", timeout=30000)
                
                # Handle cookie consent
                await self.handle_cookie_consent()
                
                # Get the page content
                content = await self.page.content()
                soup = BeautifulSoup(content, 'html.parser')
                
                # Extract product information
                break  # If we get here, the navigation was successful
            except Exception as e:
                logger.error(f"Error navigating to product page (attempt {attempt+1}/{max_attempts}): {str(e)}")
                if attempt == max_attempts - 1:
                    # This was the last attempt
                    logger.error(f"Failed to scrape product after {max_attempts} attempts: {url}")
                    return product_data
                else:
                    # Wait before retrying
                    await asyncio.sleep(5)
        
        try:
            # Extract product name
            product_name_selectors = [
                'h1.product-title',
                'h1.product-name',
                'h1.product__title',
                '.product-title h1',
                '.product-name h1',
                '.product__title h1',
                'h1[data-test="product-title"]',
                'h1.page-title'
            ]
            
            for selector in product_name_selectors:
                product_name_element = soup.select_one(selector)
                if product_name_element:
                    product_data['product_name'] = product_name_element.text.strip()
                    logger.info(f"Found product name: {product_data['product_name']}")
                    break
            
            # If product name still not found, try a more general approach
            if not product_data['product_name']:
                h1_elements = soup.find_all('h1')
                for h1 in h1_elements:
                    if h1.text.strip() and len(h1.text.strip()) > 5:  # Reasonable product name length
                        product_data['product_name'] = h1.text.strip()
                        logger.info(f"Found product name from h1: {product_data['product_name']}")
                        break
        except Exception as e:
            logger.error(f"Error extracting product name: {str(e)}")
        
        try:
            # Extract brand
            brand_selectors = [
                '.product-brand',
                '.brand-name',
                '.product__brand',
                '[data-test="product-brand"]',
                '.brand'
            ]
            
            for selector in brand_selectors:
                brand_element = soup.select_one(selector)
                if brand_element:
                    product_data['brand'] = brand_element.text.strip()
                    logger.info(f"Found brand: {product_data['brand']}")
                    break
            
            # If brand still not found, try to extract it from the product name
            if not product_data['brand'] and product_data['product_name']:
                # Many product names start with the brand name
                potential_brand = product_data['product_name'].split(' ')[0]
                if len(potential_brand) > 2:  # Reasonable brand name length
                    product_data['brand'] = potential_brand
                    logger.info(f"Extracted brand from product name: {product_data['brand']}")
        except Exception as e:
            logger.error(f"Error extracting brand: {str(e)}")
        
        try:
            # Extract price
            price_selectors = [
                '.product-price',
                '.price',
                '.product__price',
                '[data-test="product-price"]',
                '.product-info__price',
                '.current-price'
            ]
            
            for selector in price_selectors:
                price_element = soup.select_one(selector)
                if price_element:
                    price_text = price_element.text.strip()
                    # Extract the price using regex
                    price_match = re.search(r'£(\d+\.\d+)', price_text)
                    if price_match:
                        product_data['price'] = float(price_match.group(1))
                        logger.info(f"Found price: {product_data['price']}")
                    break
        except Exception as e:
            logger.error(f"Error extracting price: {str(e)}")
        
        try:
            # Extract original price and discount
            original_price_selectors = [
                '.original-price',
                '.was-price',
                '.product-price__was',
                '[data-test="product-original-price"]'
            ]
            
            for selector in original_price_selectors:
                original_price_element = soup.select_one(selector)
                if original_price_element:
                    original_price_text = original_price_element.text.strip()
                    # Extract the original price using regex
                    original_price_match = re.search(r'£(\d+\.\d+)', original_price_text)
                    if original_price_match:
                        product_data['original_price'] = float(original_price_match.group(1))
                        logger.info(f"Found original price: {product_data['original_price']}")
                        
                        # Calculate discount if both prices are available
                        if product_data['price'] and product_data['original_price']:
                            product_data['discount'] = round((1 - product_data['price'] / product_data['original_price']) * 100, 2)
                            logger.info(f"Calculated discount: {product_data['discount']}%")
                        
                        break
        except Exception as e:
            logger.error(f"Error extracting original price and discount: {str(e)}")
        
        try:
            # Extract rating and review count
            rating_selectors = [
                '.product-rating',
                '.rating',
                '.product__rating',
                '[data-test="product-rating"]',
                '.star-rating'
            ]
            
            for selector in rating_selectors:
                rating_element = soup.select_one(selector)
                if rating_element:
                    # Try to find the rating value
                    rating_value = rating_element.get('data-rating') or rating_element.get('data-value')
                    if rating_value:
                        try:
                            product_data['rating'] = float(rating_value)
                            logger.info(f"Found rating: {product_data['rating']}")
                        except ValueError:
                            pass
                    
                    # Try to find the review count
                    review_count_element = soup.select_one('.review-count, .rating-count, [data-test="review-count"]')
                    if review_count_element:
                        review_count_text = review_count_element.text.strip()
                        review_count_match = re.search(r'(\d+)', review_count_text)
                        if review_count_match:
                            product_data['review_count'] = int(review_count_match.group(1))
                            logger.info(f"Found review count: {product_data['review_count']}")
                    
                    break
        except Exception as e:
            logger.error(f"Error extracting rating and review count: {str(e)}")
        
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
            
            # Extract specifications from product details
            if product_data['product_details']:
                product_data['specifications'] = self.extract_specifications(product_data['product_details'])
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
        
        # Clean the product data
        product_data = self.clean_product_data(product_data)
        
        # Check if we successfully extracted the product name
        if product_data['product_name']:
            logger.info(f"Successfully scraped: {product_data['product_name']}")
        else:
            logger.warning(f"Failed to extract meaningful data from {url}")
        
        # Add the product data to the list
        self.products_data.append(product_data)
        
        return product_data
    
    def _extract_product_id(self, url: str) -> str:
        """
        Extract product ID from URL.
        
        Args:
            url: Product URL
            
        Returns:
            Product ID or empty string if not found
        """
        # Try to extract product ID from the URL
        # Pattern 1: URLs ending with a number (e.g., /product-name-12345)
        pattern1 = r'(\d+)$'
        # Pattern 2: URLs with a product code in the middle (e.g., /product-name-12345-size)
        pattern2 = r'[-/](\d+)[-/]'
        # Pattern 3: URLs with a product code at the end (e.g., /product-name-12345)
        pattern3 = r'[-/](\d+)(?:[^0-9/]*)$'
        
        for pattern in [pattern1, pattern2, pattern3]:
            match = re.search(pattern, url)
            if match:
                return match.group(1)
        
        # If no pattern matches, return empty string
        return ""
    
    def parse_ingredients(self, ingredients_text: str) -> List[str]:
        """
        Parse ingredients text into a list of individual ingredients.
        
        Args:
            ingredients_text: Raw ingredients text
            
        Returns:
            List of individual ingredients
        """
        if not ingredients_text:
            return []
        
        # Clean the ingredients text
        cleaned_text = re.sub(r'Skip to .*?$', '', ingredients_text, flags=re.MULTILINE).strip()
        cleaned_text = re.sub(r'Ingredients:', '', cleaned_text, flags=re.IGNORECASE).strip()
        cleaned_text = re.sub(r'\s+', ' ', cleaned_text).strip()
        
        # Remove common non-ingredient phrases
        common_phrases = [
            'Please check the product packaging for up-to-date ingredients',
            'Ingredients may change',
            'Please refer to the packaging',
            'For the most up-to-date ingredient list',
            'See packaging for full ingredients list',
            'Please check packaging',
            'For full ingredients list',
            'Out of stock',
            'Maximum basket size reached'
        ]
        for phrase in common_phrases:
            cleaned_text = cleaned_text.replace(phrase, '').strip()
        
        # Split ingredients by common separators
        if ';' in cleaned_text:
            ingredients_list = cleaned_text.split(';')
        elif ',' in cleaned_text:
            ingredients_list = cleaned_text.split(',')
        else:
            # If no clear separators, try to split by capitalized words
            ingredients_list = re.findall(r'[A-Z][a-z]+(?:\s+[a-z]+)*', cleaned_text)
            if not ingredients_list:
                # If still no clear ingredients, return the whole text as one ingredient
                return [cleaned_text]
        
        # Clean and standardize each ingredient
        cleaned_ingredients = []
        for ingredient in ingredients_list:
            ingredient = ingredient.strip()
            if ingredient:
                # Standardize the ingredient
                standardized = self.standardize_ingredient(ingredient)
                cleaned_ingredients.append(standardized)
        
        return cleaned_ingredients
    
    def standardize_ingredient(self, ingredient: str) -> str:
        """
        Standardize an ingredient name.
        
        Args:
            ingredient: Raw ingredient name
            
        Returns:
            Standardized ingredient name
        """
        # Convert to lowercase for consistent comparison
        ingredient_lower = ingredient.lower()
        
        # Check if the ingredient is in our standardization mapping
        if ingredient_lower in INGREDIENT_STANDARDIZATION:
            return INGREDIENT_STANDARDIZATION[ingredient_lower]
        
        # Check for common prefixes and suffixes
        for prefix in INGREDIENT_PREFIXES:
            if ingredient_lower.startswith(prefix + " "):
                # Standardize prefix format
                return prefix.capitalize() + " " + ingredient[len(prefix) + 1:].strip()
        
        for suffix in INGREDIENT_SUFFIXES:
            if ingredient_lower.endswith(" " + suffix):
                # Standardize suffix format
                return ingredient[:-(len(suffix) + 1)].strip() + " " + suffix
        
        # If no standardization rules apply, return the original ingredient
        # but with proper capitalization
        return ingredient
    
    def extract_key_ingredients(self, ingredients_text: str, product_details: str) -> List[str]:
        """
        Extract key/highlighted ingredients from product text.
        
        Args:
            ingredients_text: Raw ingredients text
            product_details: Product details text
            
        Returns:
            List of key ingredients
        """
        key_ingredients = []
        
        # Parse all ingredients first
        all_ingredients = self.parse_ingredients(ingredients_text)
        
        # Look for key ingredients in product details
        if product_details:
            # Common patterns for key ingredients
            key_patterns = [
                r'key ingredients?[:\s]+([^\.]+)',
                r'with ([^\.]+) to ',
                r'contains ([^\.]+) to ',
                r'enriched with ([^\.]+)',
                r'formulated with ([^\.]+)',
                r'infused with ([^\.]+)'
            ]
            
            for pattern in key_patterns:
                matches = re.findall(pattern, product_details, re.IGNORECASE)
                for match in matches:
                    # Split by common separators and clean
                    if ',' in match:
                        ingredients = [i.strip() for i in match.split(',')]
                    elif 'and' in match:
                        ingredients = [i.strip() for i in match.split('and')]
                    else:
                        ingredients = [match.strip()]
                    
                    for ingredient in ingredients:
                        if ingredient and ingredient not in key_ingredients:
                            key_ingredients.append(ingredient)
        
        # If we didn't find any key ingredients in the product details,
        # try to identify them from the full ingredients list
        if not key_ingredients and all_ingredients:
            # Heuristic: First few ingredients are often key ingredients
            key_ingredients = all_ingredients[:3]
        
        return key_ingredients
    
    def extract_specifications(self, product_details: str) -> Dict[str, str]:
        """
        Extract product specifications from product details.
        
        Args:
            product_details: Product details text
            
        Returns:
            Dictionary of specifications
        """
        specs = {}
        
        if not product_details:
            return specs
        
        # Look for common specifications
        size_match = re.search(r'(\d+(\.\d+)?)\s*(ml|g|oz|fl\.?\s*oz)', product_details, re.IGNORECASE)
        if size_match:
            value = size_match.group(1)
            unit = size_match.group(3).lower()
            specs['size'] = f"{value} {unit}"
        
        # Look for skin type
        skin_type_match = re.search(r'for\s+(dry|oily|normal|combination|sensitive|all)\s+skin', product_details, re.IGNORECASE)
        if skin_type_match:
            specs['skin_type'] = skin_type_match.group(1).lower()
        
        # Look for product type
        product_types = ['cleanser', 'moisturizer', 'serum', 'toner', 'mask', 'cream', 'lotion', 'oil', 'balm', 'scrub']
        for product_type in product_types:
            if re.search(r'\b' + product_type + r'\b', product_details, re.IGNORECASE):
                specs['product_type'] = product_type.lower()
                break
        
        return specs
    
    def clean_product_data(self, product_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Clean and process the scraped product data.
        
        Args:
            product_data: The raw product data
            
        Returns:
            The cleaned product data
        """
        cleaned_data = product_data.copy()
        
        # Clean product name
        if cleaned_data['product_name']:
            # Remove excessive whitespace
            cleaned_data['product_name'] = re.sub(r'\s+', ' ', cleaned_data['product_name']).strip()
            # Remove any navigation text that might have been captured
            cleaned_data['product_name'] = re.sub(r'Skip to .*?$', '', cleaned_data['product_name'], flags=re.MULTILINE).strip()
        
        # Clean brand
        if cleaned_data['brand']:
            cleaned_data['brand'] = re.sub(r'\s+', ' ', cleaned_data['brand']).strip()
        
        # Clean product details
        if cleaned_data['product_details']:
            cleaned_data['product_details'] = re.sub(r'Skip to .*?$', '', cleaned_data['product_details'], flags=re.MULTILINE).strip()
            cleaned_data['product_details'] = re.sub(r'\s+', ' ', cleaned_data['product_details']).strip()
        
        # Clean how to use
        if cleaned_data['how_to_use']:
            cleaned_data['how_to_use'] = re.sub(r'Skip to .*?$', '', cleaned_data['how_to_use'], flags=re.MULTILINE).strip()
            cleaned_data['how_to_use'] = re.sub(r'How to use:', '', cleaned_data['how_to_use'], flags=re.IGNORECASE).strip()
            cleaned_data['how_to_use'] = re.sub(r'\s+', ' ', cleaned_data['how_to_use']).strip()
        
        # Clean hazards and cautions
        if cleaned_data['hazards_and_cautions']:
            cleaned_data['hazards_and_cautions'] = re.sub(r'Skip to .*?$', '', cleaned_data['hazards_and_cautions'], flags=re.MULTILINE).strip()
            cleaned_data['hazards_and_cautions'] = re.sub(r'Warnings:|Cautions:', '', cleaned_data['hazards_and_cautions'], flags=re.IGNORECASE).strip()
            cleaned_data['hazards_and_cautions'] = re.sub(r'\s+', ' ', cleaned_data['hazards_and_cautions']).strip()
        
        # Clean country of origin
        if cleaned_data['country_of_origin']:
            cleaned_data['country_of_origin'] = re.sub(r'\s+', ' ', cleaned_data['country_of_origin']).strip()
        
        return cleaned_data
    
    async def scrape_all_products(self, max_products: int = None) -> List[Dict[str, Any]]:
        """
        Scrape all products from the collected product URLs.
        
        Args:
            max_products: Maximum number of products to scrape
            
        Returns:
            List of product data dictionaries
        """
        logger.info(f"Scraping {len(self.product_urls) if not max_products else min(len(self.product_urls), max_products)} products")
        
        # Convert set to list for indexing
        product_urls = list(self.product_urls)
        if max_products:
            product_urls = product_urls[:max_products]
        
        for i, url in enumerate(product_urls):
            logger.info(f"Scraping product {i+1}/{len(product_urls)}: {url}")
            await self.scrape_product(url)
        
        logger.info(f"Scraped {len(self.products_data)} products")
        return self.products_data
    
    async def run(self, max_categories: int = None, max_products_per_category: int = None, max_total_products: int = None) -> None:
        """
        Run the scraper.
        
        Args:
            max_categories: Maximum number of categories to scrape
            max_products_per_category: Maximum number of products to scrape per category
            max_total_products: Maximum total number of products to scrape
        """
        self.stats["start_time"] = datetime.now().isoformat()
        
        try:
            # Set up the browser
            await self.setup_browser()
            
            # Find category URLs
            category_urls = await self.find_category_urls()
            
            # Limit the number of categories if specified
            if max_categories:
                category_urls = list(category_urls)[:max_categories]
            
            # Find product URLs from each category
            for category_url in category_urls:
                # Check if we've reached the maximum total products
                if max_total_products and len(self.product_urls) >= max_total_products:
                    break
                
                # Calculate how many more products we need
                remaining_products = None
                if max_total_products:
                    remaining_products = max_total_products - len(self.product_urls)
                    if remaining_products <= 0:
                        break
                
                # Find product URLs from this category
                await self.find_product_urls(
                    category_url, 
                    max_products=min(max_products_per_category, remaining_products) if max_products_per_category and remaining_products else max_products_per_category
                )
            
            # Scrape all products
            await self.scrape_all_products(max_products=max_total_products)
            
            # Save the data
            self.save_data()
            
        except Exception as e:
            logger.error(f"Error running scraper: {str(e)}")
        finally:
            # Close the browser
            if self.browser:
                await self.browser.close()
            
            self.stats["end_time"] = datetime.now().isoformat()
            logger.info(f"Scraping completed. Stats: {self.stats}")
    
    def save_data(self, suffix="") -> None:
        """
        Save scraped data to CSV files.
        
        Args:
            suffix: Optional suffix to add to the output filenames
        """
        if not self.products_data:
            logger.warning("No product data to save")
            return
        
        # Create timestamp for filenames
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Create output directory if it doesn't exist
        os.makedirs(self.data_dir, exist_ok=True)
        
        # Convert product data to DataFrame
        df = pd.DataFrame(self.products_data)
        
        # Save to CSV
        filename = f"boots_products_{timestamp}{suffix}.csv"
        output_path = os.path.join(self.data_dir, filename)
        df.to_csv(output_path, index=False)
        logger.info(f"Saved {len(df)} products to {output_path}")
        
        # Save ingredients to a separate CSV
        ingredients_data = []
        for product in self.products_data:
            product_id = product.get('product_id', '')
            product_name = product.get('product_name', '')
            for ingredient in product.get('ingredients_list', []):
                ingredients_data.append({
                    'product_id': product_id,
                    'product_name': product_name,
                    'ingredient': ingredient
                })
        
        if ingredients_data:
            ingredients_df = pd.DataFrame(ingredients_data)
            ingredients_filename = f"boots_ingredients_{timestamp}{suffix}.csv"
            ingredients_output_path = os.path.join(self.data_dir, ingredients_filename)
            ingredients_df.to_csv(ingredients_output_path, index=False)
            logger.info(f"Saved {len(ingredients_df)} ingredients to {ingredients_output_path}")
        
        # Save key ingredients to a separate CSV
        key_ingredients_data = []
        for product in self.products_data:
            product_id = product.get('product_id', '')
            product_name = product.get('product_name', '')
            for ingredient in product.get('key_ingredients', []):
                key_ingredients_data.append({
                    'product_id': product_id,
                    'product_name': product_name,
                    'key_ingredient': ingredient
                })
        
        if key_ingredients_data:
            key_ingredients_df = pd.DataFrame(key_ingredients_data)
            key_ingredients_filename = f"boots_key_ingredients_{timestamp}{suffix}.csv"
            key_ingredients_output_path = os.path.join(self.data_dir, key_ingredients_filename)
            key_ingredients_df.to_csv(key_ingredients_output_path, index=False)
            logger.info(f"Saved {len(key_ingredients_df)} key ingredients to {key_ingredients_output_path}")
        
        # Save stats to JSON
        stats_file = os.path.join(self.data_dir, f"boots_stats_{timestamp}{suffix}.json")
        with open(stats_file, 'w') as f:
            json.dump(self.stats, f, indent=2)
        logger.info(f"Saved stats to {stats_file}")
        
        # Save URLs to text files
        category_urls_file = os.path.join(self.data_dir, f"boots_category_urls_{timestamp}{suffix}.txt")
        with open(category_urls_file, 'w') as f:
            for url in self.category_urls:
                f.write(f"{url}\n")
        logger.info(f"Saved {len(self.category_urls)} category URLs to {category_urls_file}")
        
        product_urls_file = os.path.join(self.data_dir, f"boots_product_urls_{timestamp}{suffix}.txt")
        with open(product_urls_file, 'w') as f:
            for url in self.product_urls:
                f.write(f"{url}\n")
        logger.info(f"Saved {len(self.product_urls)} product URLs to {product_urls_file}")

    async def find_5star_product_urls(self, max_products: Optional[int] = None) -> Set[str]:
        """
        Find all 5-star rated skincare product URLs.
        
        Args:
            max_products: Maximum number of products to find
            
        Returns:
            Set of product URLs
        """
        logger.info("Finding 5-star rated skincare product URLs")
        
        # URL for 5-star rated skincare products
        five_star_url = "https://www.boots.com/beauty/skincare/skincare-all-skincare?criteria.roundedReviewScore=5"
        
        # Navigate to the 5-star products page
        await asyncio.sleep(random.uniform(self.min_delay, self.max_delay))
        success = await self.navigate_with_retry(five_star_url)
        if not success:
            logger.error(f"Failed to navigate to {five_star_url}")
            return set()
        
        # Wait for the page to load
        await self.page.wait_for_load_state("networkidle")
        
        # Get the total number of products
        try:
            total_products_element = await self.page.query_selector(".plp__results-count")
            if total_products_element:
                total_products_text = await total_products_element.text_content()
                total_products_match = re.search(r'(\d+) items', total_products_text)
                if total_products_match:
                    total_products = int(total_products_match.group(1))
                    logger.info(f"Found {total_products} 5-star rated products")
                else:
                    total_products = 285  # Default from the URL description
                    logger.info(f"Using default count of {total_products} 5-star rated products")
            else:
                total_products = 285  # Default from the URL description
                logger.info(f"Using default count of {total_products} 5-star rated products")
        except Exception as e:
            total_products = 285  # Default from the URL description
            logger.error(f"Error getting total product count: {str(e)}")
        
        # Calculate how many times we need to scroll to load all products
        # Typically, 24 products are loaded per page
        products_per_page = 24
        scroll_count = (total_products // products_per_page) + 1
        
        # Find product URLs
        product_urls = set()
        
        # Scroll to load all products
        for i in range(scroll_count):
            logger.info(f"Scrolling to load more products (scroll {i+1}/{scroll_count})...")
            
            # Scroll to the bottom of the page
            await self.page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            
            # Wait for new products to load
            await self.page.wait_for_timeout(5000)
            
            # Click on "Load more" button if it exists
            try:
                load_more_button = await self.page.query_selector("button.load-more")
                if load_more_button:
                    await load_more_button.click()
                    await self.page.wait_for_timeout(5000)
            except Exception as e:
                logger.warning(f"Error clicking load more button: {str(e)}")
            
            # Get the updated page content
            content = await self.page.content()
            soup = BeautifulSoup(content, 'html.parser')
            
            # Find product cards
            product_cards = soup.select(".product-list-item, .product-card, .product-tile")
            logger.info(f"Found {len(product_cards)} potential product cards on the page")
            
            # Extract product URLs from cards
            for card in product_cards:
                link = card.find('a', href=True)
                if link:
                    href = link.get('href')
                    if href:
                        # Ensure it's an absolute URL
                        if href.startswith('/'):
                            href = urljoin(BASE_URL, href)
                        
                        # Check if it looks like a product URL
                        if self.is_product_url(href):
                            product_urls.add(href)
                            logger.debug(f"Found 5-star product URL: {href}")
            
            # Check if we've found enough products
            if max_products and len(product_urls) >= max_products:
                logger.info(f"Found {len(product_urls)} 5-star product URLs (reached max_products limit)")
                break
        
        # Update statistics
        self.stats["products_found"] += len(product_urls)
        self.product_urls.update(product_urls)
        
        # Limit the number of products if specified
        if max_products and len(product_urls) > max_products:
            product_urls_list = list(product_urls)[:max_products]
            product_urls = set(product_urls_list)
        
        logger.info(f"Found {len(product_urls)} 5-star product URLs")
        return product_urls

    async def run_5star_scraper(self, max_products: int = None) -> None:
        """
        Run the scraper specifically for 5-star rated products.
        
        Args:
            max_products: Maximum number of products to scrape
        """
        self.stats["start_time"] = datetime.now().isoformat()
        
        try:
            # Set up the browser
            await self.setup_browser()
            
            # Find 5-star product URLs
            product_urls = await self.find_5star_product_urls(max_products=max_products)
            
            # Scrape all products
            await self.scrape_all_products(max_products=max_products)
            
            # Save the data
            self.save_data()
            
        except Exception as e:
            logger.error(f"Error running 5-star scraper: {str(e)}")
            # Take a screenshot of the error state
            if self.page:
                error_screenshot_path = os.path.join(self.screenshot_dir, f"error_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png")
                await self.page.screenshot(path=error_screenshot_path)
                logger.info(f"Error screenshot saved to {error_screenshot_path}")
        finally:
            # Close the browser
            if self.browser:
                await self.browser.close()
            
            self.stats["end_time"] = datetime.now().isoformat()
            logger.info(f"5-star scraping completed. Stats: {self.stats}")

async def main_async():
    """Main async function to run the scraper."""
    parser = argparse.ArgumentParser(description='Boots.com Skincare Products Scraper')
    parser.add_argument('--headless', action='store_true', help='Run in headless mode')
    parser.add_argument('--use-proxies', action='store_true', help='Use proxy rotation')
    parser.add_argument('--respect-robots', action='store_true', help='Respect robots.txt')
    parser.add_argument('--max-categories', type=int, default=None, help='Maximum number of categories to scrape')
    parser.add_argument('--max-products-per-category', type=int, default=None, help='Maximum number of products to scrape per category')
    parser.add_argument('--max-total-products', type=int, default=None, help='Maximum total number of products to scrape')
    parser.add_argument('--min-delay', type=float, default=2.0, help='Minimum delay between requests in seconds')
    parser.add_argument('--max-delay', type=float, default=10.0, help='Maximum delay between requests in seconds')
    parser.add_argument('--max-retries', type=int, default=3, help='Maximum number of retries for failed requests')
    parser.add_argument('--five-star-only', action='store_true', help='Only scrape 5-star rated products')
    
    args = parser.parse_args()
    
    # Create and run the scraper
    scraper = BootsScraper(
        headless=args.headless,
        use_proxies=args.use_proxies,
        respect_robots=args.respect_robots,
        max_retries=args.max_retries,
        min_delay=args.min_delay,
        max_delay=args.max_delay
    )
    
    if args.five_star_only:
        # Run the 5-star scraper
        await scraper.run_5star_scraper(max_products=args.max_total_products)
    else:
        # Run the regular scraper
        await scraper.run(
            max_categories=args.max_categories,
            max_products_per_category=args.max_products_per_category,
            max_total_products=args.max_total_products
        )

def main():
    """Main function to run the scraper."""
    asyncio.run(main_async())

if __name__ == "__main__":
    main()
