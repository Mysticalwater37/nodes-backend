# ===== Imports =====
from flask import Flask, request, jsonify, send_file
import swisseph as swe
from timezonefinder import TimezoneFinder
from datetime import datetime
import pytz
import uuid
import os
import resend
import base64
import openai
import requests
import logging

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import inch
from reportlab.lib.colors import HexColor
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak
from reportlab.lib.styles import ParagraphStyle, TA_CENTER, TA_JUSTIFY
import uuid

# ===== App Setup =====
app = Flask(__name__)
logging.basicConfig(level=logging.DEBUG)

# ===== API Keys / Config =====
openai.api_key = os.getenv("OPENAI_API_KEY")
resend.api_key = os.getenv("RESEND_API_KEY")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")  # must be set in Render

# ===== Swiss Ephemeris =====
swe.set_ephe_path('.')  # expects ephemeris files in working dir or system path

# ===== Globals =====
temp_files = {}

# ===== Helpers =====
def get_zodiac_sign(longitude):
    signs = [
        "Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo",
        "Libra", "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces"
    ]
    idx = int(longitude // 30) % 12
    return signs[idx]

def calculate_nodes_and_big_three(birthdate, birthtime, latitude, longitude):
    """
    Compute Sun, Moon, Rising, and Nodes using Swiss Ephemeris.
    birthdate: 'YYYY-MM-DD'
    birthtime: 'HH:MM' 24h local time
    latitude, longitude: floats (lon negative for W)
    """
    try:
        # 1) Parse local date/time (naive)
        dt_str = f"{birthdate} {birthtime}"
        local_dt = datetime.strptime(dt_str, "%Y-%m-%d %H:%M")

        # 2) Resolve timezone from coordinates
        tf = TimezoneFinder()
        tz_name = tf.timezone_at(lat=latitude, lng=longitude)
        if not tz_name:
            tz_name = "UTC"
        local_tz = pytz.timezone(tz_name)

        # 3) Localize then convert to UTC
        local_dt = local_tz.localize(local_dt)
        utc_dt = local_dt.astimezone(pytz.utc)

        # 4) Julian Day in UT
        jd_ut = swe.julday(
            utc_dt.year,
            utc_dt.month,
            utc_dt.day,
            utc_dt.hour + utc_dt.minute / 60.0
        )

        # Debug
        print("DEBUG utc_dt:", utc_dt)
        print("DEBUG jd_ut:", jd_ut)
        print("DEBUG latitude:", latitude, "longitude:", longitude)

        # Sun
        sun_long, _ = swe.calc_ut(jd_ut, swe.SUN)
        sun_sign = get_zodiac_sign(sun_long[0])

        # Moon
        moon_long, _ = swe.calc_ut(jd_ut, swe.MOON)
        moon_sign = get_zodiac_sign(moon_long[0])

        # Rising (Ascendant)
        ascmc, cusps = swe.houses(jd_ut, latitude, longitude, b"P")
        rising_long = ascmc[0]
        rising_sign = get_zodiac_sign(rising_long)
        print("DEBUG rising_long:", rising_long, "rising_sign:", rising_sign)

        # Nodes (True Node)
        north_node_long, _ = swe.calc_ut(jd_ut, swe.TRUE_NODE)
        north_node_sign = get_zodiac_sign(north_node_long[0])
        south_node_sign = get_zodiac_sign((north_node_long[0] + 180.0) % 360.0)

        return {
            "sun_sign": sun_sign,
            "moon_sign": moon_sign,
            "rising_sign": rising_sign,
            "north_node": {"sign": north_node_sign},
            "south_node": {"sign": south_node_sign}
        }

    except Exception as e:
        import traceback
        print("[calculate_nodes_and_big_three] ERROR:", e)
        print(traceback.format_exc())
        return None

def generate_ai_report(chart_data, first_name):
    """Generate the narrative report via OpenAI. Avoid em dashes in prompt."""
    sun_sign = chart_data.get('sun_sign', 'Unknown')
    moon_sign = chart_data.get('moon_sign', 'Unknown')
    rising_sign = chart_data.get('rising_sign', 'Unknown')
    north_node_sign = chart_data.get('north_node', {}).get('sign', 'Unknown')
    south_node_sign = chart_data.get('south_node', {}).get('sign', 'Unknown')

    prompt = f"""
You are an expert astrologer. Write a personalized report for {first_name}.
Do not use em dashes. Use plain periods or commas.

Placements:
Sun {sun_sign}; Moon {moon_sign}; Rising {rising_sign}; North Node {north_node_sign}; South Node {south_node_sign}.

Create exactly these sections with clear headers:

SECTION: Your Cosmic Blueprint
[2–3 short paragraphs introducing {first_name} to their combination. No em dashes.]

SECTION: Your Inner Light - Sun in {sun_sign}
[2 short paragraphs on {sun_sign} core identity. No em dashes.]

SECTION: Your Emotional Nature - Moon in {moon_sign}
[2 short paragraphs on emotions and needs. No em dashes.]

SECTION: Your Rising Persona - {rising_sign} Ascending
[2 short paragraphs on first impression and approach. No em dashes.]

SECTION: Your Soul's Journey - The Nodal Pathway
[3 short paragraphs: growth from {south_node_sign} to {north_node_sign}. No em dashes.]

SECTION: Integration and Growth
[2–3 short paragraphs of practical guidance. No em dashes.]

Use {first_name}'s name naturally. Counseling tone. No em dashes.
"""

    try:
        # If you use the new Chat Completions API name:
        # resp = openai.ChatCompletion.create(...)
        resp = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=2000,
            temperature=0.7
        )
        return resp.choices[0].message.content.strip()
    except Exception as e:
        print("OpenAI error:", e)
        fallback = f"""SECTION: Your Personal Report
Hi {first_name}. Your report could not be generated automatically. Please contact support."""
        return fallback

