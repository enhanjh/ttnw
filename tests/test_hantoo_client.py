
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
    account_no = os.getenv("BROKER_ACCOUNT_NO", "50155201-01")
    
    print(f"Provider: {provider}, Account: {account_no}")

    if not provider or not account_no:
        print("[FAIL] BROKER_PROVIDER or BROKER_ACCOUNT_NO not found in .env file.")
        return

    # 1. 클라이언트 초기화 및 인증 테스트
    try:
        print("\nStep 1: Initializing HantooClient and authenticating...")
        client = HantooClient(broker_provider=provider, broker_account_no=account_no)
        print("  -> [SUCCESS] HantooClient initialized and authenticated.")
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
            print(f"  -> [SUCCESS] Fetched balance info.")
            print(f"     - Total Value: {balance.get('total_value')}")
            print(f"     - Cash: {balance.get('cash')}")
            print(f"     - Holdings: {len(balance.get('holdings', []))} items")
        else:
            print(f"  -> [FAIL] Failed to get balance. Received: {balance}")
    except Exception as e:
        print(f"  -> [FAIL] An exception occurred during get_balance: {e}")

if __name__ == "__main__":
    test_hantoo_connection()
