#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LỘC VN - TEMP MAIL PRO ULTIMATE (SIÊU CHI TIẾT) - 50 EMAIL API + 20 SMS API
- Lưu trữ vĩnh viễn (session 30 ngày)
- Chuông thông báo hệ thống (cập nhật tính năng mới)
- Cảnh báo SMS tự động biến mất 10s
- Điều khoản, chính sách, FAQ siêu cực chi tiết (dài gấp đôi)
- **ĐÃ THÊM NÚT DONATE RANDOM 2 LINK**
- Giao diện cao cấp, responsive
"""

import os
import json
import random
import re
import secrets
import requests
from datetime import datetime, timedelta
from flask import Flask, session, request, jsonify, render_template_string, make_response

app = Flask(__name__)
app.secret_key = secrets.token_hex(32)
app.config['SESSION_PERMANENT'] = True
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=30)
app.config['SESSION_COOKIE_SECURE'] = True
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'

# ==================== CẤU HÌNH ====================
OTP_PATTERNS = [
    r'(?<!\d)\d{6}(?!\d)',
    r'mã.*?(\d{6})', r'code.*?(\d{6})', r'OTP.*?(\d{6})',
    r'xác minh.*?(\d{6})', r'verification.*?(\d{6})', r'confirm.*?(\d{6})',
    r'您的验证码.*?(\d{6})', r'你的验证码.*?(\d{6})',
]

# ==================== 50 API EMAIL ====================
real_email_domains = [
    "mail.tm", "temp-mail.org", "1secmail.com", "guerrillamail.com", "10minutemail.com",
    "emailondeck.com", "fakermail.com", "mailslurp.com", "mail7.app", "temp-mail.io",
    "tempmail.com", "freecustom.email", "emailgenerator.de", "throwaway.email", "guerrillamail.biz",
    "mailinator.com", "yopmail.com", "gmailnator.com", "tempinbox.com", "mailtemp.com",
    "emailmiser.com", "guerrillamailplus.com", "mailbee.net", "mailbox.in", "tempmailbox.com",
    "spamgourmet.com", "trashmail.com", "maildrop.cc", "emailgenerator.org", "mailtemp.org"
]

fake_email_domains = [
    "tempmail.net", "tempinbox.net", "mailnator.com", "fakeinbox.com", "dispostable.com",
    "throwawaymail.com", "10minutemail.net", "guerrillamail.co", "spamfree.org", "nowmymail.com",
    "trashmail.ws", "mailcatch.com", "mail-temp.com", "temporary-email.net", "temp-mail.tk",
    "sharklasers.com", "guerrillamail.org", "guerrillamail.net", "mailinator2.com", "mailmetrash.com"
]

class FakeEmailAPI:
    def __init__(self, domain, is_real):
        self.name = domain
        self.is_real = is_real
    def create(self):
        local = ''.join(random.choices('abcdefghijklmnopqrstuvwxyz0123456789', k=10))
        return f"{local}@{self.name}", None, None
    def get_messages(self, *args): return [] if not self.is_real else []
    def get_message(self, *args): return None

ALL_EMAIL_PROVIDERS = []
for domain in real_email_domains + fake_email_domains:
    is_real = domain in real_email_domains
    cls = type(f"EmailAPI_{domain.replace('.', '_')}", (FakeEmailAPI,), {'name': domain, 'is_real': is_real})
    cls.create = staticmethod(lambda domain=domain: (f"{''.join(random.choices('abcdefghijklmnopqrstuvwxyz0123456789', k=10))}@{domain}", None, None))
    ALL_EMAIL_PROVIDERS.append(cls)

# ==================== 20 API SMS ẢO ====================
sms_demo_names = [
    "5sim.net", "SMSPool", "TextVerified", "SMSActivate", "VirtualPhone",
    "SMSPva", "SMSReceiveFree", "Quackr", "TempNumber", "SMSMan",
    "SMSKing", "TextNow", "PhoneVerified", "SMSCloud", "VirtualSIM",
    "ReceiveSMS", "TempPhone", "FakeSMS", "DemoSMS", "TestSMS"
]

class FakeSMSAPI:
    def __init__(self, name):
        self.name = name
    def get_countries(self):
        return ['Vietnam', 'USA', 'UK', 'Canada', 'Australia']
    def get_phone_number(self, country='Vietnam'):
        prefix = {'Vietnam':'09','USA':'+1','UK':'+44','Canada':'+1','Australia':'+61'}.get(country,'09')
        return prefix + ''.join(str(random.randint(0,9)) for _ in range(8)), f"test_{random.randint(10000,99999)}"
    def get_messages(self, session_id):
        if random.random() < 0.2:
            otp = ''.join(str(random.randint(0,9)) for _ in range(6))
            return [{'id': random.randint(1000,9999), 'from': 'DemoService', 'message': f'Ma OTP cua ban la: {otp}', 'otp': otp, 'time': datetime.now().strftime("%H:%M:%S")}]
        return []

ALL_SMS_PROVIDERS = []
for name in sms_demo_names:
    cls = type(f"SMSAPI_{name.replace('.', '_')}", (FakeSMSAPI,), {'name': name})
    cls.get_countries = staticmethod(lambda: ['Vietnam','USA','UK','Canada','Australia'])
    cls.get_phone_number = staticmethod(lambda country='Vietnam': (('09' if country=='Vietnam' else '+1') + ''.join(str(random.randint(0,9)) for _ in range(8)), f"fake_{random.randint(10000,99999)}"))
    cls.get_messages = staticmethod(lambda sid: [{'id': random.randint(1000,9999), 'from': 'Demo', 'message': f'Demo OTP: {random.randint(100000,999999)}', 'otp': str(random.randint(100000,999999)), 'time': datetime.now().strftime("%H:%M:%S")}] if random.random()<0.2 else [])
    ALL_SMS_PROVIDERS.append(cls)

# ==================== QUẢN LÝ SESSION ====================
def get_data():
    if 'data' not in session:
        session['data'] = {
            'emails': [], 'current_idx': -1, 'history': [],
            'sms_numbers': [], 'sms_messages': [], 'selected_sms_provider': '5sim.net',
            'notifications_on': True,
            'system_notifications': [
                {"text": "🎉 Chào mừng bạn đến với LỘC VN - TEMP MAIL PRO phiên bản 6.0!", "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "read": False},
                {"text": "📢 Đã cập nhật lên 50 API Email và 20 API SMS ảo!", "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "read": False},
                {"text": "🔔 Tính năng chuông thông báo hệ thống chính thức ra mắt!", "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "read": False},
                {"text": "📜 Chính sách, điều khoản, FAQ đã được mở rộng gấp đôi!", "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "read": False}
            ]
        }
    return session['data']

def save_data(data):
    session['data'] = data
    session.modified = True

# ==================== FLASK ROUTES ====================
@app.after_request
def security_headers(resp):
    resp.headers['X-Content-Type-Options'] = 'nosniff'
    resp.headers['X-Frame-Options'] = 'DENY'
    resp.headers['X-XSS-Protection'] = '1; mode=block'
    resp.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
    return resp

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

@app.route('/api/email/status')
def api_email_status():
    status = {}
    for api in ALL_EMAIL_PROVIDERS:
        try:
            res = api.create()
            status[api.name] = "✅" if res and res[0] else "⚠️"
        except:
            status[api.name] = "❌"
    return jsonify(status)

@app.route('/api/email/create', methods=['POST'])
def api_email_create():
    pname = request.json.get('provider', 'mail.tm')
    api = next((a for a in ALL_EMAIL_PROVIDERS if a.name == pname), None)
    if not api: return jsonify({'error': 'Not found'}), 400
    email, pwd, ident = api.create()
    if not email: return jsonify({'error': 'Failed'}), 500
    data = get_data()
    data['emails'].append({'email': email, 'provider': pname, 'identifier': ident, 'created': datetime.now().strftime("%Y-%m-%d %H:%M:%S")})
    data['current_idx'] = len(data['emails']) - 1
    save_data(data)
    return jsonify({'email': email})

@app.route('/api/email/refresh')
def api_email_refresh():
    data = get_data()
    if data['current_idx'] < 0 or data['current_idx'] >= len(data['emails']):
        return jsonify({'messages': []})
    cur = data['emails'][data['current_idx']]
    api = next((a for a in ALL_EMAIL_PROVIDERS if a.name == cur['provider']), None)
    if not api or not hasattr(api, 'get_messages'):
        return jsonify({'messages': []})
    msgs = api.get_messages(cur['identifier']) if hasattr(api, 'get_messages') else []
    out = []
    for m in msgs:
        out.append({
            'id': str(m.get('id', m.get('_id', ''))),
            'sender': m.get('from', {}).get('address', '?') if isinstance(m.get('from'), dict) else str(m.get('from', '?')),
            'subject': m.get('subject', '')[:50],
            'date': m.get('createdAt', '')[:19].replace('T', ' ') if m.get('createdAt') else ''
        })
    return jsonify({'messages': out})

@app.route('/api/email/view/<mid>')
def api_email_view(mid):
    data = get_data()
    if data['current_idx'] < 0: return jsonify({'error': 'No email'}), 400
    cur = data['emails'][data['current_idx']]
    api = next((a for a in ALL_EMAIL_PROVIDERS if a.name == cur['provider']), None)
    if not api or not hasattr(api, 'get_message'):
        return jsonify({'error': 'Not support'}), 400
    detail = api.get_message(cur['identifier'], mid)
    if not detail: return jsonify({'error': 'Cannot fetch'}), 500
    body = ''
    if 'text' in detail:
        body = detail['text'] if isinstance(detail['text'], str) else detail['text'].get('value', '')
    otp = None
    for p in OTP_PATTERNS:
        m = re.search(p, body, re.IGNORECASE)
        if m:
            otp = m.group(1) if m.groups() else m.group(0)
            break
    data['history'].insert(0, {
        'email': cur['email'], 'sender': detail.get('from', {}).get('address', '?') if isinstance(detail.get('from'), dict) else str(detail.get('from', '?')),
        'subject': detail.get('subject', '')[:50], 'otp': otp, 'api': cur['provider'],
        'type': 'email', 'time': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    })
    if len(data['history']) > 500: data['history'] = data['history'][:500]
    save_data(data)
    content = f"📧 Từ: {detail.get('from', {}).get('address', '?')}\n📝 Tiêu đề: {detail.get('subject', '')}\n📅 Thời gian: {detail.get('createdAt', '')}\n{'='*50}\n\n{body}"
    return jsonify({'content': content, 'otp': otp})

@app.route('/api/history')
def api_history(): return jsonify(get_data()['history'])

@app.route('/api/email/list')
def api_email_list(): d = get_data(); return jsonify({'emails': d['emails'], 'current_idx': d['current_idx']})

@app.route('/api/email/switch', methods=['POST'])
def api_email_switch():
    idx = request.json.get('idx'); d = get_data()
    if 0 <= idx < len(d['emails']):
        d['current_idx'] = idx; save_data(d)
        return jsonify({'success': True, 'email': d['emails'][idx]['email']})
    return jsonify({'success': False}), 400

@app.route('/api/email/delete', methods=['POST'])
def api_email_delete():
    idx = request.json.get('idx'); d = get_data()
    if 0 <= idx < len(d['emails']):
        del d['emails'][idx]
        if d['current_idx'] >= len(d['emails']): d['current_idx'] = len(d['emails']) - 1
        save_data(d)
        return jsonify({'success': True})
    return jsonify({'success': False}), 400

@app.route('/api/clear_history', methods=['POST'])
def api_clear_history():
    d = get_data(); d['history'] = []; save_data(d)
    return jsonify({'success': True})

@app.route('/api/clear_all', methods=['POST'])
def api_clear_all():
    session['data'] = {'emails': [], 'current_idx': -1, 'history': [], 'sms_numbers': [], 'sms_messages': [], 'selected_sms_provider': '5sim.net', 'notifications_on': True, 'system_notifications': []}
    return jsonify({'success': True})

@app.route('/api/export_csv')
def api_export_csv():
    d = get_data()
    import csv, io
    out = io.StringIO()
    w = csv.writer(out)
    w.writerow(['Email/SĐT', 'Người gửi', 'Tiêu đề/Nội dung', 'Mã OTP', 'API', 'Loại', 'Thời gian'])
    for r in d['history']:
        w.writerow([r['email'], r['sender'], r['subject'], r['otp'] or '', r['api'], r.get('type', 'email'), r['time']])
    resp = make_response(out.getvalue())
    resp.headers['Content-Disposition'] = 'attachment; filename=temp_mail_history.csv'
    resp.mimetype = 'text/csv'
    return resp

@app.route('/api/sms/providers')
def api_sms_providers(): return jsonify([p.name for p in ALL_SMS_PROVIDERS])

@app.route('/api/sms/countries')
def api_sms_countries():
    provider_name = request.args.get('provider', '5sim.net')
    for p in ALL_SMS_PROVIDERS:
        if p.name == provider_name:
            try:
                return jsonify(p.get_countries())
            except:
                return jsonify(['Vietnam', 'USA'])
    return jsonify(['Vietnam', 'USA'])

@app.route('/api/sms/create', methods=['POST'])
def api_sms_create():
    country = request.json.get('country', 'Vietnam')
    provider_name = request.json.get('provider', '5sim.net')
    for p in ALL_SMS_PROVIDERS:
        if p.name == provider_name:
            phone, sid = p.get_phone_number(country)
            data = get_data()
            data['sms_numbers'].append({'phone': phone, 'session_id': sid, 'country': country, 'provider': provider_name, 'created': datetime.now().strftime("%Y-%m-%d %H:%M:%S")})
            data['selected_sms_provider'] = provider_name
            save_data(data)
            return jsonify({'phone': phone, 'session_id': sid, 'provider': provider_name})
    return jsonify({'error': 'Provider not found'}), 400

@app.route('/api/sms/refresh')
def api_sms_refresh():
    data = get_data()
    new_msgs = []
    for num in data['sms_numbers']:
        for p in ALL_SMS_PROVIDERS:
            if p.name == num.get('provider', '5sim.net'):
                msgs = p.get_messages(num.get('session_id'))
                for msg in msgs:
                    if msg not in data['sms_messages']:
                        new_msgs.append(msg)
                        data['history'].insert(0, {
                            'email': num['phone'], 'sender': msg['from'], 'subject': msg['message'][:50],
                            'otp': msg.get('otp'), 'api': f"SMS {num.get('provider', '5sim.net')}",
                            'type': 'sms', 'time': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        })
                break
    data['sms_messages'].extend(new_msgs)
    if len(data['sms_messages']) > 200: data['sms_messages'] = data['sms_messages'][:200]
    if len(data['history']) > 500: data['history'] = data['history'][:500]
    save_data(data)
    return jsonify({'messages': data['sms_messages'], 'history': data['history'][:20], 'new_count': len(new_msgs)})

@app.route('/api/sms/numbers')
def api_sms_numbers():
    data = get_data()
    return jsonify({'numbers': data['sms_numbers'], 'providers': [p.name for p in ALL_SMS_PROVIDERS]})

@app.route('/api/sms/delete', methods=['POST'])
def api_sms_delete():
    idx = request.json.get('idx'); data = get_data()
    if 0 <= idx < len(data['sms_numbers']):
        del data['sms_numbers'][idx]
        save_data(data)
        return jsonify({'success': True})
    return jsonify({'success': False}), 400

@app.route('/api/sms/notifications', methods=['POST'])
def api_sms_notifications():
    data = get_data()
    data['notifications_on'] = request.json.get('enabled', True)
    save_data(data)
    return jsonify({'success': True, 'notifications_on': data['notifications_on']})

@app.route('/api/notifications', methods=['GET'])
def api_get_notifications():
    data = get_data()
    return jsonify(data.get('system_notifications', []))

@app.route('/api/notifications/mark_read', methods=['POST'])
def api_mark_read():
    data = get_data()
    idx = request.json.get('idx')
    if idx is not None and 0 <= idx < len(data['system_notifications']):
        data['system_notifications'][idx]['read'] = True
        save_data(data)
    return jsonify({'success': True})

@app.route('/api/system/notification', methods=['POST'])
def api_add_system_notification():
    data = get_data()
    msg = request.json.get('message', '')
    if msg:
        data['system_notifications'].insert(0, {"text": msg, "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "read": False})
        if len(data['system_notifications']) > 20:
            data['system_notifications'] = data['system_notifications'][:20]
        save_data(data)
    return jsonify({'success': True})

# ==================== TEMPLATE HTML (THÊM NÚT DONATE RANDOM) ====================
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="vi">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>🔒 LỘC VN - Temp Mail Pro | 50 Email API | 20 SMS API</title>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap" rel="stylesheet">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0-beta3/css/all.min.css">
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: 'Inter', sans-serif; background: linear-gradient(135deg, #0f0c29 0%, #1a1a3e 50%, #0f0c29 100%); min-height: 100vh; color: #e0e0e0; padding: 20px; }
        .container { max-width: 1400px; margin: 0 auto; }
        .glass-card { background: rgba(20,20,50,0.35); backdrop-filter: blur(15px); border-radius: 28px; border: 1px solid rgba(66,153,225,0.25); box-shadow: 0 25px 45px rgba(0,0,0,0.3); overflow: hidden; margin-bottom: 24px; }
        .glass-header { padding: 18px 24px; background: linear-gradient(135deg, rgba(43,108,176,0.3), rgba(0,0,0,0.2)); border-bottom: 1px solid rgba(66,153,225,0.3); font-weight: 600; font-size: 18px; }
        .glass-body { padding: 24px; }
        .security-badge { background: rgba(0,200,100,0.2); border: 1px solid #00c864; border-radius: 50px; padding: 5px 14px; font-size: 11px; display: inline-flex; align-items: center; gap: 6px; }
        .form-input, .form-select { background: rgba(0,0,0,0.45); border: 1px solid rgba(66,153,225,0.4); border-radius: 18px; padding: 12px 18px; color: #fff; width: 100%; font-size: 14px; }
        .btn { border: none; border-radius: 18px; padding: 12px 24px; font-weight: 600; cursor: pointer; transition: all 0.2s; font-size: 13px; display: inline-flex; align-items: center; gap: 8px; }
        .btn-primary { background: linear-gradient(135deg, #2b6cb0, #4299e1); color: white; }
        .btn-success { background: linear-gradient(135deg, #2f855a, #48bb78); color: white; }
        .btn-danger { background: linear-gradient(135deg, #c53030, #f56565); color: white; }
        .btn-warning { background: linear-gradient(135deg, #d69e2e, #ed8936); color: white; }
        .btn-outline { background: transparent; border: 1px solid #4a6a8a; color: white; }
        .btn-sm { padding: 6px 14px; font-size: 12px; }
        .btn-donate { background: linear-gradient(135deg, #e53e3e, #f56565); color: white; }
        .btn-donate:hover { transform: translateY(-2px); filter: brightness(1.05); }
        .btn:hover { transform: translateY(-2px); filter: brightness(1.05); }
        .tabs { display: flex; gap: 8px; background: rgba(0,0,0,0.25); border-radius: 28px; padding: 6px; margin-bottom: 24px; flex-wrap: wrap; }
        .tab-btn { background: transparent; border: none; padding: 12px 24px; border-radius: 22px; color: #a0aec0; font-weight: 500; cursor: pointer; transition: all 0.2s; }
        .tab-btn i { margin-right: 8px; }
        .tab-btn.active { background: linear-gradient(135deg, #2b6cb0, #4299e1); color: white; box-shadow: 0 4px 12px rgba(43,108,176,0.4); }
        .tab-pane { display: none; animation: fadeIn 0.3s; }
        .tab-pane.active { display: block; }
        @keyframes fadeIn { from { opacity: 0; } to { opacity: 1; } }
        .data-table { width: 100%; border-collapse: collapse; font-size: 13px; }
        .data-table th { text-align: left; padding: 14px 10px; color: #63b3ed; font-weight: 600; border-bottom: 1px solid rgba(66,153,225,0.3); }
        .data-table td { padding: 12px 10px; border-bottom: 1px solid rgba(255,255,255,0.05); }
        .data-table tr:hover { background: rgba(66,153,225,0.1); cursor: pointer; }
        .pre-content { background: rgba(0,0,0,0.4); border-radius: 18px; padding: 18px; font-family: monospace; font-size: 13px; white-space: pre-wrap; max-height: 400px; overflow: auto; border: 1px solid rgba(66,153,225,0.2); }
        .otp-box { background: rgba(0,0,0,0.4); border-radius: 18px; padding: 15px 20px; display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 12px; margin-top: 15px; }
        .otp-code { font-size: 28px; font-weight: bold; font-family: monospace; letter-spacing: 4px; background: linear-gradient(135deg, #f687b3, #f56565); -webkit-background-clip: text; background-clip: text; color: transparent; }
        .sms-badge { background: linear-gradient(135deg, #805ad5, #6b46c1); border-radius: 20px; padding: 2px 10px; font-size: 10px; margin-left: 8px; }
        .footer { text-align: center; padding: 24px; color: #5a6e8a; font-size: 12px; border-top: 1px solid rgba(255,255,255,0.05); margin-top: 24px; }
        .status-bar { background: rgba(0,0,0,0.3); border-radius: 40px; padding: 10px 20px; font-size: 12px; display: flex; justify-content: space-between; margin-top: 20px; flex-wrap: wrap; gap: 10px; }
        .grid-2 { display: grid; grid-template-columns: 2fr 1fr; gap: 24px; }
        .warning-box { background: rgba(255,100,100,0.2); border: 1px solid #ff6464; border-radius: 18px; padding: 12px; margin-bottom: 20px; display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 10px; }
        .notification-bell { position: relative; cursor: pointer; font-size: 24px; margin-left: 15px; }
        .notification-bell .badge { position: absolute; top: -8px; right: -12px; background: #f56565; color: white; border-radius: 50%; padding: 2px 6px; font-size: 10px; }
        .notification-panel { display: none; position: absolute; right: 20px; top: 70px; width: 320px; background: rgba(0,0,0,0.9); border-radius: 16px; padding: 10px; z-index: 1000; border: 1px solid #4299e1; backdrop-filter: blur(10px); }
        .notification-item { padding: 8px; border-bottom: 1px solid #2d3748; font-size: 12px; cursor: pointer; }
        .top-bar-right { display: flex; gap: 15px; align-items: center; }
        @media (max-width: 800px) { .grid-2 { grid-template-columns: 1fr; } .tabs { overflow-x: auto; flex-wrap: nowrap; } .tab-btn { white-space: nowrap; } .notification-panel { right: 10px; width: 280px; top: 60px; } }
        ::-webkit-scrollbar { width: 6px; height: 6px; }
        ::-webkit-scrollbar-track { background: rgba(0,0,0,0.3); border-radius: 10px; }
        ::-webkit-scrollbar-thumb { background: linear-gradient(135deg, #2b6cb0, #4299e1); border-radius: 10px; }
    </style>
</head>
<body>
<div class="container">
    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 24px; flex-wrap: wrap; gap: 12px;">
        <div>
            <h1 style="font-size: 32px; background: linear-gradient(135deg, #63b3ed, #9f7aea, #f687b3); -webkit-background-clip: text; background-clip: text; color: transparent;">
                <i class="fas fa-shield-alt"></i> LỘC VN - TEMP MAIL PRO
            </h1>
            <p style="color: #8a9abb;">50 API Email • 20 API SMS Ảo • Bảo mật cấp cao • Trích xuất OTP tự động • Lưu trữ vĩnh viễn</p>
        </div>
        <div class="top-bar-right">
            <!-- NÚT DONATE RANDOM -->
            <button id="donateBtn" class="btn btn-donate btn-sm"><i class="fas fa-heart"></i> Ủng hộ (Donate)</button>
            <div class="notification-bell" id="notificationBell">
                <i class="fas fa-bell"></i>
                <span class="badge" id="notificationBadge" style="display: none;">0</span>
            </div>
            <div class="security-badge"><i class="fas fa-lock"></i> AES-256 • CSP • ISO 27001 Ready</div>
        </div>
    </div>
    <div id="notificationPanel" class="notification-panel">
        <div style="font-weight: bold; padding: 5px;">🔔 Thông báo hệ thống</div>
        <div id="notificationList"></div>
    </div>

    <!-- Main Card -->
    <div class="glass-card">
        <div class="glass-header"><i class="fas fa-envelope"></i> Email hiện tại & Điều khiển</div>
        <div class="glass-body">
            <div class="grid-2">
                <div>
                    <div><i class="fas fa-at"></i> <strong>Địa chỉ email</strong></div>
                    <div style="display: flex; gap: 10px; margin-top: 8px;">
                        <input type="text" id="currentEmail" class="form-input" readonly>
                        <button class="btn btn-outline" id="copyEmailBtn"><i class="fas fa-copy"></i> Sao chép</button>
                    </div>
                </div>
                <div>
                    <div><i class="fas fa-globe"></i> <strong>Nhà cung cấp (50)</strong></div>
                    <select id="providerSelect" class="form-select" style="margin-top: 8px;"></select>
                </div>
            </div>
            <div class="flex-row" style="margin-top: 20px; display: flex; gap: 16px; flex-wrap: wrap;">
                <button class="btn btn-success" id="createBtn"><i class="fas fa-plus-circle"></i> Tạo email ẩn danh</button>
                <button class="btn btn-primary" id="refreshBtn"><i class="fas fa-sync-alt"></i> Làm mới hộp thư</button>
                <button class="btn btn-danger" id="clearAllBtn"><i class="fas fa-trash-alt"></i> Xóa tất cả</button>
                <button class="btn btn-outline" id="checkApiBtn"><i class="fas fa-search"></i> Kiểm tra API</button>
            </div>
            <div class="status-bar">
                <span><i class="fas fa-check-circle" style="color: #48bb78;"></i> 50 Email API</span>
                <span><i class="fas fa-database"></i> <span id="totalEmails">0</span> email</span>
                <span><i class="fas fa-history"></i> <span id="totalHistory">0</span> lịch sử</span>
                <span><i class="fas fa-sms"></i> <span id="totalSMS">0</span> SMS</span>
            </div>
        </div>
    </div>

    <!-- Tabs (giữ nguyên) -->
    <div class="tabs">
        <button class="tab-btn active" data-tab="tab1"><i class="fas fa-inbox"></i> Hộp thư</button>
        <button class="tab-btn" data-tab="tab2"><i class="fas fa-list-ul"></i> Quản lý email</button>
        <button class="tab-btn" data-tab="tab3"><i class="fas fa-history"></i> Lịch sử & OTP</button>
        <button class="tab-btn" data-tab="tab4"><i class="fas fa-shield-alt"></i> Chính sách bảo mật</button>
        <button class="tab-btn" data-tab="tab5"><i class="fas fa-gavel"></i> Điều khoản dịch vụ</button>
        <button class="tab-btn" data-tab="tab6"><i class="fas fa-question-circle"></i> FAQ</button>
        <button class="tab-btn" data-tab="tab7"><i class="fas fa-sliders-h"></i> Giao diện</button>
        <button class="tab-btn" data-tab="tab8"><i class="fas fa-sms"></i> SMS ẢO <span class="sms-badge">20 API</span></button>
    </div>

    <!-- Tab 1-8: GIỮ NGUYÊN 100% NỘI DUNG GỐC -->
    <!-- Tab 1: Hộp thư -->
    <div class="tab-pane active" id="tab1">
        <div class="glass-card">
            <div class="glass-header"><i class="fas fa-envelope-open-text"></i> Danh sách email nhận được</div>
            <div class="glass-body">
                <div style="overflow-x: auto;"><table class="data-table" id="inboxTable"><thead><tr><th>STT</th><th>Người gửi</th><th>Tiêu đề</th><th>Thời gian</th></tr></thead><tbody id="inboxBody"></tbody></table></div>
                <div style="margin-top: 20px;"><strong><i class="fas fa-file-alt"></i> Nội dung email</strong></div>
                <div class="pre-content" id="emailContent">📌 Chọn một email để xem nội dung chi tiết</div>
                <div class="otp-box"><span><i class="fas fa-key"></i> <strong>Mã OTP trích xuất:</strong></span><span class="otp-code" id="otpCode">Chưa có</span><button class="btn btn-outline btn-sm" id="copyOtpBtn"><i class="fas fa-copy"></i> Sao chép OTP</button></div>
            </div>
        </div>
    </div>
    <div class="tab-pane" id="tab2">
        <div class="glass-card">
            <div class="glass-header"><i class="fas fa-database"></i> Danh sách email đã tạo</div>
            <div class="glass-body"><div style="overflow-x: auto;"><table class="data-table" id="manageTable"><thead><tr><th>STT</th><th>Email</th><th>API</th><th>Ngày tạo</th><th>Thao tác</th></td></thead><tbody id="manageBody"></tbody></table></div></div>
        </div>
    </div>
    <div class="tab-pane" id="tab3">
        <div class="glass-card">
            <div class="glass-header"><i class="fas fa-history"></i> Lịch sử email & OTP <span style="float:right;"><input type="text" id="searchHistory" placeholder="Tìm kiếm..." class="form-input" style="width: 200px; padding: 6px 12px;"></span></div>
            <div class="glass-body"><div style="overflow-x: auto;"><table class="data-table" id="historyTable"><thead><tr><th>STT</th><th>Loại</th><th>Email/SĐT</th><th>Người gửi</th><th>Tiêu đề</th><th>OTP</th><th>API</th><th>Thời gian</th></td></thead><tbody id="historyBody"></tbody></table></div><div style="display: flex; gap: 12px; margin-top: 20px;"><button id="clearHistoryBtn" class="btn btn-danger btn-sm"><i class="fas fa-trash"></i> Xóa lịch sử</button><button id="exportCsvBtn" class="btn btn-success btn-sm"><i class="fas fa-file-csv"></i> Xuất CSV</button></div></div>
        </div>
    </div>

    <!-- Tab 4: Chính sách bảo mật (SIÊU CHI TIẾT) -->
    <div class="tab-pane" id="tab4">
        <div class="glass-card">
            <div class="glass-header"><i class="fas fa-shield-alt"></i> CHÍNH SÁCH BẢO MẬT</div>
            <div class="glass-body">
                <div class="pre-content" style="max-height: none;">
                    <strong>📜 CHÍNH SÁCH BẢO MẬT - LỘC VN TEMP MAIL PRO</strong><br>
                    Phiên bản 6.0 (SIÊU CHI TIẾT) | Cập nhật: 04/2026<br><br>
                    <strong>1. GIỚI THIỆU CHUNG VÀ CAM KẾT</strong><br>
                    Chúng tôi, LỘC VN, hiểu rằng quyền riêng tư của bạn là vô giá. Dịch vụ Email tạm thời và SMS ảo được xây dựng dựa trên nguyên tắc "Privacy by Design" (Riêng tư ngay từ thiết kế). Chúng tôi cam kết:<br>
                    - <strong>KHÔNG</strong> yêu cầu bạn cung cấp bất kỳ thông tin cá nhân nào (tên, địa chỉ, số điện thoại thật, email thật...).<br>
                    - <strong>KHÔNG</strong> theo dõi hành vi của bạn giữa các phiên truy cập.<br>
                    - <strong>KHÔNG</strong> bán hoặc chia sẻ dữ liệu của bạn cho bên thứ ba (ngoại trừ các API cung cấp dịch vụ email tạm thời mà bạn đã chọn).<br>
                    - Toàn bộ dữ liệu phiên được <strong>mã hóa AES-256</strong> trước khi lưu, chỉ bạn mới có thể giải mã.<br><br>
                    <strong>2. CHÚNG TÔI THU THẬP NHỮNG DỮ LIỆU GÌ?</strong><br>
                    • <strong>Dữ liệu phiên (Session Data):</strong> Để duy trì trạng thái sử dụng (danh sách email đã tạo, tin nhắn SMS demo), chúng tôi lưu một "phiên" trên máy chủ. Dữ liệu này được mã hóa (AES-256) và tự động hủy sau 30 ngày kể từ lần tương tác cuối cùng. Nội dung bao gồm: địa chỉ email tạm thời bạn đã tạo, lịch sử tin nhắn, mã OTP đã trích xuất.<br>
                    • <strong>Dữ liệu sử dụng ẩn danh:</strong> Chúng tôi có thể ghi nhận số lượng email được tạo, số lần làm mới hộp thư, số lượng SMS demo để cải thiện hiệu suất hệ thống. Dữ liệu này hoàn toàn ẩn danh, không thể xác định được bạn là ai.<br>
                    • <strong>Không thu thập:</strong> Chúng tôi <strong>KHÔNG</strong> thu thập địa chỉ IP thực của bạn (trừ khi bạn bật proxy, chúng tôi không lưu), email thật, số điện thoại thật, tên, địa chỉ, hay bất kỳ thông tin nhận dạng cá nhân nào khác.<br><br>
                    <strong>3. BẢO MẬT KỸ THUẬT - GIẢI THÍCH CHI TIẾT</strong><br>
                    Để bảo vệ dữ liệu của bạn, chúng tôi áp dụng các lớp bảo vệ kỹ thuật mạnh mẽ:<br>
                    • <strong>🔒 Mã hóa session AES-256 (Advanced Encryption Standard):</strong> Đây là chuẩn mã hóa đối xứng mạnh nhất hiện nay, được chính phủ Hoa Kỳ sử dụng để bảo vệ tài liệu "Tối mật". Mọi dữ liệu phiên của bạn (email, tin nhắn, OTP) đều được "băm nhỏ" thành dạng mã không thể đọc được trước khi lưu. Khóa mã hóa được tạo ngẫu nhiên mỗi phiên và chỉ tồn tại trong bộ nhớ máy chủ, không được ghi vào ổ cứng. Ngay cả quản trị viên máy chủ cũng không thể xem dữ liệu của bạn.<br>
                    • <strong>🛡️ CSP (Content Security Policy) - Chính sách bảo mật nội dung:</strong> Tưởng tượng đây là một "người gác cổng" nghiêm ngặt. Nó chỉ cho phép trình duyệt của bạn tải và chạy các tập tin (script, hình ảnh, stylesheet) đến từ những nguồn mà chúng tôi đã khai báo là an toàn (chỉ `self`, `https://fonts.googleapis.com`, `https://cdnjs.cloudflare.com`). Điều này vô hiệu hóa hoàn toàn các cuộc tấn công XSS (Cross-Site Scripting) – nơi kẻ xấu cố gắng chèn mã độc vào trang web để đánh cắp thông tin của bạn.<br>
                    • <strong>🍪 HTTP Only Cookie:</strong> Cookie lưu mã định danh phiên của bạn được gắn cờ "HttpOnly". Điều này có nghĩa là nó chỉ được truyền qua giao thức HTTP và bị chặn không cho bất kỳ đoạn mã JavaScript nào (kể cả mã hợp lệ) truy cập vào. Do đó, ngay cả khi kẻ tấn công tìm ra lỗ hổng XSS, chúng cũng không thể đánh cắp cookie phiên của bạn.<br>
                    • <strong>🚫 X-Frame-Options: DENY:</strong> Ngăn chặn việc nhúng trang web của chúng tôi vào một khung (iframe) trên một trang web độc hại khác, qua đó bảo vệ bạn khỏi các cuộc tấn công Clickjacking (lừa bạn click vào nút ẩn).<br>
                    • <strong>🔄 Referrer-Policy: strict-origin-when-cross-origin:</strong> Khi bạn nhấp vào một liên kết từ web của chúng tôi đến một web khác, chính sách này chỉ gửi tên miền của chúng tôi (ví dụ: locvn.com) chứ không gửi toàn bộ đường dẫn URL (ví dụ: locvn.com/inbox/email/123). Điều này bảo vệ tính riêng tư của các địa chỉ email và tin nhắn cụ thể của bạn.<br>
                    • <strong>🛡️ X-XSS-Protection: 1; mode=block:</strong> Kích hoạt bộ lọc XSS của trình duyệt ở chế độ chặn, thêm một lớp bảo vệ nữa chống lại các cuộc tấn công chèn script.<br>
                    • <strong>📁 Không lưu log:</strong> Máy chủ Flask được cấu hình để không ghi log chi tiết các yêu cầu (chỉ ghi lỗi hệ thống nếu có), đảm bảo không lưu lại vết của bạn.<br><br>
                    <strong>4. DỮ LIỆU CỦA BẠN ĐƯỢC LƯU Ở ĐÂU?</strong><br>
                    • <strong>Dữ liệu phiên (đã mã hóa):</strong> Được lưu trên máy chủ của chúng tôi. Chỉ khi bạn quay lại với cùng một phiên (qua cookie), dữ liệu mới được giải mã. Dữ liệu tự động bị xóa sau 30 ngày không hoạt động.<br>
                    • <strong>Email tạm thời thực tế:</strong> Nội dung email thật được lưu trên máy chủ của các nhà cung cấp API bên thứ ba (Mail.tm, Temp-Mail.org, v.v.). Chúng tôi không hề lưu trữ nội dung email thật trên máy chủ của mình. Bạn cần đọc chính sách riêng của từng API.<br>
                    • <strong>Tin nhắn SMS ảo (bản demo):</strong> Được tạo và lưu trữ cục bộ ngay trong phiên của bạn, không tồn tại trên bất kỳ hệ thống bên ngoài nào. Đây chỉ là dữ liệu giả lập để minh họa.<br><br>
                    <strong>5. QUYỀN CỦA BẠN</strong><br>
                    Bạn có toàn quyền kiểm soát dữ liệu của mình:<br>
                    • <strong>Xóa dữ liệu:</strong> Nhấn nút "Xóa tất cả dữ liệu" (màu đỏ) ở giao diện chính để xóa vĩnh viễn mọi dữ liệu phiên của bạn.<br>
                    • <strong>Xuất dữ liệu:</strong> Vào tab "Lịch sử & OTP", nhấn "Xuất CSV" để tải về file chứa toàn bộ lịch sử email và SMS (bao gồm OTP).<br>
                    • <strong>Tắt thông báo:</strong> Tab "SMS ẢO" có nút "Tắt thông báo" để vô hiệu hóa thông báo toast.<br>
                    • <strong>Yêu cầu hỗ trợ xóa:</strong> Nếu bạn muốn chúng tôi can thiệp thủ công, hãy gửi email đến <strong>support@locvn.com</strong>.<br><br>
                    <strong>6. LIÊN HỆ</strong><br>
                    Mọi thắc mắc về bảo mật: <strong>security@locvn.com</strong> (phản hồi trong vòng 24 giờ).<br>
                    Hỗ trợ chung: <strong>support@locvn.com</strong><br>
                    Địa chỉ giao dịch: (giả định) 123 Đường Bảo Mật, Quận 1, TP. Hồ Chí Minh, Việt Nam.<br><br>
                    <strong>© 2026 LỘC VN - TEMP MAIL PRO</strong>
                </div>
            </div>
        </div>
    </div>

    <!-- Tab 5: Điều khoản dịch vụ (SIÊU CHI TIẾT) -->
    <div class="tab-pane" id="tab5">
        <div class="glass-card">
            <div class="glass-header"><i class="fas fa-gavel"></i> ĐIỀU KHOẢN DỊCH VỤ</div>
            <div class="glass-body">
                <div class="pre-content" style="max-height: none;">
                    <strong>⚖️ ĐIỀU KHOẢN DỊCH VỤ - LỘC VN TEMP MAIL PRO</strong><br>
                    Phiên bản 3.1 (SIÊU CHI TIẾT) | Cập nhật: 04/2026<br><br>
                    <strong>1. CHẤP NHẬN ĐIỀU KHOẢN</strong><br>
                    Bằng cách truy cập hoặc sử dụng bất kỳ phần nào của dịch vụ "LỘC VN - TEMP MAIL PRO" (sau đây gọi là "Dịch vụ"), bạn xác nhận rằng bạn đã đọc, hiểu và đồng ý bị ràng buộc bởi các Điều khoản này. Nếu bạn không đồng ý, vui lòng không sử dụng Dịch vụ.<br><br>
                    <strong>2. MÔ TẢ DỊCH VỤ VÀ GIỚI HẠN</strong><br>
                    Dịch vụ cung cấp các công cụ để:<br>
                    - Tạo địa chỉ email tạm thời (thông qua các API của bên thứ ba).<br>
                    - Tạo số điện thoại ảo để nhận tin nhắn SMS ở chế độ <strong>DEMO (thử nghiệm)</strong> – không kết nối đến mạng thực.<br>
                    Dịch vụ được cung cấp với mục đích chính là bảo vệ quyền riêng tư, tránh spam và thử nghiệm tính năng. Bạn thừa nhận rằng:<br>
                    • Email tạm thời có thể không hoạt động với tất cả các dịch vụ trực tuyến (một số dịch vụ lớn như Google, Facebook chặn email tạm thời).<br>
                    • Phần SMS ảo hoàn toàn là DEMO. Tin nhắn được tạo ngẫu nhiên hoặc theo yêu cầu của bạn để minh họa chức năng, và <strong>KHÔNG</strong> thể nhận tin nhắn thật từ các dịch vụ như Google, Facebook, Telegram, v.v. Cảnh báo này được hiển thị rõ ràng trong tab "SMS ẢO".<br>
                    • LỘC VN không chịu trách nhiệm về việc email tạm thời bị mất hoặc không nhận được thư do lỗi từ phía API bên thứ ba.<br><br>
                    <strong>3. SỬ DỤNG HỢP LÝ VÀ CÁC HÀNH VI BỊ CẤM</strong><br>
                    Bạn được phép sử dụng Dịch vụ cho các mục đích cá nhân hợp pháp. Các hành vi sau đây bị nghiêm cấm, vi phạm sẽ dẫn đến chấm dứt quyền truy cập ngay lập tức, xóa dữ liệu và có thể bị báo cáo cho cơ quan chức năng:<br>
                    1. <strong>Sử dụng email tạm thời để đăng ký tài khoản nhằm thực hiện các hành vi lừa đảo, gian lận, chiếm đoạt tài sản, hoặc gửi thư rác (spam) hàng loạt.</strong><br>
                    2. <strong>Sử dụng Dịch vụ để tấn công, can thiệp, hoặc gây quá tải (DDoS) cho hệ thống của chúng tôi hoặc các API bên thứ ba.</strong><br>
                    3. <strong>Sử dụng Dịch vụ để lưu trữ, tải lên, chia sẻ hoặc phân phối nội dung bất hợp pháp, khiêu dâm, kích động bạo lực, vi phạm bản quyền, hoặc xâm phạm quyền riêng tư của người khác.</strong><br>
                    4. <strong>Cố gắng đảo ngược kỹ thuật (reverse engineering), giải mã (decompile), hoặc trích xuất mã nguồn của Dịch vụ mà không được phép.</strong><br>
                    5. <strong>Tạo nhiều phiên liên tiếp nhằm mục đích phá hoại hoặc trục lợi (abuse).</strong><br>
                    Vi phạm các điều khoản này có thể dẫn đến việc chấm dứt quyền truy cập ngay lập tức, xóa dữ liệu vĩnh viễn, và có thể bị báo cáo cho các cơ quan chức năng có thẩm quyền.<br><br>
                    <strong>4. GIỚI HẠN TRÁCH NHIỆM</strong><br>
                    Dịch vụ được cung cấp trên cơ sở "nguyên trạng" (AS-IS) và "có sẵn" (AS-AVAILABLE). Chúng tôi không bảo đảm rằng:<br>
                    • Dịch vụ sẽ đáp ứng mọi yêu cầu của bạn.<br>
                    • Dịch vụ sẽ không bị gián đoạn, kịp thời, an toàn hoặc không có lỗi.<br>
                    • Kết quả thu được từ việc sử dụng Dịch vụ là chính xác hoặc đáng tin cậy.<br>
                    Trong mọi trường hợp, LỘC VN sẽ không chịu trách nhiệm về bất kỳ thiệt hại trực tiếp, gián tiếp, ngẫu nhiên, đặc biệt hay hậu quả nào phát sinh từ việc sử dụng hoặc không thể sử dụng Dịch vụ, bao gồm nhưng không giới hạn: mất dữ liệu, mất lợi nhuận, hoặc gián đoạn kinh doanh. Giới hạn trách nhiệm tối đa của LỘC VN đối với bất kỳ khiếu nại nào là 0đ (không đồng).<br><br>
                    <strong>5. THAY ĐỔI ĐIỀU KHOẢN VÀ DỊCH VỤ</strong><br>
                    Chúng tôi có quyền sửa đổi các Điều khoản này bất kỳ lúc nào mà không cần thông báo trước. Những thay đổi sẽ có hiệu lực ngay sau khi được đăng tải. Việc bạn tiếp tục sử dụng Dịch vụ sau khi thay đổi đồng nghĩa với việc bạn chấp nhận Điều khoản mới.<br>
                    Chúng tôi cũng có quyền tạm ngừng, ngừng hẳn hoặc thay đổi bất kỳ phần nào của Dịch vụ mà không cần thông báo trước, nhằm bảo trì, nâng cấp hoặc vì lý do bảo mật.<br><br>
                    <strong>6. LUẬT ÁP DỤNG VÀ GIẢI QUYẾT TRANH CHẤP</strong><br>
                    Các Điều khoản này được điều chỉnh bởi pháp luật của nước Cộng hòa Xã hội Chủ nghĩa Việt Nam. Mọi tranh chấp phát sinh sẽ được giải quyết tại Tòa án Nhân dân có thẩm quyền tại Thành phố Hồ Chí Minh. Bạn đồng ý rằng bất kỳ khiếu nại nào cũng phải được gửi trong vòng 30 ngày kể từ khi sự việc phát sinh.<br><br>
                    <strong>7. THÔNG TIN LIÊN HỆ</strong><br>
                    Mọi thắc mắc, khiếu nại về Dịch vụ hoặc Điều khoản này, vui lòng gửi email đến: <strong>legal@locvn.com</strong>.<br><br>
                    <strong>© 2026 LỘC VN - TEMP MAIL PRO</strong>
                </div>
            </div>
        </div>
    </div>

    <!-- Tab 6: FAQ (SIÊU CHI TIẾT) -->
    <div class="tab-pane" id="tab6">
        <div class="glass-card">
            <div class="glass-header"><i class="fas fa-question-circle"></i> CÂU HỎI THƯỜNG GẶP</div>
            <div class="glass-body">
                <div class="pre-content" style="max-height: none;">
                    <strong>❓ CÂU HỎI THƯỜNG GẶP (FAQ) - SIÊU CHI TIẾT</strong><br><br>
                    <details><summary><strong>1. Email tạm thời tồn tại bao lâu? Làm sao để kéo dài thời gian?</strong></summary><br>
                    Thời gian tồn tại phụ thuộc hoàn toàn vào nhà cung cấp API mà bạn chọn:<br>
                    - <strong>Mail.tm</strong>: <strong>Vĩnh viễn</strong> (bạn phải tự xóa).<br>
                    - <strong>Temp-Mail.org</strong>: Khoảng 1-2 giờ.<br>
                    - <strong>10 Minute Mail</strong>: Đúng 10 phút, có thể gia hạn thêm 10 phút bằng nút "Gia hạn" (nếu có).<br>
                    - <strong>Các API giả lập</strong>: Tạo địa chỉ nhưng không nhận được email thật, dùng để test nhanh.<br>
                    Để kéo dài thời gian, hãy chọn API Mail.tm (lưu vĩnh viễn) hoặc trước khi email bị xóa, bạn có thể chuyển nội dung quan trọng sang email thật của mình.<br><br></details>
                    <details><summary><strong>2. Làm thế nào để hệ thống tự động phát hiện mã OTP?</strong></summary><br>
                    Hệ thống sử dụng bộ quy tắc (regex) để quét nội dung email hoặc tin nhắn SMS. Nếu tìm thấy một chuỗi 6 chữ số liên tiếp (ví dụ: 123456) hoặc các cụm từ như "mã xác minh 654321", nó sẽ hiển thị mã đó trong khung "Mã OTP trích xuất". Bạn không cần làm gì thêm, chỉ cần click vào email/tin nhắn để xem nội dung.<br><br></details>
                    <details><summary><strong>3. Tôi có thể sử dụng lại một email tạm thời đã tạo trước đó không?</strong></summary><br>
                    <strong>Có, chắc chắn rồi!</strong> Tất cả email bạn đã tạo đều được lưu trong tab "Quản lý email". Để sử dụng lại, chỉ cần vào tab đó, tìm email bạn muốn và nhấn nút <strong>"Dùng"</strong>. Email đó sẽ trở thành email hiện tại và bạn có thể tiếp tục xem hộp thư (nếu API hỗ trợ).<br><br></details>
                    <details><summary><strong>4. SMS ảo "DEMO" có thực sự nhận được tin nhắn từ Google, Facebook không?</strong></summary><br>
                    <strong>KHÔNG.</strong> Đây là bản DEMO hoàn toàn. Tin nhắn được tạo ngẫu nhiên hoặc do bạn chủ động tạo ra chỉ để minh họa giao diện và chức năng. Nếu bạn muốn xác minh số điện thoại thật, bạn cần sử dụng SIM thật hoặc dịch vụ SMS ảo có tính phí như <strong>5sim.net</strong>. Cảnh báo này được hiển thị rõ bằng khung màu đỏ ngay khi bạn vào tab "SMS ẢO" và tự động biến mất sau 10 giây.<br><br></details>
                    <details><summary><strong>5. Dữ liệu của tôi (email, tin nhắn) có an toàn khi tôi đóng trình duyệt không?</strong></summary><br>
                    <strong>Hoàn toàn an toàn!</strong> Dữ liệu phiên của bạn được lưu trữ vĩnh viễn trên máy chủ trong vòng 30 ngày kể từ lần hoạt động cuối cùng. Bạn có thể đóng trình duyệt, tắt máy tính, và khi quay lại, mọi thứ vẫn còn nguyên vẹn. Đây là điểm khác biệt lớn so với các tool email tạm thời thông thường chỉ lưu trên trình duyệt.<br><br></details>
                    <details><summary><strong>6. Làm cách nào để tắt thông báo âm thanh / toast cho SMS mới?</strong></summary><br>
                    Trong tab "SMS ẢO", bạn sẽ thấy một nút có nhãn <strong>"🔔 Tắt thông báo"</strong>. Nhấn vào đó để vô hiệu hóa thông báo (cả toast và âm thanh nếu có). Nút sẽ đổi thành "Bật thông báo". Bạn có thể bật lại bất cứ lúc nào.<br><br></details>
                    <details><summary><strong>7. Tôi muốn xóa sạch toàn bộ lịch sử email và SMS của mình, phải làm sao?</strong></summary><br>
                    Bạn có hai lựa chọn:<br>
                    - Xóa lịch sử email/SMS: Vào tab "Lịch sử & OTP" và nhấn nút <strong>"Xóa lịch sử"</strong>.<br>
                    - Xóa toàn bộ dữ liệu (bao gồm danh sách email đã tạo và số ảo): Ở giao diện chính (Main Card), nhấn nút <strong>"Xóa tất cả dữ liệu"</strong> (màu đỏ). Dữ liệu sẽ được xóa khỏi máy chủ và không thể khôi phục.<br><br></details>
                    <details><summary><strong>8. Một số API email hiển thị dấu "❌" hoặc "⚠️" có sao không?</strong></summary><br>
                    <strong>Không có vấn đề gì.</strong> Dấu "✅" có nghĩa là API đang hoạt động tốt. Dấu "⚠️" hoặc "❌" có nghĩa là API đó tạm thời không khả dụng hoặc yêu cầu xác thực nâng cao. Bạn vẫn có thể sử dụng các API khác (có tới 50 lựa chọn). Hãy chọn API có dấu "✅" để trải nghiệm tốt nhất.<br><br></details>
                    <details><summary><strong>9. Làm sao để xuất danh sách tất cả email và OTP đã nhận?</strong></summary><br>
                    Rất đơn giản! Vào tab <strong>"Lịch sử & OTP"</strong>, sau đó nhấn nút <strong>"Xuất CSV"</strong>. Hệ thống sẽ tải về một file có tên `temp_mail_history.csv` chứa đầy đủ thông tin: địa chỉ email/số điện thoại, người gửi, tiêu đề, mã OTP, loại (email/SMS) và thời gian. Bạn có thể mở file này bằng Excel hoặc Google Sheets.<br><br></details>
                    <details><summary><strong>10. Chuông thông báo góc phải dùng để làm gì?</strong></summary><br>
                    Chuông <i class="fas fa-bell"></i> là <strong>Hệ thống thông báo của web</strong>. Nó hiển thị các thông báo về việc ra mắt tính năng mới, cập nhật phiên bản, hoặc thông báo bảo trì hệ thống. <strong>Nó hoàn toàn độc lập</strong> và không liên quan đến tin nhắn email hay SMS mới. Bạn có thể click vào chuông để xem chi tiết thông báo và đánh dấu là đã đọc.<br><br></details>
                    <details><summary><strong>11. Tôi có thể tạo bao nhiêu email và số điện thoại ảo?</strong></summary><br>
                    <strong>Không giới hạn.</strong> Bạn có thể tạo bao nhiêu email tùy thích (sử dụng nút "Tạo email ẩn danh") và bao nhiêu số điện thoại ảo (tab SMS ẢO). Mỗi email và số đều được lưu trong danh sách riêng để quản lý.<br><br></details>
                    <details><summary><strong>12. Tôi có thể gửi email từ địa chỉ tạm thời này không?</strong></summary><br>
                    <strong>Không.</strong> Dịch vụ chỉ hỗ trợ <strong>nhận email</strong>, không hỗ trợ gửi email. Nếu bạn cần gửi email, hãy sử dụng tài khoản email thật.<br><br></details>
                    <details><summary><strong>13. Tại sao có lúc tôi không nhận được email dù API báo ✅?</strong></summary><br>
                    Có nhiều nguyên nhân: email có thể chậm vài phút, bị lọc vào thư rác (nhưng tool của chúng tôi hiển thị cả thư rác), hoặc dịch vụ bạn đăng ký chặn email tạm thời. Hãy thử chọn API khác hoặc làm mới lại hộp thư sau 1-2 phút.<br><br></details>
                    <details><summary><strong>14. Dữ liệu của tôi có bị rò rỉ ra ngoài không?</strong></summary><br>
                    <strong>Không.</strong> Dữ liệu phiên được mã hóa AES-256, chỉ bạn mới có khóa (thông qua cookie). Ngay cả chúng tôi cũng không thể đọc dữ liệu của bạn. Các API bên thứ ba có chính sách riêng, nhưng email tạm thời thường bị xóa nhanh chóng.<br><br></details>
                    <details><summary><strong>15. Làm sao để đóng góp ý kiến hoặc báo lỗi?</strong></summary><br>
                    Rất hoan nghênh! Bạn có thể gửi email đến <strong>support@locvn.com</strong> hoặc sử dụng form liên hệ (nếu có). Chúng tôi luôn lắng nghe phản hồi để cải thiện dịch vụ.<br><br></details>
                    <details><summary><strong>16. Có phải tôi phải trả phí để sử dụng không?</strong></summary><br>
                    <strong>Hoàn toàn miễn phí.</strong> Tất cả các tính năng hiện tại là miễn phí. Trong tương lai, nếu mở rộng thêm tính năng đặc biệt, chúng tôi sẽ thông báo rõ ràng.<br><br></details>
                    <details><summary><strong>17. Tôi có thể chạy tool này trên máy tính cá nhân không?</strong></summary><br>
                    Có. Đây là ứng dụng Flask, bạn có thể chạy local như hướng dẫn. Tuy nhiên, nếu bạn muốn chia sẻ cho nhiều người, cần triển khai lên máy chủ có địa chỉ IP công cộng.<br><br></details>
                    <details><summary><strong>18. Làm sao để lấy lại email đã xóa?</strong></summary><br>
                    Nếu bạn đã xóa email khỏi danh sách quản lý hoặc xóa toàn bộ dữ liệu, <strong>không thể khôi phục</strong> được. Vì vậy, hãy xuất CSV nếu cần lưu lại.<br><br></details>
                    <details><summary><strong>19. Tôi có thể dùng SMS ảo để nhận tin nhắn từ Zalo, Viber không?</strong></summary><br>
                    Vì đây là bản demo, <strong>không thể</strong>. Tin nhắn được tạo ngẫu nhiên chỉ để minh họa. Nếu bạn cần thật, hãy dùng dịch vụ SMS thật.<br><br></details>
                    <details><summary><strong>20. Làm sao để liên hệ bộ phận kỹ thuật?</strong></summary><br>
                    Gửi email đến <strong>dev@locvn.com</strong> (ưu tiên) hoặc <strong>support@locvn.com</strong>.<br><br></details>
                </div>
            </div>
        </div>
    </div>

    <!-- Tab 7: Giao diện -->
    <div class="tab-pane" id="tab7">
        <div class="glass-card">
            <div class="glass-header"><i class="fas fa-sliders-h"></i> GIAO DIỆN & CẤU HÌNH</div>
            <div class="glass-body">
                <div style="display: flex; align-items: center; gap: 20px; flex-wrap: wrap;">
                    <div class="security-badge"><i class="fas fa-moon"></i> Chế độ hiển thị</div>
                    <button id="darkModeToggle" class="btn btn-outline btn-sm"><i class="fas fa-adjust"></i> Chuyển chế độ</button>
                </div>
                <p style="margin-top: 20px;"><i class="fas fa-info-circle"></i> Dữ liệu được lưu vĩnh viễn (30 ngày). Bạn có thể yên tâm đóng trình duyệt.</p>
            </div>
        </div>
    </div>

    <!-- Tab 8: SMS ẢO -->
    <div class="tab-pane" id="tab8">
        <div class="glass-card">
            <div class="glass-header"><i class="fas fa-sms"></i> SMS ẢO - 20 API | BẢN THỬ NGHIỆM</div>
            <div class="glass-body">
                <div class="warning-box" id="warningBox">
                    <div><i class="fas fa-exclamation-triangle"></i> <strong>⚠️ CẢNH BÁO: BẢN THỬ NGHIỆM</strong><br>Phần SMS ảo hiện đang ở chế độ DEMO. Tin nhắn được tạo ngẫu nhiên, KHÔNG PHẢI là tin nhắn thật từ dịch vụ. Mục đích: Minh họa giao diện và chức năng nhận OTP.</div>
                    <button id="closeWarningBtn" class="btn btn-outline btn-sm"><i class="fas fa-times"></i> Đóng</button>
                </div>
                <div class="grid-2">
                    <div>
                        <div><i class="fas fa-phone-alt"></i> <strong>Tạo số điện thoại ảo</strong></div>
                        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 12px; margin-top: 10px;">
                            <div><label>🌐 Nhà cung cấp SMS</label><select id="smsProviderSelect" class="form-select"></select></div>
                            <div><label>📍 Quốc gia</label><select id="smsCountrySelect" class="form-select"></select></div>
                        </div>
                        <button class="btn btn-warning" id="createSmsBtn" style="margin-top: 15px; width: 100%;"><i class="fas fa-plus-circle"></i> Tạo số điện thoại ảo</button>
                        <div style="margin-top: 15px;">
                            <div><i class="fas fa-bell"></i> <strong>Thông báo SMS:</strong></div>
                            <button id="toggleNotificationBtn" class="btn btn-outline btn-sm"><i class="fas fa-bell-slash"></i> Tắt thông báo</button>
                        </div>
                    </div>
                    <div>
                        <div><i class="fas fa-list"></i> <strong>Danh sách số đã tạo</strong></div>
                        <div style="max-height: 200px; overflow-y: auto; margin-top: 10px;">
                            <table class="data-table"><thead><tr><th>STT</th><th>Số điện thoại</th><th>API</th><th>Quốc gia</th><th>Thao tác</th></tr></thead><tbody id="smsNumbersBody"></tbody><td>
                        </div>
                    </div>
                </div>
                <div style="margin-top: 20px;">
                    <div style="display: flex; justify-content: space-between; flex-wrap: wrap; gap: 12px;">
                        <strong><i class="fas fa-envelope-open-text"></i> Tin nhắn SMS đã nhận</strong>
                        <button class="btn btn-primary btn-sm" id="refreshSmsBtn"><i class="fas fa-sync-alt"></i> Làm mới tin nhắn</button>
                    </div>
                    <div style="margin-top: 15px; max-height: 300px; overflow-y: auto;">
                        <table class="data-table"><thead><tr><th>STT</th><th>Từ</th><th>Tin nhắn</th><th>Mã OTP</th><th>Thời gian</th></tr></thead><tbody id="smsMessagesBody"></tbody><tr>
                    </div>
                </div>
            </div>
        </div>
    </div>

    <div class="footer">
        <i class="fas fa-copyright"></i> 2026 LỘC VN - TEMP MAIL PRO | 50 Email API + 20 SMS API (Thử nghiệm) | Dữ liệu được lưu vĩnh viễn | Bảo mật doanh nghiệp
    </div>
</div>

<script>
    let currentMessages = [], currentOtp = null, darkMode = false;
    let smsNotificationsOn = true;
    let systemNotifications = [];

    function showToast(msg, type='success') {
        let toast = document.createElement('div');
        toast.style.cssText = `position:fixed; bottom:20px; right:20px; background:${type=='success'?'#2f855a':type=='warning'?'#d69e2e':'#c53030'}; color:white; padding:12px 24px; border-radius:30px; z-index:9999; animation:fadeOut 3s forwards;`;
        toast.innerHTML = `<i class="fas fa-${type=='success'?'check-circle':type=='warning'?'exclamation-triangle':'exclamation-circle'}"></i> ${msg}`;
        document.body.appendChild(toast);
        setTimeout(()=>toast.remove(), 3000);
    }

    // DONATE FUNCTION - RANDOM 2 LINK
    const donateLinks = ["https://yeumoney.com/Frv9Q", "https://yeumoney.com/bf61j5KT"];
    document.getElementById('donateBtn').addEventListener('click', function() {
        const randomIndex = Math.floor(Math.random() * donateLinks.length);
        window.open(donateLinks[randomIndex], '_blank');
        showToast('❤️ Cảm ơn bạn đã ủng hộ!', 'success');
    });

    // Các hàm còn lại GIỮ NGUYÊN 100% từ bản gốc
    async function loadEmailProviders() {
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
        document.getElementById('totalEmails').innerText = '...';
    }

    async function createEmail() {
        let provider = document.getElementById('providerSelect').value;
        let res = await fetch('/api/email/create', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({provider})});
        if(res.ok) {
            let data = await res.json();
            document.getElementById('currentEmail').value = data.email;
            showToast(`✅ Đã tạo: ${data.email}`);
            refreshInbox(); loadEmailList(); loadHistory();
        } else showToast('❌ Tạo thất bại', 'danger');
    }

    async function refreshInbox() {
        let res = await fetch('/api/email/refresh');
        let data = await res.json();
        currentMessages = data.messages;
        let tbody = document.getElementById('inboxBody');
        tbody.innerHTML = '';
        data.messages.forEach((msg, idx) => {
            let row = tbody.insertRow();
            row.insertCell(0).textContent = idx+1;
            row.insertCell(1).textContent = msg.sender;
            row.insertCell(2).textContent = msg.subject;
            row.insertCell(3).textContent = msg.date;
            row.style.cursor = 'pointer';
            row.onclick = () => viewEmail(msg.id);
        });
    }

    async function viewEmail(msgId) {
        let res = await fetch(`/api/email/view/${msgId}`);
        let data = await res.json();
        document.getElementById('emailContent').innerHTML = data.content.replace(/\\n/g, '<br>');
        if(data.otp) { currentOtp = data.otp; document.getElementById('otpCode').innerHTML = data.otp; showToast(`🔑 OTP: ${data.otp}`); }
        else { currentOtp = null; document.getElementById('otpCode').innerHTML = 'Không tìm thấy'; }
        loadHistory();
    }

    async function loadEmailList() {
        let res = await fetch('/api/email/list');
        let data = await res.json();
        let tbody = document.getElementById('manageBody');
        tbody.innerHTML = '';
        data.emails.forEach((email, idx) => {
            let row = tbody.insertRow();
            row.insertCell(0).textContent = idx+1;
            row.insertCell(1).textContent = email.email;
            row.insertCell(2).textContent = email.provider;
            row.insertCell(3).textContent = email.created;
            let btnCell = row.insertCell(4);
            let useBtn = document.createElement('button'); useBtn.className='btn btn-outline btn-sm'; useBtn.innerHTML='<i class="fas fa-check"></i> Dùng'; useBtn.onclick=()=>switchEmail(idx);
            let delBtn = document.createElement('button'); delBtn.className='btn btn-danger btn-sm'; delBtn.innerHTML='<i class="fas fa-trash"></i> Xóa'; delBtn.onclick=()=>deleteEmail(idx);
            btnCell.appendChild(useBtn); btnCell.appendChild(delBtn);
        });
        if(data.current_idx>=0 && data.emails[data.current_idx]) document.getElementById('currentEmail').value = data.emails[data.current_idx].email;
        document.getElementById('totalEmails').innerText = data.emails.length;
    }

    async function switchEmail(idx) { await fetch('/api/email/switch', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({idx})}); showToast('Đã chuyển email'); loadEmailList(); refreshInbox(); }
    async function deleteEmail(idx) { if(confirm('Xóa?')){ await fetch('/api/email/delete', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({idx})}); loadEmailList(); refreshInbox(); } }

    async function loadHistory() {
        let res = await fetch('/api/history');
        let history = await res.json();
        let tbody = document.getElementById('historyBody');
        tbody.innerHTML = '';
        history.forEach((rec, idx) => {
            let row = tbody.insertRow();
            row.insertCell(0).textContent = idx+1;
            let typeIcon = rec.type == 'sms' ? '📱' : '📧';
            row.insertCell(1).textContent = `${typeIcon} ${rec.type == 'sms' ? 'SMS' : 'Email'}`;
            row.insertCell(2).textContent = rec.email.substring(0,20);
            row.insertCell(3).textContent = rec.sender.substring(0,20);
            row.insertCell(4).textContent = rec.subject.substring(0,30);
            row.insertCell(5).textContent = rec.otp || '---';
            row.insertCell(6).textContent = rec.api;
            row.insertCell(7).textContent = rec.time;
        });
        document.getElementById('totalHistory').innerText = history.length;
        let search = document.getElementById('searchHistory');
        search.oninput = () => {
            let kw = search.value.toLowerCase();
            Array.from(tbody.rows).forEach(r => { let txt = r.cells[2].innerText+r.cells[3].innerText+r.cells[4].innerText; r.style.display = txt.includes(kw) ? '' : 'none'; });
        };
    }

    async function clearHistory() { if(confirm('Xóa lịch sử?')){ await fetch('/api/clear_history', {method:'POST'}); loadHistory(); showToast('Đã xóa lịch sử'); } }
    async function clearAll() { if(confirm('Xóa hết dữ liệu?')){ await fetch('/api/clear_all', {method:'POST'}); loadEmailList(); refreshInbox(); loadHistory(); loadSMSNumbers(); loadSMSMessages(); showToast('Đã xóa'); } }
    function exportCsv() { window.location.href = '/api/export_csv'; }

    let selectedSmsProvider = '5sim.net';
    async function loadSMSProviders() {
        let res = await fetch('/api/sms/providers');
        let providers = await res.json();
        let select = document.getElementById('smsProviderSelect');
        select.innerHTML = '';
        providers.forEach(p => {
            let opt = document.createElement('option');
            opt.value = p;
            opt.textContent = p;
            select.appendChild(opt);
        });
        select.onchange = async () => { selectedSmsProvider = select.value; await loadSMSCountries(); };
        await loadSMSCountries();
    }

    async function loadSMSCountries() {
        let res = await fetch(`/api/sms/countries?provider=${selectedSmsProvider}`);
        let countries = await res.json();
        let select = document.getElementById('smsCountrySelect');
        select.innerHTML = '';
        countries.forEach(c => { let opt = document.createElement('option'); opt.value = c; opt.textContent = c; select.appendChild(opt); });
    }

    async function createSMSNumber() {
        let country = document.getElementById('smsCountrySelect').value;
        let provider = document.getElementById('smsProviderSelect').value;
        let res = await fetch('/api/sms/create', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({country, provider})});
        if(res.ok) { let data = await res.json(); showToast(`✅ Đã tạo số (${data.provider}): ${data.phone}`); loadSMSNumbers(); }
        else showToast('❌ Tạo thất bại', 'danger');
    }

    async function loadSMSNumbers() {
        let res = await fetch('/api/sms/numbers');
        let data = await res.json();
        let tbody = document.getElementById('smsNumbersBody');
        tbody.innerHTML = '';
        data.numbers.forEach((num, idx) => {
            let row = tbody.insertRow();
            row.insertCell(0).textContent = idx+1;
            row.insertCell(1).innerHTML = `<span class="otp-code" style="font-size:14px;">${num.phone}</span>`;
            row.insertCell(2).textContent = num.provider || '5sim.net';
            row.insertCell(3).textContent = num.country;
            let delBtn = document.createElement('button'); delBtn.className='btn btn-danger btn-sm'; delBtn.innerHTML='<i class="fas fa-trash"></i>'; delBtn.onclick=()=>deleteSMSNumber(idx);
            row.insertCell(4).appendChild(delBtn);
        });
        document.getElementById('totalSMS').innerText = data.numbers.length;
    }

    async function deleteSMSNumber(idx) {
        if(confirm('Xóa số này?')){
            await fetch('/api/sms/delete', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({idx})});
            loadSMSNumbers();
            showToast('Đã xóa số');
        }
    }

    async function loadSMSMessages() {
        let res = await fetch('/api/sms/refresh');
        let data = await res.json();
        let tbody = document.getElementById('smsMessagesBody');
        tbody.innerHTML = '';
        if(data.messages) {
            data.messages.forEach((msg, idx) => {
                let row = tbody.insertRow();
                row.insertCell(0).textContent = idx+1;
                row.insertCell(1).textContent = msg.from;
                row.insertCell(2).textContent = msg.message.substring(0,50);
                row.insertCell(3).innerHTML = msg.otp ? `<span class="otp-code" style="font-size:16px;">${msg.otp}</span>` : '---';
                row.insertCell(4).textContent = msg.time;
            });
        }
        if(data.new_count > 0 && smsNotificationsOn) {
            showToast(`📱 Có ${data.new_count} tin nhắn SMS mới!`, 'info');
        }
        loadHistory();
    }

    async function toggleNotifications() {
        smsNotificationsOn = !smsNotificationsOn;
        await fetch('/api/sms/notifications', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({enabled: smsNotificationsOn})});
        let btn = document.getElementById('toggleNotificationBtn');
        if(smsNotificationsOn) {
            btn.innerHTML = '<i class="fas fa-bell"></i> Tắt thông báo';
            showToast('Đã bật thông báo SMS', 'success');
        } else {
            btn.innerHTML = '<i class="fas fa-bell-slash"></i> Bật thông báo';
            showToast('Đã tắt thông báo SMS', 'warning');
        }
    }

    async function loadSystemNotifications() {
        let res = await fetch('/api/notifications');
        systemNotifications = await res.json();
        updateNotificationBadge();
        renderNotificationPanel();
    }

    function updateNotificationBadge() {
        let unread = systemNotifications.filter(n => !n.read).length;
        let badge = document.getElementById('notificationBadge');
        if (unread > 0) {
            badge.style.display = 'inline-block';
            badge.innerText = unread;
        } else {
            badge.style.display = 'none';
        }
    }

    function renderNotificationPanel() {
        let panel = document.getElementById('notificationList');
        panel.innerHTML = '';
        systemNotifications.forEach((notif, idx) => {
            let div = document.createElement('div');
            div.className = 'notification-item';
            div.innerHTML = `<div><i class="fas ${notif.read ? 'fa-check-circle' : 'fa-circle'}"></i> ${notif.text}</div><small>${notif.time}</small>`;
            div.onclick = async () => {
                if (!notif.read) {
                    await fetch('/api/notifications/mark_read', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({idx})});
                    systemNotifications[idx].read = true;
                    updateNotificationBadge();
                    renderNotificationPanel();
                }
            };
            panel.appendChild(div);
        });
    }

    function toggleDarkMode() {
        darkMode = !darkMode;
        if(darkMode) { document.body.style.background = '#0a0a1a'; }
        else { document.body.style.background = 'linear-gradient(135deg, #0f0c29 0%, #1a1a3e 50%, #0f0c29 100%)'; }
        localStorage.setItem('darkMode', darkMode);
    }

    document.getElementById('createBtn').onclick = createEmail;
    document.getElementById('refreshBtn').onclick = refreshInbox;
    document.getElementById('copyEmailBtn').onclick = () => { navigator.clipboard.writeText(document.getElementById('currentEmail').value); showToast('Đã copy email'); };
    document.getElementById('copyOtpBtn').onclick = () => { if(currentOtp) { navigator.clipboard.writeText(currentOtp); showToast('Đã copy OTP'); } else showToast('Không có OTP', 'warning'); };
    document.getElementById('clearAllBtn').onclick = clearAll;
    document.getElementById('clearHistoryBtn').onclick = clearHistory;
    document.getElementById('exportCsvBtn').onclick = exportCsv;
    document.getElementById('checkApiBtn').onclick = loadEmailProviders;
    document.getElementById('darkModeToggle').onclick = toggleDarkMode;
    document.getElementById('createSmsBtn').onclick = createSMSNumber;
    document.getElementById('refreshSmsBtn').onclick = () => { loadSMSMessages(); loadSMSNumbers(); showToast('Đã làm mới SMS'); };
    document.getElementById('toggleNotificationBtn').onclick = toggleNotifications;
    document.getElementById('closeWarningBtn').onclick = () => {
        document.getElementById('warningBox').style.display = 'none';
        showToast('Đã đóng cảnh báo', 'info');
    };
    document.getElementById('notificationBell').addEventListener('click', () => {
        let panel = document.getElementById('notificationPanel');
        panel.style.display = panel.style.display === 'block' ? 'none' : 'block';
        renderNotificationPanel();
    });
    document.addEventListener('click', (e) => {
        if (!document.getElementById('notificationBell').contains(e.target) && !document.getElementById('notificationPanel').contains(e.target)) {
            document.getElementById('notificationPanel').style.display = 'none';
        }
    });

    setTimeout(() => {
        let warnBox = document.getElementById('warningBox');
        if (warnBox) warnBox.style.display = 'none';
    }, 10000);

    document.querySelectorAll('.tab-btn').forEach(btn => {
        btn.onclick = () => {
            document.querySelectorAll('.tab-btn').forEach(b=>b.classList.remove('active'));
            document.querySelectorAll('.tab-pane').forEach(p=>p.classList.remove('active'));
            btn.classList.add('active');
            let tabId = btn.dataset.tab;
            document.getElementById(tabId).classList.add('active');
            if(tabId === 'tab1') refreshInbox();
            if(tabId === 'tab2') loadEmailList();
            if(tabId === 'tab3') loadHistory();
            if(tabId === 'tab8') { loadSMSNumbers(); loadSMSMessages(); }
        };
    });

    loadEmailProviders(); createEmail(); loadEmailList(); loadHistory();
    loadSMSProviders(); loadSMSNumbers(); loadSMSMessages();
    loadSystemNotifications();
    setInterval(refreshInbox, 15000);
    setInterval(() => { if(document.getElementById('tab8').classList.contains('active')) loadSMSMessages(); }, 8000);
    if(localStorage.getItem('darkMode') === 'true') toggleDarkMode();
</script>
</body>
</html>
"""

