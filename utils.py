import re
from datetime import datetime

def format_otp_message(otp_data):
    otp = otp_data.get('otp', 'N/A')
    phone = otp_data.get('phone', 'N/A')
    service = otp_data.get('service', 'Unknown')
    timestamp = otp_data.get('timestamp', datetime.now().strftime('%H:%M:%S'))
    return f"""
🔐 *New OTP Received*
━━━━━━━━━━━━━
📱 *Kode OTP:* `{otp}`
📞 *Nomor:* `{phone}`
🏷️ *Layanan:* {service}
⏰ *Waktu:* {timestamp}
━━━━━━━━━━━━━
Tap kode OTP di atas untuk menyalin.
"""

def extract_otp_from_text(text):
    if not text:
        return None
    patterns = [r'\b(\d{6})\b', r'\b(\d{5})\b', r'\b(\d{4})\b',
                r'code[:\s]*(\d+)', r'verification[:\s]*(\d+)',
                r'otp[:\s]*(\d+)', r'pin[:\s]*(\d+)']
    for p in patterns:
        m = re.search(p, text, re.I)
        if m:
            return m.group(1)
    return None

def clean_phone_number(phone):
    if not phone:
        return "N/A"
    cleaned = re.sub(r'[^\d+]', '', phone)
    if cleaned and not cleaned.startswith('+'):
        if cleaned.startswith('62') or cleaned.startswith('88'):
            cleaned = '+' + cleaned
        elif len(cleaned) >= 10:
            cleaned = '+' + cleaned
    return cleaned or phone

def clean_service_name(service):
    if not service:
        return "Unknown"
    cleaned = service.strip().title()
    mapping = {'fb':'Facebook','google':'Google','whatsapp':'WhatsApp','telegram':'Telegram','instagram':'Instagram','twitter':'Twitter'}
    for k,v in mapping.items():
        if k in cleaned.lower():
            return v
    return cleaned

def get_status_message(stats):
    uptime = stats.get('uptime','Unknown')
    total = stats.get('total_otps_sent',0)
    last = stats.get('last_check','Never')
    cache = stats.get('cache_size',0)
    running = stats.get('monitor_running',False)
    return f"""
📊 *Bot Status*
━━━━━━━━━━━━━
⚡ *Status:* Online
⏱️ *Uptime:* {uptime}
📨 *Total OTPs Sent:* {total}
🕐 *Last Check:* {last}
💾 *Cache Size:* {cache} items
🏃 *Monitor:* {'✅ Aktif' if running else '❌ Berhenti'}
━━━━━━━━━━━━━
"""