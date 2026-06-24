from flask import Flask, request, jsonify
import requests
import os
import json
from datetime import datetime

app = Flask(__name__)

# ─────────────────────────────────────────────
# AYARLAR
# ─────────────────────────────────────────────
TELEGRAM_TOKEN   = os.environ.get("TELEGRAM_TOKEN", "7916314680:AAEr1gcNI1DAQGNL2bvxL1VJ5h_Uq5Rv3-w")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "384728743")
WEBHOOK_SECRET   = os.environ.get("WEBHOOK_SECRET", "bybit2024")

def send_telegram(message):
    url  = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    data = {
        "chat_id"    : TELEGRAM_CHAT_ID,
        "text"       : message,
        "parse_mode" : "HTML"
    }
    requests.post(url, data=data)

# ─────────────────────────────────────────────
# WEBHOOK — TradingView buraya POST atacak
# ─────────────────────────────────────────────
@app.route("/webhook", methods=["POST"])
def webhook():
    # Güvenlik kontrolü
    secret = request.args.get("secret", "")
    if secret != WEBHOOK_SECRET:
        return jsonify({"error": "Unauthorized"}), 401

    try:
        data = request.get_json(force=True)
    except:
        data = {}

    signal    = data.get("signal", "")       # LONG / SHORT / TP1 / TP2 / SL
    symbol    = data.get("symbol", "BTCUSDT")
    entry     = data.get("entry",  "")
    sl        = data.get("sl",     "")
    tp1       = data.get("tp1",    "")
    tp2       = data.get("tp2",    "")
    risk      = data.get("risk",   "10")
    leverage  = data.get("leverage","10")
    close     = data.get("close",  "")
    pnl       = data.get("pnl",    "")

    now = datetime.now().strftime("%d.%m.%Y %H:%M")

    # ── LONG Sinyali ──
    if signal == "LONG":
        msg = (
            f"🟢 <b>LONG SİNYALİ — {symbol}</b>\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"📍 Giriş:  <b>{entry}$</b>\n"
            f"🛑 SL:     <b>{sl}$</b>  (Risk: <b>-{risk}$</b>)\n"
            f"🎯 TP1:    <b>{tp1}$</b>  (+{float(risk)*1.5:.1f}$)\n"
            f"🎯 TP2:    <b>{tp2}$</b>  (+{float(risk)*3.5:.1f}$)\n"
            f"⚡ Kaldıraç: <b>{leverage}x</b>\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"🕐 {now}"
        )

    # ── SHORT Sinyali ──
    elif signal == "SHORT":
        msg = (
            f"🔴 <b>SHORT SİNYALİ — {symbol}</b>\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"📍 Giriş:  <b>{entry}$</b>\n"
            f"🛑 SL:     <b>{sl}$</b>  (Risk: <b>-{risk}$</b>)\n"
            f"🎯 TP1:    <b>{tp1}$</b>  (+{float(risk)*1.5:.1f}$)\n"
            f"🎯 TP2:    <b>{tp2}$</b>  (+{float(risk)*3.5:.1f}$)\n"
            f"⚡ Kaldıraç: <b>{leverage}x</b>\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"🕐 {now}"
        )

    # ── TP1 Kapandı ──
    elif signal == "TP1":
        msg = (
            f"✅ <b>TP1 HIT — {symbol}</b>\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"💰 Kar:  <b>+{float(risk)*1.5:.1f}$</b>\n"
            f"📊 Pozisyonun %60'ı kapandı\n"
            f"🎯 TP2 bekleniyor: <b>{tp2}$</b>\n"
            f"🔒 SL breakeven'a çekildi\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"🕐 {now}"
        )

    # ── TP2 Kapandı ──
    elif signal == "TP2":
        msg = (
            f"🏆 <b>TP2 HIT — {symbol}</b>\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"💰 Toplam Kar:  <b>+{float(risk)*5.0:.1f}$</b>\n"
            f"✅ Pozisyon tamamen kapandı\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"🕐 {now}"
        )

    # ── SL Tetiklendi ──
    elif signal == "SL":
        msg = (
            f"❌ <b>STOP LOSS — {symbol}</b>\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"💸 Zarar:  <b>-{risk}$</b>\n"
            f"🔄 Yeni sinyal bekleniyor...\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"🕐 {now}"
        )

    # ── Bilinmeyen sinyal ──
    else:
        msg = f"⚡ Sinyal: {signal} | {symbol} | {now}"

    send_telegram(msg)
    return jsonify({"status": "ok", "signal": signal})



# ─────────────────────────────────────────────
# TEST ENDPOINT — Tarayıcıdan GET ile test et
# ─────────────────────────────────────────────
@app.route("/test", methods=["GET"])
def test():
    secret = request.args.get("secret", "")
    if secret != WEBHOOK_SECRET:
        return jsonify({"error": "Unauthorized"}), 401

    signal = request.args.get("signal", "LONG")
    now    = datetime.now().strftime("%d.%m.%Y %H:%M")

    messages = {
        "LONG":  f"🟢 <b>LONG SİNYALİ — BTCUSDT</b>\n━━━━━━━━━━━━━━━━━━\n📍 Giriş:  <b>67450$</b>\n🛑 SL:     <b>66980$</b>  (Risk: <b>-10$</b>)\n🎯 TP1:    <b>67920$</b>  (+15.0$)\n🎯 TP2:    <b>68650$</b>  (+35.0$)\n⚡ Kaldıraç: <b>10x</b>\n━━━━━━━━━━━━━━━━━━\n🕐 {now}",
        "SHORT": f"🔴 <b>SHORT SİNYALİ — BTCUSDT</b>\n━━━━━━━━━━━━━━━━━━\n📍 Giriş:  <b>67450$</b>\n🛑 SL:     <b>67920$</b>  (Risk: <b>-10$</b>)\n🎯 TP1:    <b>66980$</b>  (+15.0$)\n🎯 TP2:    <b>66250$</b>  (+35.0$)\n⚡ Kaldıraç: <b>10x</b>\n━━━━━━━━━━━━━━━━━━\n🕐 {now}",
        "TP1":   f"✅ <b>TP1 HIT — BTCUSDT</b>\n━━━━━━━━━━━━━━━━━━\n💰 Kar:  <b>+15.0$</b>\n📊 Pozisyonun %60\'ı kapandı\n🎯 TP2 bekleniyor\n━━━━━━━━━━━━━━━━━━\n🕐 {now}",
        "TP2":   f"🏆 <b>TP2 HIT — BTCUSDT</b>\n━━━━━━━━━━━━━━━━━━\n💰 Toplam Kar:  <b>+50.0$</b>\n✅ Pozisyon tamamen kapandı\n━━━━━━━━━━━━━━━━━━\n🕐 {now}",
        "SL":    f"❌ <b>STOP LOSS — BTCUSDT</b>\n━━━━━━━━━━━━━━━━━━\n💸 Zarar:  <b>-10$</b>\n🔄 Yeni sinyal bekleniyor...\n━━━━━━━━━━━━━━━━━━\n🕐 {now}",
    }

    msg = messages.get(signal, f"⚡ Test mesajı — {now}")
    send_telegram(msg)
    return jsonify({"status": "ok", "signal": signal, "message": "Telegram'ı kontrol et!"})

# ─────────────────────────────────────────────
# SAĞLIK KONTROLÜ
# ─────────────────────────────────────────────
@app.route("/", methods=["GET"])
def health():
    return jsonify({"status": "CVİS Sinyal Botu çalışıyor 🚀"})


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
