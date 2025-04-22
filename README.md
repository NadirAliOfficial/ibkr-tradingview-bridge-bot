
# IBKR TradingView Bridge Bot

A flexible Python-based bridge that connects TradingView alerts (both manual and Pine Script) with Interactive Brokers (IBKR). Designed for algorithmic trading via webhook, this bot supports paper/live trading, Buy/Sell with Stop-Loss, and customizable configs.

---

## ✅ Features

- 📡 Accepts TradingView webhook alerts (manual or Pine Script)
- 🛒 Supports Buy/Sell market orders
- 🛡️ Customizable Stop-Loss (%-based)
- 🔁 Toggle between Paper and Live accounts via config
- 🧾 Includes alert templates and setup guide

---

## 🧠 Requirements

- IB Gateway or TWS running
- Python 3.7+
- `ib_insync` and `Flask` libraries

```bash
pip install ib_insync flask
```

---

## ⚙️ Setup

1. **Run IB Gateway** on Paper account (port `7497`)
2. Clone this repo:
```bash
git clone https://github.com/yourusername/ibkr-tradingview-bridge-bot.git
cd ibkr-tradingview-bridge-bot
```
3. Edit `config.json` to customize:
```json
{
  "use_paper": true,
  "default_symbol": "AAPL",
  "default_qty": 10,
  "stop_loss_pct": 0.02
}
```
4. Start the bot:
```bash
python main.py
```

---

## 🔔 Webhook Alert Format

Use this format in TradingView alert (manual or Pine Script):

```json
{
  "symbol": "AAPL",
  "action": "BUY",
  "qty": 5,
  "stop_loss_pct": 0.015
}
```

Webhook URL in TradingView:
```
http://<YOUR-IP>:5000/webhook
```

---

## 📋 Roadmap (Milestone 2)

- [ ] Take-Profit & trailing stop support
- [ ] Desktop/email alerts
- [ ] GUI or background daemon support
- [ ] Trade logging (CSV or JSON)

---

## 🛡️ License

MIT License

---

## 🤝 Contact

For help or feature requests, contact [@NadirAliOfficial](https://github.com/NadirAliOfficial).
