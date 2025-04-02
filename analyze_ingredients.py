import pandas as pd
import numpy as np
import re
from collections import Counter

def analyze_ingredients_data():
    print("Analyzing ingredients data in cosmetics_database.csv...")
    
    # Load the data
    df = pd.read_csv('cosmetics_database.csv')
    
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
        
        # Distribution by count ranges
        bins = [0, 10, 20, 30, 40, 50, 100, np.inf]
        labels = ['1-10', '11-20', '21-30', '31-40', '41-50', '51-100', '100+']
        df['count_range'] = pd.cut(df['ingredients_count'], bins=bins, labels=labels)
        count_distribution = df['count_range'].value_counts().sort_index()
        print("\nDistribution of products by ingredient count:")
        for range_name, count in count_distribution.items():
            if not pd.isna(range_name):
                print(f"  {range_name}: {count} products")
    
    # Sample 5 random products with ingredients to verify data quality
    if products_with_ingredients > 0:
        print("\nRandom sample of 5 products with ingredients:")
        sample = df[df['ingredients_list'].notna()].sample(min(5, products_with_ingredients))
        
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
    
    # Find most common ingredients (if data is properly formatted)
    sample_for_common = df[df['ingredients_list'].notna()].sample(min(100, products_with_ingredients))
    all_ingredients = []
    
    for ing_list in sample_for_common['ingredients_list']:
        if isinstance(ing_list, str):
            ingredients = [ing.strip().lower() for ing in ing_list.split(', ') if ing.strip()]
            all_ingredients.extend(ingredients)
    
    if all_ingredients:
        common_ingredients = Counter(all_ingredients).most_common(10)
        print("\nTop 10 most common ingredients in sample:")
        for ingredient, count in common_ingredients:
            print(f"  {ingredient}: {count} occurrences")

if __name__ == "__main__":
    analyze_ingredients_data()
