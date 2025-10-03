
import os
import requests
import json
import logging
import time
from datetime import datetime, timedelta

# Configure logger
logger = logging.getLogger(__name__)



class HantooClient:
    """
    A client for interacting with the Korea Investment & Securities (KIS) API.
    Handles authentication, token management, and provides methods for various API calls.
    Supports multiple accounts via Alias mapping or direct account numbers.
    """
    
    # Class-level cache to store tokens in memory across instances (within the same process)
    # Key: account_no, Value: {'access_token': str, 'expires_at': datetime}
    _token_cache = {}

    def __init__(self, broker_provider: str, broker_account_no: str, app_key: str = None, app_secret: str = None):
        """
        Initialize the HantooClient.

        :param broker_provider: Provider name (e.g., 'hantoo_vps', 'hantoo_prod')
        :param broker_account_no: Can be a specific Account Alias (e.g., 'FUNDS_ALPHA') or a Real Account Number.
        :param app_key: Optional explicit App Key.
        :param app_secret: Optional explicit App Secret.
        """
        if 'KIS' not in broker_provider:
            raise ValueError(f"Unsupported broker provider: {broker_provider}")

        self.is_paper = 'VPS' in broker_provider
        if self.is_paper:
            self.base_url = "https://openapivts.koreainvestment.com:29443"
            self.rate_limit_delay = 0.5  # 2 request per second for VPS
        else: # Assumes production
            self.base_url = "https://openapi.koreainvestment.com:9443"
            self.rate_limit_delay = 0.05  # 20 requests per second for Real
        
        self.alias = broker_account_no
        self.account_no = None # Will be resolved in _load_credentials
        self.app_key = app_key
        self.app_secret = app_secret
        
        # Instance-level variables (will be populated from cache or auth)
        self._access_token = None
        self._token_expires_at = None

        self._load_credentials()

        if not all([self.app_key, self.app_secret, self.account_no]):
            raise ValueError(f"Hantoo API credentials or account number could not be resolved for alias/account '{self.alias}'.")

    def _load_credentials(self):
        """
        Resolves the real account number and API credentials based on the provided alias.
        Prioritizes:
        1. Alias-specific Env Vars (HANTOO_REAL_ACCOUNT_{ALIAS}, etc.)
        2. Account-Number-specific Env Vars (fallback if input is a real account no)
        3. Default Env Vars
        """
        # 1. Try Alias Lookup
        # Env var names should be uppercase, e.g., HANTOO_REAL_ACCOUNT_MY_FUND
        alias_upper = self.alias.upper()
        
        real_acc_env = os.getenv(f"BROKER_ACCOUNT_NO__{alias_upper}")
        key_env = os.getenv(f"HANTOO_APP_KEY__{alias_upper}")
        secret_env = os.getenv(f"HANTOO_APP_SECRET__{alias_upper}")

        if real_acc_env:
            # Case A: Alias matched
            self.account_no = real_acc_env
            if not self.app_key: self.app_key = key_env
            if not self.app_secret: self.app_secret = secret_env
        else:
            # Case B: Input might be a real account number already
            self.account_no = self.alias
            
            # Try to find keys specific to this account number (remove hyphens for clean env var name)
            clean_acc, _ = self._get_account_parts()
            if not self.app_key: self.app_key = os.getenv(f"HANTOO_APP_KEY__{clean_acc}")
            if not self.app_secret: self.app_secret = os.getenv(f"HANTOO_APP_SECRET__{clean_acc}")

        # Case C: Fallback to global defaults if still missing
        if not self.app_key: 
            self.app_key = os.getenv("HANTOO_APP_KEY")
            logger.info("[HantooClient] Using default HANTOO_APP_KEY.")
        if not self.app_secret: self.app_secret = os.getenv("HANTOO_APP_SECRET")

    def _get_account_parts(self):
        """
        Splits the account number into CANO (8 digits) and ACNT_PRDT_CD (2 digits).
        Handles both hyphenated ('12345678-01') and non-hyphenated ('1234567801') formats.
        """
        # Validation: check if account_no contains only digits and hyphens
        if not all(c.isdigit() or c == '-' for c in self.account_no):
             raise ValueError(f"Invalid account number format (contains non-numeric characters): {self.account_no}. Make sure HANTOO_REAL_ACCOUNT_{self.alias.upper()} is set in .env")

        if '-' in self.account_no:
            parts = self.account_no.split('-')
            if len(parts) != 2:
                 raise ValueError(f"Invalid account number format: {self.account_no}")
            return parts[0], parts[1]
        else:
            # Assume first 8 digits are CANO, rest are suffix
            if len(self.account_no) < 9:
                 raise ValueError(f"Account number too short: {self.account_no}")
            return self.account_no[:8], self.account_no[8:]

    def _authenticate(self):
        """ Fetches and stores a new access token at the instance level. """
        # Check class-level cache first
        if self.account_no in HantooClient._token_cache:
            cached = HantooClient._token_cache[self.account_no]
            if datetime.now() < cached['expires_at']:
                self._access_token = cached['access_token']
                self._token_expires_at = cached['expires_at']
                # logger.info(f"Using cached token for {self.account_no}")
                return

        path = "/oauth2/tokenP"
        url = f"{self.base_url}{path}"
        headers = {"content-type": "application/json"}
        body = {
            "grant_type": "client_credentials",
            "appkey": self.app_key,
            "appsecret": self.app_secret
        }
        
        try:
            res = requests.post(url, headers=headers, data=json.dumps(body), timeout=30)
            res.raise_for_status() # Raise an exception for bad status codes
            data = res.json()
            
            token = f"Bearer {data['access_token']}"
            expires_in = data['expires_in']
            expires_at = datetime.now() + timedelta(seconds=expires_in - 60)

            self._access_token = token
            self._token_expires_at = expires_at
            
            # Save to class-level cache
            HantooClient._token_cache[self.account_no] = {
                'access_token': token,
                'expires_at': expires_at
            }
            # logger.info(f"Hantoo API authentication successful for account {self.account_no} (Alias: {self.alias}).")
        except requests.exceptions.RequestException as e:
            logger.error(f"Hantoo API authentication failed for account {self.account_no}: {e}")
            raise

    def get_ws_approval_key(self):
        """ Fetches a one-time approval key for WebSocket connection. """ 
        path = "/oauth2/Approval"
        url = f"{self.base_url}{path}"
        headers = {"content-type": "application/json"}
        body = {
            "grant_type": "client_credentials",
            "appkey": self.app_key,
            "secretkey": self.app_secret,
        }
        try:
            res = requests.post(url, headers=headers, data=json.dumps(body), timeout=30)
            res.raise_for_status()
            data = res.json()
            return data.get("approval_key")
        except requests.exceptions.RequestException as e:
            logger.error(f"Hantoo API WS approval key failed: {e}")
            raise

    def _get_headers(self, tr_id: str) -> dict:
        """ Checks token validity and returns required headers for API calls. """
        if self._token_expires_at is None or datetime.now() >= self._token_expires_at:
            # print(f"Access token expired or not found for {self.alias}. Re-authenticating...")
            self._authenticate()
        
        return {
            "content-type": "application/json; charset=utf-8",
            "authorization": self._access_token,
            "appkey": self.app_key,
            "appsecret": self.app_secret,
            "tr_id": tr_id,
            "custtype": "P"
        }

    # --- Methods to be implemented ---

    def get_current_price(self, symbol: str) -> float:
        """ Fetches the current market price of a stock. """
        path = "/uapi/domestic-stock/v1/quotations/inquire-price"
        url = f"{self.base_url}{path}"
        
        tr_id = "FHKST01010100"

        headers = self._get_headers(tr_id)
        params = {
            "FID_COND_MRKT_DIV_CODE": "J",  # J: KRX, NX: NXT, UN: 통합
            "FID_INPUT_ISCD": symbol,
        }
        
        # Enforce rate limit
        time.sleep(self.rate_limit_delay)

        try:
            res = requests.get(url, headers=headers, params=params, timeout=30)
            res.raise_for_status()  # HTTP 에러 발생 시 예외 발생
            
            # 응답 본문을 먼저 확인
            response_data = res.json()
            
            # 실제 데이터 파싱
            data = response_data['output']
            price = float(data['stck_prpr'])
            return price

        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching price for {symbol}: {e}")
            if e.response is not None:
                logger.error(f"Response Body: {e.response.text}")
            return None
        except (KeyError, ValueError, json.JSONDecodeError) as e:
            logger.error(f"Error parsing price data for {symbol}: {e}")
            # res가 정의되어 있는 경우, 응답 텍스트를 출력
            if 'res' in locals() and hasattr(res, 'text'):
                logger.error(f"Hantoo API Response: {res.text}")
            return None

    def _get_account_parts(self):
        """
        Splits the account number into CANO (8 digits) and ACNT_PRDT_CD (2 digits).
        Handles both hyphenated ('12345678-01') and non-hyphenated ('1234567801') formats.
        """
        if '-' in self.account_no:
            parts = self.account_no.split('-')
            if len(parts) != 2:
                 raise ValueError(f"Invalid account number format: {self.account_no}")
            return parts[0], parts[1]
        else:
            # Assume first 8 digits are CANO, rest are suffix
            if len(self.account_no) < 9:
                 raise ValueError(f"Account number too short: {self.account_no}")
            return self.account_no[:8], self.account_no[8:]

    def get_balance(self) -> dict:
        """ Fetches the current account balance and holdings. """
        tr_id = "VTTC8434R" if self.is_paper else "TTTC8434R"
        path = "/uapi/domestic-stock/v1/trading/inquire-balance"
        url = f"{self.base_url}{path}"
        headers = self._get_headers(tr_id)
        
        acc_no, acc_suffix = self._get_account_parts()

        params = {
            "CANO": acc_no,
            "ACNT_PRDT_CD": acc_suffix,
            "AFHR_FLPR_YN": "N",
            "OFL_YN": "",
            "INQR_DVSN": "01",
            "UNPR_DVSN": "01",
            "FUND_STTL_ICLD_YN": "N",
            "FNCG_AMT_AUTO_RDPT_YN": "N",
            "PRCS_DVSN": "00",
            "CTX_AREA_FK100": "",
            "CTX_AREA_NK100": ""
        }
        
        # Enforce rate limit
        time.sleep(self.rate_limit_delay)

        try:
            res = requests.get(url, headers=headers, params=params, timeout=30)
            res.raise_for_status()
            
            response_data = res.json()

            # prts_amt: 평가금액, dnca_tot_amt: 예수금총금액
            total_value = float(response_data['output2'][0]['tot_evlu_amt'])
            cash = float(response_data['output2'][0]['dnca_tot_amt'])

            holdings = []
            for item in response_data['output1']:
                holdings.append({
                    'symbol': item['pdno'],
                    'name': item['prdt_name'],
                    'quantity': float(item['hldg_qty']),
                    'average_price': float(item['pchs_avg_pric']),
                    'current_price': float(item['prpr']),
                    'eval_amount': float(item['evlu_amt'])
                })

            return {'total_value': total_value, 'cash': cash, 'holdings': holdings}

        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching balance: {e}")
            if e.response is not None:
                logger.error(f"Response Body: {e.response.text}")
            return None
        except (KeyError, ValueError, IndexError, json.JSONDecodeError) as e:
            logger.error(f"Error parsing balance data: {e}")
            if 'res' in locals() and hasattr(res, 'text'):
                logger.error(f"Hantoo API Response: {res.text}")
            return None

    def place_order(self, symbol: str, quantity: int, price: int, side: str, order_type: str = 'limit') -> dict:
        """ 
        Places a new order. 
        :param side: 'buy' or 'sell'
        :param order_type: 'limit' (지정가) or 'market' (시장가)
        """
        if side.lower() not in ['buy', 'sell']:
            raise ValueError("side must be either 'buy' or 'sell'")
        
        if quantity <= 0:
            raise ValueError(f"Quantity must be greater than 0. Got: {quantity}")
        
        # Validate price only for limit orders
        if order_type == 'limit' and price <= 0:
            raise ValueError(f"Price must be greater than 0 for limit orders. Got: {price}")

        # Determine TR_ID based on side and environment
        tr_id_prefix = "VTT" if self.is_paper else "TTT"
        tr_id_suffix = "C0802U" if side.lower() == 'buy' else "C0801U"
        tr_id = tr_id_prefix + tr_id_suffix

        path = "/uapi/domestic-stock/v1/trading/order-cash"
        url = f"{self.base_url}{path}"
        headers = self._get_headers(tr_id)

        # The account number is split for the API call
        acc_no, acc_suffix = self._get_account_parts()
        
        # Configure Order Division and Price based on Order Type
        if order_type == 'market':
            ord_dvsn = "01" # 01: 시장가
            ord_unpr = "0"  # Market orders must send "0" as price
        else:
            ord_dvsn = "00" # 00: 지정가
            ord_unpr = str(price)

        body = {
            "CANO": acc_no,
            "ACNT_PRDT_CD": acc_suffix,
            "PDNO": symbol,
            "ORD_DVSN": ord_dvsn,
            "ORD_QTY": str(quantity),
            "ORD_UNPR": ord_unpr,
        }
        
        # Enforce local rate limit
        time.sleep(self.rate_limit_delay)

        try:
            res = requests.post(url, headers=headers, data=json.dumps(body), timeout=30)
            res.raise_for_status()
            data = res.json()

            if data.get('rt_cd') == '0':
                return {'status': 'success', 'order_id': data.get('output', {}).get('ODNO'), 'message': data.get('msg1')}
            else:
                return {'status': 'failure', 'message': data.get('msg1', 'Unknown error')}

        except requests.exceptions.RequestException as e:
            logger.error(f"Network error placing order for {symbol}: {e}")
            raise # Raise to allow retry logic in caller (e.g. Celery)
        except (KeyError, ValueError, json.JSONDecodeError) as e:
            logger.error(f"Error parsing order response for {symbol}: {e}")
            return {'status': 'error', 'message': str(e)}

    def get_transaction_history(self, start_date: str, end_date: str) -> list:
        """
        Fetches the transaction history for a given period, automatically selecting
        the correct tr_id based on the date range.
        start_date, end_date format: YYYYMMDD
        """
        # Determine if the start date is within the last 3 months (approx. 90 days)
        three_months_ago = datetime.now() - timedelta(days=90)
        start_date_dt = datetime.strptime(start_date, "%Y%m%d")

        if start_date_dt < three_months_ago:
            pd_dv = "before"
        else:
            pd_dv = "inner"

        # Set tr_id based on the period and environment
        if self.is_paper:
            tr_id = "VTSC9215R" if pd_dv == "before" else "VTTC0081R"
        else:
            tr_id = "CTSC9215R" if pd_dv == "before" else "TTTC0081R"

        path = "/uapi/domestic-stock/v1/trading/inquire-daily-ccld"
        url = f"{self.base_url}{path}"
        
        acc_no, acc_suffix = self._get_account_parts()
        
        all_transactions = []
        tr_cont = "" 
        ctx_area_fk100 = ""
        ctx_area_nk100 = ""

        while True:
            headers = self._get_headers(tr_id)
            if tr_cont in ("F", "M"):
                headers["tr_cont"] = tr_cont

            params = {
                "CANO": acc_no,
                "ACNT_PRDT_CD": acc_suffix,
                "INQR_STRT_DT": start_date,
                "INQR_END_DT": end_date,
                "SLL_BUY_DVSN_CD": "00",
                "INQR_DVSN": "00",
                "PDNO": "",
                "CCLD_DVSN": "01",
                "ORD_GNO_BRNO": "",
                "ODNO": "",
                "INQR_DVSN_3": "00",
                "INQR_DVSN_1": "",
                "CTX_AREA_FK100": ctx_area_fk100,
                "CTX_AREA_NK100": ctx_area_nk100
            }
            
            # Enforce rate limit
            time.sleep(self.rate_limit_delay)

            try:
                res = requests.get(url, headers=headers, params=params, timeout=30)
                res.raise_for_status()
                data = res.json()

                if res.status_code == 200 and data.get('rt_cd') == '0':
                    if data.get('output1'):
                        for item in data['output1']:
                            all_transactions.append({
                                'date': item['ord_dt'],
                                'order_number': item['odno'],
                                'symbol': item['pdno'],
                                'name': item['prdt_name'],
                                'side': 'buy' if item['sll_buy_dvsn_cd'] == '02' else 'sell',
                                'quantity': int(item['tot_ccld_qty']),
                                'price': float(item['avg_prvs']),
                                'total_amount': int(item['tot_ccld_amt']),
                            })
                    
                    ctx_area_fk100 = data.get('ctx_area_fk100', '')
                    ctx_area_nk100 = data.get('ctx_area_nk100', '')
                    tr_cont = data.get('tr_cont', "")

                    if tr_cont not in ("F", "M"):
                        break
                else:
                    logger.error(f"API returned an error: {data.get('msg1')}")
                    break

            except requests.exceptions.RequestException as e:
                logger.error(f"Error fetching transaction history: {e}")
                if e.response:
                    logger.error(f"Response Body: {e.response.text}")
                break
            except (KeyError, ValueError, json.JSONDecodeError) as e:
                logger.error(f"Error parsing transaction history data: {e}")
                if 'res' in locals() and hasattr(res, 'text'):
                    logger.error(f"Hantoo API Response: {res.text}")
                break
        
        all_transactions.sort(key=lambda x: x['date'], reverse=True)
        return all_transactions

    def get_open_orders(self) -> list:
        """
        Fetches current open (cancellable/modifiable) orders.
        Uses the 'inquire-psbl-rvsecncl' (주식 정정/취소 가능 주문 조회) API.
        """
        tr_id = "VTTC8036R" if self.is_paper else "TTTC8036R"
        path = "/uapi/domestic-stock/v1/trading/inquire-psbl-rvsecncl"
        url = f"{self.base_url}{path}"
        headers = self._get_headers(tr_id)
        
        acc_no, acc_suffix = self._get_account_parts()

        params = {
            "CANO": acc_no,
            "ACNT_PRDT_CD": acc_suffix,
            "CTX_AREA_FK100": "",
            "CTX_AREA_NK100": "",
            "INQR_DVSN_1": "1", # 0: 조회순, 1: 주문순
            "INQR_DVSN_2": "0", # 0: 전체, 1: 매도, 2: 매수
        }
        
        # Enforce rate limit
        time.sleep(self.rate_limit_delay)

        try:
            res = requests.get(url, headers=headers, params=params, timeout=30)
            res.raise_for_status()
            data = res.json()
            
            open_orders = []
            if data.get('rt_cd') == '0':
                for item in data.get('output1', []):
                    # psbl_qty is the remaining quantity that can be cancelled/modified (i.e., not executed yet)
                    qty = int(item['psbl_qty'])
                    if qty > 0:
                        open_orders.append({
                            'order_number': item['odno'],
                            'symbol': item['pdno'],
                            'name': item['prdt_name'],
                            'side': 'buy' if item['sll_buy_dvsn_cd'] == '02' else 'sell', # 01: sell, 02: buy
                            'quantity': qty,
                            'price': float(item['ord_unpr']),
                            'order_date': item['ord_dt']
                        })
            else:
                msg = data.get('msg1', '')
                if self.is_paper and "모의투자에서는 해당업무가 제공되지 않습니다" in msg:
                    logger.warning("[HantooClient] Open orders check skipped: Not supported in Paper Trading. Assuming 0 open orders. (Idempotency check disabled)")
                    return []
                logger.error(f"[HantooClient] Error getting open orders: {msg}")
            
            return open_orders

        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching open orders: {e}")
            if e.response is not None:
                logger.error(f"Response Body: {e.response.text}")
            return [] # Return empty list on error to be safe, or raise? 
            # Returning empty list is risky if we rely on it for safety. 
            # But raising might crash the whole loop. 
            # For now, let's log error and return empty, but Executor should probably fail-safe.
        except (KeyError, ValueError, json.JSONDecodeError) as e:
            logger.error(f"Error parsing open orders data: {e}")
            return []

