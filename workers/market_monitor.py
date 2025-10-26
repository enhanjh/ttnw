
import os
import sys
import json
import threading
import websocket
from dotenv import load_dotenv

# Add project root to Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from workers.tasks import execute_trade_task
from core.api_clients.hantoo_client import HantooClient
# TODO: Dynamically load strategy
from core.strategies.buy_and_hold import BuyAndHoldStrategy

# --- Configuration ---
load_dotenv()
BROKER_PROVIDER = 'hantoo_vps' # For paper trading
BROKER_ACCOUNT_NO = os.getenv('BROKER_ACCOUNT_NO')
# TODO: Make the list of symbols to monitor configurable
SYMBOLS_TO_MONITOR = ["005930"] # Example: Samsung Electronics

# --- WebSocket Event Handlers ---

def on_message(ws, message):
    """Called when a message is received from the WebSocket server."""
    try:
        # The first character of the message determines its type
        if message[0] in ['0', '1']: # Real-time execution data
            parts = message.split('|')
            if len(parts) > 1 and parts[1] == "H0STCNT0": # KRX Stock Execution
                process_execution_data(parts)
        elif message[0] == '{': # JSON message (e.g., connection response)
            data = json.loads(message)
            print(f"[INFO] Received JSON message: {data}")
        else:
            print(f"[INFO] Received other message: {message}")

    except Exception as e:
        print(f"[ERROR] Error in on_message: {e}")

def process_execution_data(data_parts):
    """Processes real-time execution data and triggers tasks."""
    # data_parts[2] contains the actual data fields, separated by '^'
    fields = data_parts[2].split('^')
    
    # Key data points from API spec (H0STCNT0)
    symbol = fields[0]
    price = int(fields[2])
    volume = int(fields[12])
    
    print(f"[DATA] Symbol: {symbol}, Price: {price}, Volume: {volume}")

    # --- Simple Strategy Logic Example ---
    # If Samsung Electronics price drops below 75,000, send a buy signal.
    if symbol == "005930" and price < 75000:
        print(f"[SIGNAL] Price for {symbol} is {price}, which is below 75000. Sending buy signal.")
        
        # Call the Celery task to execute the trade
        execute_trade_task.delay(
            symbol=symbol,
            side='buy', 
            quantity=1, 
            price=str(price), # Pass price as string as per order API
            broker_provider=BROKER_PROVIDER, 
            broker_account_no=BROKER_ACCOUNT_NO
        )
    # --- End of Strategy Logic ---


def on_error(ws, error):
    """Called on WebSocket error."""
    print(f"[ERROR] WebSocket error: {error}")

def on_close(ws, close_status_code, close_msg):
    """Called when the WebSocket connection is closed."""
    print(f"[INFO] WebSocket connection closed: {close_status_code} - {close_msg}")

def on_open(ws):
    """Called when the WebSocket connection is established."""
    print("[INFO] WebSocket connection opened. Subscribing to real-time data...")
    
    # Subscribe to real-time execution data for the specified symbols
    for symbol in SYMBOLS_TO_MONITOR:
        subscription_request = {
            "header": {
                "approval_key": APPROVAL_KEY,
                "custtype": "P",
                "tr_type": "1", # 1: Register, 2: Unregister
                "content-type": "utf-8"
            },
            "body": {
                "input": {
                    "tr_id": "H0STCNT0", # Real-time KRX stock execution price
                    "tr_key": symbol
                }
            }
        }
        ws.send(json.dumps(subscription_request))
        print(f"[INFO] Sent subscription request for {symbol}")

# --- Main Execution ---

if __name__ == "__main__":
    print("Starting Market Monitor...")

    if not BROKER_ACCOUNT_NO:
        print("[ERROR] BROKER_ACCOUNT_NO environment variable not set.")
        sys.exit(1)

    try:
        # 1. Initialize HantooClient to get the approval key
        client = HantooClient(BROKER_PROVIDER, BROKER_ACCOUNT_NO)
        APPROVAL_KEY = client.get_ws_approval_key()
        
        if not APPROVAL_KEY:
            print("[ERROR] Could not get WebSocket approval key.")
            sys.exit(1)
            
        # 2. Initialize Strategy
        # strategy = BuyAndHoldStrategy(...) # TODO: Initialize with proper params

        # 3. Setup and run WebSocket client
        if 'vps' in BROKER_PROVIDER:
            ws_url = "ws://ops.koreainvestment.com:31000" # Paper trading
        else:
            ws_url = "ws://ops.koreainvestment.com:21000" # Real trading
        
        print(f"[INFO] Connecting to WebSocket URL: {ws_url}")

        ws_app = websocket.WebSocketApp(ws_url,
                                      on_open=on_open,
                                      on_message=on_message,
                                      on_error=on_error,
                                      on_close=on_close)
        
        # Run the websocket in a separate thread
        wst = threading.Thread(target=ws_app.run_forever)
        wst.daemon = True
        wst.start()
        print("[INFO] Market Monitor is running. Press Ctrl+C to stop.")

        # Keep the main thread alive
        while True:
            threading.Event().wait(1)

    except KeyboardInterrupt:
        print("[INFO] Stopping Market Monitor...")
        ws_app.close()
    except Exception as e:
        print(f"[ERROR] An unexpected error occurred: {e}")