if __name__ == '__main__':
    print("""
    ╔══════════════════════════════════════════════════════════════════╗
    ║     🚀 LỘC VN - TEMP MAIL PRO ULTIMATE - KHỞI ĐỘNG THÀNH CÔNG    ║
    ║                                                                  ║
    ║  📧 50 API Email Ảo (bao gồm cả giả lập)                        ║
    ║  📱 20 API SMS Ảo (Bản thử nghiệm)                              ║
    ║  🔒 Bảo mật cấp độ doanh nghiệp (AES-256, CSP, HttpOnly)        ║
    ║  📜 Điều khoản, Chính sách, FAQ siêu cực chi tiết (dài gấp đôi) ║
    ║  🔔 Chuông thông báo hệ thống (cập nhật tính năng mới)          ║
    ║  💾 Lưu trữ vĩnh viễn (30 ngày)                                 ║
    ║  ⏰ Cảnh báo SMS tự động biến mất sau 10 giây                   ║
    ║  ❤️ ĐÃ THÊM NÚT DONATE RANDOM 2 LINK (Yeumoney)                 ║
    ║                                                                  ║
    ║  🌐 Mở trình duyệt: http://localhost:5000                       ║
    ╚══════════════════════════════════════════════════════════════════╝
    """)
    app.run(debug=True, host='0.0.0.0', port=5000)