def create_pdf_report(report_text, first_name="Friend"):
    """Create a styled PDF and return file path."""
    filename = f"nodal_report_{uuid.uuid4()}.pdf"
    filepath = f"/tmp/{filename}"

    doc = SimpleDocTemplate(
        filepath,
        pagesize=A4,
        rightMargin=0.75*inch, leftMargin=0.75*inch,
        topMargin=1*inch, bottomMargin=1*inch
    )

    gold = HexColor('#edd598')
    white = HexColor('#ffffff')
    body_color = HexColor('#e2e8f0')
    bg_dark = HexColor('#2d3748')  # used in section header background

    title_style = ParagraphStyle(
        'Title',
        fontSize=32,
        textColor=gold,
        spaceAfter=30,
        alignment=TA_CENTER,
        fontName='Helvetica-Bold',
        leading=36
    )
    subtitle_style = ParagraphStyle(
        'Subtitle',
        fontSize=18,
        textColor=body_color,
        spaceAfter=36,
        alignment=TA_CENTER,
        fontName='Helvetica',
        leading=24
    )
    section_style = ParagraphStyle(
        'SectionHeader',
        fontSize=22,
        textColor=gold,
        spaceAfter=18,
        spaceBefore=28,
        alignment=TA_CENTER,
        fontName='Helvetica-Bold',
        leading=28,
        borderWidth=1,
        borderColor=gold,
        borderPadding=12,
        backColor=bg_dark
    )
    body_style = ParagraphStyle(
        'Body',
        fontSize=12.5,
        textColor=body_color,
        spaceAfter=12,
        spaceBefore=4,
        alignment=TA_JUSTIFY,
        fontName='Helvetica',
        leading=18
    )
    disclaimer_style = ParagraphStyle(
        'Disclaimer',
        fontSize=11.5,
        textColor=body_color,
        spaceAfter=10,
        spaceBefore=22,
        alignment=TA_CENTER,
        fontName='Helvetica-Oblique',
        leading=16,
        leftIndent=20,
        rightIndent=20
    )

    story = []
    story.append(Spacer(1, 0.6*inch))
    story.append(Paragraph("Nodal Pathways", title_style))
    story.append(Paragraph(f"Personalized Astrological Report for {first_name}", subtitle_style))

    # Parse the AI sections and render
    sections = [s for s in report_text.split('SECTION:') if s.strip()]
    for sec in sections:
        lines = [ln.strip() for ln in sec.strip().split('\n') if ln.strip()]
        if not lines:
            continue
        header = lines[0]
        story.append(Paragraph(header, section_style))
        text = ' '.join(lines[1:])
        # Split into pseudo-paragraphs by double spaces or sentence ends
        parts = [p.strip() for p in text.replace('\n', ' ').split('. ') if p.strip()]
        for p in parts:
            if not p.endswith('.'):
                p += '.'
            story.append(Paragraph(p, body_style))

    # Footer with merged disclaimer sentence
    story.append(Spacer(1, 0.6*inch))
    story.append(Paragraph("Nodal Pathways", section_style))
    story.append(Paragraph(
        "Guiding you on your cosmic journey of self-discovery. "
        "For entertainment and self-reflection purposes only. Not predictive or definitive.",
        disclaimer_style
    ))

    doc.build(story)
    return filepath

