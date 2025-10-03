
import sys
import os
import pandas as pd

# 프로젝트 루트 디렉토리를 Python 경로에 추가합니다.
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from backend.data_collector import get_historical_data

def run_test():
    print("--- Testing data_collector.get_historical_data ---")
    
    symbols_to_test = {
        "Korean Stock (Samsung)": "005930",
        "US ETF (SPY)": "SPY",
        "International ETF (EFA)": "EFA",
        "US Bond ETF (AGG)": "AGG"
    }
    
    start_date = "2022-01-01"
    end_date = "2022-01-31"
    
    all_passed = True
    for name, symbol in symbols_to_test.items():
        print(f"\nFetching data for: {name} ({symbol})")
        try:
            data = get_historical_data(symbol, start_date, end_date)
            if isinstance(data, pd.DataFrame) and not data.empty:
                print(f"  [SUCCESS] Successfully fetched {len(data)} rows.")
                print("  Sample data:")
                print(data.head(2))
            else:
                print(f"  [FAILURE] Fetched empty or invalid data.")
                all_passed = False
        except Exception as e:
            print(f"  [ERROR] An exception occurred: {e}")
            all_passed = False
    
    print("\n--- Test Summary ---")
    if all_passed:
        print("All symbols fetched successfully!")
    else:
        print("One or more symbols failed to fetch. Please review the logs above.")

if __name__ == "__main__":
    run_test()
