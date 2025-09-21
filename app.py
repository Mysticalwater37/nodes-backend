# ===== Imports =====
from flask import Flask, request, jsonify, send_file
import swisseph as swe
from geopy.geocoders import Nominatim
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
import re

from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib.colors import HexColor
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_LEFT
from io import BytesIO

# ===== App Setup =====
app = Flask(__name__)
logging.basicConfig(level=logging.DEBUG)

# ===== API Keys =====
openai.api_key = os.getenv("OPENAI_API_KEY")
resend.api_key = os.getenv("RESEND_API_KEY")

# ===== Ephemeris Path =====
swe.set_ephe_path('.')  

# ===== Global Storage =====
SIGNS = [
    "Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo",
    "Libra", "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces"
]
temp_files = {}

# ===== Debug Routes =====
@app.route('/test', methods=['GET'])
def test():
    print("HIT /test route")
    return jsonify({"status": "ok"})
@app.route('/ping', methods=['POST'])
def ping():
    print("HIT /ping")
    print(f"Content-Type: {request.content_type}")
    print(f"Headers: {dict(request.headers)}")
    print(f"Raw body: {request.data}")
    return jsonify({"parsed": request.get_json(silent=True)})


from geopy.geocoders import Nominatim

def calculate_nodes_and_big_three(date, time, location):
    try:
        latitude, longitude = None, None

        # Nominatim geocoder
        try:
            geolocator = Nominatim(user_agent="nodes_backend/1.0")
            loc = geolocator.geocode(location, timeout=10)
            if loc:
                latitude = loc.latitude
                longitude = loc.longitude
                print(f"Geocoded {location}: {latitude}, {longitude}")
            else:
                raise ValueError(f"Could not find location: {location}")
        except Exception as e:
            print(f"Nominatim geocoding error: {e}")
            raise

        # --- your existing astrology + timezone code goes here ---
        # (parse birth date, find timezone, compute chart, etc.)

    except Exception as e:
        print(f"Error in chart calculation: {e}")
        return None

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

        # North Node - bulletproof lookups
        report.append("NORTH NODE GUIDANCE")
        report.append("-" * 20)
        north_sign_data = KNOWLEDGE_BASE["north_nodes"][north_node["sign"]]
        
        # Handle multiple possible key names for meaning
        north_meaning = (north_sign_data.get("meaning") or 
                        north_sign_data.get("north_meaning") or 
                        "This placement guides your soul's growth.")
        
        # Handle multiple possible key names for guidance
        north_guidance = (north_sign_data.get("guidance") or 
                         north_sign_data.get("north_guidance_sign") or 
                         north_sign_data.get("north_guidance") or [])
        
        report.append(
            f"Your North Node in {north_node['sign']} reveals your soul's primary growth direction. "
            f"{north_meaning} This placement asks you to embrace qualities that may feel "
            f"unfamiliar or challenging at first, but will ultimately lead to fulfillment."
        )
        report.append("")

        if north_guidance:
            report.append("To develop these qualities, focus on practical steps:")
            for i, guidance in enumerate(north_guidance):
                guidance_clean = guidance.rstrip('.').lower()
                if i == 0:
                    report.append(f"Start by {guidance_clean}.")
                elif i == len(north_guidance) - 1:
                    report.append(f"Most importantly, {guidance_clean}.")
                else:
                    report.append(f"Additionally, {guidance_clean}.")
            report.append("")

        # House Guidance - bulletproof lookups
        if north_node.get("house"):
            house_data = KNOWLEDGE_BASE["houses"][north_node["house"]]
            
            # Handle multiple possible key names for house meaning
            house_meaning = (house_data.get("meaning") or 
                           house_data.get("focus") or 
                           house_data.get("north_meaning") or 
                           "This house placement adds depth to your growth.")
            
            # Handle multiple possible key names for house guidance
            house_guidance = (house_data.get("guidance") or 
                            house_data.get("north_guidance_house") or 
                            house_data.get("north_guidance") or [])
            
            report.append(f"Your North Node's placement in the {north_node['house']}th house adds depth. "
                          f"{house_meaning} This shows the life areas where your {north_node['sign']} growth "
                          f"will be most transformative.")
            
            if house_guidance:
                for i, guidance in enumerate(house_guidance):
                    guidance_clean = guidance.rstrip('.').lower()
                    if i == 0:
                        report.append(f"Begin by learning to {guidance_clean}.")
                    elif i == len(house_guidance) - 1:
                        report.append(f"Most importantly, focus on how to {guidance_clean}.")
                    else:
                        report.append(f"Practice {guidance_clean}.")
                report.append("")

        # South Node - bulletproof lookups
        report.append("SOUTH NODE AWARENESS")
        report.append("-" * 20)
        south_sign_data = KNOWLEDGE_BASE["south_nodes"][south_node["sign"]]
        
        # Handle multiple possible key names for patterns
        south_patterns = (south_sign_data.get("patterns") or 
                         south_sign_data.get("south_patterns") or 
                         south_sign_data.get("meaning") or 
                         "familiar patterns from past experiences")
        
        # Handle multiple possible key names for south guidance
        south_guidance = (south_sign_data.get("guidance") or 
                         south_sign_data.get("south_guidance") or [])
        
        report.append(
            f"Your South Node in {south_node['sign']} represents gifts and patterns from past lifetimes. "
            f"The challenge lies in {south_patterns.lower()} — familiar tendencies that can hold "
            f"you back if overused."
        )
        
        if south_guidance:
            report.append("To find balance, practice awareness in these areas:")
            for guidance in south_guidance:
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

