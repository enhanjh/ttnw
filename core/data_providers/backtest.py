
import pandas as pd
from typing import Dict, List
import datetime
import os

# core 폴더와 backend 폴더가 동일한 상위 디렉토리에 있다고 가정합니다.
from backend.data_collector import get_historical_data as fetch_historical_data_by_range
from backend.data_collector import get_asset_universe as fetch_asset_universe
from backend.data_collector import get_korean_fundamental_data as fetch_korean_fundamental_data
# from backend.data_collector import get_us_fundamental_data as fetch_us_fundamental_data # 필요시 추가

from core.strategies.base import DataContext

class BacktestDataContext(DataContext):
    """
    백테스팅을 위한 데이터 컨텍스트 구현체입니다.
    data_collector를 사용하여 과거 데이터를 가져와 전략과 실행기에 제공합니다.
    """

    def __init__(self):
        # 간단한 캐시를 사용하여 동일한 데이터를 반복적으로 불러오는 것을 방지합니다.
        self._cache = {}

    def get_current_prices(self, symbols: List[str]) -> Dict[str, float]:
        """
        백테스팅 환경에서 '현재가'는 모호한 개념입니다. 이 메소드는 API 호환성을 위해
        구현되었으며, 가장 최근에 사용 가능한 종가를 반환합니다.
        BacktestExecutor는 이 메소드를 직접 사용하지 않습니다.
        """
        today = datetime.date.today()
        five_days_ago = today - datetime.timedelta(days=5)
        
        data = self.get_historical_data_by_range(symbols, five_days_ago.strftime('%Y-%m-%d'), today.strftime('%Y-%m-%d'))
        
        prices = {}
        for symbol in symbols:
            if symbol in data and not data[symbol].empty:
                prices[symbol] = data[symbol]['Close'].iloc[-1]
            else:
                prices[symbol] = None
        return prices

    def get_historical_data(self, symbols: List[str], end_date: pd.Timestamp, lookback_days: int) -> Dict[str, pd.DataFrame]:
        """
        `end_date`를 기준으로 특정 기간(lookback_days)만큼의 과거 데이터를 가져옵니다.
        주로 모멘텀 전략 등에서 lookback 기간의 수익률을 계산할 때 사용될 수 있습니다.
        """
        start_date = end_date - pd.DateOffset(days=lookback_days)
        return self.get_historical_data_by_range(symbols, start_date.strftime('%Y-%m-%d'), end_date.strftime('%Y-%m-%d'))

    def get_historical_data_by_range(self, symbols: List[str], start_date: str, end_date: str) -> Dict[str, pd.DataFrame]:
        """
        BacktestExecutor가 전체 시뮬레이션 기간의 데이터를 한 번에 가져오기 위해 사용하는 메소드입니다.
        """
        data_dict = {}
        for symbol in symbols:
            cache_key = f"{symbol}_{start_date}_{end_date}"
            if cache_key in self._cache:
                data_dict[symbol] = self._cache[cache_key]
                continue
            
            try:
                df = fetch_historical_data_by_range(symbol, start_date, end_date)
                if not df.empty:
                    self._cache[cache_key] = df
                    data_dict[symbol] = df
            except Exception as e:
                print(f"Warning: Could not fetch data for {symbol} from {start_date} to {end_date}. Error: {e}")
        
        return data_dict

    def get_asset_universe(self, date: pd.Timestamp, region: str, top_n: int = None, ranking_metric: str = None) -> pd.DataFrame:
        """
        지정된 지역의 자산 유니버스를 가져옵니다. `date` 인자는 현재 백테스트 시점의 유니버스를
        가져오기 위함이지만, 현재 `fetch_asset_universe`는 `date` 인자를 받지 않으므로 무시합니다.
        """
        cache_key = f"asset_universe_{region}"
        if cache_key in self._cache:
            return self._cache[cache_key]
        
        df = fetch_asset_universe(region) # date, top_n, ranking_metric은 현재 data_collector에서 처리하지 않음
        self._cache[cache_key] = df
        return df

    def get_fundamental_data(self, symbol: str, date: pd.Timestamp) -> Dict:
        """
        지정된 자산의 특정 연도/분기별 기본 데이터를 가져옵니다.
        `date` 인자를 사용하여 해당 시점의 가장 최신 분기 데이터를 가져옵니다.
        """
        year = date.year
        quarter = (date.month - 1) // 3 + 1

        # region은 DataContext 추상 메소드에 없으므로, 여기서는 KR로 고정하거나 다른 방식으로 처리해야 합니다.
        # 현재는 fetch_korean_fundamental_data만 호출합니다.
        cache_key = f"fundamental_data_{symbol}_{year}_{quarter}_KR" # 캐시 키에 region 고정
        if cache_key in self._cache:
            return self._cache[cache_key]

        data = {}
        opendart_api_key = os.getenv("OPENDART_API_KEY")
        if not opendart_api_key:
            print("Error: OPENDART_API_KEY environment variable not set for Korean fundamental data.")
            return {}
        data = fetch_korean_fundamental_data(symbol, opendart_api_key, year, quarter)
        
        self._cache[cache_key] = data
        return data
