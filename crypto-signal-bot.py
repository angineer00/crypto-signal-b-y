import os
import ccxt
import pandas as pd
import requests
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from dotenv import load_dotenv

load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
DEFAULT_PAIRS = os.getenv("DEFAULT_PAIRS", "BTC/USDT,ETH/USDT").split(",")
DEFAULT_TIMEFRAME = os.getenv("DEFAULT_TIMEFRAME", "1h")
USE_FUNDAMENTALS = os.getenv("USE_FUNDAMENTALS", "true").lower() == "true"
FEAR_GREED_FILTER = os.getenv("FEAR_GREED_FILTER", "true").lower() == "true"

exchange = ccxt.binance()

def get_fear_greed_index():
    try:
        data = requests.get("https://api.alternative.me/fng/?limit=1").json()
        return int(data['data'][0]['value'])
    except:
        return None

def get_signal(symbol, timeframe="1h"):
    bars = exchange.fetch_ohlcv(symbol, timeframe, limit=100)
    df = pd.DataFrame(bars, columns=["time", "open", "high", "low", "close", "volume"])
    df["EMA50"] = df["close"].ewm(span=50).mean()
    df["EMA200"] = df["close"].ewm(span=200).mean()

    last_close = df["close"].iloc[-1]
    ema50 = df["EMA50"].iloc[-1]
    ema200 = df["EMA200"].iloc[-1]

    signal = "Neutral"
    if ema50 > ema200 and last_close > ema50:
        signal = "Long ✅"
    elif ema50 < ema200 and last_close < ema50:
        signal = "Short ❌"

    if FEAR_GREED_FILTER:
        fng = get_fear_greed_index()
        if fng:
            if fng < 25 and signal == "Short ❌":
                signal = "Neutral (Extreme Fear)"
            elif fng > 75 and signal == "Long ✅":
                signal = "Neutral (Extreme Greed)"

    return f"Pair: {symbol}\nTimeframe: {timeframe}\nSignal: {signal}"

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("📊 Crypto Signal Bot çalışıyor! /signal kullan.")

async def signal(update: Update, context: ContextTypes.DEFAULT_TYPE):
    args = context.args
    if len(args) == 0:
        pairs = DEFAULT_PAIRS
        tf = DEFAULT_TIMEFRAME
    else:
        pairs = [args[0]]
        tf = args[1] if len(args) > 1 else DEFAULT_TIMEFRAME

    response = ""
    for p in pairs:
        try:
            response += get_signal(p, tf) + "\n\n"
        except Exception as e:
            response += f"{p} için hata: {str(e)}\n"

    await update.message.reply_text(response)

def main():
    app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("signal", signal))
    app.run_polling()

if __name__ == "__main__":
    main()
