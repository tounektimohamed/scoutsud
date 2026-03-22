from flask import Flask, render_template, request, jsonify, make_response
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.lib.colors import HexColor
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from PIL import Image as PILImage
import arabic_reshaper
from bidi.algorithm import get_display
import io
import base64
import requests
import os

FIREBASE_CONFIG = {
    "apiKey": "AIzaSyAVacEYZNH0jIimwurEE0g4mTRUz1RvkT0",
    "projectId": "waste-sorting-ai-36421",
    "authDomain": "waste-sorting-ai-36421.firebaseapp.com",
    "storageBucket": "waste-sorting-ai-36421.firebasestorage.app"
}

FIREBASE_URL = f"https://firestore.googleapis.com/v1/projects/{FIREBASE_CONFIG['projectId']}/databases/(default)/documents"

pdfmetrics.registerFont(TTFont('Arabic', 'fonts/NotoNaskhArabic-Regular.ttf'))
pdfmetrics.registerFont(TTFont('ArabicBold', 'fonts/NotoNaskhArabic-Bold.ttf'))

def reshape_arabic(text):
    if not text:
        return ""
    reshaped = arabic_reshaper.reshape(text)
    return get_display(reshaped)

app = Flask(__name__)

def get_badges():
    try:
        resp = requests.get(f"{FIREBASE_URL}/badges")
        if resp.status_code != 200:
            print(f"Firestore error: {resp.status_code} - {resp.text}")
            return []
        data = resp.json()
        docs = data.get('documents', [])
        badges = []
        for doc in docs:
            fields = doc.get('fields', {})
            badges.append({
                'id': doc['name'].split('/')[-1],
                'firstName': fields.get('firstName', {}).get('stringValue', ''),
                'lastName': fields.get('lastName', {}).get('stringValue', ''),
                'mission': fields.get('mission', {}).get('stringValue', ''),
                'photoUrl': fields.get('photoUrl', {}).get('stringValue', ''),
                'bgImage': fields.get('bgImage', {}).get('stringValue', ''),
                'backgroundColor': fields.get('backgroundColor', {}).get('stringValue', 'linear-gradient(135deg,#2d4a1e,#556b2f)'),
                'createdAt': fields.get('createdAt', {}).get('integerValue', 0)
            })
        return list(reversed(badges))
    except Exception as e:
        print(f"Error fetching badges: {e}")
        return []

def create_badge(data):
    fields = {}
    
    fn = data.get('firstName', '')
    ln = data.get('lastName', '')
    ms = data.get('mission', '') or ' '
    pu = data.get('photoUrl') or ' '
    bi = data.get('bgImage') or ' '
    bc = data.get('backgroundColor', 'linear-gradient(135deg,#2d4a1e,#556b2f)')
    ts = int(__import__('time').time() * 1000)
    
    fields['firstName'] = {'stringValue': fn}
    fields['lastName'] = {'stringValue': ln}
    fields['mission'] = {'stringValue': ms}
    fields['photoUrl'] = {'stringValue': pu}
    fields['bgImage'] = {'stringValue': bi}
    fields['backgroundColor'] = {'stringValue': bc}
    fields['createdAt'] = {'integerValue': ts}
    
    badge_data = {'fields': fields}
    
    try:
        resp = requests.post(f"{FIREBASE_URL}/badges", json=badge_data)
        if resp.status_code == 200:
            return resp.json()
        return {'error': resp.text, 'status': resp.status_code}
    except Exception as e:
        return {'error': str(e)}

def delete_badge(badge_id):
    try:
        resp = requests.delete(f"{FIREBASE_URL}/badges/{badge_id}")
        resp.raise_for_status()
        return True
    except Exception as e:
        print(f"Error deleting badge: {e}")
        return False

@app.route('/')
def index():
    return render_template('badge.html')

@app.route('/api/badges', methods=['GET'])
def get_badges_api():
    badges = get_badges()
    return jsonify(badges)

