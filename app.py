from flask import Flask, request, jsonify
import requests, os, hmac, hashlib, time, json
from datetime import datetime

app = Flask(__name__)

TELEGRAM_TOKEN   = os.environ.get("TELEGRAM_TOKEN",   "7916314680:AAEr1gcNI1DAQGNL2bvxL1VJ5h_Uq5Rv3-w")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "384728743")
WEBHOOK_SECRET   = os.environ.get("WEBHOOK_SECRET",   "bybit2024")
BYBIT_API_KEY    = os.environ.get("BYBIT_API_KEY",    "igo1oiqmAHSPVJWVeQ")
BYBIT_API_SECRET = os.environ.get("BYBIT_API_SECRET", "8mPzVVVzziZkCt1fhqnypNBXH8bFHNljCJGe")
BYBIT_BASE_URL   = "https://api.bybit.com"

def send_telegram(message):
    try:
        requests.post(
            f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
            data={"chat_id": TELEGRAM_CHAT_ID, "text": message, "parse_mode": "HTML"},
            timeout=10
        )
    except Exception as e:
        print(f"Telegram error: {e}")

def bybit_request(endpoint, params):
    try:a
        ts        = str(int(time.time() * 1000))
        recv_win  = "5000"
        body_str  = json.dumps(params)
        sign_str  = ts + BYBIT_API_KEY + recv_win + body_str
        signature = hmac.new(
            BYBIT_API_SECRET.encode("utf-8"),
            sign_str.encode("utf-8"),
            hashlib.sha256
        ).hexdigest()
        headers = {
            "X-BAPI-API-KEY":     BYBIT_API_KEY,
            "X-BAPI-TIMESTAMP":   ts,
            "X-BAPI-SIGN":        signature,
            "X-BAPI-RECV-WINDOW": recv_win,
            "Content-Type":       "application/json"
        }
        r = requests.post(BYBIT_BASE_URL + endpoint, data=body_str, headers=headers, timeout=10)
        return r.json()
    except Exception as e:
        print(f"Bybit error: {e}")
        return {"retCode": -1, "retMsg": str(e)}

def set_leverage(symbol, leverage):
    return bybit_request("/v5/position/set-leverage", {
        "category":     "linear",
        "symbol":       symbol,
        "buyLeverage":  str(leverage),
        "sellLeverage": str(leverage)
    })

def open_position(symbol, side, qty, sl, tp1):
    return bybit_request("/v5/order/create", {
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
            set_leverage(symbol, leverage)
            result   = open_position(symbol, side, qty, sl, tp1)
            ret_code = result.get("retCode", -1)
            ret_msg  = result.get("retMsg", "Bilinmeyen hata")
            if ret_code == 0:
                msg = (f"{emoji} <b>{signal} AÇILDI — {symbol}</b>\n"
                       f"━━━━━━━━━━━━━━━━━━\n"
                       f"📍 Giriş: <b>{entry}$</b>\n"
                       f"🛑 SL: <b>{sl}$</b> (-{risk}$)\n"
                       f"🎯 TP1: <b>{tp1}$</b>\n"
                       f"🎯 TP2: <b>{tp2}$</b>\n"
                       f"⚡ Kaldıraç: <b>{leverage}x</b>\n"
                       f"📦 Miktar: <b>{qty}</b>\n"
                       f"━━━━━━━━━━━━━━━━━━\n"
                       f"✅ Bybit'e gönderildi\n🕐 {now}")
            else:
                msg = (f"⚠️ <b>{signal} HATASI — {symbol}</b>\n"
                       f"━━━━━━━━━━━━━━━━━━\n"
                       f"❌ Hata: {ret_msg}\n"
                       f"📋 Kod: {ret_code}\n🕐 {now}")
        elif signal == "TP1":
            msg = (f"✅ <b>TP1 HIT — {symbol}</b>\n"
                   f"💰 Kar: <b>+{float(risk)*1.5:.1f}$</b>\n"
                   f"🎯 TP2 bekleniyor: {tp2}$\n🕐 {now}")
        elif signal == "TP2":
            msg = (f"🏆 <b>TP2 HIT — {symbol}</b>\n"
                   f"💰 Toplam Kar: <b>+{float(risk)*5.0:.1f}$</b>\n"
                   f"✅ Pozisyon kapandı\n🕐 {now}")
        elif signal == "SL":
            msg = (f"❌ <b>STOP LOSS — {symbol}</b>\n"
                   f"💸 Zarar: <b>-{risk}$</b>\n"
                   f"🔄 Yeni sinyal bekleniyor\n🕐 {now}")
        else:
            msg = f"⚡ {signal} | {symbol} | {now}"

        send_telegram(msg)
        return jsonify({"status": "ok", "signal": signal})
    except Exception as e:
        print(f"Webhook error: {e}")
        return jsonify({"error": str(e)}), 500

@app.route("/test", methods=["GET"])
def test():
    if request.args.get("secret") != WEBHOOK_SECRET:
        return jsonify({"error": "Unauthorized"}), 401
    now = datetime.now().strftime("%d.%m.%Y %H:%M")
    send_telegram(f"✅ <b>TEST MESAJI</b>\n🕐 {now}\nBot çalışıyor!")
    return jsonify({"status": "ok"})

@app.route("/", methods=["GET"])
def health():
    return jsonify({"status": "CVİS Bot calisiyor!"})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
