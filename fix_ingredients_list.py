import pandas as pd
import json
import re
import os
from datetime import datetime

def clean_ingredients_text(ingredients_text):
    """
    Clean ingredients text by removing non-ingredient text patterns.
    
    Args:
        ingredients_text (str): Raw ingredients text
        
    Returns:
        str: Cleaned ingredients text
    """
    if not isinstance(ingredients_text, str):
        return ""
    
    # First identify the actual ingredients section
    # Look for specific ingredient lists in HTML format
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
    
    # Remove non-ingredient text patterns
    ingredients_text = re.sub(r'ingredients:|\bingrédients:|\bingredients\b|:|\*|\+|\.|\bINGREDIENTS\b', '', ingredients_text, flags=re.IGNORECASE)
    
    return ingredients_text.strip()

def extract_ingredients_list(ingredients_text):
    """
    Extract ingredients list from cleaned ingredients text.
    
    Args:
        ingredients_text (str): Cleaned ingredients text
        
    Returns:
        list: List of individual ingredients
    """
    if not ingredients_text:
        return []
    
    # Normalize separators - handle bullet points and dots
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

def fix_database(input_file='cosmetics_database.csv', test_mode=True, sample_size=10):
    """
    Fix the database by cleaning ingredients and creating ingredients_list.
    
    Args:
        input_file (str): Path to input CSV file
        test_mode (bool): Whether to run in test mode (process only a sample)
        sample_size (int): Number of products to process in test mode
    """
    print(f"Processing database file: {input_file}")
    
    try:
        # Read the CSV file with proper quoting
        df = pd.read_csv(input_file, quoting=1)  # QUOTE_ALL
        print(f"Loaded {len(df)} products from {input_file}")
        
        # Create a copy for testing to avoid modifying the original in test mode
        if test_mode:
            print(f"Running in test mode with sample size of {sample_size}")
            # Select products with ingredients
            df_with_ingredients = df[df['ingredients'].notna()].head(sample_size).copy()
            working_df = df_with_ingredients
        else:
            # Use the full dataframe
            working_df = df.copy()
        
        # Process each product
        updated_count = 0
        success_count = 0
        
        for idx, row in working_df.iterrows():
            ingredients_text = row['ingredients']
            
            # Skip missing ingredients
            if not isinstance(ingredients_text, str) or not ingredients_text.strip():
                continue
            
            # Clean the ingredients text
            cleaned_text = clean_ingredients_text(ingredients_text)
            
            # Extract ingredients list
            ingredients_list = extract_ingredients_list(cleaned_text)
            
            # Only update if we found ingredients
            if ingredients_list:
                # Update the dataframe
                working_df.loc[idx, 'ingredients'] = cleaned_text
                working_df.loc[idx, 'ingredients_count'] = len(ingredients_list)
                working_df.loc[idx, 'ingredients_list'] = ', '.join(ingredients_list)
                success_count += 1
            
            updated_count += 1
            
            # Print progress in non-test mode
            if not test_mode and updated_count % 100 == 0:
                print(f"Processed {updated_count} products...")
        
        print(f"Updated {updated_count} products, successfully extracted ingredients for {success_count} products")
        
        if test_mode:
            # Save to a test file
            output_file = f"test_fixed_cosmetics_database_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
            working_df.to_csv(output_file, index=False, quoting=1)  # QUOTE_ALL to preserve commas
            print(f"Test output saved to {output_file}")
            
            # Show sample results
            print("\nSample results:")
            for idx, row in working_df.head(3).iterrows():
                print(f"\nProduct: {row['product_name']}")
                if pd.notna(row.get('ingredients_count')):
                    print(f"Ingredients count: {row['ingredients_count']}")
                    if isinstance(row.get('ingredients_list'), str):
                        sample_text = row['ingredients_list'][:100] + "..." if len(row['ingredients_list']) > 100 else row['ingredients_list']
                        print(f"Sample ingredients: {sample_text}")
                else:
                    print("No ingredients extracted")
        else:
            # Save the full updated dataframe
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            output_file = f"fixed_cosmetics_database_{timestamp}.csv"
            output_json = f"fixed_cosmetics_database_{timestamp}.json"
            
            # Create a backup of the original file
            backup_file = f"original_cosmetics_database_backup_{timestamp}.csv"
            df.to_csv(backup_file, index=False, quoting=1)  # QUOTE_ALL
            print(f"Original data backed up to {backup_file}")
            
            # Save to CSV
            working_df.to_csv(output_file, index=False, quoting=1)  # QUOTE_ALL
            print(f"Updated data saved to {output_file}")
            
            # Convert to serializable format and save as JSON
            serializable_data = []
            for _, row in working_df.iterrows():
                row_dict = row.to_dict()
                # Convert ingredients_list to a list if it's a string
                if 'ingredients_list' in row_dict and isinstance(row_dict['ingredients_list'], str):
                    row_dict['ingredients_list'] = [ing.strip() for ing in row_dict['ingredients_list'].split(',') if ing.strip()]
                # Handle NaN values
                for key, val in row_dict.items():
                    if pd.isna(val):
                        row_dict[key] = None
                serializable_data.append(row_dict)
                
            with open(output_json, 'w') as f:
                json.dump(serializable_data, f, indent=2)
            print(f"Data also saved to {output_json}")
        
    except Exception as e:
        print(f"Error processing database: {str(e)}")
        import traceback
        traceback.print_exc()

