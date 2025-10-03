import os
import sys
import json
import threading
import time
import datetime
import pandas as pd
import websocket
from collections import defaultdict
from dotenv import load_dotenv
import logging # Import logging module

# Add project root to Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.api_clients.hantoo_client import HantooClient

# --- Configuration ---
load_dotenv()

# Settings
DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "market_data")
FLUSH_INTERVAL = 3600  # Seconds
BUFFER_LIMIT = 100000  # Records per symbol
SYMBOLS_TO_MONITOR = ["069500", "114800"] # KODEX 200, KODEX 인버스

BROKER_PROVIDER = 'KIS_PROD' # 'KIS_VPS' or 'KIS_PROD'
BROKER_ACCOUNT_NO = os.getenv('BROKER_ACCOUNT_NO')

# --- Logging Configuration ---
# You can adjust the level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
# In production, set to INFO or WARNING.
logging.basicConfig(level=logging.INFO, # Default log level
                    format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class ParquetRecorder:
    """
    Buffers real-time data and writes it to Parquet files periodically.
    Uses 'fastparquet' as the engine to avoid illegal instruction errors.
    """
    def __init__(self, base_dir):
        self.base_dir = base_dir
        self.buffer = defaultdict(list)
        self.lock = threading.Lock()
        
        if not os.path.exists(self.base_dir):
            os.makedirs(self.base_dir)
            logger.info(f"Created data directory: {self.base_dir}")

    def add_record(self, symbol, data):
        with self.lock:
            self.buffer[symbol].append(data)
            if len(self.buffer[symbol]) >= BUFFER_LIMIT:
                self.flush_symbol(symbol)

    def flush_all(self):
        with self.lock:
            for symbol in list(self.buffer.keys()):
                self.flush_symbol(symbol)

    def flush_symbol(self, symbol):
        data = self.buffer[symbol]
        if not data:
            return

        df = pd.DataFrame(data)
        
        today = datetime.datetime.now().strftime("%Y%m%d")
        daily_dir = os.path.join(self.base_dir, today)
        if not os.path.exists(daily_dir):
            os.makedirs(daily_dir)

        timestamp = datetime.datetime.now().strftime("%H%M%S_%f")
        filename = f"{symbol}_{timestamp}.parquet"
        filepath = os.path.join(daily_dir, filename)

        try:
            # Using fastparquet engine
            df.to_parquet(filepath, engine='fastparquet', compression='snappy')
            logger.info(f"{symbol}: Saved {len(df)} records to {filename}")
            self.buffer[symbol] = [] 
        except Exception as e:
            logger.error(f"Failed to save parquet: {e}")

# Global Recorder
recorder = ParquetRecorder(DATA_DIR)

class KoreaInvestmentWebSocket:
    """
    Manages WebSocket connection to Korea Investment Securities.
    Based on the official 'domestic_stock_examples_ws.py'.
    """
    def __init__(self, broker_provider, symbols):
        self.broker_provider = broker_provider
        self.symbols = symbols
        self.ws_app = None
        self.approval_key = None
        self.data_received = False
        
        # Determine URL
        if 'vps' in self.broker_provider:
            self.base_url = "ws://ops.koreainvestment.com:31000"
        else:
            self.base_url = "ws://ops.koreainvestment.com:21000"

    def get_approval_key(self):
        try:
            client = HantooClient(BROKER_PROVIDER, BROKER_ACCOUNT_NO)
            key = client.get_ws_approval_key()
            if not key:
                raise ValueError("Returned key is empty")
            return key
        except Exception as e:
            logger.error(f"Failed to get Approval Key: {e}")
            sys.exit(1)

    def on_open(self, ws):
        logger.info("Connected. Subscribing...")
        for symbol in self.symbols:
            self.subscribe(ws, symbol)

    def subscribe(self, ws, symbol):
        # Standard H0STCNT0 (Real-time Execution) Subscription
        req = {
            "header": {
                "approval_key": self.approval_key,
                "custtype": "P",
                "tr_type": "1", # 1: Register
                "content-type": "utf-8"
            },
            "body": {
                "input": {
                    "tr_id": "H0STCNT0", 
                    "tr_key": symbol
                }
            }
        }
        ws.send(json.dumps(req))
        logger.info(f"Request sent for {symbol}")

    def on_message(self, ws, message):
        # logger.debug(f"Received msg len: {len(message)}, prefix: {message[:10]}") # Uncomment for very verbose debug

        if message[0] in ['0', '1']:
            self.process_realtime_data(message)
        elif message.startswith('{'):
            msg = json.loads(message)
            if 'header' in msg and msg['header']['tr_id'] == 'PINGPONG':
                logger.info(f"PINGPONG received from server. Replying...")
                ws.send(message)
            else:
                logger.info(f"System Message: {msg.get('body', {}).get('msg1', message)}")
        else:
            logger.debug(f"Other Message: {message}")

    def process_realtime_data(self, message):
        try:
            parts = message.split('|')
            if len(parts) < 4:
                logger.warning(f"Invalid data format: {message}")
                return

            encrypt_flag = parts[0]
            tr_id = parts[1]
            raw_data = parts[3]

            if encrypt_flag == '1':
                logger.warning("Encrypted data received. Skipping.")
                return

            if tr_id == "H0STCNT0":
                self.parse_execution_data(raw_data)
            else:
                logger.info(f"Unhandled TR_ID: {tr_id}")

        except Exception as e:
            logger.error(f"Processing Error: {e}")

    def parse_execution_data(self, raw_data):
        fields = raw_data.split('^')
        try:
            symbol = fields[0]
            record = {
                "symbol": symbol,
                "time": fields[1],
                "price": int(fields[2]),
                "diff_sign": fields[3],
                "diff": int(fields[4]),
                "open": int(fields[7]),
                "high": int(fields[8]),
                "low": int(fields[9]),
                "volume": int(fields[12]),
                "accum_volume": int(fields[13]),
                "timestamp": datetime.datetime.now()
            }
            logger.debug(f"DATA: {symbol}: {record['price']}") # Use debug for data points
            recorder.add_record(symbol, record)
            self.data_received = True
        except (IndexError, ValueError) as e:
            logger.error(f"Parse fail: {e} | Data: {raw_data[:50]}...")

    def on_error(self, ws, error):
        logger.error(f"WebSocket Error: {error}")

    def on_close(self, ws, close_status_code, close_msg):
        logger.info(f"WebSocket Closed: {close_msg}")
        recorder.flush_all()

    def run(self):
        self.approval_key = self.get_approval_key()
        logger.info(f"Approval Key Obtained: {self.approval_key[:10]}...")

        self.ws_app = websocket.WebSocketApp(
            self.base_url,
            on_open=self.on_open,
            on_message=self.on_message,
            on_error=self.on_error,
            on_close=self.on_close
        )

        # Start shutdown checker thread
        shutdown_thread = threading.Thread(target=self.check_shutdown_time, daemon=True)
        shutdown_thread.start()

        self.ws_app.run_forever(ping_interval=100, ping_timeout=10)

    def check_shutdown_time(self):
        """Checks time every minute and closes connection at 16:00 or if holiday."""
        while True:
            now = datetime.datetime.now()
            
            # Holiday Check: If no real data by 10:00 AM, assume holiday/weekend
            if now.hour >= 10 and not self.data_received:
                logger.info("No market data received by 10:00 AM. Assuming holiday. Shutting down...")
                if self.ws_app:
                    self.ws_app.close()
                break

            # Regular Close at 16:00
            if now.hour >= 16:
                logger.info("Market closed (16:00). Shutting down...")
                if self.ws_app:
                    self.ws_app.close()
                break
            time.sleep(60)

def periodic_flush():
    while True:
        time.sleep(FLUSH_INTERVAL)
        recorder.flush_all()

def check_shutdown_time(ws_app):
    """Checks if it's time to shut down (16:00) and closes the WebSocket."""
    while True:
        now = datetime.datetime.now()
        if now.hour >= 16:
            logger.info("It's 16:00. Initiating shutdown...")
            ws_app.close()
            break
        time.sleep(60) # Check every minute

if __name__ == "__main__":
    logger.info("--- Market Data Recorder (Parquet / FastParquet) ---")
    
    if not BROKER_ACCOUNT_NO:
        logger.error("BROKER_ACCOUNT_NO not set.")
        sys.exit(1)

    # Start Flush Thread
    t = threading.Thread(target=periodic_flush, daemon=True)
    t.start()

    # Start WebSocket
    ks_ws = KoreaInvestmentWebSocket(BROKER_PROVIDER, SYMBOLS_TO_MONITOR)
    
    # Connect first to initialize ks_ws.ws_app (will happen inside run(), but we need reference)
    # Since run() blocks, we can't start the shutdown checker there easily without refactoring.
    # A better way: Start the shutdown checker thread just before run_forever, 
    # passing the app instance is tricky because it's created inside run().
    # Let's slightly refactor the run method or pass the checker to it.
    
    try:
        ks_ws.run()
    except KeyboardInterrupt:
        logger.info("Stopping...")
        recorder.flush_all()