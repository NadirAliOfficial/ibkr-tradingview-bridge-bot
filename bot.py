import json
import time
import logging
import threading
import asyncio
from fastapi import FastAPI, Request, Header, HTTPException
from ib_insync import IB, Stock, MarketOrder, LimitOrder, StopOrder
import uvicorn
import random

import nest_asyncio
nest_asyncio.apply()


# === CONFIGURATION ===
config = {
    "PAPER_TRADING": True,
    "IB_HOST": "127.0.0.1",
    "IB_PORT_PAPER": 7497,
    "IB_PORT_LIVE": 7496,
    "CLIENT_ID": random.randint(1000, 9999),  # Use a random clientId to avoid conflicts
    "SL_PERCENT": 0.02,
    "TP_PERCENT": 0.04,
    "WEBHOOK_TOKEN": "98cf0874d857d8f512205d6ea9f21881",
    "LOG_FILE": "trading_bot.log",
    "TRADE_LOG_FILE": "trade_log.jsonl"
}

# Logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(config["LOG_FILE"]),
        logging.StreamHandler()
    ]
)

# Create global IB client
ib = None
ib_connected = False
connection_lock = threading.Lock()

# Function to handle ib_insync operations that need to run in the IB thread
def run_in_ib_thread(func, *args, **kwargs):
    global ib
    if ib is None or not ib.isConnected():
        raise Exception("IB not connected")
    
    # Use ib.waitOnUpdate() which is thread-safe instead of running in the event loop
    try:
        result = func(*args, **kwargs)
        ib.waitOnUpdate(timeout=10)  # Wait for any pending updates
        return result
    except Exception as e:
        logging.error(f"Error in IB operation: {str(e)}")
        raise

def ib_thread():
    global ib, ib_connected
    # Each thread needs its own event loop for ib_insync internals
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    with connection_lock:
        if ib is None:
            ib = IB()
        elif ib.isConnected():
            logging.info("IB already connected, skipping connection attempt")
            return
        
        port = config["IB_PORT_PAPER"] if config["PAPER_TRADING"] else config["IB_PORT_LIVE"]
        
        # Try to connect with exponential backoff
        max_retries = 3
        retry_delay = 2
        
        for attempt in range(max_retries):
            try:
                # Generate a new client ID for each attempt to avoid conflicts
                client_id = config["CLIENT_ID"] + attempt
                logging.info(f"Attempting connection with clientId {client_id}")
                
                if ib.isConnected():
                    ib.disconnect()
                    time.sleep(1)  # Give it a moment to fully disconnect
                
                ib.connect(config["IB_HOST"], port, clientId=client_id)
                ib_connected = True
                logging.info(f"✅ IBKR connected on port {port} with clientId {client_id}")
                break
            except Exception as e:
                logging.error(f"Connection attempt {attempt+1} failed: {str(e)}")
                if ib.isConnected():
                    try:
                        ib.disconnect()
                    except:
                        pass
                
                if attempt < max_retries - 1:
                    retry_delay = retry_delay * 2
                    logging.info(f"Retrying in {retry_delay} seconds...")
                    time.sleep(retry_delay)
                else:
                    logging.error("Failed to connect after maximum retries")
    
    if ib_connected and ib.isConnected():
        try:
            ib.run()  # starts the ib_insync event loop
        except Exception as e:
            logging.error(f"Error in IB event loop: {str(e)}")
            ib_connected = False

# Start IBKR thread
def ensure_connection():
    global ib, ib_connected, ib_thread_instance
    
    with connection_lock:
        if ib is None or not ib.isConnected():
            # If there's an existing thread, make sure it's not running
            if 'ib_thread_instance' in globals() and ib_thread_instance.is_alive():
                logging.info("Waiting for existing connection thread to complete")
                ib_thread_instance.join(timeout=5)
            
            logging.info("Starting new IB connection thread")
            ib_thread_instance = threading.Thread(target=ib_thread, daemon=True)
            ib_thread_instance.start()
            
            # Give it time to connect
            timeout = 10
            start_time = time.time()
            while time.time() - start_time < timeout:
                if ib_connected and ib is not None and ib.isConnected():
                    return True
                time.sleep(0.5)
            
            return ib_connected and ib is not None and ib.isConnected()
        else:
            return True

# Initial connection
ib_thread_instance = threading.Thread(target=ib_thread, daemon=True)
ib_thread_instance.start()
time.sleep(3)  # Give it time to establish the initial connection

# FastAPI
app = FastAPI()
positions = {}

