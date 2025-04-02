import pandas as pd
import json
import re
import os
from datetime import datetime

def extract_and_clean_ingredients(ingredients_text):
    """Extract and clean ingredients from text."""
    if not isinstance(ingredients_text, str) or not ingredients_text.strip():
        return "", []
    
    # Look for ingredients section with common patterns
    patterns = [
        r'(?:INGREDIENTS|ACTIVE|Active).*?((?:AQUA|WATER)[\s/]+(?:WATER|EAU|AQUA)[^<>]*(?:,|\s+•\s+)[^<>]*)',
        r'(?:[0-9]{5,})\s*[- ]\s*(.+?)(?:read more|$|\(FIL|\(F\.I\.L)',
        r'Active\s*(?:\w+\s*)+\s*(?:-\s*)?(.+?)(?:\(FIL|\(F\.I\.L)',
        r'Ingredients[:\s]+(.+?)(?:How to use|Hazards|$)'
    ]
    
    cleaned_text = ingredients_text
    
    # Try to match one of the patterns
    for pattern in patterns:
        match = re.search(pattern, ingredients_text, re.IGNORECASE | re.DOTALL)
        if match:
            cleaned_text = match.group(1).strip()
            break
    
    # Clean up the text
    cleaned_text = re.sub(r'<[^>]+>', '', cleaned_text)  # Remove HTML tags
    cleaned_text = re.sub(r'\s+', ' ', cleaned_text)     # Normalize whitespace
    cleaned_text = re.sub(r'ingredients:|\bingrédients:|\bingredients\b|:|\*|\+|\.|\bINGREDIENTS\b', '', 
                         cleaned_text, flags=re.IGNORECASE)
    
    # Normalize separators
    normalized_text = re.sub(r'\s+•\s+', ', ', cleaned_text)
    normalized_text = re.sub(r'\s*\|\s*', ', ', normalized_text)
    
    # Split by commas and clean up
    ingredients_list = []
    for item in normalized_text.split(','):
        item = item.strip()
        item = re.sub(r'^[^a-zA-Z0-9]+', '', item)  # Remove leading symbols
        item = re.sub(r'[^a-zA-Z0-9]+$', '', item)  # Remove trailing symbols
        
        if item and len(item) > 1:  # Only add non-empty ingredients
            ingredients_list.append(item)
    
    return cleaned_text, ingredients_list

def process_batch(df, start_idx, end_idx):
    """Process a batch of products."""
    updated_count = 0
    batch_df = df.iloc[start_idx:end_idx].copy()
    
    for idx, row in batch_df.iterrows():
        ingredients_text = row['ingredients']
        
        # Extract and clean ingredients
        cleaned_text, ingredients_list = extract_and_clean_ingredients(ingredients_text)
        
        # Only update if we got ingredients
        if ingredients_list:
            df.loc[idx, 'ingredients'] = cleaned_text
            df.loc[idx, 'ingredients_count'] = len(ingredients_list)
            df.loc[idx, 'ingredients_list'] = ', '.join(ingredients_list)
            updated_count += 1
    
    return updated_count

def main():
    # Parameters
    input_file = 'cosmetics_database.csv'
    batch_size = 100  # Process in batches of 100 products
    
    # Set output file names with timestamp
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    output_file = f"fixed_cosmetics_database_{timestamp}.csv"
    
    print(f"Reading {input_file}...")
    try:
        df = pd.read_csv(input_file)
        total_products = len(df)
        print(f"Loaded {total_products} products")
        
        # Create a backup of the original file
        backup_file = f"original_cosmetics_database_backup_{timestamp}.csv"
        df.to_csv(backup_file, index=False)
        print(f"Original data backed up to {backup_file}")
        
        # Process in batches
        total_updated = 0
        
        for start_idx in range(0, total_products, batch_size):
            end_idx = min(start_idx + batch_size, total_products)
            print(f"Processing batch {start_idx//batch_size + 1}/{(total_products+batch_size-1)//batch_size} "
                  f"(products {start_idx+1}-{end_idx})...")
            
            batch_updated = process_batch(df, start_idx, end_idx)
            total_updated += batch_updated
            
            print(f"  Updated {batch_updated}/{end_idx-start_idx} products in this batch")
            
            # Save progress after each batch
            if (start_idx//batch_size + 1) % 5 == 0:
                progress_file = f"progress_fixed_database_{timestamp}.csv"
                df.to_csv(progress_file, index=False)
                print(f"Progress saved to {progress_file}")
        
        # Save final results
        df.to_csv(output_file, index=False)
        print(f"\nProcessing complete. Updated {total_updated}/{total_products} products.")
        print(f"Final data saved to {output_file}")
        
        # Create JSON version
        output_json = output_file.replace('.csv', '.json')
        
        # Convert to serializable format
        serializable_data = []
        for _, row in df.iterrows():
            row_dict = row.to_dict()
            # Handle ingredients_list
            if 'ingredients_list' in row_dict and isinstance(row_dict['ingredients_list'], str):
                row_dict['ingredients_list'] = [ing.strip() for ing in row_dict['ingredients_list'].split(',') if ing.strip()]
            # Handle NaN values
            for key, val in row_dict.items():
                if pd.isna(val):
                    row_dict[key] = None
            serializable_data.append(row_dict)
        
        with open(output_json, 'w') as f:
            json.dump(serializable_data, f, indent=2)
        print(f"JSON data saved to {output_json}")
        
        # Analyze results
        print("\nResults Analysis:")
        products_with_ingredients = df['ingredients'].notna().sum()
        products_with_ingredients_list = df['ingredients_list'].notna().sum()
        print(f"Products with ingredients data: {products_with_ingredients}/{total_products} ({products_with_ingredients/total_products*100:.1f}%)")
        print(f"Products with extracted ingredients lists: {products_with_ingredients_list}/{total_products} ({products_with_ingredients_list/total_products*100:.1f}%)")
        
        # Show sample of ingredients
        if products_with_ingredients_list > 0:
            sample = df[df['ingredients_list'].notna()].sample(min(5, products_with_ingredients_list))
            print("\nRandom sample of 5 products with ingredients:")
            
            for idx, row in sample.iterrows():
                print(f"\nProduct: {row['product_name']}")
                print(f"Brand: {row['brand']}")
                print(f"Ingredients count: {row['ingredients_count']}")
                
                if isinstance(row['ingredients_list'], str):
                    ingredients = row['ingredients_list'].split(', ')
                    display_ingredients = ingredients[:5]
                    print(f"First 5 ingredients: {', '.join(display_ingredients)}")
                    if len(ingredients) > 5:
                        print(f"...and {len(ingredients)-5} more")
        
    except Exception as e:
        print(f"Error: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()