def generate_ai_report(chart_data, first_name):
    sun_sign = chart_data.get('sun_sign', 'Unknown')
    moon_sign = chart_data.get('moon_sign', 'Unknown') 
    rising_sign = chart_data.get('rising_sign', 'Unknown')
    north_node_sign = chart_data.get('north_node', {}).get('sign', 'Unknown')
    south_node_sign = chart_data.get('south_node', {}).get('sign', 'Unknown')
    
    prompt = f"""Write a personalized astrological report for {first_name} with these placements:
Sun in {sun_sign}, Moon in {moon_sign}, Rising {rising_sign}, North Node {north_node_sign}, South Node {south_node_sign}
Create exactly these sections:
SECTION: Your Cosmic Blueprint
[2-3 paragraphs introducing {first_name} to their unique chart combination]
SECTION: Your Inner Light - Sun in {sun_sign}
[2 paragraphs about {first_name}'s core identity and {sun_sign} traits]
SECTION: Your Emotional Nature - Moon in {moon_sign}
[2 paragraphs about {first_name}'s emotional patterns and {moon_sign} qualities]
SECTION: Your Rising Persona - {rising_sign} Ascending
[2 paragraphs about how {first_name} presents to the world]
SECTION: Your Soul's Journey - The Nodal Pathway
[3 paragraphs about {first_name}'s growth from {south_node_sign} to {north_node_sign}]
SECTION: Integration and Growth
[2-3 paragraphs of guidance for {first_name}]
Use {first_name}'s name naturally throughout. Professional counseling tone."""
    
    try:
        response = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=2500,
            temperature=0.7
        )
        ai_content = response.choices[0].message.content.strip()
        return ai_content
    except Exception as e:
        print(f"OpenAI error: {e}")
        return f"SECTION: Your Personal Report\nHello {first_name}, please contact support for your personalized report."

