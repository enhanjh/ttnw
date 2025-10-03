from fredapi import Fred
import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta
from typing import List
import ssl
import requests
from io import BytesIO
import urllib.request
import zipfile
import os
import tempfile
import shutil
import FinanceDataReader as fdr

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
            series.name = short_name
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

if __name__ == "__main__":
    aapl_data = get_stock_data("AAPL", "2023-01-01", "2023-12-31")
    if not aapl_data.empty:
        print(aapl_data.head())
