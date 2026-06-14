import os
import time
import json
import logging
import threading
import requests
from datetime import datetime
from flask import Flask, jsonify
from dotenv import load_dotenv

load_dotenv()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
GROUP_ID = os.getenv('TELEGRAM_GROUP_ID')
FORCE_CHANNEL_USERNAME = "wilzusuka"
API_BASE_URL = os.getenv('API_BASE_URL', 'https://iva-sms-api-xxx.vercel.app')  # Ganti dengan URL Vercel

bot_stats = {
    'start_time': datetime.now(),
    'total_otps_sent': 0,
    'last_check': 'Never',
    'monitor_running': False
}
update_offset = 0

# ========== TELEGRAM API WRAPPER ==========
def tg_call(method, data=None):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/{method}"
    try:
        r = requests.post(url, json=data) if data else requests.get(url)
        return r.json() if r.status_code == 200 else None
    except Exception as e:
        logger.error(f"Telegram API error: {e}")
        return None

def send_message(chat_id, text, reply_markup=None, parse_mode=None):
    data = {'chat_id': chat_id, 'text': text}
    if reply_markup:
        data['reply_markup'] = json.dumps(reply_markup)
    if parse_mode:
        data['parse_mode'] = parse_mode
    return tg_call('sendMessage', data)

def edit_message(chat_id, msg_id, text, reply_markup=None, parse_mode=None):
    data = {'chat_id': chat_id, 'message_id': msg_id, 'text': text}
    if reply_markup:
        data['reply_markup'] = json.dumps(reply_markup)
    if parse_mode:
        data['parse_mode'] = parse_mode
    return tg_call('editMessageText', data)

def answer_callback(callback_id, text=None, show_alert=False):
    data = {'callback_query_id': callback_id}
    if text:
        data['text'] = text
        data['show_alert'] = show_alert
    return tg_call('answerCallbackQuery', data)

# ========== CEK JOIN CHANNEL ==========
def is_user_joined_channel(user_id):
    try:
        chat = tg_call('getChat', {'chat_id': f"@{FORCE_CHANNEL_USERNAME}"})
        if not chat or not chat.get('ok'):
            return False
        chat_id = chat['result']['id']
        member = tg_call('getChatMember', {'chat_id': chat_id, 'user_id': user_id})
        if member and member.get('ok'):
            return member['result']['status'] in ['member', 'administrator', 'creator']
    except:
        pass
    return False

def send_force_join(chat_id, msg_id=None):
    keyboard = {
        'inline_keyboard': [
            [{'text': '📢 Join Channel', 'url': f'https://t.me/{FORCE_CHANNEL_USERNAME}'}],
            [{'text': '✅ Done', 'callback_data': 'check_join'}]
        ]
    }
    text = f"🔒 *Akses Ditutup*\nAnda harus join @{FORCE_CHANNEL_USERNAME} dulu."
    if msg_id:
        edit_message(chat_id, msg_id, text, keyboard, 'Markdown')
    else:
        send_message(chat_id, text, keyboard, 'Markdown')

# ========== MENU UTAMA ==========
def send_main_menu(chat_id, edit_msg_id=None):
    keyboard = {
        'inline_keyboard': [
            [{'text': '👤 STATISTIK SMS', 'callback_data': 'menu_profile'}],
            [{'text': '📨 CEK OTP', 'callback_data': 'menu_check'}],
            [{'text': '🕐 TRAFFIC SMS', 'callback_data': 'menu_traffic'}],
            [{'text': '⚡ STATUS BOT', 'callback_data': 'menu_status'}],
            [{'text': '📊 STATISTIK', 'callback_data': 'menu_stats'}]
        ]
    }
    caption = (
        "☐☳☳☳☳☳☳☳☳☳☳☳☳☳☳\n"
        "📊 *IVAS REAL TIME BOT*\n"
        "☐☳☳☳☳☳☳☳☳☳☳☳☳☳☳\n\n"
        f"API: {API_BASE_URL}"
    )
    if edit_msg_id:
        edit_message(chat_id, edit_msg_id, caption, keyboard, 'Markdown')
    else:
        send_message(chat_id, caption, keyboard, 'Markdown')

# ========== HANDLER ==========
def handle_start(chat_id, user_id):
    if not is_user_joined_channel(user_id):
        send_force_join(chat_id)
        return
    send_main_menu(chat_id)

