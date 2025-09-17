from flask import Flask, request, jsonify, send_file
import swisseph as swe
from geopy.geocoders import Nominatim
from timezonefinder import TimezoneFinder
from datetime import datetime
import pytz
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib.pagesizes import letter
from reportlab.lib.colors import HexColor
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_JUSTIFY
import uuid
import os
import resend
import base64
from flask import Flask, jsonify  # Add this import
from knowledge_base import KNOWLEDGE_BASE
import knowledge_base as kb
print(">>> LOADED KNOWLEDGE_BASE KEYS:", list(kb.KNOWLEDGE_BASE.keys()))
print(">>> LOADED FROM FILE:", kb.__file__)
app = Flask(__name__)
import logging
logging.basicConfig(level=logging.DEBUG)

print("=== APP STARTING - IMPORTS SUCCESSFUL ===")  # Add this line
print(f"KNOWLEDGE_BASE loaded with keys: {list(KNOWLEDGE_BASE.keys())}")  # Add this line

@app.route('/test', methods=['GET'])
def test():
    print("TEST ROUTE WORKING")
    print("=== CHECKING KNOWLEDGE BASE ===")
    print(f"KNOWLEDGE_BASE keys: {list(KNOWLEDGE_BASE.keys())}")
    return jsonify({
        "status": "test successful", 
        "kb_keys": list(KNOWLEDGE_BASE.keys())
    })

# Path to Swiss Ephemeris data files
swe.set_ephe_path('.')  

# Set your Resend API key from environment variable
resend.api_key = os.getenv("RESEND_API_KEY")

SIGNS = [
    "Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo",
    "Libra", "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces"
]
# Store for temporary files
temp_files = {}

