from fredapi import Fred
import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta
from typing import List, Dict
import ssl
import requests
from io import BytesIO
import urllib.request
import zipfile
import os
import tempfile
import shutil
import FinanceDataReader as fdr
import OpenDartReader as odr

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
        if data.empty:
            print(f"Warning: No data fetched for {symbol} from {start_date} to {end_date} using FinanceDataReader")
        return data
    except Exception as e:
        print(f"Error fetching historical data for {symbol} using FinanceDataReader: {e}")
        return pd.DataFrame()

def get_stock_data(symbol: str, start_date: str, end_date: str = None) -> pd.DataFrame:
    """
    Fetches historical stock data for a given symbol and date range.
    """
    if end_date is None:
        end_date = datetime.now().strftime('%Y-%m-%d')

    try:
        data = yf.download(symbol, start=start_date, end=end_date, progress=False)
        if data.empty:
            print(f"Warning: No data fetched for {symbol} from {start_date} to {end_date}")
        return data
    except Exception as e:
        print(f"Error fetching data for {symbol} from {start_date} to {end_date}: {e}")
        return pd.DataFrame()

def get_fred_yield_curve(api_key: str, start_date: str, end_date: str) -> pd.DataFrame:
    """
    Fetches US Treasury yield curve rates from the FRED API.
    """
    try:
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

def get_korean_fundamental_data(symbol: str, api_key: str, year: int, quarter: int) -> Dict:
    """
    Fetches Korean fundamental data (balance sheet, income statement) for a given symbol and period using OpenDartReader.
    Assumes symbol is the stock_code (e.g., '005930') which can be used directly as corp_code.
    """
    odr.api_key = api_key

    # Use symbol directly as corp_code as per user's clarification
    corp_code = symbol # Assuming symbol is the stock_code

    # Fetch financial statements
    report_codes = {
        1: '11013', # Q1
        2: '11012', # Q2 (Half-year)
        3: '11014', # Q3
        4: '11011'  # Annual (Q4)
    }
    reprt_code = report_codes.get(quarter)
    if not reprt_code:
        print(f"Error: Invalid quarter {quarter} for OpenDartReader.")
        return {}

    try:
        finstate = odr.finstate(corp_code, year, reprt_code=reprt_code)
        if finstate is None or finstate.empty:
            print(f"Warning: No financial statements found for {symbol} ({corp_code}) in {year} Q{quarter}.")
            return {}

        # Extract relevant data
        current_assets = finstate[finstate['account_nm'] == '유동자산']['thstrm_amount'].iloc[0] if '유동자산' in finstate['account_nm'].values else 0
        total_liabilities = finstate[finstate['account_nm'] == '부채총계']['thstrm_amount'].iloc[0] if '부채총계' in finstate['account_nm'].values else 0
        net_income = finstate[finstate['account_nm'] == '당기순이익']['thstrm_amount'].iloc[0] if '당기순이익' in finstate['account_nm'].values else 0
        eps = finstate[finstate['account_nm'] == '주당순이익']['thstrm_amount'].iloc[0] if '주당순이익' in finstate['account_nm'].values else 0

        return {
            "current_assets": float(current_assets),
            "total_liabilities": float(total_liabilities),
            "net_income": float(net_income),
            "eps": float(eps),
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

if __name__ == "__main__":
    aapl_data = get_stock_data("AAPL", "2023-01-01", "2023-12-31")
    if not aapl_data.empty:
        print(aapl_data.head())
