import os
import asyncio
import requests
from datetime import datetime
from typing import Dict, Optional

from backend.database import init_db, close_db
from backend.models import Portfolio, Asset
from core.api_clients.hantoo_client import HantooClient

class OrderManager:
    """
    Handles the execution of orders via the broker client and records transactions
    to the backend system.
    """
    def __init__(self, broker_provider: str, broker_account_no: str):
        self.broker_provider = broker_provider
        self.broker_account_no = broker_account_no
        self.client = HantooClient(broker_provider, broker_account_no)
        self.backend_api_url = os.getenv("BACKEND_API_URL", "http://127.0.0.1:8000")

    async def execute_order(self, symbol: str, quantity: int, price: float, side: str, order_type: str = 'market') -> Dict:
        """
        Executes an order and records the transaction if successful.
        
        Args:
            symbol: The asset symbol.
            quantity: Number of shares.
            price: Price per share (0 for market orders usually, but needed for recording).
            side: 'buy' or 'sell'.
            order_type: 'market' or 'limit'.
            
        Returns:
            Dict containing the status and result of the order.
        """
        # 1. Place Order via Broker Client
        # TODO: Make HantooClient async to avoid blocking the event loop
        try:
            # Run blocking IO in a separate thread
            loop = asyncio.get_running_loop()
            order_result = await loop.run_in_executor(
                None,
                lambda: self.client.place_order(symbol, quantity, price if price > 0 else 0, side, order_type=order_type)
            )
        except Exception as e:
            return {"status": "error", "message": f"Broker exception: {str(e)}"}

        # 2. Handle Result
        if order_result and order_result.get('status') == 'success':
            print(f"[SUCCESS] {side.upper()} order for {symbol} placed. Result: {order_result}")
            
            # 3. Record Transaction
            # We record the price passed in (which might be current market price) 
            # because the actual execution price might not be immediately available depending on the broker API response.
            await self._record_transaction_via_api(symbol, quantity, price, side)
            
            return {"status": "success", "result": order_result}
        else:
            error_msg = order_result.get('message', 'Unknown error') if order_result else 'No response'
            return {"status": "failed", "message": error_msg}

    async def _record_transaction_via_api(self, symbol: str, quantity: float, price: float, side: str):
        """Asynchronously records a transaction by calling the backend API."""
        
        portfolio_id, asset_id = None, None
        try:
            # We need to find the portfolio ID associated with this broker account
            # This logic assumes one portfolio per account for now
            # Note: init_db/close_db usages might need refinement if connection pooling is used globally
            await init_db()
            portfolio = await Portfolio.find_one(
                Portfolio.broker_provider == self.broker_provider,
                Portfolio.broker_account_no == self.broker_account_no
            )
            asset = await Asset.find_one(Asset.symbol == symbol)
            
            if portfolio:
                portfolio_id = portfolio.id
            if asset:
                asset_id = asset.id
        except Exception as e:
            print(f"[API_ERROR] DB lookup failed: {e}")
            return
        finally:
             # In a highly concurrent async env, closing might be risky if shared, 
             # but here we follow the pattern of opening/closing per logical unit if no global lifespan exists.
             # However, since init_db is typically global, repeatedly calling it might be redundant but safe if idempotent.
             # close_db() # Skipping close_db to avoid closing shared connections in Celery or FastAPI context unexpectedly
             pass

        if not portfolio_id or not asset_id:
            print(f"[API_ERROR] Could not get portfolio/asset ID for {symbol}. Transaction not recorded.")
            return

        try:
            payload = {
                "asset_id": str(asset_id),
                "portfolio_id": str(portfolio_id),
                "transaction_type": side,
                "quantity": quantity,
                "price": price,
                "transaction_date": datetime.now().isoformat(),
            }
            
            api_endpoint = f"{self.backend_api_url}/api/transactions/"
            
            loop = asyncio.get_running_loop()
            response = await loop.run_in_executor(
                None, 
                lambda: requests.post(api_endpoint, json=payload)
            )

            if response.status_code == 200:
                print(f"[API_SUCCESS] Successfully recorded {side} of {quantity} {symbol} via API.")
            else:
                print(f"[API_ERROR] Failed to record transaction for {symbol}. Status: {response.status_code}, Response: {response.text}")

        except Exception as e:
            print(f"[API_ERROR] An exception occurred while recording transaction for {symbol}: {e}")
