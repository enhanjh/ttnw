
import os
import requests
import json
import logging
from datetime import datetime, timedelta


class HantooClient:
    """
    A client for interacting with the Korea Investment & Securities (KIS) API.
    Handles authentication, token management, and provides methods for various API calls.
    """
    # Class-level variables to store the token and its expiry
    _access_token = None
    _token_expires_at = None

    def __init__(self, broker_provider: str, broker_account_no: str):
        if 'KIS' not in broker_provider:
            raise ValueError(f"Unsupported broker provider: {broker_provider}")

        self.is_paper = 'VPS' in broker_provider
        if self.is_paper:
            self.base_url = "https://openapivts.koreainvestment.com:29443"
        else: # Assumes production
            self.base_url = "https://openapi.koreainvestment.com:9443"
        
        self.app_key = os.getenv("HANTOO_APP_KEY")
        self.app_secret = os.getenv("HANTOO_APP_SECRET")
        self.account_no = broker_account_no

        if not all([self.app_key, self.app_secret, self.account_no]):
            raise ValueError("Hantoo API credentials or account number are not set.")

    def _authenticate(self):
        """ Fetches and stores a new access token at the class level. """
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
            HantooClient._access_token = f"Bearer {data['access_token']}"
            # Set expiry time with a small buffer
            HantooClient._token_expires_at = datetime.now() + timedelta(seconds=data['expires_in'] - 60)
            print("Hantoo API authentication successful.")
        except requests.exceptions.RequestException as e:
            print(f"Hantoo API authentication failed: {e}")
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
            print(f"Hantoo API WS approval key failed: {e}")
            raise

    def _get_headers(self, tr_id: str) -> dict:
        """ Checks token validity and returns required headers for API calls. """
        if HantooClient._token_expires_at is None or datetime.now() >= HantooClient._token_expires_at:
            print("Access token expired or not found. Re-authenticating...")
            self._authenticate()
        
        return {
            "content-type": "application/json; charset=utf-8",
            "authorization": HantooClient._access_token,
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
            print(f"Error fetching price for {symbol}: {e}")
            if e.response is not None:
                print(f"Response Body: {e.response.text}")
            return None
        except (KeyError, ValueError, json.JSONDecodeError) as e:
            print(f"Error parsing price data for {symbol}: {e}")
            # res가 정의되어 있는 경우, 응답 텍스트를 출력
            if 'res' in locals() and hasattr(res, 'text'):
                print(f"Hantoo API Response: {res.text}")
            return None

    def get_balance(self) -> dict:
        """ Fetches the current account balance and holdings. """
        tr_id = "VTTC8434R" if self.is_paper else "TTTC8434R"
        path = "/uapi/domestic-stock/v1/trading/inquire-balance"
        url = f"{self.base_url}{path}"
        headers = self._get_headers(tr_id)
        
        acc_no, acc_suffix = self.account_no.split('-')

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
            print(f"Error fetching balance: {e}")
            if e.response is not None:
                print(f"Response Body: {e.response.text}")
            return None
        except (KeyError, ValueError, IndexError, json.JSONDecodeError) as e:
            print(f"Error parsing balance data: {e}")
            if 'res' in locals() and hasattr(res, 'text'):
                print(f"Hantoo API Response: {res.text}")
            return None

    def place_order(self, symbol: str, quantity: int, price: int, side: str) -> dict:
        """ Places a new order. `side` can be 'buy' or 'sell'. """
        if side.lower() not in ['buy', 'sell']:
            raise ValueError("side must be either 'buy' or 'sell'")

        # Determine TR_ID based on side and environment
        tr_id_prefix = "VTT" if self.is_paper else "TTT"
        tr_id_suffix = "C0802U" if side.lower() == 'buy' else "C0801U"
        tr_id = tr_id_prefix + tr_id_suffix

        path = "/uapi/domestic-stock/v1/trading/order-cash"
        url = f"{self.base_url}{path}"
        headers = self._get_headers(tr_id)

        # The account number is split for the API call
        acc_no, acc_suffix = self.account_no.split('-')

        body = {
            "CANO": acc_no,
            "ACNT_PRDT_CD": acc_suffix,
            "PDNO": symbol,
            "ORD_DVSN": "01",  # 01: 지정가, 00: 시장가
            "ORD_QTY": str(quantity),
            "ORD_UNPR": str(price),
        }

        try:
            res = requests.post(url, headers=headers, data=json.dumps(body), timeout=30)
            res.raise_for_status()
            data = res.json()

            if data.get('rt_cd') == '0':
                return {'status': 'success', 'order_id': data.get('output', {}).get('ODNO'), 'message': data.get('msg1')}
            else:
                return {'status': 'failure', 'message': data.get('msg1', 'Unknown error')}

        except requests.exceptions.RequestException as e:
            print(f"Error placing order for {symbol}: {e}")
            return {'status': 'error', 'message': str(e)}
        except (KeyError, ValueError) as e:
            print(f"Error parsing order response for {symbol}: {e}")
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
        
        acc_no, acc_suffix = self.account_no.split('-')
        
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
                    print(f"API returned an error: {data.get('msg1')}")
                    break

            except requests.exceptions.RequestException as e:
                print(f"Error fetching transaction history: {e}")
                if e.response:
                    print(f"Response Body: {e.response.text}")
                break
            except (KeyError, ValueError, json.JSONDecodeError) as e:
                print(f"Error parsing transaction history data: {e}")
                if 'res' in locals() and hasattr(res, 'text'):
                    print(f"Hantoo API Response: {res.text}")
                break
        
        all_transactions.sort(key=lambda x: x['date'], reverse=True)
        return all_transactions

