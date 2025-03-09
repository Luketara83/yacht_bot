import os
import telebot
from flask import Flask, request

# Prende il Token dal sistema (Render)
TOKEN = os.getenv("BOT_TOKEN")
bot = telebot.TeleBot(TOKEN)

# Imposta il server Flask
app = Flask(__name__)

# URL del tuo bot su Render (da modificare dopo)
WEBHOOK_URL = "https://yacht-bot.onrender.com"

@app.route("/", methods=["GET"])
def home():
    return "Il bot è attivo!", 200

@app.route(f"/{TOKEN}", methods=["POST"])
def webhook():
    json_str = request.get_data().decode("utf-8")
    update = telebot.types.Update.de_json(json_str)
    bot.process_new_updates([update])
    return "OK", 200

# Comando di base
@bot.message_handler(commands=["start"])
def send_welcome(message):
    bot.reply_to(message, "Ciao! Il bot è attivo su Render 🚀")

# Imposta il Webhook
@app.route("/set_webhook", methods=["GET"])
def set_webhook():
    success = bot.set_webhook(url=f"{WEBHOOK_URL}/{TOKEN}")
    return f"Webhook impostato: {success}", 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5001)  # PORTA 5001
