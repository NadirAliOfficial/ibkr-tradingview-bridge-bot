
# IBKR TradingView Bridge Bot

A fast, secure, and customizable trading bot that acts as a bridge between TradingView webhook alerts and Interactive Brokers (IBKR) via the `ib_insync` API. Built with `FastAPI`, this bot listens for trading signals and executes real-time orders with configurable SL/TP logic.

---

## 🚀 Features

- Accepts TradingView webhook alerts (or any JSON POST requests)
- Executes market and limit orders via IBKR API
- Automatically attaches Stop Loss (SL) and Take Profit (TP) orders
- Supports canceling and closing positions
- Logs trades to a `.jsonl` file
- Configurable for paper trading and live environments

---

## 🛠 Requirements

- Python 3.9+
- Interactive Brokers TWS or IB Gateway running on localhost
- Market data subscription for real-time execution

---

## 🔧 Setup

```bash
# Clone the repo
git clone https://github.com/yourusername/ibkr-tradingview-bridge-bot.git
cd ibkr-tradingview-bridge-bot

# Setup virtual environment
python3 -m venv .venv
source .venv/bin/activate  # or .venv\Scripts\activate on Windows

# Install dependencies
pip install -r requirements.txt
```

---

## 🚦 Usage

### 1. Start IBKR (TWS or IB Gateway)
- Make sure it's running on `127.0.0.1:7497` (paper) or `7496` (live)

### 2. Run the bot
```bash
python trading_bot_milestone2.py
```

### 3. Send Webhook (Example `curl`)
```bash
curl -X POST http://127.0.0.1:8000/webhook \
  -H "Content-Type: application/json" \
  -H "X-API-KEY: 98cf0874d857d8f512205d6ea9f21881" \
  -d '{"symbol":"AAPL","action":"BUY","quantity":1,"order_type":"MKT"}'
```

---

## 🧠 Webhook JSON Format

```json
{
  "symbol": "AAPL",
  "action": "BUY",
  "quantity": 1,
  "order_type": "MKT",          # or "LMT"
  "limit_price": 174.50         # required if order_type is LMT
}
```

---

## ✅ Status Endpoint

You can verify if the bot is running and IBKR is connected:

```bash
curl http://127.0.0.1:8000/status
```

---

## 📜 License

MIT License. Use at your own risk. Not responsible for financial losses or broker issues.

---

## 🙏 Credits

Built by [Nadir Ali Khan / Team NAK] with ❤️ using:
- [ib_insync](https://github.com/erdewit/ib_insync)
- [FastAPI](https://fastapi.tiangolo.com/)