@app.route('/api/badges', methods=['POST'])
def create_badge_api():
    data = request.get_json()
    if not data or not data.get('firstName') or not data.get('lastName'):
        return jsonify({'error': 'First name and last name are required'}), 400
    
    result = create_badge(data)
    if result and 'error' not in result:
        return jsonify({'message': 'Badge created', 'data': result}), 201
    return jsonify({'error': result.get('error', 'Failed to create badge')}), 500

@app.route('/api/badges/<badge_id>', methods=['DELETE'])
def delete_badge_api(badge_id):
    if delete_badge(badge_id):
        return jsonify({'message': 'Badge deleted'})
    return jsonify({'error': 'Failed to delete badge'}), 500

@app.route('/api/export/print')
def export_print():
    badges = get_badges()
    
    badges_html = ""
    for badge in badges:
        bg_style = f"background-image: url({badge.get('bgImage')}); background-size: cover; background-position: center;" if badge.get('bgImage') else f"background: {badge.get('backgroundColor', '#2d4a1e')};"
        photo = badge.get('photoUrl', 'https://via.placeholder.com/150')
        
        badges_html += f"""
        <div class="badge-item">
            <div class="badge" style="{bg_style}">
                <div class="badge-bg-overlay"></div>
                <div class="badge-event">الملتقى الوطني للاستكشاف والمغامرة</div>
                <div class="badge-content">
                    <div class="photo-container">
                        <img class="badge-photo" src="{photo}" alt="">
                        <img class="badge-logo" src="https://upload.wikimedia.org/wikipedia/commons/thumb/e/e6/Star_and_Crescent.svg/120px-Star_and_Crescent.svg.png" alt="logo">
                    </div>
                    <div class="badge-name">{badge.get('firstName', '')} {badge.get('lastName', '')}</div>
                </div>
                <div class="badge-mission-wrap">
                    <div class="badge-mission-label">المهمة</div>
                    <div class="badge-mission-value">{badge.get('mission', '—')}</div>
                </div>
            </div>
        </div>
        """
    
    html = f"""<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
<meta charset="UTF-8">
<title>طباعة البطاقات</title>
<link href="https://fonts.googleapis.com/css2?family=Tajawal:wght@400;700;800;900&display=swap" rel="stylesheet">
<style>
* {{ margin:0; padding:0; box-sizing:border-box; }}
body {{ font-family: 'Tajawal', sans-serif; background: white; padding: 20px; }}
.badges-list {{ display: flex; flex-wrap: wrap; gap: 20px; justify-content: flex-start; }}
.badge-item {{ position: relative; break-inside: avoid; }}
.delete-badge {{ display: none; }}
.badge {{ width: 310px; height: 450px; border-radius: 14px; position: relative; overflow: hidden;
  box-shadow: 0 0 0 4px #c8a96e, 0 0 0 8px #556b2f;
  background-size: cover !important; background-position: center !important; }}
.badge-bg-overlay {{ position: absolute; inset: 0; background: rgba(15,25,8,0.5); z-index: 1; display: none; }}
.badge.has-bg-image .badge-bg-overlay {{ display: block; }}
.badge-event {{ position: absolute; top: 0; left: 0; right: 0; z-index: 3;
  background: rgba(0,0,0,0.55); border-bottom: 2px solid #c8a96e;
  color: #f5e6b0; font-family: 'Tajawal', sans-serif; font-size: 12.5px; font-weight: 800;
  padding: 9px 12px; text-align: center; line-height: 1.5; }}
.badge-content {{ position: absolute; inset: 0; z-index: 2; display: flex; flex-direction: column;
  align-items: center; justify-content: center; padding: 70px 16px 70px; }}
.badge-photo {{ width: 110px; height: 110px; border-radius: 50%; border: 4px solid #d4a84b;
  box-shadow: 0 0 0 3px rgba(255,255,255,0.15), 0 6px 16px rgba(0,0,0,0.45);
  object-fit: cover; margin-bottom: 10px; }}
.photo-container {{ position: relative; }}
.badge-logo {{ position: absolute; bottom: 0; right: 0; width: 40px; height: 40px; border-radius: 50%; border: 2px solid #d4a84b; object-fit: cover; background: white; }}
.badge-name {{ font-family: 'Tajawal', sans-serif; font-size: 18px; font-weight: 900;
  color: #fff; text-shadow: 1px 1px 8px rgba(0,0,0,0.8); text-align: center; }}
.badge-mission-wrap {{ position: absolute; bottom: 0; left: 0; right: 0; z-index: 3;
  background: rgba(0,0,0,0.55); border-top: 2px solid #c8a96e; padding: 8px 12px; text-align: center; }}
.badge-mission-label {{ font-family: 'Tajawal', sans-serif; font-size: 10px; color: #c8a96e; font-weight: 700; }}
.badge-mission-value {{ font-family: 'Tajawal', sans-serif; font-size: 14px; font-weight: 800;
  color: #f5e6b0; text-shadow: 1px 1px 4px rgba(0,0,0,0.7); }}
@media print {{ body {{ padding: 8px; }} .badge-item {{ break-inside: avoid; }} }}
</style>
</head>
<body>
<div class="badges-list">{badges_html}</div>
<script>window.onload = function() {{ window.print(); }}</script>
</body>
</html>"""
    
    response = make_response(html)
    response.headers['Content-Type'] = 'text/html; charset=utf-8'
    return response

