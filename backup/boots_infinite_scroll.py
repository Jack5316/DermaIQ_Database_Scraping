#!/usr/bin/env python3
"""
Boots.com Skincare Products Scraper

This script uses Playwright to:
1. Navigate to the Boots skincare products page
2. Scroll to the bottom of the page
3. Click "View more" button until all products are loaded
4. Optionally save product data

Usage:
    python boots_infinite_scroll.py
"""

import asyncio
import time
import os
from playwright.async_api import async_playwright

# URL for Boots skincare products
TARGET_URL = "https://www.boots.com/beauty/skincare/skincare-all-skincare"

async def main():
    # Launch Playwright with Brave browser
    async with async_playwright() as p:
        # Use Brave browser (which is Chromium-based)
        # The executable path may need to be adjusted based on your system
        browser_path = "/Applications/Brave Browser.app/Contents/MacOS/Brave Browser"
        
        # Launch the browser
        browser = await p.chromium.launch(
            headless=False,  # Set to True for headless mode
            executable_path=browser_path
        )
        
        # Create a new context and page
        context = await browser.new_context(
            viewport={"width": 1280, "height": 800}
        )
        page = await context.new_page()
        
        # Navigate to the target URL
        print(f"Navigating to {TARGET_URL}")
        await page.goto(TARGET_URL)
        
        # Accept cookies if the dialog appears
        try:
            # Wait for cookie consent dialog and accept it
            accept_button = page.locator('button:has-text("Accept All Cookies")')
            if await accept_button.count() > 0:
                await accept_button.click()
                print("Accepted cookies")
        except Exception as e:
            print(f"No cookie dialog found or error: {e}")
        
        # Initialize counters
        view_more_clicks = 0
        last_product_count = 0
        
        # Function to get the current product count
        async def get_product_count():
            return await page.locator('.product-list__item').count()
        
        # Scroll and click "View more" until no more products are loaded
        while True:
            # Scroll to the bottom of the page
            await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            print("Scrolled to bottom of page")
            
            # Wait for any dynamic content to load
            await asyncio.sleep(2)
            
            # Look for the "View more" button
            view_more_button = page.locator('button:has-text("View more")')
            
            # Check if the button exists and is visible
            if await view_more_button.count() > 0 and await view_more_button.is_visible():
                # Click the "View more" button
                await view_more_button.click()
                view_more_clicks += 1
                print(f"Clicked 'View more' button ({view_more_clicks} times)")
                
                # Wait for new products to load
                await asyncio.sleep(3)
                
                # Get the current product count
                current_product_count = await get_product_count()
                print(f"Current product count: {current_product_count}")
                
                # Check if new products were loaded
                if current_product_count == last_product_count:
                    print("No new products loaded, reached the end")
                    break
                
                last_product_count = current_product_count
            else:
                print("'View more' button not found, reached the end")
                break
        
        # Get the final product count
        final_product_count = await get_product_count()
        print(f"Finished loading all products. Total: {final_product_count}")
        
        # Optional: Take a screenshot of the loaded page
        screenshot_path = "boots_all_skincare_products.png"
        await page.screenshot(path=screenshot_path, full_page=True)
        print(f"Screenshot saved to {screenshot_path}")
        
        # Optional: Extract product information here
        # This would involve parsing the product elements and extracting data
        
        # Wait a moment before closing
        await asyncio.sleep(3)
        
        # Close the browser
        await browser.close()
        print("Browser closed")

if __name__ == "__main__":
    asyncio.run(main())
