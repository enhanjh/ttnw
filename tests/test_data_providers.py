
import sys
import os
import pandas as pd

# 프로젝트 루트 디렉토리를 Python 경로에 추가합니다.
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from core.data_providers import BacktestDataContext, LiveDataContext
from core.api_clients.hantoo_client import HantooClient

def test_backtest_data_context():
    print("\n--- Testing BacktestDataContext ---")
    context = BacktestDataContext()

    # 1. Test get_historical_data_by_range
    print("1. Testing get_historical_data_by_range for 005930...")
    hist_data = context.get_historical_data_by_range(['005930'], '2022-01-01', '2022-01-31')
    assert '005930' in hist_data and not hist_data['005930'].empty
    print("  -> OK")

    # 2. Test get_asset_universe
    print("2. Testing get_asset_universe for KR...")
    universe = context.get_asset_universe(pd.Timestamp.now(), 'KR')
    assert not universe.empty and 'Code' in universe.columns
    print(f"  -> OK, {len(universe)} symbols found.")

    # 3. Test get_fundamental_data
    print("3. Testing get_fundamental_data for 005930...")
    fund_data = context.get_fundamental_data('005930', pd.Timestamp('2022-03-31'))
    assert fund_data and fund_data['eps'] > 0
    print("  -> OK")
    print("--- BacktestDataContext Test Passed ---\n")

def test_live_data_context():
    print("--- Testing LiveDataContext ---")
    try:
        # 모의투자 정보로 클라이언트 초기화
        client = HantooClient(broker_provider='hantoo_vps', broker_account_no='50155201-01')
        live_context = LiveDataContext(hantoo_client=client)

        # 1. Test get_current_prices
        print("1. Testing get_current_prices for 005930...")
        prices = live_context.get_current_prices(['005930'])
        assert '005930' in prices and prices['005930'] > 0
        print(f"  -> OK, Current price for 005930: {prices['005930']}")
        print("--- LiveDataContext Test Passed ---")

    except Exception as e:
        print(f"  [ERROR] LiveDataContext test failed: {e}")
        print("  -> Please check your HANTOO_APP_KEY, HANTOO_APP_SECRET in backend/.env and the account number.")

if __name__ == "__main__":
    # 백테스트 데이터 컨텍스트 테스트 실행
    test_backtest_data_context()

    # 실거래 데이터 컨텍스트 테스트 실행
    # 주의: 이 테스트는 실제 한투 API에 연결을 시도합니다.
    # backend/.env 파일에 실계좌용 HANTOO_APP_KEY, HANTOO_APP_SECRET이 설정되어 있어야 합니다.
    # 아래 YOUR_REAL_ACCOUNT_NO를 실제 계좌번호로 바꿔주세요.
    test_live_data_context()
