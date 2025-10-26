
import sys
import os
import pandas as pd

# 프로젝트 루트 디렉토리를 Python 경로에 추가합니다.
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from backend.data_collector import get_asset_universe, get_korean_fundamental_data

def run_unit_test():
    print("--- Testing Fundamental Data Fetching Unit for Bottom 5 Stocks ---")
    
    # 1. Get the bottom 5 stocks from the universe
    print("\n1. Fetching asset universe (bottom 5 stocks)...")
    universe_df = get_asset_universe(region='KR', top_n=5, ranking_metric='Marcap', ranking_order='asc')
    
    if universe_df.empty:
        print("  [FAILURE] Could not fetch asset universe.")
        return
        
    print(f"  [SUCCESS] Fetched bottom 5 stocks:")
    print(universe_df[['Code', 'Name', 'Marcap']])

    # 2. Fetch fundamental data for each of the bottom 5 stocks
    for index, stock in universe_df.iterrows():
        symbol = stock['Code']
        name = stock['Name']
        print(f"\n----------------------------------------")
        print(f"Fetching fundamental data for {name} ({symbol})...")
        year = 2022
        quarter = 1
        
        try:
            fundamental_data = get_korean_fundamental_data(
                symbol=symbol, 
                year=year, 
                quarter=quarter, 
                re_evaluation_frequency='quarterly'
            )
            
            if fundamental_data:
                print(f"  [SUCCESS] Successfully fetched fundamental data for Q1 {year}.")
                print("  Data:")
                for key, value in fundamental_data.items():
                    print(f"    - {key}: {value}")
            else:
                print(f"  [FAILURE] Fetched empty or invalid fundamental data.")
        except Exception as e:
            print(f"  [ERROR] An exception occurred: {e}")

if __name__ == "__main__":
    run_unit_test()
