from fredapi import Fred
import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import ssl
import requests
from io import BytesIO
import urllib.request
import zipfile
import os
import tempfile
import shutil
import FinanceDataReader as fdr
import OpenDartReader

from . import models

# For development only: Disable SSL certificate verification
ssl._create_default_https_context = ssl._create_unverified_context

async def _save_symbols_to_db(symbol_model, symbols: List[dict]):
    for item in symbols:
        symbol_str = item['symbol']
        name_str = item['name']
        existing_symbol = await symbol_model.find_one(symbol_model.symbol == symbol_str)
        if not existing_symbol:
            new_symbol = symbol_model(symbol=symbol_str, name=name_str)
            await new_symbol.insert()
        else:
            existing_symbol.name = name_str
            existing_symbol.last_updated = datetime.now()
            await existing_symbol.save()

async def _get_symbols_from_db(symbol_model) -> List[str]:
    symbols = await symbol_model.find_all().to_list()
    return [s.symbol for s in symbols]

def get_historical_data(symbol: str, start_date: str, end_date: str) -> pd.DataFrame:
    """
    Fetches historical stock data for a given symbol and date range using FinanceDataReader.
    """
    try:
        data = fdr.DataReader(symbol, start=start_date, end=end_date)
        return data
    except Exception as e:
        print(f"[DEBUG] Error fetching historical data for {symbol} using FinanceDataReader: {e}")
        return pd.DataFrame()

def get_stock_data(symbol: str, start_date: str, end_date: str = None) -> pd.DataFrame:
    """
    Fetches historical stock data for a given symbol and date range using FinanceDataReader.
    Supports both Korean stocks (6-digit codes) and US stocks (Tickers).
    """
    if end_date is None:
        end_date = datetime.now().strftime('%Y-%m-%d')

    try:
        # FinanceDataReader handles both KR (005930) and US (AAPL) symbols automatically.
        data = fdr.DataReader(symbol, start=start_date, end=end_date)
        
        if data.empty:
            print(f"Warning: No data fetched for {symbol} from {start_date} to {end_date} using FinanceDataReader.")
        
        return data

    except Exception as e:
        print(f"Error fetching data for {symbol} from {start_date} to {end_date} using FinanceDataReader: {e}")
        return pd.DataFrame()

async def get_benchmark_historical_data(start_date: str, end_date: str) -> Dict[str, pd.DataFrame]:
    benchmark_dfs = {}

    # S&P 500 - Use FinanceDataReader
    try:
        sp500_df = get_historical_data("S&P500", start_date, end_date)
        if not sp500_df.empty:
            benchmark_dfs["S&P 500"] = sp500_df
        else:
            print("Warning: No historical data for S&P 500 using FinanceDataReader.")
    except Exception as e:
        print(f"Error fetching S&P 500 data using FinanceDataReader: {e}")

    # KOSPI (KS11) - Use FinanceDataReader
    try:
        kospi_df = get_historical_data("KS11", start_date, end_date)
        if not kospi_df.empty:
            benchmark_dfs["KOSPI"] = kospi_df
        else:
            print("Warning: No historical data for KOSPI (KS11).")
    except Exception as e:
        print(f"Error fetching KOSPI (KS11) data: {e}")

    # Nikkei 225 (N225) - Use FinanceDataReader
    try:
        nikkei_df = get_historical_data("N225", start_date, end_date)
        if not nikkei_df.empty:
            benchmark_dfs["Nikkei 225"] = nikkei_df
        else:
            print("Warning: No historical data for Nikkei 225 (N225).")
    except Exception as e:
        print(f"Error fetching Nikkei 225 (N225) data: {e}")

    return benchmark_dfs

from dotenv import load_dotenv

def get_fred_yield_curve(start_date: str, end_date: str) -> pd.DataFrame:
    """
    Fetches US Treasury yield curve rates from the FRED API.
    It reads the FRED_API_KEY from a .env file in the same directory.
    """
    try:
        # Load .env file from the backend directory
        backend_dir = os.path.dirname(os.path.abspath(__file__))
        dotenv_path = os.path.join(backend_dir, '.env')
        load_dotenv(dotenv_path=dotenv_path)

        api_key = os.getenv("FRED_API_KEY")
        if not api_key:
            print("Error: FRED_API_KEY not found in .env file.")
            return pd.DataFrame()
        
        fred = Fred(api_key=api_key)
        
        series_map = {
            '1m': 'DGS1MO',
            '3m': 'DGS3MO',
            '6m': 'DGS6MO',
            '1y': 'DGS1',
            '2y': 'DGS2',
            '3y': 'DGS3',
            '5y': 'DGS5',
            '7y': 'DGS7',
            '10y': 'DGS10',
            '20y': 'DGS20',
            '30y': 'DGS30'
        }
        
        all_series = []
        for short_name, series_id in series_map.items():
            series = fred.get_series(series_id, observation_start=start_date, observation_end=end_date)
            # Use the series_id as the column name to match the ticker used in the strategy parameters
            series.name = series_id
            all_series.append(series)
            
        if not all_series:
            print(f"Warning: No FRED yield curve data fetched from {start_date} to {end_date}")
            return pd.DataFrame()
            
        df = pd.concat(all_series, axis=1)
        
        # FRED data is already in percent, so divide by 100
        df = df / 100.0
        
        # Forward fill to handle missing values on non-business days
        df = df.ffill()
        
        return df

    except Exception as e:
        print(f"Error fetching or processing FRED data: {e}")
        return pd.DataFrame()

