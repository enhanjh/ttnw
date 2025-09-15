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
import urllib.request
import zipfile
import os
import tempfile
import shutil

from sqlalchemy.orm import Session
from .database import SessionLocal
from . import models


# For development only: Disable SSL certificate verification
ssl._create_default_https_context = ssl._create_unverified_context

def _save_symbols_to_db(db: Session, symbol_model, symbols: List[dict]):
    for item in symbols:
        symbol_str = item['symbol']
        name_str = item['name']
        # Check if symbol already exists
        existing_symbol = db.query(symbol_model).filter(symbol_model.symbol == symbol_str).first()
        if not existing_symbol:
            new_symbol = symbol_model(symbol=symbol_str, name=name_str, last_updated=datetime.now())
            db.add(new_symbol)
        else:
            existing_symbol.name = name_str
            existing_symbol.last_updated = datetime.now()
    db.commit()

def _get_symbols_from_db(db: Session, symbol_model) -> List[str]:
    symbols = db.query(symbol_model).all()
    return [s.symbol for s in symbols]

def get_historical_data(symbol: str, start_date: str, end_date: str) -> pd.DataFrame:
    """
    Fetches historical stock data for a given symbol and date range using FinanceDataReader.
    """
    try:
        # FinanceDataReader는 start_date만 있어도 동작하지만, 명시적으로 end_date를 전달합니다.
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
    :param symbol: Stock ticker symbol (e.g., 'AAPL', 'MSFT').
    :param start_date: Start date in 'YYYY-MM-DD' format.
    :param end_date: End date in 'YYYY-MM-DD' format. Defaults to today.
    :return: Pandas DataFrame with historical stock data.
    """
    if end_date is None:
        end_date = datetime.now().strftime('%Y-%m-%d')

    try:
        data = yf.download(symbol, start=start_date, end=end_date, progress=False) # progress=False to suppress download messages
        if data.empty:
            print(f"Warning: No data fetched for {symbol} from {start_date} to {end_date}")
        return data
    except Exception as e:
        print(f"Error fetching data for {symbol} from {start_date} to {end_date}: {e}")
        return pd.DataFrame()

if __name__ == "__main__":
    # Example usage:
    aapl_data = get_stock_data("AAPL", "2023-01-01", "2023-12-31")
    if not aapl_data.empty:
        print(aapl_data.head())
