import pandas as pd
import json
import re
import os
from datetime import datetime

def clean_ingredients_text(ingredients_text):
    """Clean ingredients text by removing non-ingredient text patterns."""
    if not isinstance(ingredients_text, str):
        return ""
    
    # Look for specific ingredient lists patterns
    pattern1 = r'(?:INGREDIENTS|ACTIVE|Active).*?((?:AQUA|WATER)[\s/]+(?:WATER|EAU|AQUA)[^<>]*(?:,|\s+•\s+)[^<>]*)'
    pattern2 = r'(?:[0-9]{5,})\s*[- ]\s*(.+?)(?:read more|$|\(FIL|\(F\.I\.L)'
    pattern3 = r'Active\s*(?:\w+\s*)+\s*(?:-\s*)?(.+?)(?:\(FIL|\(F\.I\.L)'
    
    for pattern in [pattern1, pattern2, pattern3]:
        match = re.search(pattern, ingredients_text, re.IGNORECASE | re.DOTALL)
        if match:
            ingredients_text = match.group(1).strip()
            break
    
    # Clean up the text
    ingredients_text = re.sub(r'<[^>]+>', '', ingredients_text)  # Remove HTML tags
    ingredients_text = re.sub(r'\s+', ' ', ingredients_text)     # Normalize whitespace
    ingredients_text = re.sub(r'ingredients:|\bingrédients:|\bingredients\b|:|\*|\+|\.|\bINGREDIENTS\b', '', 
                             ingredients_text, flags=re.IGNORECASE)
    
    return ingredients_text.strip()

def extract_ingredients_list(ingredients_text):
    """Extract ingredients list from cleaned ingredients text."""
    if not ingredients_text:
        return []
    
    # Normalize separators
    ingredients_text = re.sub(r'\s+•\s+', ', ', ingredients_text)
    ingredients_text = re.sub(r'\s*\|\s*', ', ', ingredients_text)
    
    # Split by commas
    ingredients_list = []
    for item in ingredients_text.split(','):
        item = item.strip()
        # Remove leading/trailing symbols
        item = re.sub(r'^[^a-zA-Z0-9]+', '', item)
        item = re.sub(r'[^a-zA-Z0-9]+$', '', item)
        
        if item and len(item) > 1:  # Only add non-empty ingredients with at least 2 chars
            ingredients_list.append(item)
    
    return ingredients_list

def process_batch(batch_df):
    """Process a batch of products."""
    results = []
    success_count = 0
    
    for idx, row in batch_df.iterrows():
        product_data = row.to_dict()
        ingredients_text = row.get('ingredients')
        
        # Skip missing ingredients
        if not isinstance(ingredients_text, str) or not ingredients_text.strip():
            results.append(product_data)
            continue
        
        # Clean the ingredients text
        cleaned_text = clean_ingredients_text(ingredients_text)
        
        # Extract ingredients list
        ingredients_list = extract_ingredients_list(cleaned_text)
        
        # Only update if we found ingredients
        if ingredients_list:
            product_data['ingredients'] = cleaned_text
            product_data['ingredients_count'] = len(ingredients_list)
            product_data['ingredients_list'] = ', '.join(ingredients_list)
            success_count += 1
        
        results.append(product_data)
    
    return results, success_count

def main():
    # Parameters
    input_file = 'cosmetics_database.csv'
    batch_size = 100
    
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    output_file = f"fixed_cosmetics_database_{timestamp}.csv"
    output_json = f"fixed_cosmetics_database_{timestamp}.json"
    
    try:
        # Read the CSV file with proper quoting
        print(f"Reading {input_file}...")
        df = pd.read_csv(input_file)
        total_rows = len(df)
        print(f"Loaded {total_rows} products")
        
        # Create a backup of the original file
        backup_file = f"original_cosmetics_database_backup_{timestamp}.csv"
        df.to_csv(backup_file, index=False)
        print(f"Original data backed up to {backup_file}")
        
        # Process in batches
        all_results = []
        total_processed = 0
        total_success = 0
        
        for i in range(0, total_rows, batch_size):
            end = min(i + batch_size, total_rows)
            print(f"Processing batch {i//batch_size + 1} (products {i+1}-{end})...")
            
            # Process this batch
            batch_df = df.iloc[i:end].copy()
            batch_results, success_count = process_batch(batch_df)
            
            # Add to overall results
            all_results.extend(batch_results)
            total_processed += len(batch_results)
            total_success += success_count
            
            print(f"  Processed {len(batch_results)} products, fixed {success_count} product(s)")
        
        # Convert results to DataFrame
        print(f"Total: Processed {total_processed} products, fixed {total_success} products")
        
        # Save results to CSV
        results_df = pd.DataFrame(all_results)
        results_df.to_csv(output_file, index=False)
        print(f"Updated data saved to {output_file}")
        
        # Save to JSON (convert ingredients_list to actual lists)
        serializable_data = []
        for item in all_results:
            # Convert ingredients_list to a list if it's a string
            if 'ingredients_list' in item and isinstance(item['ingredients_list'], str):
                item['ingredients_list'] = [ing.strip() for ing in item['ingredients_list'].split(',') if ing.strip()]
            serializable_data.append(item)
        
        with open(output_json, 'w') as f:
            json.dump(serializable_data, f, indent=2)
        print(f"Data also saved to {output_json}")
        
    except Exception as e:
        print(f"Error: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()