@app.post("/webhook")
async def webhook(request: Request, x_api_key: str = Header(None)):
    global ib, ib_connected
    
    if x_api_key != config["WEBHOOK_TOKEN"]:
        raise HTTPException(status_code=401, detail="Invalid API token")
    
    # Ensure IB is connected before proceeding
    if not ensure_connection():
        raise HTTPException(status_code=503, detail="IB connection not available after retry")
    
    data = await request.json()
    logging.info(f"📩 Received alert: {data}")

    action = data.get("action", "").upper()
    symbol = data.get("symbol")
    quantity = data.get("quantity", 1)
    order_type = data.get("order_type", "MKT").upper()
    limit_price = data.get("limit_price")

    # CANCEL
    if action == "CANCEL":
        oid = data.get("order_id")
        if oid in positions:
            order_obj = positions[oid]["order_obj"]
            try:
                run_in_ib_thread(ib.cancelOrder, order_obj)
                logging.info(f"❌ Cancelled order {oid}")
                positions.pop(oid, None)
                return {"status": "success", "message": f"Cancelled order {oid}"}
            except Exception as e:
                return {"status": "error", "message": f"Error cancelling order: {str(e)}"}
        return {"status": "error", "message": "Order ID not found"}

    # CLOSE
    if action == "CLOSE":
        oid = data.get("order_id")
        pos = positions.pop(oid, None)
        if pos:
            try:
                side = "SELL" if pos["action"]=="BUY" else "BUY"
                mkt = MarketOrder(side, pos["quantity"])
                trade = run_in_ib_thread(ib.placeOrder, pos["contract"], mkt)
                logging.info(f"🔒 Closed position {oid}")
                return {"status": "success", "order_id": trade.order.orderId}
            except Exception as e:
                return {"status": "error", "message": f"Error closing position: {str(e)}"}
        return {"status": "error", "message": "Position not found"}

    # NEW BUY/SELL
    if action not in ("BUY","SELL") or not symbol:
        return {"status": "error", "message": "Invalid symbol or action"}

    try:
        contract = Stock(symbol, "SMART", "USD")
        run_in_ib_thread(ib.qualifyContracts, contract)

        if order_type=="MKT":
            order = MarketOrder(action, quantity)
        elif order_type=="LMT" and limit_price is not None:
            order = LimitOrder(action, quantity, float(limit_price))
        else:
            return {"status":"error","message":"Invalid order_type or missing limit_price"}

        trade = run_in_ib_thread(ib.placeOrder, contract, order)
        oid = trade.order.orderId
        logging.info(f"✅ Placed {order_type} order {oid}: {action} {quantity} {symbol}")

        # Determine fill price - use a thread-safe approach
        fill_price = None
        if order_type == "MKT":
            # Wait a bit for market orders to fill
            time.sleep(1)
            fill_price = trade.orderStatus.avgFillPrice
            if not fill_price or fill_price <= 0:
                # Try to get the current market price
                ticker = run_in_ib_thread(ib.reqMktData, contract)
                time.sleep(1)  # Wait for market data
                fill_price = ticker.marketPrice()
        else:
            fill_price = float(limit_price)
                
        # If we still don't have a price for stop loss calculation, use a default
        if not fill_price or fill_price <= 0:
            logging.warning(f"No valid price available for SL/TP calculation, skipping SL/TP orders")
            fill_price = None

        # Attach SL/TP
        sl = None
        tp = None
        if fill_price:
            if action=="BUY":
                sl = round(fill_price*(1-config["SL_PERCENT"]),2)
                tp = round(fill_price*(1+config["TP_PERCENT"]),2)
                slO = StopOrder("SELL", quantity, sl)
                tpO = LimitOrder("SELL", quantity, tp)
            else:
                sl = round(fill_price*(1+config["SL_PERCENT"]),2)
                tp = round(fill_price*(1-config["TP_PERCENT"]),2)
                slO = StopOrder("BUY", quantity, sl)
                tpO = LimitOrder("BUY", quantity, tp)
            grp = f"OCA_{oid}"
            slO.ocaGroup = tpO.ocaGroup = grp
            slO.ocaType = tpO.ocaType = 1
            run_in_ib_thread(ib.placeOrder, contract, slO)
            run_in_ib_thread(ib.placeOrder, contract, tpO)
            logging.info(f"🎯 SL={sl}, TP={tp}")

        positions[oid] = {
            "contract": contract,
            "action": action,
            "quantity": quantity,
            "order_obj": order
        }

        # Log to JSONL
        record = {
            "timestamp": time.time(),
            "order_id": oid,
            "symbol": symbol,
            "action": action,
            "quantity": quantity,
            "order_type": order_type,
            "limit_price": limit_price,
            "fill_price": fill_price,
            "sl_price": sl,
            "tp_price": tp
        }
        with open(config["TRADE_LOG_FILE"], "a") as f:
            f.write(json.dumps(record) + "\n")

        return {"status":"success","order_id":oid}
        
    except Exception as e:
        logging.error(f"Error placing order: {str(e)}")
        return {"status":"error","message":f"Order placement failed: {str(e)}"}

@app.get("/status")
async def status():
    """Check the status of the trading bot and IB connection"""
    return {
        "ib_connected": ib_connected and ib is not None and ib.isConnected(),
        "active_positions": len(positions),
        "paper_trading": config["PAPER_TRADING"]
    }

if __name__=="__main__":
    uvicorn.run("trading_bot_milestone2:app", host="0.0.0.0", port=8000)