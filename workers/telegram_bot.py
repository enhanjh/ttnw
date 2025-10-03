import asyncio
import logging
import os
import sys
from datetime import datetime, timedelta

# Add project root to sys.path to allow importing backend modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler
from telegram.constants import ParseMode

from backend.database import init_db
from backend import models, portfolio_calculator, data_collector

# Load environment variables
load_dotenv()

# Logging setup
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    await update.message.reply_text(
        f"안녕하세요! 포트폴리오 비서입니다.\n"
        f"당신의 텔레그램 ID: `{user_id}`\n\n"
        "**사용 가능한 명령어:**\n"
        "/help - 도움말 및 내 ID 확인\n"
        "/portfolio - 내 포트폴리오 및 보유 자산 조회\n\n"
        "데이터를 조회하려면 관리자에게 위 ID를 포트폴리오 권한에 추가해달라고 요청하세요.",
        parse_mode=ParseMode.MARKDOWN
    )

async def portfolio(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    logger.info(f"Received /portfolio command from user {user_id}")

    # Find portfolios where this user is allowed
    # distinct allowed_telegram_ids might need In operator
    # Beanie 'In' operator usage: models.Portfolio.find(models.Portfolio.allowed_telegram_ids == user_id) 
    # Logic: if user_id is in the list allowed_telegram_ids. 
    # MongoDB query: { "allowed_telegram_ids": user_id } matches if the array contains the value.
    
    portfolios = await models.Portfolio.find(models.Portfolio.allowed_telegram_ids == user_id).to_list()

    if not portfolios:
        await update.message.reply_text("조회 가능한 포트폴리오가 없습니다. 권한 설정을 확인해주세요.")
        return
    await update.message.reply_text(f"보유 중인 포트폴리오 {len(portfolios)}개를 찾았습니다. 데이터를 불러오는 중...")

    for pf in portfolios:
        try:
            msg = f"📂 **포트폴리오: {pf.name}**\n"
            msg += f"환경: {'실전' if pf.environment == 'live' else '백테스트'}\n"
            
            transactions = await models.Transaction.find(models.Transaction.portfolio_id == pf.id).to_list()
            holdings_data = portfolio_calculator.calculate_current_holdings(transactions)

            if not holdings_data:
                msg += "보유 중인 자산이 없습니다.\n"
                await update.message.reply_text(msg, parse_mode=ParseMode.MARKDOWN)
                continue

            asset_ids = list(holdings_data.keys())
            assets = await models.Asset.find({"_id": {"$in": asset_ids}}).to_list()
            asset_map = {a.id: a for a in assets}

            total_portfolio_value = 0.0
            total_invested_amount = 0.0
            
            # Prepare data for message
            holdings_list = []
            
            end_date = datetime.now().strftime('%Y-%m-%d')
            start_date = (datetime.now() - timedelta(days=5)).strftime('%Y-%m-%d')

            for asset_id, data in holdings_data.items():
                asset = asset_map.get(asset_id)
                if not asset:
                    continue
                
                symbol = asset.symbol
                name = asset.name
                quantity = data['quantity']
                avg_price = data['average_price']
                
                current_price = avg_price # Fallback
                try:
                    df = data_collector.get_stock_data(symbol, start_date, end_date)
                    if not df.empty:
                        current_price = float(df['Close'].iloc[-1])
                except Exception as e:
                    logger.error(f"Error fetching price for {symbol}: {e}")

                current_value = quantity * current_price
                invested_amount = quantity * avg_price
                
                total_portfolio_value += current_value
                total_invested_amount += invested_amount
                
                return_pct = 0.0
                if invested_amount > 0:
                    return_pct = ((current_value - invested_amount) / invested_amount) * 100
                
                holdings_list.append({
                    "symbol": symbol,
                    "name": name,
                    "qty": quantity,
                    "val": current_value,
                    "ret": return_pct
                })

            # Calculate total portfolio return
            total_profit_loss = total_portfolio_value - total_invested_amount
            total_return_pct = 0.0
            if total_invested_amount > 0:
                total_return_pct = (total_profit_loss / total_invested_amount) * 100

            msg += f"💵 총 매수금액: {total_invested_amount:,.0f} KRW\n"
            msg += f"💰 총 평가액: {total_portfolio_value:,.0f} KRW\n"
            msg += f"📊 총 수익금액: {total_profit_loss:+,.0f} KRW\n"
            msg += f"📈 총 수익률: {total_return_pct:+.2f}%\n"
            msg += "------------------------\n"
            
            for h in holdings_list:
                icon = "🔴" if h['ret'] > 0 else "🔵" if h['ret'] < 0 else "⚪"
                msg += f"{icon} **{h['name']}** ({h['symbol']})\n"
                msg += f"   수량: {h['qty']:.2f} | 평가: {h['val']:,.0f}\n"
                msg += f"   수익: {h['ret']:+.2f}%\n"
            
            await update.message.reply_text(msg, parse_mode=ParseMode.MARKDOWN)

        except Exception as e:
            logger.error(f"Error processing portfolio {pf.name}: {e}")
            await update.message.reply_text(f"포트폴리오 {pf.name} 처리 중 오류가 발생했습니다.")

async def post_init(application: ApplicationBuilder) -> None:
    """Initialize database after bot application starts"""
    await init_db()
    logger.info("Database initialized.")

def main():
    if not TELEGRAM_TOKEN:
        logger.error("TELEGRAM_BOT_TOKEN is not set in environment variables.")
        return

    # Create the application
    application = ApplicationBuilder().token(TELEGRAM_TOKEN).post_init(post_init).build()

    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("portfolio", portfolio))

    logger.info("Bot started. Polling...")
    
    # Run the bot (this handles the event loop automatically)
    application.run_polling()

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        pass
