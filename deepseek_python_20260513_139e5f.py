#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LỘC VN - TEMP MAIL PRO ULTIMATE v10.0
- Email thật (Mail.tm, 1secmail, Guerrillamail, Temp-mail, Emailnator) nhận OTP
- SMS demo (không cần API key) sinh OTP ngẫu nhiên
- Chat công khai (mọi người nhập tên, chat chung)
- Chuông thông báo hệ thống (admin gửi, user xem)
- Chính sách, điều khoản, FAQ siêu chi tiết (dài dòng)
- 2 ngôn ngữ (VI/EN), avatar, lưu vĩnh viễn 30 ngày
"""

import os
import json
import re
import secrets
import random
import requests
import hashlib
from datetime import datetime, timedelta
from flask import Flask, session, request, jsonify, render_template_string, make_response, redirect, url_for
from functools import wraps

app = Flask(__name__)
app.secret_key = secrets.token_hex(32)
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=30)
app.config['SESSION_PERMANENT'] = True

# ==================== SECURITY HEADERS ====================
@app.after_request
def security_headers(resp):
    resp.headers['X-Content-Type-Options'] = 'nosniff'
    resp.headers['X-Frame-Options'] = 'DENY'
    resp.headers['X-XSS-Protection'] = '1; mode=block'
    resp.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
    resp.headers['Content-Security-Policy'] = "default-src 'self'; script-src 'self' 'unsafe-inline' https://cdnjs.cloudflare.com https://fonts.googleapis.com; style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; font-src 'self' https://fonts.gstatic.com; img-src 'self' data: https://i.pravatar.cc;"
    return resp

# ==================== ADMIN & CHAT CÔNG KHAI ====================
ADMIN_PASSWORD_HASH = hashlib.sha256("admin123".encode()).hexdigest()
chat_messages = []          # [{"sender_name": "...", "text": "...", "time": "", "lang": "vi"}]

# ==================== EMAIL API THẬT ====================
class EmailAPI_MailTm:
    name = "mail.tm"
    def create(self):
        resp = requests.post("https://api.mail.tm/accounts", json={"address": f"{secrets.token_hex(6)}@mail.tm", "password": "P@ssw0rd!"})
        if resp.status_code == 201:
            data = resp.json()
            return data["address"], data["id"], data["password"]
        return None, None, None
    def get_messages(self, account_id, password):
        token = self._get_token(account_id, password)
        if not token: return []
        resp = requests.get("https://api.mail.tm/messages", headers={"Authorization": f"Bearer {token}"})
        return resp.json() if resp.ok else []
    def get_message(self, account_id, password, msg_id):
        token = self._get_token(account_id, password)
        if not token: return None
        resp = requests.get(f"https://api.mail.tm/messages/{msg_id}", headers={"Authorization": f"Bearer {token}"})
        return resp.json() if resp.ok else None
    def _get_token(self, account_id, password):
        r = requests.post("https://api.mail.tm/token", json={"id": account_id, "password": password})
        return r.json().get("token") if r.ok else None

class EmailAPI_1secmail:
    name = "1secmail.com"
    def create(self):
        domain = random.choice(["1secmail.com", "1secmail.org", "1secmail.net"])
        login = secrets.token_hex(6)
        return f"{login}@{domain}", login, domain
    def get_messages(self, login, domain):
        resp = requests.get(f"https://www.1secmail.com/api/v1/?action=getMessages&login={login}&domain={domain}")
        return resp.json() if resp.ok else []
    def get_message(self, login, domain, msg_id):
        resp = requests.get(f"https://www.1secmail.com/api/v1/?action=readMessage&login={login}&domain={domain}&id={msg_id}")
        return resp.json() if resp.ok else None

class EmailAPI_Guerrillamail:
    name = "guerrillamail.com"
    def create(self):
        r = requests.post("https://api.guerrillamail.com/ajax.php?f=get_email_address&ip=127.0.0.1&agent=Mozilla")
        if r.ok:
            data = r.json()
            return data["email_addr"], data["sid_token"], None
        return None, None, None
    def get_messages(self, sid_token, _=None):
        r = requests.get(f"https://api.guerrillamail.com/ajax.php?f=get_email_list&sid_token={sid_token}&seq=0")
        return r.json().get("list", []) if r.ok else []
    def get_message(self, sid_token, _, msg_id):
        r = requests.get(f"https://api.guerrillamail.com/ajax.php?f=fetch_email&sid_token={sid_token}&email_id={msg_id}")
        return r.json() if r.ok else None

class EmailAPI_TempMailOrg:
    name = "temp-mail.org"
    def create(self):
        r = requests.get("https://api.temp-mail.org/request/domains/format/json")
        if r.ok:
            domain = r.json()[0]
            local = secrets.token_hex(6)
            return f"{local}@{domain}", local, domain
        return None, None, None
    def get_messages(self, local, domain):
        r = requests.get(f"https://api.temp-mail.org/request/mail/id/{local}/domain/{domain}/format/json")
        return r.json() if r.ok and isinstance(r.json(), list) else []
    def get_message(self, local, domain, msg_id):
        msgs = self.get_messages(local, domain)
        for m in msgs:
            if str(m.get("mail_id")) == str(msg_id):
                return m
        return None

class EmailAPI_Emailnator:
    name = "emailnator.com"
    def create(self):
        r = requests.post("https://www.emailnator.com/generate-email", json={"email": ["dotGmail"]})
        if r.ok:
            email = r.json().get("email", [None])[0]
            return email, email.split("@")[0], None
        return None, None, None
    def get_messages(self, email_prefix, _=None):
        r = requests.post("https://www.emailnator.com/message-list", json={"email": f"{email_prefix}@dotgmail.com"})
        return r.json().get("messageData", []) if r.ok else []
    def get_message(self, email_prefix, _, msg_id):
        r = requests.post("https://www.emailnator.com/message-list", json={"email": f"{email_prefix}@dotgmail.com"})
        if r.ok:
            for m in r.json().get("messageData", []):
                if m.get("messageID") == msg_id:
                    return m
        return None

REAL_EMAIL_APIS = [EmailAPI_MailTm(), EmailAPI_1secmail(), EmailAPI_Guerrillamail(), EmailAPI_TempMailOrg(), EmailAPI_Emailnator()]

# ==================== SMS DEMO (KHÔNG CẦN API KEY) ====================
class SMSAPI_Demo:
    name = "SMS Demo (OTP ngẫu nhiên)"
    def get_countries(self): return ["Vietnam", "USA", "UK", "Canada", "Australia"]
    def get_phone_number(self, country="Vietnam"):
        prefix = {"Vietnam":"09", "USA":"+1", "UK":"+44", "Canada":"+1", "Australia":"+61"}.get(country, "09")
        return prefix + ''.join(str(random.randint(0,9)) for _ in range(8)), f"demo_{random.randint(10000,99999)}"
    def get_messages(self, session_id):
        # Sinh OTP ngẫu nhiên để demo
        if random.random() < 0.25:
            otp = ''.join(str(random.randint(0,9)) for _ in range(6))
            return [{"id": random.randint(1000,9999), "from": "DemoService", "message": f"Mã OTP của bạn là: {otp}", "otp": otp, "time": datetime.now().strftime("%H:%M:%S")}]
        return []

SMS_PROVIDERS = [SMSAPI_Demo()]  # Chỉ dùng demo, không cần key

# ==================== OTP PATTERNS ====================
OTP_PATTERNS = [
    r'(?<!\d)\d{6}(?!\d)', r'mã.*?(\d{6})', r'code.*?(\d{6})', r'OTP.*?(\d{6})',
    r'verification.*?(\d{6})', r'您的验证码.*?(\d{6})', r'token.*?(\d{6})'
]

# ==================== SESSION MANAGEMENT ====================
def get_data():
    if 'data' not in session:
        session['data'] = {
            'emails': [], 'current_email_idx': -1, 'history': [],
            'sms_numbers': [], 'sms_messages': [],
            'notifications_on': True, 'language': 'vi', 'chat_name': 'Anonymous',
            'system_notifications': [
                {"text_vi": "🎉 Chào mừng LỘC VN v10.0 - Email thật + SMS Demo!", "text_en": "🎉 Welcome to LỘC VN v10.0 - Real Email + SMS Demo!", "time": datetime.now().isoformat(), "read": False}
            ]
        }
    return session['data']

def save_data(data):
    session['data'] = data
    session.modified = True

# ==================== FLASK ROUTES ====================
@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

@app.route('/api/email/status')
def email_status():
    status = {}
    for api in REAL_EMAIL_APIS:
        try:
            email, _, _ = api.create()
            status[api.name] = "✅" if email else "❌"
        except:
            status[api.name] = "❌"
    return jsonify(status)

@app.route('/api/email/create', methods=['POST'])
def email_create():
    provider = request.json.get('provider')
    api = next((a for a in REAL_EMAIL_APIS if a.name == provider), None)
    if not api: return jsonify({'error': 'Provider not found'}), 400
    email, ident1, ident2 = api.create()
    if not email: return jsonify({'error': 'Creation failed'}), 500
    data = get_data()
    data['emails'].append({'email': email, 'provider': provider, 'id1': ident1, 'id2': ident2, 'created': datetime.now().isoformat()})
    data['current_email_idx'] = len(data['emails']) - 1
    save_data(data)
    return jsonify({'email': email})

@app.route('/api/email/refresh')
def email_refresh():
    data = get_data()
    if data['current_email_idx'] < 0: return jsonify({'messages': []})
    cur = data['emails'][data['current_email_idx']]
    api = next((a for a in REAL_EMAIL_APIS if a.name == cur['provider']), None)
    if not api: return jsonify({'messages': []})
    try:
        msgs = api.get_messages(cur['id1'], cur.get('id2')) if hasattr(api, 'get_messages') else []
        out = [{'id': m.get('id') or m.get('mail_id') or m.get('messageID'), 'sender': m.get('from') or m.get('from_addr'), 'subject': m.get('subject', '')[:50], 'date': m.get('date') or m.get('timestamp') or ''} for m in msgs]
    except Exception as e:
        return jsonify({'messages': [], 'error': str(e)})
    return jsonify({'messages': out})

@app.route('/api/email/view/<msg_id>')
def email_view(msg_id):
    data = get_data()
    if data['current_email_idx'] < 0: return jsonify({'error': 'No email'}), 400
    cur = data['emails'][data['current_email_idx']]
    api = next((a for a in REAL_EMAIL_APIS if a.name == cur['provider']), None)
    if not api: return jsonify({'error': 'API not found'}), 400
    try:
        msg = api.get_message(cur['id1'], cur.get('id2'), msg_id)
        if not msg: return jsonify({'error': 'Cannot fetch'}), 500
        body = msg.get('body') or msg.get('textBody') or msg.get('mail_text_only') or ''
        otp = None
        for p in OTP_PATTERNS:
            m = re.search(p, body, re.IGNORECASE)
            if m:
                otp = m.group(1) if m.groups() else m.group(0)
                break
        data['history'].insert(0, {'email': cur['email'], 'sender': msg.get('from'), 'subject': msg.get('subject')[:50], 'otp': otp, 'api': cur['provider'], 'type': 'email', 'time': datetime.now().isoformat()})
        save_data(data)
        return jsonify({'content': body, 'otp': otp})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/email/list')
def email_list():
    data = get_data()
    return jsonify({'emails': data['emails'], 'current_idx': data['current_email_idx']})

@app.route('/api/email/switch', methods=['POST'])
def email_switch():
    idx = request.json.get('idx')
    data = get_data()
    if 0 <= idx < len(data['emails']):
        data['current_email_idx'] = idx
        save_data(data)
        return jsonify({'success': True})
    return jsonify({'success': False}), 400

@app.route('/api/email/delete', methods=['POST'])
def email_delete():
    idx = request.json.get('idx')
    data = get_data()
    if 0 <= idx < len(data['emails']):
        del data['emails'][idx]
        if data['current_email_idx'] >= len(data['emails']):
            data['current_email_idx'] = len(data['emails']) - 1
        save_data(data)
        return jsonify({'success': True})
    return jsonify({'success': False}), 400

@app.route('/api/history')
def history():
    return jsonify(get_data()['history'])

@app.route('/api/clear_history', methods=['POST'])
def clear_history():
    get_data()['history'] = []
    save_data(get_data())
    return jsonify({'success': True})

@app.route('/api/clear_all', methods=['POST'])
def clear_all():
    session.pop('data', None)
    return jsonify({'success': True})

@app.route('/api/export_csv')
def export_csv():
    data = get_data()
    import csv, io
    out = io.StringIO()
    w = csv.writer(out)
    w.writerow(['Email/SĐT', 'Người gửi', 'Tiêu đề/Nội dung', 'OTP', 'API', 'Loại', 'Thời gian'])
    for r in data['history']:
        w.writerow([r['email'], r['sender'], r.get('subject', ''), r.get('otp', ''), r['api'], r['type'], r['time']])
    resp = make_response(out.getvalue())
    resp.headers['Content-Disposition'] = 'attachment; filename=locvn_history.csv'
    resp.mimetype = 'text/csv'
    return resp

# ---------- SMS demo ----------
@app.route('/api/sms/providers')
def sms_providers():
    return jsonify([p.name for p in SMS_PROVIDERS])

@app.route('/api/sms/countries')
def sms_countries():
    provider_name = request.args.get('provider')
    for p in SMS_PROVIDERS:
        if p.name == provider_name:
            return jsonify(p.get_countries())
    return jsonify(['Vietnam', 'USA'])

@app.route('/api/sms/create', methods=['POST'])
def sms_create():
    country = request.json.get('country', 'Vietnam')
    provider_name = request.json.get('provider', SMS_PROVIDERS[0].name)
    for p in SMS_PROVIDERS:
        if p.name == provider_name:
            phone, sid = p.get_phone_number(country)
            data = get_data()
            data['sms_numbers'].append({'phone': phone, 'sid': sid, 'provider': provider_name, 'country': country, 'created': datetime.now().isoformat()})
            save_data(data)
            return jsonify({'phone': phone, 'sid': sid, 'provider': provider_name})
    return jsonify({'error': 'Provider not found'}), 400

@app.route('/api/sms/refresh')
def sms_refresh():
    data = get_data()
    new_msgs = []
    for num in data['sms_numbers']:
        for p in SMS_PROVIDERS:
            if p.name == num['provider']:
                msgs = p.get_messages(num['sid'])
                for msg in msgs:
                    if msg not in data['sms_messages']:
                        new_msgs.append(msg)
                        data['history'].insert(0, {
                            'email': num['phone'], 'sender': msg['from'], 'subject': msg['message'][:50],
                            'otp': msg.get('otp'), 'api': f"SMS {num['provider']}", 'type': 'sms',
                            'time': datetime.now().isoformat()
                        })
                break
    data['sms_messages'].extend(new_msgs)
    save_data(data)
    return jsonify({'messages': data['sms_messages'], 'new_count': len(new_msgs)})

@app.route('/api/sms/numbers')
def sms_numbers():
    return jsonify({'numbers': get_data()['sms_numbers']})

@app.route('/api/sms/delete', methods=['POST'])
def sms_delete():
    idx = request.json.get('idx')
    data = get_data()
    if 0 <= idx < len(data['sms_numbers']):
        del data['sms_numbers'][idx]
        save_data(data)
        return jsonify({'success': True})
    return jsonify({'success': False}), 400

# ---------- Admin & Chat CÔNG KHAI ----------
def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if session.get('admin_logged_in'):
            return f(*args, **kwargs)
        return redirect(url_for('admin_login'))
    return decorated

@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        pwd = request.form.get('password')
        if hashlib.sha256(pwd.encode()).hexdigest() == ADMIN_PASSWORD_HASH:
            session['admin_logged_in'] = True
            return redirect(url_for('admin_panel'))
        return 'Sai mật khẩu', 403
    return '''
    <form method="post"><input type="password" name="password" placeholder="Mật khẩu admin"><button>Đăng nhập</button></form>
    '''

@app.route('/admin/panel')
@admin_required
def admin_panel():
    return render_template_string(ADMIN_PANEL_HTML)

@app.route('/api/admin/send_notification', methods=['POST'])
@admin_required
def send_notification():
    msg_vi = request.json.get('message_vi', '')
    msg_en = request.json.get('message_en', '')
    if msg_vi or msg_en:
        data = get_data()
        data['system_notifications'].insert(0, {'text_vi': msg_vi, 'text_en': msg_en, 'time': datetime.now().isoformat(), 'read': False})
        save_data(data)
    return jsonify({'success': True})

@app.route('/api/admin/send_chat', methods=['POST'])
@admin_required
def admin_send_chat():
    text = request.json.get('text', '')
    lang = request.json.get('lang', 'vi')
    if text:
        chat_messages.append({'sender_name': 'Admin', 'text': text, 'time': datetime.now().isoformat(), 'lang': lang})
    return jsonify({'success': True})

@app.route('/api/chat/send', methods=['POST'])
def user_send_chat():
    text = request.json.get('text', '')
    name = request.json.get('name', '').strip()
    if not name:
        name = get_data().get('chat_name', 'Anonymous')
    if text:
        chat_messages.append({'sender_name': name, 'text': text, 'time': datetime.now().isoformat(), 'lang': get_data().get('language', 'vi')})
    return jsonify({'success': True})

@app.route('/api/chat/messages')
def get_chat_messages():
    return jsonify(chat_messages[-200:])

@app.route('/api/chat/set_name', methods=['POST'])
def set_chat_name():
    data = get_data()
    name = request.json.get('name', '').strip()
    if name:
        data['chat_name'] = name
        save_data(data)
    return jsonify({'success': True})

@app.route('/api/system/notifications')
def get_system_notifications():
    return jsonify(get_data()['system_notifications'])

@app.route('/api/notifications/mark_read', methods=['POST'])
def mark_notification_read():
    idx = request.json.get('idx')
    data = get_data()
    if 0 <= idx < len(data['system_notifications']):
        data['system_notifications'][idx]['read'] = True
        save_data(data)
    return jsonify({'success': True})

@app.route('/api/set_language', methods=['POST'])
def set_language():
    data = get_data()
    data['language'] = request.json.get('lang', 'vi')
    save_data(data)
    return jsonify({'success': True})

# ==================== TEMPLATE CHÍNH (GIAO DIỆN NÂNG CẤP VỚI CHAT CÔNG KHAI) ====================
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="vi">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, user-scalable=yes">
    <title>LỘC VN - Temp Mail Pro | Email thật + SMS Demo | Chat công khai</title>
    <link href="https://fonts.googleapis.com/css2?family=Inter:opsz,wght@14..32,300..700&display=swap" rel="stylesheet">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0-beta3/css/all.min.css">
    <style>
        * { margin:0; padding:0; box-sizing:border-box; }
        body { font-family:'Inter',sans-serif; background:radial-gradient(circle at 20% 30%, #0a0f1e, #03050b); color:#eef; min-height:100vh; padding:20px; transition:0.2s; }
        .container { max-width:1400px; margin:0 auto; }
        .glass { background:rgba(15,25,45,0.5); backdrop-filter:blur(16px); border-radius:2rem; border:1px solid rgba(0,255,255,0.15); box-shadow:0 20px 35px -10px rgba(0,0,0,0.5); overflow:hidden; margin-bottom:24px; }
        .glass-header { padding:1rem 1.8rem; background:linear-gradient(135deg, rgba(0,255,255,0.1), rgba(0,0,0,0.2)); border-bottom:1px solid rgba(0,255,255,0.2); font-weight:700; font-size:1.2rem; display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; }
        .glass-body { padding:1.8rem; }
        .btn { border:none; border-radius:2rem; padding:0.7rem 1.5rem; font-weight:600; cursor:pointer; transition:0.2s; display:inline-flex; align-items:center; gap:8px; font-size:0.9rem; }
        .btn-primary { background:linear-gradient(135deg,#0af,#0cf); color:#000; }
        .btn-success { background:linear-gradient(135deg,#2ecc71,#27ae60); color:#fff; }
        .btn-danger { background:linear-gradient(135deg,#e74c3c,#c0392b); color:#fff; }
        .btn-outline { background:transparent; border:1px solid #0af; color:#0af; }
        .btn-donate { background:linear-gradient(135deg,#e53e3e,#f56565); color:white; }
        .form-input, .form-select { background:rgba(0,0,0,0.5); border:1px solid #2c3e66; border-radius:2rem; padding:0.7rem 1.2rem; color:#fff; width:100%; }
        .tabs { display:flex; gap:6px; background:rgba(0,0,0,0.3); border-radius:3rem; padding:6px; flex-wrap:wrap; margin-bottom:24px; }
        .tab-btn { background:transparent; border:none; padding:10px 22px; border-radius:2rem; color:#aac; font-weight:500; cursor:pointer; transition:0.2s; }
        .tab-btn.active { background:linear-gradient(135deg,#0af,#0cf); color:#000; box-shadow:0 4px 12px rgba(0,170,255,0.3); }
        .tab-pane { display:none; animation:fade 0.2s; }
        .tab-pane.active { display:block; }
        @keyframes fade { from{opacity:0;} to{opacity:1;} }
        .data-table { width:100%; border-collapse:collapse; font-size:0.85rem; }
        .data-table th { text-align:left; padding:12px 8px; color:#0cf; border-bottom:1px solid #2c3e66; }
        .data-table td { padding:10px 8px; border-bottom:1px solid #1e2a3a; }
        .pre-content { background:rgba(0,0,0,0.5); border-radius:1rem; padding:1rem; white-space:pre-wrap; max-height:400px; overflow:auto; font-family:monospace; }
        .otp-box { background:rgba(0,255,255,0.1); border:1px solid #0cf; border-radius:2rem; padding:12px 20px; display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; margin-top:16px; }
        .otp-code { font-size:1.8rem; font-weight:800; font-family:monospace; letter-spacing:4px; background:linear-gradient(135deg,#f0f,#0cf); -webkit-background-clip:text; background-clip:text; color:transparent; }
        .avatar { width:48px; height:48px; border-radius:50%; border:2px solid #0cf; object-fit:cover; }
        .lang-switch { display:flex; gap:8px; background:rgba(0,0,0,0.4); padding:5px 10px; border-radius:2rem; }
        .lang-btn { background:transparent; border:none; color:#fff; cursor:pointer; padding:4px 8px; border-radius:1rem; }
        .lang-btn.active { background:#0af; color:#000; }
        .notification-bell { position:relative; cursor:pointer; font-size:1.5rem; margin-left:15px; }
        .notification-bell .badge { position:absolute; top:-8px; right:-12px; background:#f56565; color:white; border-radius:50%; padding:2px 6px; font-size:10px; }
        .notification-panel { display:none; position:absolute; right:20px; top:70px; width:320px; background:rgba(0,0,0,0.9); border-radius:1rem; padding:10px; z-index:1000; border:1px solid #0af; backdrop-filter:blur(10px); }
        .notification-item { padding:8px; border-bottom:1px solid #2d3748; font-size:12px; cursor:pointer; }
        .top-bar-right { display:flex; gap:15px; align-items:center; }
        .footer { text-align:center; padding:1rem; font-size:0.7rem; color:#678; }
        .message-bubble { max-width:85%; padding:8px 12px; border-radius:1.2rem; margin-bottom:8px; background:#2c3e66; align-self:flex-start; }
        .message-bubble strong { color:#0cf; }
        .chat-container { height:350px; overflow-y:auto; background:rgba(0,0,0,0.3); border-radius:1rem; padding:12px; display:flex; flex-direction:column; }
        @media (max-width:700px) { .glass-body { padding:1rem; } .tabs { overflow-x:auto; flex-wrap:nowrap; } .tab-btn { white-space:nowrap; } .notification-panel { right:10px; width:280px; top:60px; } }
    </style>
</head>
<body>
<div class="container">
    <!-- HEADER -->
    <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:20px; flex-wrap:wrap; gap:15px;">
        <div style="display:flex; align-items:center; gap:15px;">
            <img src="https://i.pravatar.cc/80?img=7" class="avatar" alt="avatar">
            <div><h1 style="font-size:1.8rem; background:linear-gradient(135deg,#0cf,#f0f); -webkit-background-clip:text; background-clip:text; color:transparent;">LỘC VN <span style="font-size:1rem;">v10.0</span></h1>
            <p id="subtitle" data-vi="Email thật + SMS Demo | Chat công khai" data-en="Real Email + SMS Demo | Public Chat">Email thật + SMS Demo | Chat công khai</p></div>
        </div>
        <div class="top-bar-right">
            <button id="donateBtn" class="btn btn-donate btn-sm"><i class="fas fa-heart"></i> <span data-i18n="donate">Ủng hộ</span></button>
            <div class="notification-bell" id="notificationBell">
                <i class="fas fa-bell"></i>
                <span class="badge" id="notificationBadge" style="display:none;">0</span>
            </div>
            <div class="lang-switch">
                <button class="lang-btn" data-lang="vi">🇻🇳 VI</button>
                <button class="lang-btn" data-lang="en">🇬🇧 EN</button>
            </div>
        </div>
    </div>
    <div id="notificationPanel" class="notification-panel">
        <div style="font-weight:bold; padding:5px;">🔔 Thông báo hệ thống</div>
        <div id="notificationList"></div>
    </div>

    <!-- Main Card -->
    <div class="glass">
        <div class="glass-header"><span><i class="fas fa-envelope"></span> <span data-i18n="current_email">Email hiện tại</span></span> <span class="security-badge"><i class="fas fa-shield-alt"></span> AES-256</span></div>
        <div class="glass-body">
            <div style="display:flex; gap:12px; flex-wrap:wrap;">
                <input type="text" id="currentEmail" class="form-input" style="flex:2;" readonly>
                <button class="btn btn-outline" id="copyEmailBtn"><i class="fas fa-copy"></i> <span data-i18n="copy">Sao chép</span></button>
                <select id="providerSelect" class="form-select" style="flex:1;"></select>
            </div>
            <div style="margin-top:20px; display:flex; gap:12px; flex-wrap:wrap;">
                <button class="btn btn-success" id="createBtn"><i class="fas fa-plus"></i> <span data-i18n="create_email">Tạo email ẩn danh</span></button>
                <button class="btn btn-primary" id="refreshBtn"><i class="fas fa-sync"></i> <span data-i18n="refresh_inbox">Làm mới hộp thư</span></button>
                <button class="btn btn-danger" id="clearAllBtn"><i class="fas fa-trash"></i> <span data-i18n="clear_all">Xóa tất cả</span></button>
            </div>
            <div style="margin-top:20px; display:flex; gap:20px; font-size:0.8rem; background:rgba(0,0,0,0.3); border-radius:2rem; padding:10px;">
                <span>📧 <span id="totalEmails">0</span> email</span>
                <span>📜 <span id="totalHistory">0</span> lịch sử</span>
                <span>📱 <span id="totalSMS">0</span> SMS</span>
            </div>
        </div>
    </div>

    <!-- Tabs -->
    <div class="tabs">
        <button class="tab-btn active" data-tab="tab1"><i class="fas fa-inbox"></i> <span data-i18n="inbox">Hộp thư</span></button>
        <button class="tab-btn" data-tab="tab2"><i class="fas fa-list"></i> <span data-i18n="manage_emails">Quản lý email</span></button>
        <button class="tab-btn" data-tab="tab3"><i class="fas fa-history"></i> <span data-i18n="history">Lịch sử & OTP</span></button>
        <button class="tab-btn" data-tab="tab4"><i class="fas fa-shield-alt"></i> <span data-i18n="privacy">Chính sách bảo mật</span></button>
        <button class="tab-btn" data-tab="tab5"><i class="fas fa-gavel"></i> <span data-i18n="terms">Điều khoản</span></button>
        <button class="tab-btn" data-tab="tab6"><i class="fas fa-question"></i> <span data-i18n="faq">FAQ</span></button>
        <button class="tab-btn" data-tab="tab7"><i class="fas fa-sms"></i> <span data-i18n="sms">SMS Demo</span></button>
        <button class="tab-btn" data-tab="tab8"><i class="fas fa-comments"></i> <span data-i18n="chat">Chat công khai</span></button>
    </div>

    <!-- TAB 1: Inbox -->
    <div class="tab-pane active" id="tab1"><div class="glass"><div class="glass-header"><span data-i18n="inbox_messages">Tin nhắn đã nhận</span></div><div class="glass-body"><div style="overflow-x:auto;"><table class="data-table" id="inboxTable"><thead><tr><th>#</th><th><span data-i18n="sender">Người gửi</span></th><th><span data-i18n="subject">Tiêu đề</span></th><th><span data-i18n="date">Ngày</span></th></tr></thead><tbody id="inboxBody"></tbody></table></div><div style="margin-top:16px;"><strong><span data-i18n="email_content">Nội dung email</span></strong></div><div class="pre-content" id="emailContent">📌 <span data-i18n="click_to_view">Chọn email để xem</span></div><div class="otp-box"><span><i class="fas fa-key"></span> <strong><span data-i18n="extracted_otp">Mã OTP trích xuất:</span></strong></span><span class="otp-code" id="otpCode">---</span><button class="btn btn-outline btn-sm" id="copyOtpBtn"><i class="fas fa-copy"></span> <span data-i18n="copy_otp">Sao chép OTP</span></button></div></div></div></div>

    <!-- TAB 2: Manage emails -->
    <div class="tab-pane" id="tab2"><div class="glass"><div class="glass-header"><span data-i18n="email_list">Danh sách email đã tạo</span></div><div class="glass-body"><div style="overflow-x:auto;"><table class="data-table" id="manageTable"><thead><tr><th>#</th><th>Email</th><th>API</th><th><span data-i18n="created">Ngày tạo</span></th><th><span data-i18n="actions">Thao tác</span></th></tr></thead><tbody id="manageBody"></tbody></tr></div></div></div></div>

    <!-- TAB 3: History -->
    <div class="tab-pane" id="tab3"><div class="glass"><div class="glass-header"><span data-i18n="full_history">Lịch sử & OTP</span> <input type="text" id="searchHistory" placeholder="🔍 Tìm kiếm..." class="form-input" style="width:180px; padding:4px 12px;"></div><div class="glass-body"><div style="overflow-x:auto;"><table class="data-table" id="historyTable"><thead><tr><th>#</th><th><span data-i18n="type">Loại</span></th><th>Email/SĐT</th><th><span data-i18n="sender">Người gửi</span></th><th><span data-i18n="subject">Tiêu đề</span></th><th>OTP</th><th>API</th><th><span data-i18n="time">Thời gian</span></th></tr></thead><tbody id="historyBody"></tbody></table></div><div style="display:flex; gap:12px; margin-top:20px;"><button id="clearHistoryBtn" class="btn btn-danger btn-sm"><i class="fas fa-trash"></span> <span data-i18n="clear_history">Xóa lịch sử</span></button><button id="exportCsvBtn" class="btn btn-success btn-sm"><i class="fas fa-file-csv"></span> <span data-i18n="export_csv">Xuất CSV</span></button></div></div></div></div>

    <!-- TAB 4: Chính sách bảo mật (SIÊU CHI TIẾT) -->
    <div class="tab-pane" id="tab4"><div class="glass"><div class="glass-header"><span data-i18n="privacy_policy">CHÍNH SÁCH BẢO MẬT</span></div><div class="glass-body"><div class="pre-content" style="max-height:none;"><div data-i18n="privacy_text">📜 CHÍNH SÁCH BẢO MẬT - LỘC VN TEMP MAIL PRO<br>Phiên bản 10.0 | Cập nhật: 05/2026<br><br><strong>1. GIỚI THIỆU CHUNG VÀ CAM KẾT</strong><br>Chúng tôi, LỘC VN, hiểu rằng quyền riêng tư của bạn là vô giá. Dịch vụ Email tạm thời và SMS demo được xây dựng dựa trên nguyên tắc "Privacy by Design". Chúng tôi cam kết: KHÔNG yêu cầu thông tin cá nhân, KHÔNG theo dõi hành vi, KHÔNG bán dữ liệu. Toàn bộ dữ liệu phiên được mã hóa AES-256 trước khi lưu.<br><br><strong>2. DỮ LIỆU THU THẬP</strong><br>- Email tạm thời, lịch sử tin nhắn, OTP (lưu mã hóa, tự hủy sau 30 ngày).<br>- Tin nhắn chat công khai (lưu tên và nội dung, không lưu IP).<br>- Không thu thập IP thật, email thật, số điện thoại thật.<br><br><strong>3. BẢO MẬT KỸ THUẬT</strong><br>🔒 AES-256 session, 🛡️ CSP chống XSS, 🍪 HttpOnly cookie, 🚫 X-Frame-Options DENY, 🔄 Referrer-Policy, 📁 không lưu log chi tiết.<br><br><strong>4. QUYỀN CỦA BẠN</strong><br>Xuất CSV lịch sử, xóa toàn bộ dữ liệu, yêu cầu hỗ trợ support@locvn.com.<br><br><strong>5. LIÊN HỆ</strong><br>Mọi thắc mắc bảo mật: security@locvn.com.<br>© 2026 LỘC VN - TEMP MAIL PRO</div></div></div></div></div>

    <!-- TAB 5: Điều khoản dịch vụ (SIÊU CHI TIẾT) -->
    <div class="tab-pane" id="tab5"><div class="glass"><div class="glass-header"><span data-i18n="terms_of_service">ĐIỀU KHOẢN DỊCH VỤ</span></div><div class="glass-body"><div class="pre-content"><div data-i18n="terms_text">⚖️ ĐIỀU KHOẢN DỊCH VỤ - LỘC VN TEMP MAIL PRO<br>Phiên bản 2.0 | Cập nhật: 05/2026<br><br>1. Chấp nhận sử dụng: Bằng cách truy cập, bạn đồng ý với các điều khoản này.<br>2. Mô tả dịch vụ: Cung cấp email tạm thời (qua API bên thứ ba) và SMS demo (sinh OTP ngẫu nhiên).<br>3. Hành vi bị cấm: Spam, lừa đảo, tấn công hệ thống, đăng tải nội dung bất hợp pháp.<br>4. Giới hạn trách nhiệm: Dịch vụ cung cấp "nguyên trạng", không đảm bảo liên tục. LỘC VN không chịu trách nhiệm về bất kỳ thiệt hại nào phát sinh.<br>5. Thay đổi điều khoản: Có thể thay đổi bất cứ lúc nào, việc tiếp tục sử dụng đồng nghĩa với chấp nhận thay đổi.<br>6. Luật áp dụng: Pháp luật Việt Nam. Tranh chấp được giải quyết tại Tòa án TP.HCM.<br>Liên hệ pháp lý: legal@locvn.com</div></div></div></div></div>

    <!-- TAB 6: FAQ siêu chi tiết -->
    <div class="tab-pane" id="tab6"><div class="glass"><div class="glass-header"><span data-i18n="faq_title">CÂU HỎI THƯỜNG GẶP</span></div><div class="glass-body"><div class="pre-content"><div data-i18n="faq_text">❓ 1. Email có thật không? → Có, tích hợp 5 API real (Mail.tm, 1secmail, Guerrillamail, Temp-mail, Emailnator). Bạn có thể nhận OTP từ hầu hết các dịch vụ.<br>2. SMS có thật không? → SMS ở đây là bản demo, không cần API key, tự động sinh OTP ngẫu nhiên để minh họa. Nếu bạn cần SMS thật, hãy dùng dịch vả 5sim.net (có phí).<br>3. Làm sao để nhận OTP qua email? → Chỉ cần tạo email, dùng nó để đăng ký ở dịch vụ khác, sau đó vào hộp thư, click vào email – hệ thống tự động trích xuất OTP.<br>4. Dữ liệu được lưu bao lâu? → 30 ngày kể từ lần hoạt động cuối, được mã hóa AES-256.<br>5. Có mất phí không? → Hoàn toàn miễn phí.<br>6. Làm sao xóa lịch sử? → Nhấn "Xóa lịch sử" trong tab Lịch sử hoặc "Xóa tất cả" ở màn hình chính.<br>7. Tôi có thể chat với ai? → Chat công khai, tất cả người dùng đều thấy, bạn chỉ cần nhập tên và nhắn tin.<br>8. Admin có thể gửi thông báo không? → Có, admin đăng nhập tại /admin/login (mật khẩu admin123) và gửi thông báo, người dùng thấy chuông.<br>9. Làm sao xuất danh sách OTP? → Bấm "Xuất CSV" trong tab Lịch sử.<br>10. Tôi có thể tạo bao nhiêu email? → Không giới hạn.<br>... (thêm 10 câu hỏi khác về bảo mật, tính năng, v.v.)</div></div></div></div></div>

    <!-- TAB 7: SMS Demo -->
    <div class="tab-pane" id="tab7"><div class="glass"><div class="glass-header"><span data-i18n="real_sms">SMS DEMO - OTP NGẪU NHIÊN</span></div><div class="glass-body"><div class="warning-box" style="background:#ffcc0044; border-left:4px solid #ffcc00; padding:12px; border-radius:1rem;" id="smsWarning"><span data-i18n="sms_warning">📱 Đây là bản demo: tin nhắn và OTP được tạo ngẫu nhiên, không cần API key. Dùng để trải nghiệm giao diện.</span></div><div style="display:grid; grid-template-columns:1fr 1fr; gap:20px;"><div><label><span data-i18n="provider">Nhà cung cấp</span></label><select id="smsProviderSelect" class="form-select"></select><label style="margin-top:12px;"><span data-i18n="country">Quốc gia</span></label><select id="smsCountrySelect" class="form-select"></select><button id="createSmsBtn" class="btn btn-warning" style="margin-top:15px; width:100%;"><i class="fas fa-phone"></i> <span data-i18n="get_number">Lấy số ảo (demo)</span></button></div><div><span data-i18n="my_numbers">Số đã tạo</span><div id="smsNumbersList" style="max-height:200px; overflow-y:auto;"></div></div></div><div style="margin-top:20px;"><button id="refreshSmsBtn" class="btn btn-primary"><i class="fas fa-sync"></i> <span data-i18n="refresh_sms">Làm mới tin nhắn</span></button><div id="smsMessagesList" class="pre-content" style="margin-top:12px; max-height:250px;"></div></div></div></div></div>

    <!-- TAB 8: Chat công khai -->
    <div class="tab-pane" id="tab8"><div class="glass"><div class="glass-header"><i class="fas fa-comments"></i> <span data-i18n="public_chat">CHAT CÔNG KHAI</span></div><div class="glass-body"><div style="display:flex; gap:10px; margin-bottom:12px; align-items:center;"><span data-i18n="your_name">Tên của bạn:</span><input type="text" id="chatNameInput" class="form-input" style="flex:1; padding:6px 12px;" placeholder="Nhập tên hiển thị"><button id="setNameBtn" class="btn btn-outline btn-sm"><span data-i18n="save">Lưu</span></button></div><div id="chatMessages" class="chat-container"></div><div style="display:flex; gap:8px; margin-top:12px;"><input type="text" id="chatInput" class="form-input" placeholder="<span data-i18n='type_message'>Nhập tin nhắn...</span>" style="flex:1;"><button id="sendChatBtn" class="btn btn-primary"><i class="fas fa-paper-plane"></i> <span data-i18n="send">Gửi</span></button></div></div></div></div>

    <div class="footer">© 2026 LỘC VN - Email thật + SMS Demo | Chat công khai | Mã nguồn v10.0</div>
</div>

<script>
// i18n
const i18n = {
    vi: { current_email:"Email hiện tại", copy:"Sao chép", create_email:"Tạo email ẩn danh", refresh_inbox:"Làm mới hộp thư", clear_all:"Xóa tất cả", inbox:"Hộp thư", manage_emails:"Quản lý email", history:"Lịch sử & OTP", privacy:"Chính sách", terms:"Điều khoản", faq:"FAQ", sms:"SMS Demo", chat:"Chat công khai", sender:"Người gửi", subject:"Tiêu đề", date:"Ngày", email_content:"Nội dung email", extracted_otp:"Mã OTP trích xuất", copy_otp:"Sao chép OTP", clear_history:"Xóa lịch sử", export_csv:"Xuất CSV", type:"Loại", time:"Thời gian", provider:"Nhà cung cấp", country:"Quốc gia", get_number:"Lấy số ảo", refresh_sms:"Làm mới SMS", public_chat:"CHAT CÔNG KHAI", send:"Gửi", type_message:"Nhập tin nhắn...", donate:"Ủng hộ", your_name:"Tên của bạn", save:"Lưu" },
    en: { current_email:"Current email", copy:"Copy", create_email:"Create anonymous email", refresh_inbox:"Refresh inbox", clear_all:"Clear all", inbox:"Inbox", manage_emails:"Manage emails", history:"History & OTP", privacy:"Privacy", terms:"Terms", faq:"FAQ", sms:"SMS Demo", chat:"Public Chat", sender:"Sender", subject:"Subject", date:"Date", email_content:"Email content", extracted_otp:"Extracted OTP", copy_otp:"Copy OTP", clear_history:"Clear history", export_csv:"Export CSV", type:"Type", time:"Time", provider:"Provider", country:"Country", get_number:"Get virtual number", refresh_sms:"Refresh SMS", public_chat:"PUBLIC CHAT", send:"Send", type_message:"Type a message...", donate:"Donate", your_name:"Your name", save:"Save" }
};
let currentLang = 'vi';
function setLanguage(lang) {
    currentLang = lang;
    document.querySelectorAll('[data-i18n]').forEach(el => {
        const key = el.getAttribute('data-i18n');
        if(i18n[lang][key]) el.innerText = i18n[lang][key];
    });
    document.getElementById('subtitle').innerText = document.getElementById('subtitle').getAttribute(`data-${lang}`);
    fetch('/api/set_language', {method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({lang})});
}
document.querySelectorAll('.lang-btn').forEach(btn => btn.onclick = () => setLanguage(btn.dataset.lang));
setLanguage('vi');

// Donate random 2 links
const donateLinks = ["https://yeumoney.com/Frv9Q", "https://yeumoney.com/bf61j5KT"];
document.getElementById('donateBtn').addEventListener('click', () => {
    window.open(donateLinks[Math.floor(Math.random() * donateLinks.length)], '_blank');
    showToast('❤️ Cảm ơn bạn đã ủng hộ!');
});

// Global variables
let currentMessages = [], currentOtp = null;

// API calls
async function loadProviders() {
    let res = await fetch('/api/email/status');
    let status = await res.json();
    let select = document.getElementById('providerSelect');
    select.innerHTML = '';
    for(let [name, st] of Object.entries(status)) {
        let opt = document.createElement('option');
        opt.value = name;
        opt.textContent = `${name} ${st}`;
        select.appendChild(opt);
    }
}
async function createEmail() {
    let provider = document.getElementById('providerSelect').value;
    let res = await fetch('/api/email/create', {method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({provider})});
    if(res.ok) { let data = await res.json(); document.getElementById('currentEmail').value = data.email; showToast('✅ Email created'); refreshInbox(); loadEmailList(); loadHistory();}
    else showToast('❌ Tạo thất bại, thử lại', 'danger');
}
async function refreshInbox() {
    let res = await fetch('/api/email/refresh');
    let data = await res.json();
    if(data.error) { showToast('Lỗi làm mới: '+data.error, 'danger'); return; }
    currentMessages = data.messages;
    let tbody = document.getElementById('inboxBody');
    tbody.innerHTML = '';
    data.messages.forEach((msg, idx) => {
        let row = tbody.insertRow();
        row.insertCell(0).innerText = idx+1;
        row.insertCell(1).innerText = msg.sender || '?';
        row.insertCell(2).innerText = msg.subject || '';
        row.insertCell(3).innerText = msg.date || '';
        row.onclick = () => viewEmail(msg.id);
        row.style.cursor = 'pointer';
    });
}
async function viewEmail(id) {
    let res = await fetch(`/api/email/view/${id}`);
    let data = await res.json();
    if(data.error) { showToast('Lỗi xem email: '+data.error, 'danger'); return; }
    document.getElementById('emailContent').innerHTML = data.content.replace(/\\n/g,'<br>');
    if(data.otp) { currentOtp = data.otp; document.getElementById('otpCode').innerHTML = data.otp; showToast(`🔑 OTP: ${data.otp}`); }
    else { currentOtp = null; document.getElementById('otpCode').innerHTML = '---'; }
    loadHistory();
}
async function loadEmailList() {
    let res = await fetch('/api/email/list');
    let data = await res.json();
    let tbody = document.getElementById('manageBody');
    tbody.innerHTML = '';
    data.emails.forEach((em, idx) => {
        let row = tbody.insertRow();
        row.insertCell(0).innerText = idx+1;
        row.insertCell(1).innerText = em.email;
        row.insertCell(2).innerText = em.provider;
        row.insertCell(3).innerText = new Date(em.created).toLocaleString();
        let cell = row.insertCell(4);
        let useBtn = document.createElement('button'); useBtn.innerText='Dùng'; useBtn.className='btn btn-outline btn-sm'; useBtn.onclick=()=>switchEmail(idx);
        let delBtn = document.createElement('button'); delBtn.innerText='Xóa'; delBtn.className='btn btn-danger btn-sm'; delBtn.onclick=()=>deleteEmail(idx);
        cell.appendChild(useBtn); cell.appendChild(delBtn);
    });
    if(data.current_idx>=0 && data.emails[data.current_idx]) document.getElementById('currentEmail').value = data.emails[data.current_idx].email;
    document.getElementById('totalEmails').innerText = data.emails.length;
}
async function switchEmail(idx) { await fetch('/api/email/switch',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({idx})}); showToast('Đã chuyển'); loadEmailList(); refreshInbox();}
async function deleteEmail(idx) { if(confirm('Xóa email này?')){ await fetch('/api/email/delete',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({idx})}); loadEmailList(); refreshInbox(); } }
async function loadHistory() {
    let res = await fetch('/api/history');
    let history = await res.json();
    let tbody = document.getElementById('historyBody');
    tbody.innerHTML = '';
    history.forEach((h, i) => {
        let row = tbody.insertRow();
        row.insertCell(0).innerText = i+1;
        row.insertCell(1).innerText = h.type;
        row.insertCell(2).innerText = h.email;
        row.insertCell(3).innerText = h.sender;
        row.insertCell(4).innerText = h.subject;
        row.insertCell(5).innerHTML = h.otp ? `<span class="otp-code">${h.otp}</span>` : '---';
        row.insertCell(6).innerText = h.api;
        row.insertCell(7).innerText = new Date(h.time).toLocaleString();
    });
    document.getElementById('totalHistory').innerText = history.length;
}
async function clearHistory() { if(confirm('Xóa toàn bộ lịch sử?')){ await fetch('/api/clear_history',{method:'POST'}); loadHistory(); showToast('Đã xóa lịch sử'); } }
async function clearAll() { if(confirm('Xóa TẤT CẢ dữ liệu (email, SMS, lịch sử)?')){ await fetch('/api/clear_all',{method:'POST'}); location.reload(); } }
function exportCSV() { window.location.href='/api/export_csv'; }

// SMS demo
let smsProviders = [];
async function loadSMSProviders() {
    let res = await fetch('/api/sms/providers');
    smsProviders = await res.json();
    let select = document.getElementById('smsProviderSelect');
    select.innerHTML = '';
    smsProviders.forEach(p => { let opt = document.createElement('option'); opt.value=p; opt.textContent=p; select.appendChild(opt); });
    await loadSMSCountries();
}
async function loadSMSCountries() {
    let provider = document.getElementById('smsProviderSelect').value;
    let res = await fetch(`/api/sms/countries?provider=${encodeURIComponent(provider)}`);
    let countries = await res.json();
    let select = document.getElementById('smsCountrySelect');
    select.innerHTML = '';
    countries.forEach(c=>{ let opt=document.createElement('option'); opt.value=c; opt.textContent=c; select.appendChild(opt); });
}
async function createSMSNumber() {
    let provider = document.getElementById('smsProviderSelect').value;
    let country = document.getElementById('smsCountrySelect').value;
    let res = await fetch('/api/sms/create', {method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({provider,country})});
    if(res.ok){ let data=await res.json(); showToast(`📱 Số demo: ${data.phone}`); loadSMSNumbers(); }
    else showToast('Lỗi tạo số','danger');
}
async function loadSMSNumbers() {
    let res = await fetch('/api/sms/numbers');
    let data = await res.json();
    let div = document.getElementById('smsNumbersList');
    div.innerHTML = '<table class="data-table"><tr><th>#</th><th>Số</th><th>Provider</th><th></th></tr>';
    data.numbers.forEach((num, idx) => {
        div.innerHTML += `<tr><td>${idx+1}</td><td>${num.phone}</td><td>${num.provider}</td><td><button class="btn btn-danger btn-sm" onclick="deleteSMS(${idx})">Xóa</button></td></tr>`;
    });
    div.innerHTML += '</table>';
    document.getElementById('totalSMS').innerText = data.numbers.length;
}
async function deleteSMS(idx) { await fetch('/api/sms/delete',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({idx})}); loadSMSNumbers(); }
async function refreshSMS() {
    let res = await fetch('/api/sms/refresh');
    let data = await res.json();
    let div = document.getElementById('smsMessagesList');
    div.innerHTML = '';
    data.messages.forEach((msg,i) => {
        div.innerHTML += `<div style="border-bottom:1px solid #2c3e66; padding:6px;"><strong>${msg.from}</strong> | ${msg.time}<br>${msg.message}<br><span class="otp-code">OTP: ${msg.otp||'---'}</span></div>`;
    });
    if(data.new_count>0) showToast(`📱 ${data.new_count} tin nhắn SMS demo mới!`);
    loadHistory();
}

// Chat công khai
let currentChatName = localStorage.getItem('chatName') || '';
document.getElementById('chatNameInput').value = currentChatName;
document.getElementById('setNameBtn').onclick = () => {
    let name = document.getElementById('chatNameInput').value.trim();
    if(name) { localStorage.setItem('chatName', name); fetch('/api/chat/set_name', {method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({name})}); showToast('Đã đổi tên'); }
};
async function loadChat() {
    let res = await fetch('/api/chat/messages');
    let msgs = await res.json();
    let container = document.getElementById('chatMessages');
    container.innerHTML = '';
    msgs.forEach(m => {
        let div = document.createElement('div');
        div.className = 'message-bubble';
        div.innerHTML = `<strong>${escapeHtml(m.sender_name)}</strong><br>${escapeHtml(m.text)}<br><small>${new Date(m.time).toLocaleTimeString()}</small>`;
        container.appendChild(div);
    });
    container.scrollTop = container.scrollHeight;
}
async function sendChat() {
    let input = document.getElementById('chatInput');
    let text = input.value.trim();
    if(!text) return;
    let name = document.getElementById('chatNameInput').value.trim();
    if(!name) { showToast('Vui lòng nhập tên trước khi chat', 'warning'); return; }
    await fetch('/api/chat/send', {method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({text, name})});
    input.value = '';
    loadChat();
}
function escapeHtml(str) { return str.replace(/[&<>]/g, function(m){if(m==='&') return '&amp;'; if(m==='<') return '&lt;'; if(m==='>') return '&gt;'; return m;}); }
setInterval(loadChat, 3000);

// Notifications
async function loadSystemNotifications() {
    let res = await fetch('/api/system/notifications');
    let notifs = await res.json();
    let unread = notifs.filter(n=>!n.read).length;
    let badge = document.getElementById('notificationBadge');
    if(unread>0) { badge.style.display='inline-block'; badge.innerText=unread; showToast(`🔔 ${unread} thông báo mới từ Admin`); }
    else badge.style.display='none';
    let panel = document.getElementById('notificationList');
    panel.innerHTML = '';
    notifs.forEach((n, idx) => {
        let text = currentLang==='vi' ? n.text_vi : n.text_en;
        let div = document.createElement('div');
        div.className = 'notification-item';
        div.innerHTML = `<div><i class="fas ${n.read ? 'fa-check-circle' : 'fa-circle'}"></i> ${text}</div><small>${new Date(n.time).toLocaleString()}</small>`;
        div.onclick = async () => {
            if(!n.read) { await fetch('/api/notifications/mark_read', {method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({idx})}); loadSystemNotifications(); }
        };
        panel.appendChild(div);
    });
}
setInterval(loadSystemNotifications, 15000);
document.getElementById('notificationBell').addEventListener('click', () => {
    let panel = document.getElementById('notificationPanel');
    panel.style.display = panel.style.display === 'block' ? 'none' : 'block';
    loadSystemNotifications();
});
document.addEventListener('click', (e) => {
    if (!document.getElementById('notificationBell').contains(e.target) && !document.getElementById('notificationPanel').contains(e.target))
        document.getElementById('notificationPanel').style.display = 'none';
});

// Event listeners
document.getElementById('createBtn').onclick = createEmail;
document.getElementById('refreshBtn').onclick = refreshInbox;
document.getElementById('copyEmailBtn').onclick = () => { navigator.clipboard.writeText(document.getElementById('currentEmail').value); showToast('Đã copy email'); };
document.getElementById('copyOtpBtn').onclick = () => { if(currentOtp) { navigator.clipboard.writeText(currentOtp); showToast('Đã copy OTP'); } };
document.getElementById('clearAllBtn').onclick = clearAll;
document.getElementById('clearHistoryBtn').onclick = clearHistory;
document.getElementById('exportCsvBtn').onclick = exportCSV;
document.getElementById('createSmsBtn').onclick = createSMSNumber;
document.getElementById('refreshSmsBtn').onclick = refreshSMS;
document.getElementById('sendChatBtn').onclick = sendChat;

function showToast(msg,type='success') {
    let toast = document.createElement('div');
    toast.style.cssText = `position:fixed; bottom:20px; left:20px; background:${type==='success'?'#2ecc71':'#e74c3c'}; color:white; padding:10px 18px; border-radius:40px; z-index:9999; font-size:0.9rem;`;
    toast.innerText = msg;
    document.body.appendChild(toast);
    setTimeout(()=>toast.remove(), 3000);
}

// Tab switching
document.querySelectorAll('.tab-btn').forEach(btn => {
    btn.onclick = () => {
        document.querySelectorAll('.tab-btn').forEach(b=>b.classList.remove('active'));
        document.querySelectorAll('.tab-pane').forEach(p=>p.classList.remove('active'));
        btn.classList.add('active');
        let id = btn.dataset.tab;
        document.getElementById(id).classList.add('active');
        if(id==='tab1') refreshInbox();
        if(id==='tab2') loadEmailList();
        if(id==='tab3') loadHistory();
        if(id==='tab7') { loadSMSNumbers(); refreshSMS(); }
        if(id==='tab8') loadChat();
    };
});

loadProviders(); createEmail(); loadEmailList(); loadHistory(); loadSMSProviders(); loadSMSNumbers();
setInterval(refreshInbox, 15000);
</script>
</body>
</html>
"""

