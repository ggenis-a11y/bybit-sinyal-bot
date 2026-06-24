cat > app.py << 'PYEOF'
from flask import Flask, request, jsonify
import requests, os
from datetime import datetime

app = Flask(__name__)

TELEGRAM_TOKEN   = "7916314680:AAEr1gcNI1DAQGNL2bvxL1VJ5h_Uq5Rv3-w"
TELEGRAM_CHAT_ID = "384728743"
WEBHOOK_SECRET   = "bybit2024"

def send_telegram(message):
    requests.post(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
        data={"chat_id": TELEGRAM_CHAT_ID, "text": message, "parse_mode": "HTML"})

@app.route("/test", methods=["GET"])
def test():
    if request.args.get("secret") != WEBHOOK_SECRET:
        return jsonify({"error": "Unauthorized"}), 401
    now = datetime.now().strftime("%d.%m.%Y %H:%M")
    send_telegram(f"✅ <b>TEST MESAJI</b>\n🕐 {now}\nBot çalışıyor!")
    return jsonify({"status": "ok", "message": "Telegram kontrol et!"})

@app.route("/webhook", methods=["POST"])
def webhook():
    if request.args.get("secret") != WEBHOOK_SECRET:
        return jsonify({"error": "Unauthorized"}), 401
    data     = request.get_json(force=True) or {}
    signal   = data.get("signal", "")
    symbol   = data.get("symbol", "BTCUSDT")
    entry    = data.get("entry", "")
    sl       = data.get("sl", "")
    tp1      = data.get("tp1", "")
    tp2      = data.get("tp2", "")
    risk     = data.get("risk", "10")
    leverage = data.get("leverage", "10")
    now      = datetime.now().strftime("%d.%m.%Y %H:%M")
    msgs = {
        "LONG":  f"🟢 <b>LONG — {symbol}</b>\n━━━━━━━━━━━━━━━━━━\n📍 Giriş: <b>{entry}$</b>\n🛑 SL: <b>{sl}$</b> (-{risk}$)\n🎯 TP1: <b>{tp1}$</b>\n🎯 TP2: <b>{tp2}$</b>\n⚡ {leverage}x\n🕐 {now}",
        "SHORT": f"🔴 <b>SHORT — {symbol}</b>\n━━━━━━━━━━━━━━━━━━\n📍 Giriş: <b>{entry}$</b>\n🛑 SL: <b>{sl}$</b> (-{risk}$)\n🎯 TP1: <b>{tp1}$</b>\n🎯 TP2: <b>{tp2}$</b>\n⚡ {leverage}x\n🕐 {now}",
        "TP1":   f"✅ <b>TP1 HIT — {symbol}</b>\n💰 Kar: <b>+{float(risk)*1.5:.1f}$</b>\n🎯 TP2 bekleniyor: {tp2}$\n🕐 {now}",
        "TP2":   f"🏆 <b>TP2 HIT — {symbol}</b>\n💰 Toplam Kar: <b>+{float(risk)*5.0:.1f}$</b>\n✅ Pozisyon kapandı\n🕐 {now}",
        "SL":    f"❌ <b>STOP LOSS — {symbol}</b>\n💸 Zarar: <b>-{risk}$</b>\n🔄 Yeni sinyal bekleniyor\n🕐 {now}",
    }
    send_telegram(msgs.get(signal, f"⚡ {signal} | {symbol} | {now}"))
    return jsonify({"status": "ok"})

@app.route("/", methods=["GET"])
def health():
    return jsonify({"status": "CVİS Bot calisiyor!"})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
PYEOF
kill -HUP 1