def _clean_and_convert_to_float(value):
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        value = value.replace(',', '')
        if value.strip() == '-' or value.strip() == '':
            return 0.0
        try:
            return float(value)
        except ValueError:
            return 0.0
    return 0.0

def get_korean_fundamental_data(symbol: str, year: int, quarter: int, re_evaluation_frequency: str) -> Dict:
    """
    Fetches Korean fundamental data for a given symbol and period using OpenDartReader.
    """
    # Load .env file from the backend directory
    backend_dir = os.path.dirname(os.path.abspath(__file__))
    dotenv_path = os.path.join(backend_dir, '.env')
    load_dotenv(dotenv_path=dotenv_path)
    
    api_key = os.getenv("OPENDART_API_KEY")
    if not api_key:
        print("Error: OPENDART_API_KEY not found in .env file.")
        return {}

    dart = OpenDartReader(api_key)

    # Use symbol directly as corp_code as per user's clarification
    corp_code = symbol # Assuming symbol is the stock_code

    # Fetch financial statements
    if re_evaluation_frequency == 'annual':
        reprt_code = '11011' # Annual report code
    else:
        report_codes = {
            1: '11013', # Q1
            2: '11012', # Q2 (Half-year)
            3: '11014', # Q3
            4: '11011'  # Annual (Q4)
        }
        reprt_code = report_codes.get(quarter)

    if not reprt_code:
        print(f"Error: Invalid quarter {quarter} or re_evaluation_frequency {re_evaluation_frequency} for OpenDartReader.")
        return {}

    try:
        finstate = dart.finstate(corp=corp_code, bsns_year=year, reprt_code=reprt_code)
        if finstate is None or finstate.empty:
            # This can happen for preferred stocks or when data is not available
            # print(f"Warning: No financial statements found for {symbol} ({corp_code}) in {year} Q{quarter}.")
            return {}

        # Extract relevant data
        current_assets_str = finstate.loc[finstate['account_nm'] == '유동자산', 'thstrm_amount'].iloc[0] if '유동자산' in finstate['account_nm'].values else '0'
        total_liabilities_str = finstate.loc[finstate['account_nm'] == '부채총계', 'thstrm_amount'].iloc[0] if '부채총계' in finstate['account_nm'].values else '0'
        net_income_str = finstate.loc[finstate['account_nm'] == '당기순이익', 'thstrm_amount'].iloc[0] if '당기순이익' in finstate['account_nm'].values else '0'
        eps_str = finstate.loc[finstate['account_nm'] == '주당순이익', 'thstrm_amount'].iloc[0] if '주당순이익' in finstate['account_nm'].values else '0'

        return {
            "current_assets": _clean_and_convert_to_float(current_assets_str),
            "total_liabilities": _clean_and_convert_to_float(total_liabilities_str),
            "net_income": _clean_and_convert_to_float(net_income_str),
            "eps": _clean_and_convert_to_float(eps_str),
            # Market Cap will be added later
        }

    except Exception as e:
        print(f"Error fetching financial statements for {symbol} ({corp_code}) in {year} Q{quarter}: {e}")
        return {}

def get_us_fundamental_data(symbol: str, year: int, quarter: int) -> Dict:
    """
    Placeholder for fetching US fundamental data (balance sheet, income statement) for a given symbol and period.
    """
    print(f"Fetching US fundamental data for {symbol} in {year} Q{quarter} (Placeholder)")
    return {
        "current_assets": 1000000000000,
        "total_liabilities": 500000000000,
        "market_cap": 1500000000000,
        "net_income": 100000000000,
        "eps": 100,
        "shares_outstanding": 1000000000,
    }

def get_asset_universe(region: str, top_n: Optional[int] = None, ranking_metric: Optional[str] = None, ranking_order: Optional[str] = 'desc') -> pd.DataFrame:
    """
    Fetches the list of assets for a given market region.
    For 'KR', it fetches all stocks listed on KRX (KOSPI, KOSDAQ, KONEX).
    If top_n, ranking_metric, and ranking_order are provided, it pre-filters the universe to 5 * top_n assets.
    """
    if region == 'KR':
        try:
            krx = fdr.StockListing('KOSPI')
            # Marcap is in KRW 100,000,000. Convert to absolute value.
            krx['Marcap'] = krx['Marcap'] * 100000000

            if top_n is not None and ranking_metric == 'Marcap' and 'Marcap' in krx.columns:
                # Sort by the ranking metric before taking the top N
                reverse_sort = (ranking_order == 'desc')
                krx = krx.sort_values(by=ranking_metric, ascending=not reverse_sort).head(top_n * 5)

            return krx
        except Exception as e:
            print(f"Error fetching KRX stock listing: {e}")
            return pd.DataFrame()
    # Add other regions like 'US' here
    # elif region == 'US':
    #     ...
    else:
        print(f"Warning: Asset universe for region '{region}' is not supported.")
        return pd.DataFrame()

if __name__ == "__main__":
    aapl_data = get_stock_data("AAPL", "2023-01-01", "2023-12-31")
    if not aapl_data.empty:
        print(aapl_data.head())
