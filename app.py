from flask import Flask, request, jsonify
import requests, os, hmac, hashlib, time
from datetime import datetime

app = Flask(__name__)

# ─────────────────────────────────────────────
# AYARLAR
# ─────────────────────────────────────────────
TELEGRAM_TOKEN   = os.environ.get("TELEGRAM_TOKEN",   "7916314680:AAEr1gcNI1DAQGNL2bvxL1VJ5h_Uq5Rv3-w")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "384728743")
WEBHOOK_SECRET   = os.environ.get("WEBHOOK_SECRET",   "bybit2024")
BYBIT_API_KEY    = os.environ.get("BYBIT_API_KEY",    "igo1oiqmAHSPVJWVeQ")
BYBIT_API_SECRET = os.environ.get("BYBIT_API_SECRET", "8mPzVVVzziZkCt1fhqnypNBXH8bFHNljCJGe")
BYBIT_BASE_URL   = "https://api.bybit.com"

# ─────────────────────────────────────────────
# TELEGRAM
# ─────────────────────────────────────────────
def send_telegram(message):
    requests.post(
        f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
        data={"chat_id": TELEGRAM_CHAT_ID, "text": message, "parse_mode": "HTML"}
    )

# ─────────────────────────────────────────────
# BYBIT API İMZA
# ─────────────────────────────────────────────
def bybit_sign(params: dict) -> dict:
    ts        = str(int(time.time() * 1000))
    recv_win  = "5000"
    param_str = ts + BYBIT_API_KEY + recv_win + "&".join([f"{k}={v}" for k, v in sorted(params.items())])
    signature = hmac.new(BYBIT_API_SECRET.encode(), param_str.encode(), hashlib.sha256).hexdigest()
    return {
        "X-BAPI-API-KEY":     BYBIT_API_KEY,
        "X-BAPI-TIMESTAMP":   ts,
        "X-BAPI-SIGN":        signature,
        "X-BAPI-RECV-WINDOW": recv_win,
        "Content-Type":       "application/json"
    }

def bybit_request(method, endpoint, params):
    headers = bybit_sign(params)
    url     = BYBIT_BASE_URL + endpoint
    if method == "POST":
        r = requests.post(url, json=params, headers=headers)
    else:
        r = requests.get(url, params=params, headers=headers)
    return r.json()

# ─────────────────────────────────────────────
# BYBIT — POZİSYON AÇ
# ─────────────────────────────────────────────
def open_position(symbol, side, qty, sl, tp1):
    params = {
        "category":         "linear",
        "symbol":           symbol,
        "side":             side,          # Buy / Sell
        "orderType":        "Market",
        "qty":              str(qty),
        "stopLoss":         str(sl),
        "takeProfit":       str(tp1),
        "timeInForce":      "GTC",
        "reduceOnly":       False,
        "closeOnTrigger":   False,
        "positionIdx":      0
    }
    return bybit_request("POST", "/v5/order/create", params)

# ─────────────────────────────────────────────
# BYBIT — LEVERAGE AYARLA
# ─────────────────────────────────────────────
def set_leverage(symbol, leverage):
    params = {
        "category":     "linear",
        "symbol":       symbol,
        "buyLeverage":  str(leverage),
        "sellLeverage": str(leverage)
    }
    return bybit_request("POST", "/v5/position/set-leverage", params)

# ─────────────────────────────────────────────
# WEBHOOK — TradingView buraya POST atacak
# ─────────────────────────────────────────────
@app.route("/webhook", methods=["POST"])
def webhook():
    if request.args.get("secret") != WEBHOOK_SECRET:
        return jsonify({"error": "Unauthorized"}), 401

    data     = request.get_json(force=True) or {}
    signal   = data.get("signal",   "")
    symbol   = data.get("symbol",   "BTCUSDT")
    entry    = data.get("entry",    "0")
    sl       = data.get("sl",       "0")
    tp1      = data.get("tp1",      "0")
    tp2      = data.get("tp2",      "0")
    risk     = data.get("risk",     "10")
    leverage = data.get("leverage", "10")
    qty      = data.get("qty",      "0.001")
    now      = datetime.now().strftime("%d.%m.%Y %H:%M")

    if signal in ["LONG", "SHORT"]:
        side = "Buy" if signal == "LONG" else "Sell"
        emoji = "🟢" if signal == "LONG" else "🔴"

        # Kaldıraç ayarla
        set_leverage(symbol, leverage)

        # İşlem aç
        result = open_position(symbol, side, qty, sl, tp1)
        ret_code = result.get("retCode", -1)
        ret_msg  = result.get("retMsg", "Bilinmeyen hata")

        if ret_code == 0:
            msg = (
                f"{emoji} <b>{signal} AÇILDI — {symbol}</b>\n"
                f"━━━━━━━━━━━━━━━━━━\n"
                f"📍 Giriş: <b>{entry}$</b>\n"
                f"🛑 SL: <b>{sl}$</b> (-{risk}$)\n"
                f"🎯 TP1: <b>{tp1}$</b>\n"
                f"🎯 TP2: <b>{tp2}$</b>\n"
                f"⚡ Kaldıraç: <b>{leverage}x</b>\n"
                f"📦 Miktar: <b>{qty}</b>\n"
                f"━━━━━━━━━━━━━━━━━━\n"
                f"✅ Bybit'e gönderildi\n"
                f"🕐 {now}"
            )
        else:
            msg = (
                f"⚠️ <b>{signal} HATASI — {symbol}</b>\n"
                f"━━━━━━━━━━━━━━━━━━\n"
                f"❌ Hata: {ret_msg}\n"
                f"🕐 {now}"
            )

    elif signal == "TP1":
        msg = (
            f"✅ <b>TP1 HIT — {symbol}</b>\n"
            f"💰 Kar: <b>+{float(risk)*1.5:.1f}$</b>\n"
            f"🎯 TP2 bekleniyor: {tp2}$\n"
            f"🕐 {now}"
        )

    elif signal == "TP2":
        msg = (
            f"🏆 <b>TP2 HIT — {symbol}</b>\n"
            f"💰 Toplam Kar: <b>+{float(risk)*5.0:.1f}$</b>\n"
            f"✅ Pozisyon kapandı\n"
            f"🕐 {now}"
        )

    elif signal == "SL":
        msg = (
            f"❌ <b>STOP LOSS — {symbol}</b>\n"
            f"💸 Zarar: <b>-{risk}$</b>\n"
            f"🔄 Yeni sinyal bekleniyor\n"
            f"🕐 {now}"
        )
    else:
        msg = f"⚡ {signal} | {symbol} | {now}"

    send_telegram(msg)
    return jsonify({"status": "ok", "signal": signal})


# ─────────────────────────────────────────────
# TEST ENDPOINT
# ─────────────────────────────────────────────
@app.route("/test", methods=["GET"])
def test():
    if request.args.get("secret") != WEBHOOK_SECRET:
        return jsonify({"error": "Unauthorized"}), 401
    now = datetime.now().strftime("%d.%m.%Y %H:%M")
    send_telegram(f"✅ <b>TEST MESAJI</b>\n🕐 {now}\nBot çalışıyor!")
    return jsonify({"status": "ok", "message": "Telegram kontrol et!"})


# ─────────────────────────────────────────────
# SAĞLIK KONTROLÜ
# ─────────────────────────────────────────────
@app.route("/", methods=["GET"])
def health():
    return jsonify({"status": "CVİS Bot calisiyor!"})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
