import requests
import os
import telebot
import sqlite3
import logging
from flask import Flask, request, jsonify
from PyPDF2 import PdfReader
from dotenv import load_dotenv

# Caricare variabili d'ambiente da un file .env
load_dotenv()
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
DATABASE = "users.db"

# Configurazione logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

bot = telebot.TeleBot(TOKEN)
app = Flask(__name__)

# Creazione del database utenti
def init_db():
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY,
            telegram_id INTEGER UNIQUE,
            username TEXT,
            messages_sent INTEGER DEFAULT 0
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS feedback (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            telegram_id INTEGER,
            username TEXT,
            message TEXT
        )
    """)
    conn.commit()
    conn.close()

init_db()

# Funzione per registrare un utente nel database
def register_user(telegram_id, username):
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    cursor.execute("INSERT OR IGNORE INTO users (telegram_id, username) VALUES (?, ?)", (telegram_id, username))
    cursor.execute("UPDATE users SET messages_sent = messages_sent + 1 WHERE telegram_id = ?", (telegram_id,))
    conn.commit()
    conn.close()

# Funzione per salvare un feedback
def save_feedback(telegram_id, username, message):
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    cursor.execute("INSERT INTO feedback (telegram_id, username, message) VALUES (?, ?, ?)", (telegram_id, username, message))
    conn.commit()
    conn.close()

# Funzione per interagire con Google Gemini API
def chiedi_a_gemini(messaggio):
    try:
        url = f"https://generativelanguage.googleapis.com/v1/models/gemini-1.5-pro-002:generateContent?key={GEMINI_API_KEY}"
        headers = {"Content-Type": "application/json"}
        data = {"contents": [{"parts": [{"text": messaggio}]}]}
        response = requests.post(url, headers=headers, json=data)
        risposta = response.json()

        if "candidates" in risposta and len(risposta["candidates"]) > 0:
            return risposta["candidates"][0]["content"]["parts"][0]["text"]
        else:
            return "Errore: Nessuna risposta valida ricevuta da Gemini."
    except Exception as e:
        logging.error(f"Errore nell'interazione con Gemini: {e}")
        return "Errore nell'elaborazione della richiesta."

# Funzione per leggere un PDF
def estrai_testo_da_pdf(file_path):
    try:
        reader = PdfReader(file_path)
        text = "\n".join([page.extract_text() for page in reader.pages if page.extract_text()])
        return text[:4000]  # Limitiamo a 4000 caratteri per evitare problemi di lunghezza
    except Exception as e:
        logging.error(f"Errore nella lettura del PDF: {e}")
        return "Errore durante la lettura del file PDF."

@bot.message_handler(commands=['feedback'])
def handle_feedback(message):
    feedback_text = message.text.replace('/feedback', '').strip()
    if feedback_text:
        save_feedback(message.from_user.id, message.from_user.username, feedback_text)
        bot.send_message(message.chat.id, "Grazie per il tuo feedback! 📝")
    else:
        bot.send_message(message.chat.id, "Per inviare un feedback, usa il comando: /feedback [il tuo messaggio]")

@bot.message_handler(content_types=['document'])
def handle_docs(message):
    try:
        file_info = bot.get_file(message.document.file_id)
        file_path = file_info.file_path
        downloaded_file = bot.download_file(file_path)
        local_path = f"downloads/{message.document.file_name}"
        os.makedirs("downloads", exist_ok=True)
        
        with open(local_path, 'wb') as new_file:
            new_file.write(downloaded_file)
        
        testo_pdf = estrai_testo_da_pdf(local_path)
        risposta = chiedi_a_gemini(f"Analizza questo documento: {testo_pdf}")
        bot.send_message(message.chat.id, risposta)
    except Exception as e:
        logging.error(f"Errore nella gestione del file: {e}")
        bot.send_message(message.chat.id, "Errore durante l'elaborazione del file PDF.")

@bot.message_handler(func=lambda message: True)
def handle_message(message):
    register_user(message.from_user.id, message.from_user.username)
    response = chiedi_a_gemini(message.text)
    bot.send_message(message.chat.id, response)

if __name__ == "__main__":
    logging.info("Avvio del bot in modalità polling...")
    bot.polling(none_stop=True)
