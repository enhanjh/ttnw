from fastapi import APIRouter, HTTPException
from typing import List, Optional
from beanie import PydanticObjectId
from .. import models, schemas
from ..database import get_client
import re

router = APIRouter(
    prefix="/api/transactions",
    tags=["transactions"],
)

@router.post("/", response_model=schemas.Transaction)
async def create_transaction(transaction: schemas.TransactionCreate):
    # Manually start a session
    db_client = get_client() # Get the client at runtime
    async with await db_client.start_session() as session:
        # Start a transaction
        async with session.start_transaction():
            try:
                # 1. Fetch the linked documents
                db_asset = await models.Asset.get(transaction.asset_id, session=session)
                if not db_asset:
                    raise HTTPException(status_code=404, detail="Asset not found")

                db_portfolio = await models.Portfolio.get(transaction.portfolio_id, session=session)
                if not db_portfolio:
                    raise HTTPException(status_code=404, detail="Portfolio not found")

                # 2. Prepare and insert the primary transaction
                transaction_data = transaction.dict()
                db_transaction = models.Transaction(**transaction_data)
                await db_transaction.insert(session=session)

                # 3. Automatic cash transaction logic
                if db_transaction.transaction_type in ['buy', 'sell']:
                    currency = None
                    if db_asset.asset_type == 'stock_us':
                        currency = 'USD'
                    elif db_asset.asset_type.startswith('stock_kr'):
                        currency = 'KRW'

                    if currency:
                        cash_symbol_pattern = re.compile(f"cash_{currency.lower()}", re.IGNORECASE)
                        cash_asset = await models.Asset.find_one(
                            models.Asset.asset_type == 'cash',
                            models.Asset.symbol == cash_symbol_pattern,
                            models.Asset.portfolio_id == db_portfolio.id,
                            session=session
                        )
                        if not cash_asset:
                            raise HTTPException(status_code=400, detail=f"Cash asset for currency {currency} not found in this portfolio. Please add it first.")

                        # Calculate cash amount
                        cash_amount = db_transaction.quantity * db_transaction.price
                        cash_transaction_type = ''
                        final_cash_amount = 0.0

                        if db_transaction.transaction_type == 'buy':
                            cash_transaction_type = 'withdrawal'
                            final_cash_amount = cash_amount + db_transaction.fee
                        elif db_transaction.transaction_type == 'sell':
                            cash_transaction_type = 'deposit'
                            final_cash_amount = cash_amount - db_transaction.fee - db_transaction.tax

                        # Create and insert the cash transaction
                        cash_transaction_data = {
                            'asset_id': cash_asset.id,
                            'portfolio_id': db_portfolio.id,
                            'transaction_type': cash_transaction_type,
                            'quantity': final_cash_amount,
                            'price': 1, # Price for cash is always 1
                            'transaction_date': db_transaction.transaction_date,
                            'fee': 0, # Fee is already accounted for
                            'tax': 0, # Tax is already accounted for
                        }
                        db_cash_transaction = models.Transaction(**cash_transaction_data)
                        await db_cash_transaction.insert(session=session)

                return db_transaction

            except HTTPException as e:
                # The transaction will be aborted automatically by the 'async with' block
                # re-raising the exception.
                raise e
            except Exception as e:
                # Any other unexpected error will also abort the transaction.
                import traceback
                traceback.print_exc() # Print traceback to server console
                raise HTTPException(status_code=500, detail=str(e))

@router.get("/", response_model=List[schemas.Transaction])
async def read_transactions(portfolio_id: Optional[PydanticObjectId] = None, skip: int = 0, limit: int = 100):
    if portfolio_id:
        query = models.Transaction.find(
            models.Transaction.portfolio_id == portfolio_id
        )
    else:
        query = models.Transaction.find_all()

    transactions_from_db = await query.skip(skip).limit(limit).to_list()
    return transactions_from_db

@router.get("/{transaction_id}", response_model=schemas.Transaction)
async def read_transaction(transaction_id: PydanticObjectId):
    transaction = await models.Transaction.get(transaction_id)
    if transaction is None:
        raise HTTPException(status_code=404, detail="Transaction not found")
    return transaction

@router.put("/{transaction_id}", response_model=schemas.Transaction)
async def update_transaction(transaction_id: PydanticObjectId, transaction: schemas.TransactionCreate):
    db_transaction = await models.Transaction.get(transaction_id)
    if db_transaction is None:
        raise HTTPException(status_code=404, detail="Transaction not found")
    
    update_data = transaction.dict(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_transaction, key, value)
    await db_transaction.save()
    return db_transaction

@router.delete("/{transaction_id}")
async def delete_transaction(transaction_id: PydanticObjectId):
    db_transaction = await models.Transaction.get(transaction_id)
    if db_transaction is None:
        raise HTTPException(status_code=404, detail="Transaction not found")
    await db_transaction.delete()
    return {"message": "Transaction deleted successfully"}