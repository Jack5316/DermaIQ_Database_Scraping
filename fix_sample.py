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
        r'Active\s*(?:\w+\s*)+\s*(?:-\s*)?(.+?)(?:\(FIL|\(F\.I\.L)'
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

def main():
    # Get a small sample of products
    input_file = 'cosmetics_database.csv'
    print(f"Reading {input_file}...")
    df = pd.read_csv(input_file)
    
    # Take a random sample of 50 products
    sample_size = 50
    df_sample = df.sample(sample_size)
    print(f"Selected {len(df_sample)} random products")
    
    # Process the sample
    updated_count = 0
    
    for idx, row in df_sample.iterrows():
        ingredients_text = row['ingredients']
        
        # Extract and clean ingredients
        cleaned_text, ingredients_list = extract_and_clean_ingredients(ingredients_text)
        
        # Only update if we got ingredients
        if ingredients_list:
            df.loc[idx, 'ingredients'] = cleaned_text
            df.loc[idx, 'ingredients_count'] = len(ingredients_list)
            df.loc[idx, 'ingredients_list'] = ', '.join(ingredients_list)
            updated_count += 1
    
    print(f"Successfully updated {updated_count} out of {sample_size} products")
    
    # Save the sample
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    output_file = f"sample_fixed_cosmetics_database_{timestamp}.csv"
    df_sample.to_csv(output_file, index=False)
    print(f"Sample output saved to {output_file}")
    
    # Verify the sample
    print("\nSample results (first 3 updated products):")
    sample_updated = df_sample[df_sample['ingredients_list'].notna()].head(3)
    
    for idx, row in sample_updated.iterrows():
        print(f"\nProduct: {row['product_name']}")
        print(f"Ingredients count: {row['ingredients_count']}")
        ingredients = row['ingredients_list'].split(', ')[:5]
        print(f"First 5 ingredients: {', '.join(ingredients)}")
        if len(row['ingredients_list'].split(', ')) > 5:
            print(f"...and {len(row['ingredients_list'].split(', ')) - 5} more")

if __name__ == "__main__":
    main()