@app.route('/api/export/pdf')
def export_pdf():
    badges = get_badges()
    
    badge_width = 8.5 * cm
    badge_height = 12 * cm
    cols = 2
    margin = 1 * cm
    
    page_width = A4[0]
    page_height = A4[1]
    
    pdf_buffer = io.BytesIO()
    c = canvas.Canvas(pdf_buffer, pagesize=A4)
    
    def get_image_buffer(base64_str, size=None):
        if base64_str and base64_str.startswith('data:image'):
            try:
                img_data = base64_str.split(',')[1]
                img_bytes = base64.b64decode(img_data)
                img = PILImage.open(io.BytesIO(img_bytes)).convert('RGB')
                if size:
                    img = img.resize((int(size[0]), int(size[1])), PILImage.LANCZOS)
                buf = io.BytesIO()
                img.save(buf, format='PNG')
                buf.seek(0)
                return buf
            except Exception as e:
                print(f"Image load error: {e}")
        return None
    
    def draw_text_rtl(c, text, x, y, font_name, font_size, color):
        c.setFont(font_name, font_size)
        c.setFillColor(color)
        reshaped = reshape_arabic(text)
        c.drawRightString(x + badge_width - 0.3*cm, y, reshaped)
    
    def draw_badge(badge, x, y):
        c.saveState()
        c.translate(x, y)
        
        c.setFillColor(HexColor('#556b2f'))
        c.roundRect(0, 0, badge_width, badge_height, 8, fill=1, stroke=0)
        
        c.setFillColor(HexColor('#d4a84b'))
        c.setLineWidth(3)
        c.roundRect(2, 2, badge_width - 4, badge_height - 4, 6, fill=0, stroke=1)
        
        bg_buf = get_image_buffer(badge.get('bgImage', ''), size=(int(badge_width/cm*100), int(badge_height/cm*100)))
        if bg_buf:
            c.drawImage(bg_buf, 0, 0, width=badge_width, height=badge_height, preserveAspectRatio=False, mask='auto')
            c.setFillColor(HexColor('#000000'))
            c.setFillAlpha(0.4)
            c.rect(0, 0, badge_width, badge_height, fill=1, stroke=0)
            c.setFillAlpha(1)
        else:
            c.setFillColor(HexColor('#2d4a1e'))
            c.roundRect(0, 0, badge_width, badge_height, 8, fill=1, stroke=0)
        
        c.setFillColor(HexColor('#3d3010'))
        c.rect(0, badge_height - 1.3*cm, badge_width, 1.3*cm, fill=1, stroke=0)
        draw_text_rtl(c, "الملتقى الوطني للاستكشاف والمغامرة", badge_width/2, badge_height - 0.6*cm, 'Arabic', 9, HexColor('#f5e6b0'))
        
        center_y = badge_height / 2 + 0.3*cm
        
        logo_buf = io.BytesIO()
        logo_img = PILImage.new('RGB', (100, 100), (212, 168, 75))
        logo_img.save(logo_buf, format='PNG')
        logo_buf.seek(0)
        c.drawImage(logo_buf, badge_width/2 - 0.7*cm, center_y + 1.5*cm, width=1.4*cm, height=1.4*cm)
        
        photo_size = 2.2 * cm
        photo_buf = get_image_buffer(badge.get('photoUrl', ''), size=(200, 200))
        if photo_buf:
            c.saveState()
            c.beginPath()
            c.circle(badge_width/2, center_y, photo_size/2)
            c.clip()
            c.drawImage(photo_buf, badge_width/2 - photo_size/2, center_y - photo_size/2, width=photo_size, height=photo_size)
            c.restoreState()
            c.setStrokeColor(HexColor('#d4a84b'))
            c.setLineWidth(4)
            c.circle(badge_width/2, center_y, photo_size/2)
        else:
            c.setFillColor(HexColor('#d4a84b'))
            c.circle(badge_width/2, center_y, photo_size/2, fill=1, stroke=0)
            c.setFillColor(HexColor('#f5e6b0'))
            c.setFont('ArabicBold', 24)
            c.drawCentredString(badge_width/2, center_y - 0.3*cm, "📷")
        
        name = f"{badge.get('firstName', '')} {badge.get('lastName', '')}"
        c.setFillColor(HexColor('#ffffff'))
        c.setFont('ArabicBold', 12)
        c.setFillColor(HexColor('#000000'))
        shadow = c.getStringWidth(name, 'ArabicBold', 12)
        c.setFillColor(HexColor('#000000'))
        c.drawCentredString(badge_width/2 + 0.5, center_y - 1.7*cm + 0.5, name[:25] if len(name) > 25 else name)
        c.setFillColor(HexColor('#ffffff'))
        c.drawCentredString(badge_width/2, center_y - 1.7*cm, name[:25] if len(name) > 25 else name)
        
        c.setFillColor(HexColor('#3d3010'))
        c.rect(0, 0, badge_width, 1.3*cm, fill=1, stroke=0)
        draw_text_rtl(c, "المهمة", badge_width/2, 0.9*cm, 'Arabic', 9, HexColor('#c8a96e'))
        mission_text = badge.get('mission', '—')
        if len(mission_text) > 20:
            mission_text = mission_text[:20]
        draw_text_rtl(c, mission_text, badge_width/2, 0.35*cm, 'ArabicBold', 10, HexColor('#f5e6b0'))
        
        c.restoreState()
    
    badges_per_page = cols * 4
    for idx, badge in enumerate(badges):
        page_idx = idx // badges_per_page
        if page_idx > 0:
            c.showPage()
        
        pos_in_page = idx % badges_per_page
        col = pos_in_page % cols
        row = pos_in_page // cols
        
        x = margin + col * (badge_width + 0.5*cm)
        y = page_height - margin - (row + 1) * (badge_height + 0.3*cm) + 0.3*cm
        
        draw_badge(badge, x, y)
    
    c.save()
    pdf_buffer.seek(0)
    
    response = make_response(pdf_buffer.getvalue())
    response.headers['Content-Type'] = 'application/pdf'
    response.headers['Content-Disposition'] = 'attachment; filename=badges.pdf'
    
    return response

if __name__ == '__main__':
    app.run(debug=False, host='0.0.0.0', port=7860)
