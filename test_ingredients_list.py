import pandas as pd
import json
import re
import os

# Load a small subset of data from the CSV file
def test_ingredients_list_processing():
    print("Testing ingredients_list processing on a small subset of data...")
    
    # Load the first 20 products with ingredients from the CSV file
    df = pd.read_csv('cosmetics_database.csv')
    df_with_ingredients = df[df['ingredients'].notna()].head(20)
    
    # Check if ingredients_list is already populated
    if 'ingredients_list' in df_with_ingredients.columns:
        missing_count = df_with_ingredients['ingredients_list'].isna().sum()
        print(f"Found {len(df_with_ingredients)} products with ingredients")
        print(f"Missing ingredients_list values: {missing_count}")
        
        # Display sample data
        print("\nSample data (first 3 products):")
        sample = df_with_ingredients.head(3)
        for idx, row in sample.iterrows():
            print(f"\nProduct: {row['product_name']}")
            print(f"Ingredients count: {row['ingredients_count']}")
            print(f"Ingredients list: {row['ingredients_list'][:100]}..." if isinstance(row['ingredients_list'], str) and len(row['ingredients_list']) > 100 else f"Ingredients list: {row['ingredients_list']}")
    else:
        print("ingredients_list column not found in the CSV file")
    
    # Test the extraction logic on a few examples
    print("\nTesting extraction logic on sample ingredients:")
    test_ingredients = [
        "INGREDIENTS: Water, Glycerin, Alcohol, Parfum, Sodium Laureth Sulfate",
        "Aqua, Cetearyl Alcohol, Glycerin, Dimethicone, Panthenol",
        "Ingredients: Aqua/Water/Eau, Glycerin, Alcohol Denat., Dimethicone"
    ]
    
    for i, ing_text in enumerate(test_ingredients):
        print(f"\nTest {i+1}: {ing_text}")
        # Clean up the text
        cleaned_text = re.sub(r'ingredients:|\bingrédients:|\bingredients\b|:|\*|\+|\.', '', ing_text, flags=re.IGNORECASE)
        # Split by commas and count non-empty items
        ingredients_list = [ing.strip() for ing in cleaned_text.split(',') if ing.strip()]
        print(f"Extracted {len(ingredients_list)} ingredients: {ingredients_list}")

if __name__ == "__main__":
    test_ingredients_list_processing()