def create_html_report(chart_data, ai_content, first_name):
    """HTML report with merged disclaimer sentence."""
    chart_basics = f"""
    <div class="chart-basics">
        <h3>Chart Essentials for {first_name}</h3>
        <div class="basics-grid">
            <div class="basic-item"><strong>Sun Sign:</strong> {chart_data['sun_sign']}</div>
            <div class="basic-item"><strong>Moon Sign:</strong> {chart_data['moon_sign']}</div>
            <div class="basic-item"><strong>Rising Sign:</strong> {chart_data['rising_sign']}</div>
            <div class="basic-item"><strong>North Node:</strong> {chart_data['north_node']['sign']}</div>
        </div>
    </div>
    """

    html = f"""<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<title>Nodal Pathways Report - {first_name}</title>
<style>
body {{ font-family: -apple-system, BlinkMacSystemFont, Inter, Helvetica, Arial, sans-serif; background:#1a202c; color:#e2e8f0; margin:0; }}
.container {{ max-width: 900px; margin: 0 auto; padding: 24px; }}
.header {{ text-align:center; padding: 36px 12px; background:#2d3748; border-radius:16px; }}
.header h1 {{ color:#edd598; margin:0 0 8px 0; }}
.header .subtitle {{ color:#cbd5e0; }}
.basics-grid {{ display:grid; grid-template-columns:1fr 1fr; gap:12px; }}
.basic-item {{ background:#2a3141; border:1px solid #3a4151; padding:14px; border-radius:10px; }}
strong {{ color:#edd598; }}
.section h2 {{ color:#edd598; text-align:center; margin:28px 0 12px; }}
.section p {{ line-height:1.7; text-align:justify; }}
.footer {{ text-align:center; margin-top:32px; padding:24px; background:#2d3748; border-radius:14px; color:#cbd5e0; }}
.disclaimer {{ margin:22px auto; max-width:760px; text-align:center; color:#cbd5e0; }}
</style>
</head>
<body>
<div class="container">
  <div class="header">
    <h1>Nodal Pathways</h1>
    <div class="subtitle">Personalized Astrological Report for {first_name}</div>
  </div>
  {chart_basics}
  <div class="section" id="content">
    {ai_content}
  </div>
  <div class="disclaimer">
    Guiding you on your cosmic journey of self-discovery. For entertainment and self-reflection purposes only. Not predictive or definitive.
  </div>
  <div class="footer">
    Nodal Pathways
  </div>
</div>
</body>
</html>"""
    return html

