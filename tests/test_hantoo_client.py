
import sys
import os

# 프로젝트 루트 디렉토리를 Python 경로에 추가합니다.
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from dotenv import load_dotenv
from core.api_clients.hantoo_client import HantooClient

def test_hantoo_connection():
    print("--- HantooClient Direct Connection Test ---")

    # .env 파일 로드
    dotenv_path = os.path.join(os.path.dirname(__file__), '..', '.env')
    load_dotenv(dotenv_path=dotenv_path)
    print(f"Loaded .env from: {dotenv_path}")

    # 환경 변수에서 계정 정보 읽기
    provider = os.getenv("BROKER_PROVIDER", "hantoo_vps")
    
    # 새로운 테스트 방식: Alias 사용
    test_client_alias = os.getenv("TEST_CLIENT_ALIAS")
    
    if test_client_alias:
        # TEST_CLIENT_ALIAS가 설정되어 있으면, Alias 기반으로 클라이언트 초기화
        target_account_identifier = test_client_alias
        print(f"Provider: {provider}, Using Alias for Client: {target_account_identifier}")
    else:
        # TEST_CLIENT_ALIAS가 없으면, 기존 BROKER_ACCOUNT_NO 사용 (실제 계좌번호)
        target_account_identifier = os.getenv("BROKER_ACCOUNT_NO")
        print(f"Provider: {provider}, Using Direct Account No for Client: {target_account_identifier}")

    if not provider or not target_account_identifier:
        print("[FAIL] BROKER_PROVIDER or account identifier not found in .env file.")
        if not test_client_alias:
            print("       Please set TEST_CLIENT_ALIAS or BROKER_ACCOUNT_NO in your .env file.")
        else:
            print("       Please set TEST_CLIENT_ALIAS in your .env file.")
        return

    # 1. 클라이언트 초기화 및 인증 테스트
    try:
        print("\nStep 1: Initializing HantooClient and authenticating...")
        # broker_account_no 파라미터는 이제 Alias 또는 실제 계좌번호가 될 수 있습니다.
        client = HantooClient(broker_provider=provider, broker_account_no=target_account_identifier)
        print(f"  -> [SUCCESS] HantooClient initialized for {client.alias} (resolved to account: {client.account_no}).")
    except Exception as e:
        print(f"  -> [FAIL] Failed to initialize or authenticate HantooClient.")
        print(f"     Error: {e}")
        return

    # 2. 시세 조회 테스트
    try:
        print("\nStep 2: Fetching current price for '005930'...")
        price = client.get_current_price('005930')
        if price and isinstance(price, float):
            print(f"  -> [SUCCESS] Current price: {price}")
        else:
            print(f"  -> [FAIL] Failed to get current price. Received: {price}")
    except Exception as e:
        print(f"  -> [FAIL] An exception occurred during get_current_price: {e}")

    # 3. 잔고 조회 테스트
    try:
        print("\nStep 3: Fetching account balance...")
        balance = client.get_balance()
        if balance and isinstance(balance, dict):
            print(f"  -> [SUCCESS] Fetched balance info for {client.account_no}.")
            print(f"     - Total Value: {balance.get('total_value')}")
            print(f"     - Cash: {balance.get('cash')}")
            print(f"     - Holdings: {len(balance.get('holdings', []))} items")
        else:
            print(f"  -> [FAIL] Failed to get balance. Received: {balance}")
    except Exception as e:
        print(f"  -> [FAIL] An exception occurred during get_balance: {e}")

if __name__ == "__main__":
    test_hantoo_connection()