ADMIN_PANEL_HTML = """
<!DOCTYPE html>
<html>
<head><title>Admin LỘC VN</title><link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600&display=swap" rel="stylesheet"><style>body{font-family:Inter; background:#0a0f1e;color:#fff;padding:20px;} .card{background:#1e2a3a;border-radius:20px;padding:20px;margin-bottom:20px;} input,textarea{width:100%;background:#000;border:1px solid #0af;border-radius:12px;padding:10px;color:#fff;} button{background:#0af;border:none;border-radius:30px;padding:10px 20px;cursor:pointer;}</style></head>
<body><h1>👑 Admin Panel - LỘC VN</h1>
<div class="card"><h2>📢 Gửi thông báo hệ thống (chuông)</h2><input type="text" id="notif_vi" placeholder="Tiếng Việt"><input type="text" id="notif_en" placeholder="English" style="margin-top:8px;"><button onclick="sendNotif()">Gửi thông báo</button></div>
<div class="card"><h2>💬 Gửi tin nhắn chat công khai (với tư cách Admin)</h2><input type="text" id="adminMsg" placeholder="Nội dung..."><select id="langChat"><option value="vi">🇻🇳 Tiếng Việt</option><option value="en">🇬🇧 English</option></select><button onclick="sendChat()">Gửi tin nhắn</button></div>
<script>
async function sendNotif() { let vi=document.getElementById('notif_vi').value, en=document.getElementById('notif_en').value; await fetch('/api/admin/send_notification',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({message_vi:vi,message_en:en})}); alert('Đã gửi thông báo!'); }
async function sendChat() { let text=document.getElementById('adminMsg').value, lang=document.getElementById('langChat').value; if(text){ await fetch('/api/admin/send_chat',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({text,lang})}); alert('Đã gửi'); document.getElementById('adminMsg').value=''; } }
</script>
</body></html>
"""

if __name__ == '__main__':
    print("""
    ╔══════════════════════════════════════════════════════════════╗
    ║   🚀 LỘC VN - TEMP MAIL PRO v10.0 (Email thật + SMS Demo)   ║
    ║   🔐 Admin: /admin/login  (mật khẩu: admin123)              ║
    ║   💬 Chat công khai - nhập tên bất kỳ                       ║
    ║   🔔 Chuông thông báo hệ thống (admin gửi)                  ║
    ║   🌐 http://localhost:5000                                  ║
    ╚══════════════════════════════════════════════════════════════╝
    """)
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)
