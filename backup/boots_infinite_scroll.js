/**
 * Boots.com Skincare Products Scraper
 * 
 * This script uses Playwright to:
 * 1. Navigate to the Boots skincare products page
 * 2. Scroll to the bottom of the page
 * 3. Click "View more" button until all products are loaded
 * 4. Optionally save product data
 * 
 * Usage:
 *    node boots_infinite_scroll.js
 */

const { chromium } = require('playwright');
const fs = require('fs');

// URL for Boots skincare products
const TARGET_URL = 'https://www.boots.com/beauty/skincare/skincare-all-skincare';

async function main() {
  // Path to Brave Browser (adjust if needed for your system)
  const bravePath = '/Applications/Brave Browser.app/Contents/MacOS/Brave Browser';
  
  console.log('Launching browser...');
  const browser = await chromium.launch({
    headless: false, // Set to true for headless mode
    executablePath: bravePath
  });
  
  // Create a new context and page
  const context = await browser.newContext({
    viewport: { width: 1280, height: 800 }
  });
  const page = await context.newPage();
  
  // Navigate to the target URL
  console.log(`Navigating to ${TARGET_URL}`);
  await page.goto(TARGET_URL);
  
  // Wait for the page to load properly
  await page.waitForLoadState('networkidle');
  console.log('Page loaded');
  
  // Accept cookies if the dialog appears
  try {
    // Try multiple possible selectors for the accept button
    const acceptButtonSelectors = [
      'button:has-text("Accept All Cookies")',
      'button:has-text("Accept all cookies")',
      '#onetrust-accept-btn-handler',
      '[aria-label="Accept cookies"]',
      '.cookie-banner__button'
    ];
    
    for (const selector of acceptButtonSelectors) {
      const acceptButton = page.locator(selector);
      if (await acceptButton.count() > 0 && await acceptButton.isVisible()) {
        await acceptButton.click();
        console.log('Accepted cookies');
        break;
      }
    }
  } catch (e) {
    console.log(`No cookie dialog found or error: ${e}`);
  }
  
  // Take a screenshot of the initial page to analyze
  await page.screenshot({ path: 'boots_initial_page.png', fullPage: true });
  console.log('Saved initial page screenshot to boots_initial_page.png');
  
  // Based on the page structure analysis, we know the correct selectors
  // The product items are in the .oct-listers-hits__item class
  // The "View more" button has text "View more"
  
  // Initialize counters
  let viewMoreClicks = 0;
  let lastProductCount = 0;
  
  // Function to get the current product count
  async function getProductCount() {
    // Based on the page analysis, these are the correct product selectors
    const productSelectors = [
      '.oct-listers-hits__item',
      '.oct-teaser--theme-productTile',
      '.product-list-item',
      '.product-tile'
    ];
    
    for (const selector of productSelectors) {
      try {
        const count = await page.locator(selector).count();
        if (count > 0) {
          console.log(`Found ${count} products using selector: ${selector}`);
          return { count, selector };
        }
      } catch (e) {
        // Skip invalid selectors
        continue;
      }
    }
    
    console.log('No products found with product selectors');
    return { count: 0, selector: null };
  }
  
  // Function to find and click the "View more" button
  async function findAndClickViewMoreButton() {
    // Based on the page analysis, this is the correct "View more" button
    const viewMoreButton = page.locator('button:has-text("View more")');
    
    if (await viewMoreButton.count() > 0 && await viewMoreButton.isVisible()) {
      await viewMoreButton.click();
      viewMoreClicks++;
      console.log(`Clicked 'View more' button (${viewMoreClicks} times)`);
      return true;
    }
    
    console.log('No "View more" button found');
    return false;
  }
  
  // Get initial product count
  const initialProductResult = await getProductCount();
  console.log(`Initial product count: ${initialProductResult.count} with selector: ${initialProductResult.selector}`);
  lastProductCount = initialProductResult.count;
  let bestProductSelector = initialProductResult.selector;
  
  // Scroll and click "View more" until no more products are loaded
  let attempts = 0;
  const maxAttempts = 30; // Limit the number of attempts to prevent infinite loops
  
  while (attempts < maxAttempts) {
    attempts++;
    
    // Scroll to the bottom of the page
    await page.evaluate(() => window.scrollTo(0, document.body.scrollHeight));
    console.log(`Attempt ${attempts}: Scrolled to bottom of page`);
    
    // Wait for any dynamic content to load
    await page.waitForTimeout(2000);
    
    // Try to find and click the "View more" button
    const buttonClicked = await findAndClickViewMoreButton();
    
    if (!buttonClicked) {
      console.log('No "View more" button found, reached the end or need to scroll more');
      
      // Try scrolling a bit more before giving up
      if (attempts < maxAttempts) {
        console.log('Trying to scroll more...');
        await page.evaluate(() => {
          window.scrollBy(0, 500); // Scroll down a bit more
        });
        await page.waitForTimeout(1000);
        continue;
      } else {
        console.log('Max attempts reached, stopping');
        break;
      }
    }
    
    // Wait for new products to load
    await page.waitForTimeout(3000);
    
    // Get the current product count
    const currentProductResult = await getProductCount();
    console.log(`Current product count: ${currentProductResult.count} with selector: ${currentProductResult.selector}`);
    
    // Update best product selector if we found a better one
    if (currentProductResult.count > 0 && (!bestProductSelector || currentProductResult.count > lastProductCount)) {
      bestProductSelector = currentProductResult.selector;
    }
    
    // Check if new products were loaded
    if (currentProductResult.count === lastProductCount && currentProductResult.count > 0) {
      console.log('No new products loaded, reached the end');
      break;
    }
    
    lastProductCount = currentProductResult.count;
    
    // Log the current pagination status
    const paginationText = await page.evaluate(() => {
      const paginationElement = document.querySelector('.oct-listers__pagination');
      return paginationElement ? paginationElement.textContent.trim() : 'Pagination not found';
    });
    console.log(`Pagination status: ${paginationText}`);
  }
  
  // Get the final product count using the best selector
  let finalProductCount = 0;
  if (bestProductSelector) {
    finalProductCount = await page.locator(bestProductSelector).count();
  }
  console.log(`Finished loading all products. Total: ${finalProductCount} with selector: ${bestProductSelector}`);
  
  // Take a screenshot of the loaded page
  const screenshotPath = 'boots_all_skincare_products.png';
  await page.screenshot({ path: screenshotPath, fullPage: true });
  console.log(`Screenshot saved to ${screenshotPath}`);
  
  // Extract product information if products were found
  if (finalProductCount > 0 && bestProductSelector) {
    console.log(`Extracting product information using selector: ${bestProductSelector}`);
    const productInfo = await page.evaluate((selector) => {
      const productElements = document.querySelectorAll(selector);
      
      return Array.from(productElements).slice(0, 10).map(product => {
        // Try different selectors for product information based on Boots.com structure
        const titleElement = product.querySelector('.oct-teaser__title, h3, .product-title');
        const priceElement = product.querySelector('.oct-teaser__productPrice, .product-price');
        const imageElement = product.querySelector('img');
        const brandElement = product.querySelector('.oct-teaser__brand, .product-brand');
        const ratingElement = product.querySelector('.oct-teaser__rating, .product-rating');
        
        return {
          title: titleElement ? titleElement.textContent.trim() : 'Title not found',
          brand: brandElement ? brandElement.textContent.trim() : 'Brand not found',
          price: priceElement ? priceElement.textContent.trim() : 'Price not found',
          rating: ratingElement ? ratingElement.textContent.trim() : 'Rating not found',
          imageUrl: imageElement ? imageElement.src : 'Image not found'
        };
      });
    }, bestProductSelector);
    
    console.log('Sample of products found (first 10):');
    console.log(JSON.stringify(productInfo, null, 2));
    
    // Save product info to a file
    fs.writeFileSync('boots_products_sample.json', JSON.stringify(productInfo, null, 2));
    console.log('Saved product sample to boots_products_sample.json');
  }
  
  // Wait a moment before closing
  await page.waitForTimeout(3000);
  
  // Close the browser
  await browser.close();
  console.log('Browser closed');
}

main().catch(error => {
  console.error('Error:', error);
  process.exit(1);
});