def calculate_nodes_and_big_three(date, time, city, country):
    """Calculate North/South Node positions and Sun/Moon/Rising signs"""
    try:
        # Cached coordinates for reliability
        CITY_COORDS = {
            "Berkeley, USA": (37.8715, -122.2730),
            "San Francisco, USA": (37.7749, -122.4194),
            "Los Angeles, USA": (34.0522, -118.2437),
            "New York, USA": (40.7128, -74.0060),
            "Chicago, USA": (41.8781, -87.6298),
            "Houston, USA": (29.7604, -95.3698),
            "Miami, USA": (25.7617, -80.1918),
            "Atlanta, USA": (33.7490, -84.3880),
            "Washington, USA": (38.9072, -77.0369),
            "Dallas, USA": (32.7767, -96.7970),
            "London, UK": (51.5074, -0.1278),
            "Paris, France": (48.8566, 2.3522),
            "Tokyo, Japan": (35.6895, 139.6917),
            "Sydney, Australia": (-33.8688, 151.2093),
            "Toronto, Canada": (43.6532, -79.3832),
        }

        # Normalize key
        city_key = f"{city.strip()}, {country.strip()}"
        city_key = " ".join(city_key.split())

        if city_key in CITY_COORDS:
            lat, lon = CITY_COORDS[city_key]
        else:
            geolocator = Nominatim(
                user_agent="nodes-backend/1.0 (support@nodalpathways.com)",
                timeout=10
            )
            loc = geolocator.geocode(city_key)
            if loc is None:
                raise ValueError(f"Could not find coordinates for {city_key}")
            lat, lon = loc.latitude, loc.longitude

        # Timezone
        tf = TimezoneFinder()
        tz_str = tf.timezone_at(lng=lon, lat=lat)
        if not tz_str:
            raise ValueError(f"Could not resolve timezone for {city_key}")
        tz = pytz.timezone(tz_str)

        # Build datetime
        dt = datetime.strptime(f"{date} {time}", "%Y-%m-%d %H:%M")
        utc_dt = tz.localize(dt).astimezone(pytz.utc)

        # Julian day
        jd = swe.julday(
            utc_dt.year,
            utc_dt.month,
            utc_dt.day,
            utc_dt.hour + utc_dt.minute / 60.0
        )

        # Node
        node, *_ = swe.calc_ut(jd, swe.TRUE_NODE)
        node_long = node[0] % 360.0
        node_sign_index = int(node_long // 30)
        node_sign = SIGNS[node_sign_index]
        node_degree = node_long % 30

        # Sun
        sun, *_ = swe.calc_ut(jd, swe.SUN)
        sun_sign = SIGNS[int((sun[0] % 360.0) // 30)]

        # Moon
        moon, *_ = swe.calc_ut(jd, swe.MOON)
        moon_sign = SIGNS[int((moon[0] % 360.0) // 30)]

        # Rising
        houses, ascmc = swe.houses_ex(jd, lat, lon, b'P')
        asc_long = ascmc[0] % 360.0
        rising_sign = SIGNS[int(asc_long // 30)]

        # Node house
        node_house = None
        for i in range(12):
            start = houses[i]
            end = houses[(i + 1) % 12]
            if start <= node_long < end or (end < start and (node_long >= start or node_long < end)):
                node_house = i + 1
                break

        # South Node
        south_sign = SIGNS[(node_sign_index + 6) % 12]
        south_house = (node_house + 6 - 1) % 12 + 1 if node_house else None

        return {
            "north_node": {"sign": node_sign, "degree": round(node_degree, 2), "house": node_house},
            "south_node": {"sign": south_sign, "degree": round(node_degree, 2), "house": south_house},
            "sun_sign": sun_sign,
            "moon_sign": moon_sign,
            "rising_sign": rising_sign
        }

    except Exception as e:
        raise Exception(f"Calculation error: {str(e)}")

def generate_full_report(chart_data):
    """Generate rich, narrative-style report with context and explanations"""
    try:
        north_node = chart_data["north_node"]
        south_node = chart_data["south_node"]
        sun_sign = chart_data["sun_sign"]
        moon_sign = chart_data["moon_sign"]
        rising_sign = chart_data["rising_sign"]

        report = []
        report.append("NODAL PATHWAYS REPORT")
        report.append("=" * 50)
        report.append("")

        # Blueprint
        report.append("YOUR ASTROLOGICAL BLUEPRINT")
        report.append("-" * 30)
        report.append(f"Sun in {sun_sign} • Moon in {moon_sign} • Rising in {rising_sign}")
        report.append(f"North Node in {north_node['sign']} • South Node in {south_node['sign']}")
        report.append("")

        # North Node
        report.append("NORTH NODE GUIDANCE")
        report.append("-" * 20)
        north_sign_data = KNOWLEDGE_BASE["north_nodes"][north_node["sign"]]
        report.append(
            f"Your North Node in {north_node['sign']} reveals your soul's primary growth direction. "
            f"{north_sign_data['meaning']} This placement asks you to embrace qualities that may feel "
            f"unfamiliar or challenging at first, but will ultimately lead to fulfillment."
        )
        report.append("")

        report.append("To develop these qualities, focus on practical steps:")
        for i, guidance in enumerate(north_sign_data['guidance']):
            guidance_clean = guidance.rstrip('.').lower()
            if i == 0:
                report.append(f"Start by {guidance_clean}.")
            elif i == len(north_sign_data['guidance']) - 1:
                report.append(f"Most importantly, {guidance_clean}.")
            else:
                report.append(f"Additionally, {guidance_clean}.")
        report.append("")

        # House Guidance
        if north_node.get("house"):
            house_data = KNOWLEDGE_BASE["houses"][north_node["house"]]
            report.append(f"Your North Node's placement in the {north_node['house']}th house adds depth. "
                          f"{house_data['meaning']} This shows the life areas where your {north_node['sign']} growth "
                          f"will be most transformative.")
            for i, guidance in enumerate(house_data['guidance']):
                guidance_clean = guidance.rstrip('.').lower()
                if i == 0:
                    report.append(f"Begin by learning to {guidance_clean}.")
                elif i == len(house_data['guidance']) - 1:
                    report.append(f"Most importantly, focus on how to {guidance_clean}.")
                else:
                    report.append(f"Practice {guidance_clean}.")
            report.append("")

        # South Node
        report.append("SOUTH NODE AWARENESS")
        report.append("-" * 20)
        south_sign_data = KNOWLEDGE_BASE["south_nodes"][south_node["sign"]]
        report.append(
            f"Your South Node in {south_node['sign']} represents gifts and patterns from past lifetimes. "
            f"The challenge lies in {south_sign_data['patterns'].lower()} — familiar tendencies that can hold "
            f"you back if overused."
        )
        report.append("To find balance, practice awareness in these areas:")
        for guidance in south_sign_data['guidance']:
            report.append(f"- {guidance}")
        report.append("")

        # Sun Interaction
        report.append("YOUR NODES AND SUN SIGN")
        report.append("-" * 25)
        if sun_sign == north_node['sign']:
            report.append(f"Your Sun in {sun_sign} aligns with your North Node, unifying identity and purpose.")
        elif sun_sign == south_node['sign']:
            report.append(f"Your Sun in {sun_sign} echoes your South Node gifts. Use them as a foundation, not a limit.")
        else:
            report.append(f"Your {sun_sign} Sun fuels your {north_node['sign']} North Node growth with vitality and drive.")
        report.append("")

        # Moon Interaction
        report.append("YOUR NODES AND MOON SIGN")
        report.append("-" * 26)
        if moon_sign == north_node['sign']:
            report.append(f"Your Moon in {moon_sign} gives you intuitive access to your North Node path.")
        elif moon_sign == south_node['sign']:
            report.append(f"Your Moon in {moon_sign} ties to your South Node comfort zone. Expand gently beyond it.")
        else:
            report.append(f"Your {moon_sign} Moon offers emotional support for your {north_node['sign']} growth.")
        report.append("")

        # Rising Interaction
        report.append("YOUR NODES AND RISING SIGN")
        report.append("-" * 28)
        if rising_sign == north_node['sign']:
            report.append(f"Your {rising_sign} Rising reflects your North Node — others already see you as living it.")
        elif rising_sign == south_node['sign']:
            report.append(f"Your {rising_sign} Rising mirrors South Node qualities. Be mindful to weave in your North Node growth.")
        else:
            report.append(f"Your {rising_sign} Rising colors how you pursue your {north_node['sign']} North Node.")
        report.append("")

        # Integration
        report.append("INTEGRATED GUIDANCE")
        report.append("-" * 18)
        report.append(f"Your journey moves from {south_node['sign']} patterns toward {north_node['sign']} mastery. "
                      f"Use your {sun_sign} Sun, {moon_sign} Moon, and {rising_sign} Rising together to support "
                      f"this growth.")
        report.append("Astrology is interpretive and meant for reflection only.")

        return "\n".join(report)

    except Exception as e:
        raise Exception(f"Report generation error: {str(e)}")

def create_pdf_report(report_text):
    """Create a beautifully formatted PDF from report text"""
    filename = f"nodal_report_{uuid.uuid4()}.pdf"
    filepath = f"/tmp/{filename}"
    
    # Create document with proper margins
    doc = SimpleDocTemplate(
        filepath, 
        pagesize=letter,
        rightMargin=1*inch, 
        leftMargin=1*inch,
        topMargin=1*inch, 
        bottomMargin=1*inch
    )
    
    # Define color scheme to match your celestial branding
    primary_color = HexColor('#2C3E50')  # Deep navy (like your dark section)
    accent_color = HexColor('#6B9BD8')   # Soft blue (like your header gradient)
    secondary_color = HexColor('#8FA8C7')  # Lighter celestial blue
    text_color = HexColor('#2C3E50')     # Dark navy for readability
    
    # Get base styles
    styles = getSampleStyleSheet()
    
    # Custom title style - celestial themed
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=24,
        textColor=primary_color,
        spaceAfter=40,
        spaceBefore=20,
        alignment=TA_CENTER,
        fontName='Helvetica-Bold'
    )
    
 # Custom main heading style - bolder and larger
    main_heading_style = ParagraphStyle(
        'MainHeading',
        parent=styles['Heading2'],
        fontSize=22,
        textColor=accent_color,
        spaceAfter=20,
        spaceBefore=30,
        fontName='Helvetica-Bold',
        borderWidth=2,
        borderColor=secondary_color,
        borderPadding=12,
        backColor=HexColor('#F0F6FF')
    )
    
    # Custom subheading style
    sub_heading_style = ParagraphStyle(
        'SubHeading',
        parent=styles['Heading3'],
        fontSize=16,
        textColor=primary_color,
        spaceAfter=10,
        spaceBefore=15,
        fontName='Helvetica-Bold'
    )
    
   # Custom body style - larger for mobile
    body_style = ParagraphStyle(
        'CustomBody',
        parent=styles['Normal'],
        fontSize=18,
        textColor=text_color,
        spaceAfter=12,
        leading=20,
        alignment=TA_JUSTIFY,
        fontName='Helvetica'
    )
    
    # Custom bullet style
    bullet_style = ParagraphStyle(
        'BulletStyle',
        parent=styles['Normal'],
        fontSize=16,
        textColor=text_color,
        spaceAfter=6,
        leading=16,
        leftIndent=20,
        bulletIndent=10,
        fontName='Helvetica'
    )
    
    # Custom insight style with celestial theme
    insight_style = ParagraphStyle(
        'InsightStyle',
        parent=styles['Normal'],
        fontSize=16,
        textColor=text_color,
        spaceAfter=12,
        leading=18,
        alignment=TA_JUSTIFY,
        fontName='Helvetica-Oblique',
        backColor=HexColor('#F0F6FF'),  # Soft celestial blue background
        borderWidth=1,
        borderColor=secondary_color,
        borderPadding=10
    )
    
    # Custom footer style
    footer_style = ParagraphStyle(
        'FooterStyle',
        parent=styles['Normal'],
        fontSize=14,
        textColor=HexColor('#7F8C8D'),
        spaceAfter=12,
        spaceBefore=20,
        alignment=TA_CENTER,
        fontName='Helvetica-Oblique'
    )
    
    story = []
    
    # Process the report text
    lines = report_text.split("\n")
    
    for i, line in enumerate(lines):
        line = line.strip()
        if not line:
            continue
            
        # Title
        if "NODAL PATHWAYS REPORT" in line:
            story.append(Paragraph(line, title_style))
            story.append(Spacer(1, 20))
        
        # Skip separator lines
        elif line.startswith("=") or line.startswith("-"):
            continue
        
        # Main sections
        elif any(keyword in line for keyword in ["NORTH NODE GUIDANCE", "SOUTH NODE AWARENESS", "COMBINED INSIGHT", "YOUR NODES AND SUN SIGN", "YOUR NODES AND MOON SIGN", "YOUR NODES AND RISING SIGN", "INTEGRATED GUIDANCE"]):
            story.append(Paragraph(line, main_heading_style))
        
        # Subsections
        elif any(keyword in line for keyword in ["North Node in", "South Node in", "House guidance:", "Areas to be mindful"]):
            story.append(Paragraph(line, sub_heading_style))
        
        # Bullet points
        elif line.startswith("•"):
            formatted_line = line.replace("•", "&#8226;")  # Use proper bullet character
            story.append(Paragraph(formatted_line, bullet_style))
        
        # Combined insight content (special formatting)
        elif "journey involves moving from" in line or "Use your South Node experience" in line:
            story.append(Paragraph(line, insight_style))
        
        # Footer/disclaimer
        elif "Astrology is interpretive" in line:
            story.append(Spacer(1, 30))
            story.append(Paragraph(line, footer_style))
        
        # Regular body text
        else:
            story.append(Paragraph(line, body_style))
    
    # Build the PDF
    doc.build(story)
    return filepath

def send_report_email(email, report_text, pdf_path):
    """Send report via email"""
    try:
        with open(pdf_path, 'rb') as f:
            pdf_content = base64.b64encode(f.read()).decode('utf-8')
        
        email_response = resend.Emails.send({
            "from": "reports@api.nodalpathways.com",
            "to": email,
            "subject": "Your Nodal Pathways Report",
            "html": """
            <h2>Your Nodal Pathways Report is Ready!</h2>
            <p>Thank you for your purchase. Your personalized nodal pathways report is attached as a PDF.</p>
            <p>This report provides guidance on your North Node (growth direction) and South Node (patterns to be mindful of).</p>
            <p>Best regards,<br>Nodal Pathways</p>
            """,
            "attachments": [{
                "filename": "nodal_pathways_report.pdf",
                "content": pdf_content
            }]
        })
        
        print("Email sent successfully:", email_response)
        
        # Clean up temp file
        try:
            os.remove(pdf_path)
        except:
            pass
            
        return email_response
    except Exception as e:
        print("Detailed email error:", str(e))
        print("Error type:", type(e).__name__)
        raise Exception(f"Email sending error: {str(e)}")

# Your existing endpoints
@app.route('/nodes', methods=['POST'])
def get_nodes():
    try:
        data = request.json
        chart_data = calculate_nodes_and_big_three(
            data['date'], 
            data.get('time', '12:00'),
            data['city'],
            data['country']
        )
        return jsonify(chart_data)
    except Exception as e:
        return jsonify({"error": str(e)}), 400

@app.route('/report', methods=['POST'])
def make_report():
    try:
        data = request.json
        report_text = data['report']
        
        file_id = str(uuid.uuid4())
        filename = f"nodal_report_{file_id}.pdf"
        filepath = f"/tmp/{filename}"
        
        styles = getSampleStyleSheet()
        doc = SimpleDocTemplate(filepath)
        story = []
        
        for paragraph in report_text.split("\n"):
            if paragraph.strip():
                story.append(Paragraph(paragraph, styles['Normal']))
                story.append(Spacer(1, 12))
        
        doc.build(story)
        temp_files[file_id] = filepath
        
        download_url = f"{request.url_root}download/{file_id}"
        
        return jsonify({
            "download_url": download_url,
            "filename": filename
        })
        
    except Exception as e:
        return jsonify({"error": str(e)}), 400

# New endpoint for Google Forms processing
@app.route('/process-form', methods=['POST'])
def process_form():
    """Process Google Form submission and email report"""
    print("=== PROCESS FORM STARTED ===")
    try:
        data = request.json
        print(f"Received data: {data}")
        
        print("=== ABOUT TO CALCULATE CHART DATA ===")
        chart_data = calculate_nodes_and_big_three(
            data['Birth Date'],
            data.get('Birth Time', '12:00'),
            data['City'],
            data['Country']
        )
        print(f"Chart calculation completed: {chart_data}")
        
        print("=== ABOUT TO GENERATE REPORT ===")
        report_text = generate_full_report(chart_data)
        print("Report generation completed")
        
        print("=== ABOUT TO CREATE PDF ===")
        pdf_path = create_pdf_report(report_text)
        print(f"PDF created at {pdf_path}")
        
        print("=== ABOUT TO SEND EMAIL ===")
        send_report_email(
            data['Email'],
            report_text,
            pdf_path
        )
        print("Email sent successfully")
        
        return jsonify({"status": "success", "message": "Report sent successfully"})
    except Exception as e:
        print(f"DETAILED ERROR: {str(e)}")
        import traceback
        print(f"FULL TRACEBACK: {traceback.format_exc()}")
        return jsonify({"error": str(e)}), 400

@app.route('/download/<file_id>', methods=['GET'])
def download_file(file_id):
    try:
        if file_id not in temp_files:
            return jsonify({"error": "File not found"}), 404
            
        filepath = temp_files[file_id]
        
        if not os.path.exists(filepath):
            return jsonify({"error": "File no longer available"}), 404
            
        return send_file(
            filepath,
            as_attachment=True,
            download_name="nodal_pathways_report.pdf",
            mimetype="application/pdf"
        )
        
    except Exception as e:
        return jsonify({"error": str(e)}), 400

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=5000)