def handle_profile(chat_id, user_id, msg_id=None):
    if not is_user_joined_channel(user_id):
        send_force_join(chat_id)
        return
    temp = send_message(chat_id, "🔍 *Mengambil data statistik...*", parse_mode='Markdown')
    temp_id = temp['result']['message_id'] if temp else None
    
    today = datetime.now().strftime('%d/%m/%Y')
    try:
        resp = requests.get(f"{API_BASE_URL}/sms?date={today}", timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            stats = data.get('sms_stats', {})
            text = (
                "☐☳☳☳☳☳☳☳☳☳☳☳☳☳☳\n"
                "📊 *STATISTIK SMS HARI INI*\n"
                "☐☳☳☳☳☳☳☳☳☳☳☳☳☳☳\n"
                f"📨 *Total SMS:* `{stats.get('count_sms', 'N/A')}`\n"
                f"💰 *Paid SMS:* `{stats.get('paid_sms', 'N/A')}`\n"
                f"🆓 *Unpaid SMS:* `{stats.get('unpaid_sms', 'N/A')}`\n"
                f"💵 *Revenue:* `{stats.get('revenue', 'N/A')} USD`\n"
                "☐☳☳☳☳☳☳☳☳☳☳☳☳☳☳"
            )
        else:
            text = f"❌ API error: {resp.status_code}"
    except Exception as e:
        text = f"❌ Gagal konek ke API: {str(e)}"
    
    if temp_id:
        tg_call('deleteMessage', {'chat_id': chat_id, 'message_id': temp_id})
    send_message(chat_id, text, parse_mode='Markdown')
    send_main_menu(chat_id)

def handle_check(chat_id, user_id, msg_id=None):
    if not is_user_joined_channel(user_id):
        send_force_join(chat_id)
        return
    temp = send_message(chat_id, "🔄 *Mengecek OTP...*", parse_mode='Markdown')
    temp_id = temp['result']['message_id'] if temp else None
    check_and_send_otps()
    if temp_id:
        tg_call('deleteMessage', {'chat_id': chat_id, 'message_id': temp_id})
    send_message(chat_id, f"✅ Selesai.\n📅 Terakhir: `{bot_stats['last_check']}`\n📨 Total OTP: `{bot_stats['total_otps_sent']}`", parse_mode='Markdown')
    send_main_menu(chat_id)

def handle_traffic(chat_id, user_id, msg_id=None):
    if not is_user_joined_channel(user_id):
        send_force_join(chat_id)
        return
    temp = send_message(chat_id, "📊 *Mengambil OTP terbaru...*", parse_mode='Markdown')
    temp_id = temp['result']['message_id'] if temp else None
    
    today = datetime.now().strftime('%d/%m/%Y')
    try:
        resp = requests.get(f"{API_BASE_URL}/sms?date={today}", timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            otp_messages = data.get('otp_messages', [])
            if otp_messages:
                msg_list = "\n".join([f"• `{m['phone_number']}`: {m['otp_message']}" for m in otp_messages[:5]])
                text = (
                    "☐☳☳☳☳☳☳☳☳☳☳☳☳☳☳\n"
                    "📨 *OTP TERBARU*\n"
                    "☐☳☳☳☳☳☳☳☳☳☳☳☳☳☳\n"
                    f"{msg_list}\n"
                    "☐☳☳☳☳☳☳☳☳☳☳☳☳☳☳"
                )
            else:
                text = "📭 *Tidak ada OTP baru hari ini.*"
        else:
            text = f"❌ API error: {resp.status_code}"
    except Exception as e:
        text = f"❌ Gagal konek ke API: {str(e)}"
    
    if temp_id:
        tg_call('deleteMessage', {'chat_id': chat_id, 'message_id': temp_id})
    send_message(chat_id, text, parse_mode='Markdown')
    send_main_menu(chat_id)

def handle_status(chat_id, user_id, msg_id=None):
    if not is_user_joined_channel(user_id):
        send_force_join(chat_id)
        return
    uptime = datetime.now() - bot_stats['start_time']
    text = (
        "☐☳☳☳☳☳☳☳☳☳☳☳☳☳☳\n"
        "⚡ *STATUS BOT*\n"
        "☐☳☳☳☳☳☳☳☳☳☳☳☳☳☳\n"
        f"⏱️ Uptime: `{str(uptime).split('.')[0]}`\n"
        f"📨 OTP terkirim: `{bot_stats['total_otps_sent']}`\n"
        f"🕐 Cek terakhir: `{bot_stats['last_check']}`\n"
        f"🏃 Monitor: `{'Aktif' if bot_stats['monitor_running'] else 'Berhenti'}`\n"
        "☐☳☳☳☳☳☳☳☳☳☳☳☳☳☳"
    )
    send_message(chat_id, text, parse_mode='Markdown')
    send_main_menu(chat_id)

def handle_stats(chat_id, user_id, msg_id=None):
    if not is_user_joined_channel(user_id):
        send_force_join(chat_id)
        return
    uptime = datetime.now() - bot_stats['start_time']
    text = (
        "☐☳☳☳☳☳☳☳☳☳☳☳☳☳☳\n"
        "📊 *STATISTIK BOT*\n"
        "☐☳☳☳☳☳☳☳☳☳☳☳☳☳☳\n"
        f"⏱️ Uptime: `{str(uptime).split('.')[0]}`\n"
        f"📨 OTP terkirim: `{bot_stats['total_otps_sent']}`\n"
        f"🕐 Pengecekan: `{bot_stats['last_check']}`\n"
        f"🏃 Monitor: `{'Aktif' if bot_stats['monitor_running'] else 'Berhenti'}`\n"
        "☐☳☳☳☳☳☳☳☳☳☳☳☳☳☳"
    )
    send_message(chat_id, text, parse_mode='Markdown')
    send_main_menu(chat_id)

def handle_callback(callback):
    cid = callback['id']
    chat_id = callback['message']['chat']['id']
    msg_id = callback['message']['message_id']
    user_id = callback['from']['id']
    data = callback.get('data')

    if data == 'check_join':
        if is_user_joined_channel(user_id):
            answer_callback(cid, "✅ Akses diberikan!")
            send_main_menu(chat_id, edit_msg_id=msg_id)
        else:
            answer_callback(cid, "❌ Belum join!", show_alert=True)
            send_force_join(chat_id, msg_id)
        return

    if not is_user_joined_channel(user_id):
        answer_callback(cid, "🔒 Harus join channel!", show_alert=True)
        send_force_join(chat_id, msg_id)
        return

    if data == 'menu_profile':
        answer_callback(cid)
        handle_profile(chat_id, user_id, msg_id)
    elif data == 'menu_check':
        answer_callback(cid)
        handle_check(chat_id, user_id, msg_id)
    elif data == 'menu_traffic':
        answer_callback(cid)
        handle_traffic(chat_id, user_id, msg_id)
    elif data == 'menu_status':
        answer_callback(cid)
        handle_status(chat_id, user_id, msg_id)
    elif data == 'menu_stats':
        answer_callback(cid)
        handle_stats(chat_id, user_id, msg_id)
    else:
        answer_callback(cid, "Menu tidak dikenal")

# ========== OTP MONITOR ==========
def check_and_send_otps():
    global bot_stats
    try:
        today = datetime.now().strftime('%d/%m/%Y')
        resp = requests.get(f"{API_BASE_URL}/sms?date={today}", timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            bot_stats['last_check'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            otp_messages = data.get('otp_messages', [])
            if otp_messages:
                for msg in otp_messages:
                    phone = msg.get('phone_number', 'N/A')
                    otp_text = msg.get('otp_message', 'N/A')
                    message = (
                        f"🔐 *New OTP Received*\n"
                        f"━━━━━━━━━━━━━\n"
                        f"📱 *Kode OTP:* `{otp_text}`\n"
                        f"📞 *Nomor:* `{phone}`\n"
                        f"⏰ *Waktu:* {datetime.now().strftime('%H:%M:%S')}\n"
                        f"━━━━━━━━━━━━━\n"
                        f"Tap kode OTP di atas untuk menyalin."
                    )
                    send_message(GROUP_ID, message, parse_mode='Markdown')
                bot_stats['total_otps_sent'] += len(otp_messages)
    except Exception as e:
        logger.error(f"OTP error: {e}")

def background_monitor():
    bot_stats['monitor_running'] = True
    while bot_stats['monitor_running']:
        check_and_send_otps()
        time.sleep(60)

# ========== POLLING UPDATE ==========
def poll_updates():
    global update_offset
    while True:
        try:
            params = {'timeout': 30, 'offset': update_offset}
            r = requests.get(f"https://api.telegram.org/bot{BOT_TOKEN}/getUpdates", params=params, timeout=35)
            if r.status_code == 200:
                data = r.json()
                if data.get('ok'):
                    for upd in data['result']:
                        update_offset = upd['update_id'] + 1
                        if 'message' in upd:
                            msg = upd['message']
                            chat_id = msg['chat']['id']
                            user_id = msg['from']['id']
                            text = msg.get('text', '')
                            if text.startswith('/start'):
                                handle_start(chat_id, user_id)
                            elif text.startswith('/profile'):
                                handle_profile(chat_id, user_id)
                            elif text.startswith('/check'):
                                handle_check(chat_id, user_id)
                            elif text.startswith('/traffic'):
                                handle_traffic(chat_id, user_id)
                            elif text.startswith('/status'):
                                handle_status(chat_id, user_id)
                            elif text.startswith('/stats'):
                                handle_stats(chat_id, user_id)
                            else:
                                send_main_menu(chat_id)
                        elif 'callback_query' in upd:
                            handle_callback(upd['callback_query'])
        except Exception as e:
            logger.error(f"Polling error: {e}")
            time.sleep(5)

# ========== FLASK ==========
@app.route('/')
def index():
    return "Bot OTP iVASMS running with IvaSms API"

@app.route('/status')
def status():
    uptime = datetime.now() - bot_stats['start_time']
    return jsonify({
        'status': 'running',
        'uptime_seconds': uptime.total_seconds(),
        'total_otps_sent': bot_stats['total_otps_sent'],
        'last_check': bot_stats['last_check']
    })

# ========== MAIN ==========
if __name__ == '__main__':
    threading.Thread(target=background_monitor, daemon=True).start()
    threading.Thread(target=poll_updates, daemon=True).start()
    port = int(os.getenv('PORT', 5001))
    app.run(host='0.0.0.0', port=port)