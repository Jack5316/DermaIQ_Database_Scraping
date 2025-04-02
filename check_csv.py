import pandas as pd

def check_csv(csv_file='Boots_Skincare.csv'):
    try:
        print(f"Reading CSV file: {csv_file}")
        df = pd.read_csv(csv_file)
        print(f"CSV columns: {df.columns.tolist()}")
        
        # Check if 'oct-link href 2' column exists
        if 'oct-link href 2' in df.columns:
            print("Found 'oct-link href 2' column")
            # Extract URLs and remove duplicates
            product_urls = df['oct-link href 2'].dropna().unique().tolist()
            print(f"Extracted {len(product_urls)} unique URLs")
            # Print first few URLs for verification
            for i, url in enumerate(product_urls[:5]):
                print(f"URL {i+1}: {url}")
        else:
            print(f"Error: 'oct-link href 2' column not found in {csv_file}")
            # Try alternative column names
            possible_columns = [col for col in df.columns if 'oct-link' in col.lower() and 'href' in col.lower()]
            if possible_columns:
                print(f"Found alternative columns: {possible_columns}")
                product_urls = df[possible_columns[0]].dropna().unique().tolist()
                print(f"Extracted {len(product_urls)} unique URLs from {possible_columns[0]}")
                # Print first few URLs for verification
                for i, url in enumerate(product_urls[:5]):
                    print(f"URL {i+1}: {url}")
    except Exception as e:
        print(f"Error reading {csv_file}: {e}")

if __name__ == "__main__":
    check_csv()