def create_pdf_report(report_text):
    """Create a beautifully formatted PDF with dark blue theme matching your brand"""
    filename = f"nodal_report_{uuid.uuid4()}.pdf"
    filepath = f"/tmp/{filename}"
    
    # Create document with proper margins
    doc = SimpleDocTemplate(
        filepath, 
        pagesize=A4,
        rightMargin=0.75*inch, 
        leftMargin=0.75*inch,
        topMargin=1*inch, 
        bottomMargin=1*inch
    )
    
    # Define color scheme to match your beautiful blue theme
    dark_bg = HexColor('#1a202c')      # Dark navy background
    gold_color = HexColor('#edd598')   # Gold for headers
    white = HexColor('#1a202c')        # Dark text for body text
    light_blue = HexColor('#1a202c')   # Same as body text for maximum visibility
    accent_blue = HexColor('#1a202c')  # Same as body text
    
    # Get base styles
    styles = getSampleStyleSheet()
    
    # Title style - large gold header
    title_style = ParagraphStyle(
        'CustomTitle',
        fontSize=36,
        textColor=gold_color,
        spaceAfter=30,
        spaceBefore=20,
        alignment=TA_CENTER,
        fontName='Helvetica-Bold',
        leading=40
    )
    
    # Subtitle style 
    subtitle_style = ParagraphStyle(
        'Subtitle',
        fontSize=18,
        textColor=light_blue,
        spaceAfter=40,
        alignment=TA_CENTER,
        fontName='Helvetica',
        leading=22
    )
    
    # Section header style - gold and prominent
    section_style = ParagraphStyle(
        'SectionHeader',
        fontSize=24,
        textColor=gold_color,
        spaceAfter=20,
        spaceBefore=40,
        alignment=TA_CENTER,
        fontName='Helvetica-Bold',
        leading=28,
        borderWidth=2,
        borderColor=gold_color,
        borderPadding=15,
        backColor=HexColor('#2d3748')  # Slightly lighter dark background
    )
    
    # Body text style - white text, larger font
    body_style = ParagraphStyle(
        'Body',
        fontSize=16,
        textColor=white,
        spaceAfter=18,
        spaceBefore=5,
        alignment=TA_JUSTIFY,
        fontName='Helvetica',
        leading=24,
        leftIndent=10,
        rightIndent=10
    )
    
    # Chart essentials style
    chart_style = ParagraphStyle(
        'ChartEssentials',
        fontSize=14,
        textColor=light_blue,
        spaceAfter=8,
        alignment=TA_CENTER,
        fontName='Helvetica',
        leading=20
    )
    
    # Disclaimer style
    disclaimer_style = ParagraphStyle(
        'Disclaimer',
        fontSize=12,
        textColor=light_blue,
        spaceAfter=20,
        spaceBefore=30,
        alignment=TA_CENTER,
        fontName='Helvetica-Oblique',
        leading=16,
        leftIndent=40,
        rightIndent=40
    )
    
    story = []
    
    # Add title page elements
    story.append(Spacer(1, 0.5*inch))
    story.append(Paragraph("Nodal Pathways", title_style))
    story.append(Paragraph("Personalized Astrological Report", subtitle_style))
    
    # Parse the report content
    sections = report_text.split('SECTION:')
    
    for section in sections:
        if not section.strip():
            continue
            
        lines = section.strip().split('\n')
        if not lines:
            continue
            
        # First line is the section header
        header = lines[0].strip()
        
        # Add section header with beautiful styling
        story.append(Paragraph(header, section_style))
        
        # Process the content paragraphs
        content_lines = []
        for line in lines[1:]:
            if line.strip():
                content_lines.append(line.strip())
        
        # Group lines into paragraphs (assuming paragraphs are separated by empty lines)
        current_paragraph = []
        for line in content_lines:
            if line:
                current_paragraph.append(line)
            else:
                if current_paragraph:
                    para_text = ' '.join(current_paragraph)
                    story.append(Paragraph(para_text, body_style))
                    current_paragraph = []
        
        # Add final paragraph if exists
        if current_paragraph:
            para_text = ' '.join(current_paragraph)
            story.append(Paragraph(para_text, body_style))
    
    # Add footer elements
    story.append(Spacer(1, 0.5*inch))
    story.append(Paragraph("Nodal Pathways", section_style))
    story.append(Paragraph("Guiding you on your cosmic journey of self-discovery", disclaimer_style))
    
    # Build the PDF
    doc.build(story)
    return filepath
    