def send_report_email(email, html_body, pdf_path):
    """Email via Resend with attached PDF."""
    with open(pdf_path, 'rb') as f:
        pdf_b64 = base64.b64encode(f.read()).decode('utf-8')

    resend.Emails.send({
        "from": "reports@api.nodalpathways.com",
        "to": email,
        "subject": "Your Nodal Pathways Report",
        "html": html_body,
        "attachments": [{
            "filename": "nodal_pathways_report.pdf",
            "content": pdf_b64
        }]
    })

# ===== Routes =====
@app.route('/test', methods=['GET'])
def test():
    return jsonify({"status": "ok"})

@app.route('/ping', methods=['POST'])
def ping():
    return jsonify({"parsed": request.get_json(silent=True)})

@app.route('/report', methods=['POST'])
def report_pdf():
    """Generate a PDF from raw 'report' text. Returns download URL and filename."""
    try:
        data = request.get_json(silent=True) or {}
        report_text = data.get("report", "").strip()
        if not report_text:
            return jsonify({"error": "Missing 'report'"}), 400

        file_path = create_pdf_report(report_text, data.get("first_name", "Friend"))
        file_id = file_path.rsplit('/', 1)[-1].replace('.pdf', '')
        temp_files[file_id] = file_path
        download_url = f"{request.url_root}download/{file_id}"
        return jsonify({"download_url": download_url, "filename": file_path.rsplit('/',1)[-1]})
    except Exception as e:
        return jsonify({"error": str(e)}), 400

@app.route('/download/<file_id>', methods=['GET'])
def download(file_id):
    path = temp_files.get(file_id)
    if not path or not os.path.exists(path):
        return jsonify({"error": "File not found"}), 404
    return send_file(path, mimetype='application/pdf', as_attachment=True, download_name=os.path.basename(path))

@app.route('/process-form', methods=['POST'])
def process_form():
    """
    Expected JSON body (from Google Form webhook or curl):
    {
      "City": "Chicago Heights",
      "State": "IL",
      "Country": "USA",
      "Email": "test@example.com",
      "First Name": "Friend",
      "Birth Date": "1999-03-13",
      "Birth Time": "16:04"
    }
    """
    try:
        data = request.get_json(silent=True) or {}
        city = data.get('City', '')
        state = data.get('State', '')
        country = data.get('Country', '')
        email = data.get('Email', 'test@example.com')
        first_name = data.get('First Name', 'Friend')
        birth_date = data.get('Birth Date', '')
        birth_time = data.get('Birth Time', '12:00')

        if not GOOGLE_API_KEY:
            return jsonify({"error": "GOOGLE_API_KEY not set"}), 400

        location_str = f"{city}, {state}, {country}" if state else f"{city}, {country}"
        geocode_url = "https://maps.googleapis.com/maps/api/geocode/json"
        params = {"address": location_str, "key": GOOGLE_API_KEY}
        r = requests.get(geocode_url, params=params, timeout=10)
        js = r.json()
        if js.get("status") != "OK" or not js.get("results"):
            return jsonify({
                "error": f"Failed to geocode location: {location_str}",
                "status": js.get("status"),
                "message": js.get("error_message")
            }), 400

        loc = js["results"][0]["geometry"]["location"]
        latitude, longitude = loc["lat"], loc["lng"]

        chart_data = calculate_nodes_and_big_three(birth_date, birth_time, latitude, longitude)
        if not chart_data:
            return jsonify({"error": "Chart calculation failed"}), 400

        ai_content = generate_ai_report(chart_data, first_name)
        html_content = create_html_report(chart_data, ai_content, first_name)
        pdf_path = create_pdf_report(ai_content, first_name)

        try:
            send_report_email(email, html_content, pdf_path)
        finally:
            try:
                os.remove(pdf_path)
            except Exception:
                pass

        return jsonify({
            "status": "success",
            "message": f"Report sent successfully to {email}",
            "chart_data": chart_data
        })

    except Exception as e:
        import traceback
        print("PROCESS-FORM ERROR:", e)
        print(traceback.format_exc())
        return jsonify({"error": str(e)}), 400

# ===== Main =====
if __name__ == '__main__':
    # For local testing
    app.run(host="0.0.0.0", port=5000)
