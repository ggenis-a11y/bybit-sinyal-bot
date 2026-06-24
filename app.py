from flask import Flask, request, jsonify
import requests, os, hmac, hashlib, time, json
from datetime import datetime

app = Flask(__name__)

TELEGRAM_TOKEN   = os.environ.get("TELEGRAM_TOKEN",   "7916314680:AAEr1gcNI1DAQGNL2bvxL1VJ5h_Uq5Rv3-w")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "384728743")
WEBHOOK_SECRET   = os.environ.get("WEBHOOK_SECRET",   "bybit2024")
BYBIT_API_KEY    = os.environ.get("BYBIT_API_KEY",    "igo1oiqmAHSPVJWVeQ")
BYBIT_API_SECRET = os.environ.get("BYBIT_API_SECRET", "8mPzVVVzziZkCt1fhqnypNBXH8bFHNljCJGe")
BYBIT_URL        = "https://api.bybit.com"

def send_telegram(msg):
    try:
        requests.post(
            "https://api.telegram.org/bot" + TELEGRAM_TOKEN + "/sendMessage",
            data={"chat_id": TELEGRAM_CHAT_ID, "text": msg, "parse_mode": "HTML"},
            timeout=10
        )
    except Exception as e:
        print("Telegram error:", e)

def bybit_post(endpoint, params):
    try:
        ts      = str(int(time.time() * 1000))
        rw      = "5000"
        body    = json.dumps(params)
        sign_in = ts + BYBIT_API_KEY + rw + body
        sig     = hmac.new(BYBIT_API_SECRET.encode(), sign_in.encode(), hashlib.sha256).hexdigest()
        headers = {
            "X-BAPI-API-KEY":     BYBIT_API_KEY,
            "X-BAPI-TIMESTAMP":   ts,
            "X-BAPI-SIGN":        sig,
            "X-BAPI-RECV-WINDOW": rw,
            "Content-Type":       "application/json"
        }
        r = requests.post(BYBIT_URL + endpoint, data=body, headers=headers, timeout=10)
        print("STATUS:", r.status_code)
        print("RESPONSE:", r.text[:500])
        try:
            return r.json()
        except Exception as e:
            print("JSON parse error:", e)
            send_telegram("Bybit raw response:\n" + r.text[:300])
            return {"retCode": -1, "retMsg": r.text[:200]}
    except Exception as e:
        print("Bybit error:", e)
        return {"retCode": -1, "retMsg": str(e)}

@app.route("/webhook", methods=["POST"])
def webhook():
    if request.args.get("secret") != WEBHOOK_SECRET:
        return jsonify({"error": "Unauthorized"}), 401
    try:
        data     = request.get_json(force=True) or {}
        signal   = data.get("signal",   "")
        symbol   = data.get("symbol",   "ETHUSDT")
        entry    = data.get("entry",    "0")
        sl       = data.get("sl",       "0")
        tp1      = data.get("tp1",      "0")
        tp2      = data.get("tp2",      "0")
        risk     = data.get("risk",     "5")
        leverage = data.get("leverage", "10")
        qty      = data.get("qty",      "0.0014")
        now      = datetime.now().strftime("%d.%m.%Y %H:%M")

        if signal in ["LONG", "SHORT"]:
            side  = "Buy" if signal == "LONG" else "Sell"
            emoji = "🟢" if signal == "LONG" else "🔴"

            bybit_post("/v5/position/set-leverage", {
                "category": "linear",
                "symbol": symbol,
                "buyLeverage": str(leverage),
                "sellLeverage": str(leverage)
            })

            result = bybit_post("/v5/order/create", {
                "category":    "linear",
                "symbol":      symbol,
                "side":        side,
                "orderType":   "Market",
                "qty":         str(qty),
                "stopLoss":    str(sl),
                "takeProfit":  str(tp1),
                "timeInForce": "GTC",
                "positionIdx": 0
            })

            rc = result.get("retCode", -1)
            rm = result.get("retMsg", "Hata")

            if rc == 0:
                msg = (emoji + " " + signal + " ACILDI - " + symbol + "\n"
                       "Giris: " + entry + "$\n"
                       "SL: " + sl + "$\n"
                       "TP1: " + tp1 + "$\n"
                       "TP2: " + tp2 + "$\n"
                       "Kaldirac: " + str(leverage) + "x\n"
                       "Miktar: " + str(qty) + "\n"
                       "Bybit onayladi! " + now)
            else:
                msg = ("HATA " + signal + " " + symbol + "\n"
                       "Kod: " + str(rc) + "\n"
                       "Mesaj: " + rm + "\n" + now)
        elif signal == "TP1":
            msg = "TP1 HIT " + symbol + " Kar:+" + str(float(risk)*1.5) + "$ " + now
        elif signal == "TP2":
            msg = "TP2 HIT " + symbol + " Kar:+" + str(float(risk)*5.0) + "$ " + now
        elif signal == "SL":
            msg = "SL HIT " + symbol + " Zarar:-" + risk + "$ " + now
        else:
            msg = signal + " " + symbol + " " + now

        send_telegram(msg)
        return jsonify({"status": "ok"})
    except Exception as e:
        print("Error:", e)
        return jsonify({"error": str(e)}), 500

@app.route("/test", methods=["GET"])
def test():
    if request.args.get("secret") != WEBHOOK_SECRET:
        return jsonify({"error": "Unauthorized"}), 401
    send_telegram("TEST - Bot calisiyor! " + datetime.now().strftime("%H:%M"))
    return jsonify({"status": "ok"})

@app.route("/", methods=["GET"])
def health():
    return jsonify({"status": "ok"})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