def create_html_report(chart_data, ai_content, first_name):
    """Generate HTML report with dark blue background and properly formatted headers"""
    try:
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
        
        # Create the complete HTML with dark blue background and large readable fonts
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <title>Nodal Pathways Report - {first_name}</title>
            <style>
                @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&family=Playfair+Display:wght@400;500;600&display=swap');
                
                * {{
                    margin: 0;
                    padding: 0;
                    box-sizing: border-box;
                }}
                
                @page {{
                    size: A4;
                    margin: 1.5in 0.75in 1in 0.75in;
                }}
                
                body {{
                    font-family: 'Inter', sans-serif;
                    font-size: 22px;
                    line-height: 1.8;
                    background: linear-gradient(135deg, #4a5568 0%, #2d3748 30%, #1a202c 100%);
                    color: #ffffff;
                    min-height: 100vh;
                    padding: 40px 0;
                    orphans: 3;
                    widows: 3;
                }}
                
                .container {{
                    max-width: 100%;
                    margin: 0 auto;
                    background: rgba(26, 32, 44, 0.95);
                    border-radius: 24px;
                    overflow: hidden;
                    border: 1px solid rgba(237, 213, 152, 0.2);
                    box-shadow: 0 25px 50px rgba(0, 0, 0, 0.3);
                }}
                
                .header {{
                    text-align: center;
                    padding: 60px 40px 40px 40px;
                    background: linear-gradient(135deg, #2d3748 0%, #1a202c 100%);
                    position: relative;
                    overflow: hidden;
                }}
                
                .header::before {{
                    content: '';
                    position: absolute;
                    top: 0;
                    left: 0;
                    right: 0;
                    bottom: 0;
                    background: radial-gradient(circle at 30% 20%, rgba(237, 213, 152, 0.1) 0%, transparent 50%),
                                radial-gradient(circle at 70% 80%, rgba(237, 213, 152, 0.08) 0%, transparent 50%);
                    pointer-events: none;
                }}
                
                .header h1 {{
                    font-family: 'Playfair Display', serif;
                    font-size: 3.8em;
                    color: #edd598;
                    margin-bottom: 20px;
                    font-weight: 500;
                    letter-spacing: -1px;
                    position: relative;
                    z-index: 1;
                }}
                
                .header .subtitle {{
                    font-size: 1.5em;
                    color: #cbd5e0;
                    font-weight: 400;
                    position: relative;
                    z-index: 1;
                    opacity: 0.9;
                    text-align: center;
                    line-height: 1.4;
                }}
                
                .chart-basics {{
                    margin: 50px 40px;
                    padding: 0;
                }}
                
                .chart-basics h3 {{
                    font-family: 'Playfair Display', serif;
                    color: #edd598;
                    text-align: center;
                    margin-bottom: 35px;
                    font-size: 2.2em;
                    font-weight: 500;
                }}
                
                .basics-grid {{
                    display: grid;
                    grid-template-columns: 1fr 1fr;
                    gap: 20px;
                }}
                
                .basic-item {{
                    background: rgba(255, 255, 255, 0.05);
                    border: 1px solid rgba(237, 213, 152, 0.2);
                    padding: 28px 22px;
                    border-radius: 12px;
                    font-size: 1.3em;
                    font-weight: 400;
                    color: #e2e8f0;
                    transition: all 0.2s ease;
                    backdrop-filter: blur(10px);
                }}
                
                .basic-item:hover {{
                    background: rgba(255, 255, 255, 0.08);
                    border-color: rgba(237, 213, 152, 0.3);
                    transform: translateY(-1px);
                }}
                
                .basic-item strong {{
                    color: #edd598;
                    font-weight: 600;
                    display: inline-block;
                    margin-right: 8px;
                }}
                
                .report-content {{
                    padding: 50px 40px;
                }}
                
                h2 {{
                    font-family: 'Playfair Display', serif;
                    color: #edd598;
                    font-size: 2.6em;
                    margin: 80px 0 35px 0;
                    text-align: center;
                    font-weight: 500;
                    position: relative;
                    letter-spacing: -0.5px;
                    line-height: 1.3;
                    page-break-after: avoid;
                    break-after: avoid;
                }}
                
                .report-content > *:first-child {{
                    margin-top: 80px !important;
                }}
                
                p {{
                    margin-bottom: 28px;
                    color: #e2e8f0;
                    text-align: justify;
                    font-size: 1.4em;
                    line-height: 1.9;
                    text-indent: 1.5em;
                    font-weight: 400;
                }}
                
                p:first-of-type {{
                    margin-top: 20px;
                }}
                
                .footer {{
                    text-align: center;
                    padding: 50px 40px;
                    background: linear-gradient(135deg, #2d3748 0%, #1a202c 100%);
                    color: #a0aec0;
                    font-size: 1.2em;
                    position: relative;
                }}
                
                .footer::before {{
                    content: '';
                    position: absolute;
                    top: 0;
                    left: 0;
                    right: 0;
                    height: 2px;
                    background: linear-gradient(90deg, transparent 0%, #edd598 50%, transparent 100%);
                }}
                
                .footer .logo {{
                    font-family: 'Playfair Display', serif;
                    color: #edd598;
                    font-size: 1.6em;
                    margin-bottom: 15px;
                    font-weight: 500;
                }}
                
                .disclaimer {{
                    background: rgba(237, 213, 152, 0.1);
                    border: 1px solid rgba(237, 213, 152, 0.3);
                    border-radius: 16px;
                    padding: 35px;
                    margin: 50px 40px;
                    color: #cbd5e0;
                    text-align: center;
                    line-height: 1.8;
                    font-size: 1.2em;
                    backdrop-filter: blur(10px);
                }}
                
                .disclaimer strong {{
                    color: #edd598;
                    font-weight: 600;
                }}
                
                /* Mobile responsiveness - Very large fonts */
                @media screen and (max-width: 768px) {{
                    body {{
                        font-size: 28px;
                        padding: 20px 10px;
                    }}
                    
                    .container {{
                        border-radius: 16px;
                        margin: 0;
                    }}
                    
                    .header {{
                        padding: 50px 30px 35px 30px;
                    }}
                    
                    .header h1 {{
                        font-size: 3.2em;
                    }}
                    
                    .header .subtitle {{
                        font-size: 1.4em;
                    }}
                    
                    .chart-basics {{
                        margin: 35px 25px;
                    }}
                    
                    .chart-basics h3 {{
                        font-size: 2em;
                        margin-bottom: 25px;
                    }}
                    
                    .basics-grid {{
                        grid-template-columns: 1fr;
                        gap: 15px;
                    }}
                    
                    .basic-item {{
                        font-size: 1.5em;
                        padding: 28px 22px;
                    }}
                    
                    .report-content {{
                        padding: 40px 25px;
                    }}
                    
                    h2 {{
                        font-size: 2.4em;
                        margin: 60px 0 30px 0;
                    }}
                    
                    p {{
                        font-size: 1.6em;
                        line-height: 2.1;
                        margin-bottom: 32px;
                        text-indent: 0;
                    }}
                    
                    .footer {{
                        padding: 40px 25px;
                        font-size: 1.3em;
                    }}
                    
                    .disclaimer {{
                        margin: 40px 20px;
                        padding: 30px 25px;
                        font-size: 1.4em;
                    }}
                }}
                
                @media screen and (max-width: 480px) {{
                    body {{
                        font-size: 30px;
                    }}
                    
                    .header h1 {{
                        font-size: 2.8em;
                    }}
                    
                    p {{
                        font-size: 1.7em;
                        line-height: 2.2;
                    }}
                    
                    .basic-item {{
                        font-size: 1.6em;
                    }}
                    
                    h2 {{
                        font-size: 2.2em;
                    }}
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>Nodal Pathways</h1>
                    <div class="subtitle">Personalized Astrological Report<br>for {first_name}</div>
                </div>
                
                {chart_basics}
                
                <div class="report-content">
                    {ai_content}
                </div>
                
                <div class="disclaimer">
                    <strong>Disclaimer:</strong> This report is for entertainment and self-reflection purposes only. 
                    Astrological interpretations are not scientific facts and should not be used as the sole basis 
                    for important life decisions. Please consult qualified professionals for medical, legal, or 
                    financial advice.
                </div>
                
                <div class="footer">
                    <div class="logo">Nodal Pathways</div>
                    <p>Guiding you on your cosmic journey of self-discovery</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        return html_content
        
    except Exception as e:
        raise Exception(f"HTML report generation error: {str(e)}")
        
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
        print("HIT /nodes")
        data = request.get_json(silent=True)
        if not data:
            return jsonify({"error": "Failed to parse JSON body"}), 400

        city = data.get('city', '')
        state = data.get('state', '')  
        country = data.get('country', '')

        if state:
            full_location = f"{city}, {state}, {country}"
        else:
            full_location = f"{city}, {country}"

        chart_data = calculate_nodes_and_big_three(
            data['date'],
            data.get('time', '12:00'),
            full_location
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
# New endpoint for Google Forms processing
@app.route('/process-form', methods=['POST'])
def process_form():
    """Process Google Form submission and email report"""
    print("=== PROCESS FORM STARTED ===")
    print(f"Content-Type: {request.content_type}")
    print(f"Raw request data: {request.data}")

    try:
        # Safely parse JSON
        print(f"Headers: {dict(request.headers)}")
        print(f"Request data (raw): {request.data}")
        data = request.get_json(silent=True)
        if not data:
            return jsonify({"error": "Failed to parse JSON body"}), 400

        print(f"Received JSON: {data}")

        city = data.get('City', '')
        state = data.get('State', '')  
        country = data.get('Country', '')
        email = data.get('Email', 'test@example.com')
        first_name = data.get('First Name', 'Friend')
        birth_date = data.get('Birth Date', '')
        birth_time = data.get('Birth Time', '12:00')

        full_location = f"{city}, {state}, {country}" if state else f"{city}, {country}"

        chart_data = calculate_nodes_and_big_three(birth_date, birth_time, full_location)

        # Guard clause to prevent NoneType errors
        if not chart_data:
            return jsonify({"error": f"Could not geocode location: {full_location}"}), 400

        ai_content = generate_ai_report(chart_data, first_name)
        html_content = create_html_report(chart_data, ai_content, first_name)
        pdf_path = create_pdf_report(ai_content)

        send_report_email(email, html_content, pdf_path)
        print("Email sent successfully")

        return jsonify({"status": "success", "message": "Report sent successfully"})

    except Exception as e:
        import traceback
        print(f"DETAILED ERROR: {str(e)}")
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