def analyze_ingredients_data(csv_file):
    """
    Analyze the ingredients data to show statistics.
    
    Args:
        csv_file (str): Path to the CSV file with ingredient data
    """
    try:
        # Load the data
        df = pd.read_csv(csv_file, quoting=1)  # QUOTE_ALL
        
        # Basic statistics
        total_products = len(df)
        products_with_ingredients = df['ingredients'].notna().sum()
        products_with_ingredients_list = df['ingredients_list'].notna().sum()
        
        print(f"Total products: {total_products}")
        print(f"Products with ingredients field: {products_with_ingredients} ({products_with_ingredients/total_products*100:.1f}%)")
        print(f"Products with ingredients_list field: {products_with_ingredients_list} ({products_with_ingredients_list/total_products*100:.1f}%)")
        
        # Check for any discrepancies
        discrepancy_count = (df['ingredients'].notna() & df['ingredients_list'].isna()).sum()
        print(f"Products with ingredients but no ingredients_list: {discrepancy_count}")
        
        # Analyze ingredients count distribution
        if 'ingredients_count' in df.columns:
            valid_counts = df['ingredients_count'].dropna()
            print(f"\nIngredients count statistics:")
            print(f"  Min: {valid_counts.min()}")
            print(f"  Max: {valid_counts.max()}")
            print(f"  Mean: {valid_counts.mean():.1f}")
            print(f"  Median: {valid_counts.median()}")
            
            # Sample 5 random products with ingredients to verify data quality
            if products_with_ingredients_list > 0:
                print("\nRandom sample of 5 products with ingredients:")
                sample = df[df['ingredients_list'].notna()].sample(min(5, products_with_ingredients_list))
                
                for idx, row in sample.iterrows():
                    print(f"\nProduct: {row['product_name']}")
                    print(f"Brand: {row['brand']}")
                    print(f"Ingredients count: {row['ingredients_count']}")
                    
                    # Display first few ingredients if available
                    if isinstance(row['ingredients_list'], str):
                        ingredients = row['ingredients_list'].split(', ')
                        display_ingredients = ingredients[:5]
                        print(f"First 5 ingredients: {', '.join(display_ingredients)}")
                        if len(ingredients) > 5:
                            print(f"...and {len(ingredients)-5} more")
                    else:
                        print("Ingredients list not available in expected format")
            
    except Exception as e:
        print(f"Error analyzing ingredients data: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Fix ingredients list in cosmetics database')
    parser.add_argument('--input', type=str, default='cosmetics_database.csv',
                        help='Input CSV file (default: cosmetics_database.csv)')
    parser.add_argument('--test', action='store_true',
                        help='Run in test mode on a small sample')
    parser.add_argument('--sample', type=int, default=10,
                        help='Sample size for test mode (default: 10)')
    parser.add_argument('--analyze', type=str, default=None,
                        help='Analyze the ingredients data from the specified CSV file')
    
    args = parser.parse_args()
    
    if args.analyze:
        analyze_ingredients_data(args.analyze)
    else:
        fix_database(input_file=args.input, test_mode=args.test, sample_size=args.sample)