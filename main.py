import json
from flask import Flask, request
from ib_insync import *

app = Flask(__name__)

# Load config
with open('config.json') as f:
    CONFIG = json.load(f)

# Connect to IBKR gateway (paper or live)
ib = IB()
host = '127.0.0.1'
port = 7497 if CONFIG["use_paper"] else 7496
ib.connect(host, port, clientId=1)

@app.route('/webhook', methods=['POST'])
def webhook():
    data = request.json
    symbol = data.get('symbol', CONFIG["default_symbol"])
    action = data.get('action', 'BUY').upper()
    qty    = int(data.get('qty', CONFIG["default_qty"]))
    sl_pct = float(data.get('stop_loss_pct', CONFIG["stop_loss_pct"]))

    # Prepare contract
    contract = Stock(symbol, 'SMART', 'USD')
    ib.qualifyContracts(contract)

    # Market price + SL calc
    market_price = ib.reqMktData(contract, '', False, False).last
    if market_price is None:
        return {"status": "error", "msg": "no market price"}, 400

    sl_price = market_price * (1 - sl_pct) if action == 'BUY' else market_price * (1 + sl_pct)

    # Place order
    order = MarketOrder(action, qty)
    trade = ib.placeOrder(contract, order)
    print(f"[WEBHOOK] {action} {qty} {symbol} @ market (≈{market_price}), SL≈{sl_price}")

    return {"status": "success"}, 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
