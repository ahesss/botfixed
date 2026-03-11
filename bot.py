import telebot
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import threading
import json
import os
import socket

# Paksa menggunakan IPv4 (Solusi untuk Errno 101: Network is unreachable)
old_getaddrinfo = socket.getaddrinfo
def new_getaddrinfo(*args, **kwargs):
    responses = old_getaddrinfo(*args, **kwargs)
    return [response for response in responses if response[0] == socket.AF_INET]
socket.getaddrinfo = new_getaddrinfo

# GANTI DENGAN TOKEN BOT ANDA
TELEGRAM_BOT_TOKEN = '8718125466:AAEJjDGXe5utkk3gm0b2IlJ_oBH0Pzsl3eo'
TARGET_EMAIL = 'support@support.whatsapp.com'

bot = telebot.TeleBot(TELEGRAM_BOT_TOKEN)

# Menyimpan Data/Status Pengguna Secara Permanen
SESSION_FILE = "user_sessions.json"

def load_sessions():
    if os.path.exists(SESSION_FILE):
        try:
            with open(SESSION_FILE, 'r') as f:
                return json.load(f)
        except Exception:
            return {}
    return {}

def save_sessions():
    with open(SESSION_FILE, 'w') as f:
        json.dump(user_sessions, f)

user_sessions = load_sessions()

def get_session(chat_id):
    c_id = str(chat_id)
    if c_id not in user_sessions:
        user_sessions[c_id] = {'step': 'none', 'email': None, 'app_pwd': None}
        save_sessions()
    return user_sessions[c_id]

def send_whatsapp_email(sender_email, app_password, phone_number):
    try:
        print(f"[{phone_number}] Menyiapkan email dari {sender_email}")
        msg = MIMEMultipart()
        msg['From'] = sender_email
        msg['To'] = TARGET_EMAIL
        msg['Subject'] = 'Question'
        
        body = f"saya ingin login akun WhatsApp saya, tolong bantu saya login akun WhatsApp saya : {phone_number}"
        msg.attach(MIMEText(body, 'plain'))
        
        print(f"[{phone_number}] Menghubungkan ke smtp.gmail.com via SSL (Port 465)...")
        server = smtplib.SMTP_SSL('smtp.gmail.com', 465, timeout=15)
        print(f"[{phone_number}] Login dengan Sandi Aplikasi...")
        server.login(sender_email, app_password)
        print(f"[{phone_number}] Mengirim pesan ke server...")
        server.send_message(msg)
        server.quit()
        print(f"[{phone_number}] Berhasil terkirim!")
        return True, "Email berhasil dikirim!"
    except Exception as e:
        print(f"[{phone_number}] ERROR: {str(e)}")
        return False, str(e)

@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    chat_id = message.chat.id
    session = get_session(chat_id)
    
    welcome_text = (
        "🤖 *WA Support Mailer Bot*\n\n"
        "Gunakan perintah /setup untuk mulai memasukkan Email & App Password Anda.\n"
        "Setelah disimpan, Anda tinggal mengirimkan nomor WhatsApp (contoh: `+529541310717`) "
        "kapanpun Anda mau, dan saya akan otomatis mengirim pengajuannya via email Anda."
    )
    bot.send_message(chat_id, welcome_text, parse_mode="Markdown")

@bot.message_handler(commands=['setup'])
def command_setup(message):
    chat_id = message.chat.id
    session = get_session(chat_id)
    session['step'] = 'wait_email'
    save_sessions()
    bot.send_message(chat_id, "📧 Kirimkan *Alamat Email Gmail* Anda (contoh: nama@gmail.com):", parse_mode="Markdown")

@bot.message_handler(commands=['status'])
def command_status(message):
    chat_id = message.chat.id
    session = get_session(chat_id)
    email = session['email'] if session['email'] else "Belum diatur"
    pwd = "Sudah diatur (tersembunyi)" if session['app_pwd'] else "Belum diatur"
    
    text = f"📊 *Status Konfigurasi*\n\n📧 Email: `{email}`\n🔑 Sandi Aplikasi: `{pwd}`\n\nUntuk mengubah, gunakan perintah /setup."
    bot.send_message(chat_id, text, parse_mode="Markdown")

@bot.message_handler(func=lambda message: True)
def handle_all_text(message):
    chat_id = message.chat.id
    text = message.text.strip()
    session = get_session(chat_id)
    
    step = session['step']
    
    if step == 'wait_email':
        if "@" in text and "." in text:
            session['email'] = text
            session['step'] = 'wait_pwd'
            save_sessions()
            # Hapus pesan email (opsional)
            try: bot.delete_message(chat_id, message.message_id) 
            except: pass
            
            bot.send_message(chat_id, f"✅ Email disimpan: `{text}`\n\n🔑 Sekarang kirimkan *Sandi Aplikasi (App Password)* Anda (biasanya 16 karakter tanpa spasi).", parse_mode="Markdown")
        else:
            bot.send_message(chat_id, "⚠️ Format email tidak valid. Silakan kirim ulang:")
            
    elif step == 'wait_pwd':
        session['app_pwd'] = text.replace(" ", "")
        session['step'] = 'ready'
        save_sessions()
        # Hapus pesan kata sandi demi keamanan
        try: bot.delete_message(chat_id, message.message_id)
        except: pass
        
        bot.send_message(chat_id, "✅ Sandi Aplikasi berhasil disimpan!\n\n🎯 *SEKARANG BOT SIAP DIGUNAKAN*.\n\nKapanpun Anda mau melaporkan nomor, tinggal tempelkan (*paste*) sebuah nomor WhatsApp berawalan `+` (contoh: `+529541310717`) lalu kirim ke bot ini.\nBot akan secara otomatis mengirimkannya via email akun Anda!", parse_mode="Markdown")

    elif step == 'ready':
        if text.startswith('+') or text.isdigit():
            bot.send_message(chat_id, f"⏳ Memproses pengajuan email ke WhatsApp Support menggunakan akun `{session['email']}` untuk nomor `{text}`...", parse_mode="Markdown")
            
            def process_email():
                try:
                    success, msg = send_whatsapp_email(session['email'], session['app_pwd'], text)
                    if success:
                        bot.send_message(chat_id, f"✅ *BERHASIL TERKIRIM!*\nNomor: `{text}`\nEmail Pengirim: `{session['email']}`", parse_mode="Markdown")
                    else:
                        bot.send_message(chat_id, f"❌ *GAGAL!*\nDetail Kesalahan: `{msg}`\n\nJika kata sandi/email Anda salah, silakan atur ulang menggunakan perintah /setup\n_(Catatan: Jika error Timeout, server hosting Anda mungkin memblokir port 587)_", parse_mode="Markdown")
                except Exception as ex:
                    print(f"Fatal error pada proses email: {ex}")
                    try:
                        bot.send_message(chat_id, f"❌ *CRITICAL ERROR!*\nDetail: `{str(ex)}`", parse_mode="Markdown")
                    except:
                        pass
                    
            threading.Thread(target=process_email).start()
        else:
            bot.send_message(chat_id, "ℹ️ Format salah. Untuk mengirim permintaan ke email, ketikkan nomor WhatsApp target yang diawali tanda `+`.\n\nContoh: `+529541310717`")

    else:
        bot.send_message(chat_id, "👋 Selamat datang! Ketik /setup untuk mengatur koneksi Email Anda terlebih dahulu.")

if __name__ == '__main__':
    print("Bot WA Support Mailer Online...")
    bot.infinity_polling()
