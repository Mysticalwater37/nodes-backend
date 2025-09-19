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
from knowledge_base import KNOWLEDGE_BASE
import knowledge_base as kb
from weasyprint import HTML
import openai 
from playwright.sync_api import sync_playwright
print(">>> LOADED KNOWLEDGE_BASE KEYS:", list(kb.KNOWLEDGE_BASE.keys()))
print(">>> LOADED FROM FILE:", kb.__file__)
app = Flask(__name__)
import logging
logging.basicConfig(level=logging.DEBUG)
openai.api_key = os.getenv("OPENAI_API_KEY")

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

def calculate_nodes_and_big_three(date, time, location):
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
            "San Rafael, USA": (37.9735, -122.5311),
            "San Rafael, CA, USA": (37.9735, -122.5311),
        }
        
        # Try to find coordinates in cache first
        latitude = None
        longitude = None
        
        # Check if location matches any cached cities
        for cached_city, coords in CITY_COORDS.items():
            if location.lower() in cached_city.lower() or cached_city.lower() in location.lower():
                latitude, longitude = coords
                print(f"Using cached coordinates for {cached_city}: {latitude}, {longitude}")
                break
        
        # If not in cache, try geocoding
        if latitude is None:
            print(f"Location '{location}' not in cache, attempting geocoding...")
            geolocator = Nominatim(user_agent="astro_app")
            location_data = geolocator.geocode(location)
            
            if not location_data:
                raise ValueError(f"Could not find location: {location}")
            
            latitude = location_data.latitude
            longitude = location_data.longitude
            print(f"Geocoded {location}: {latitude}, {longitude}")
        
        # Parse birth date and time
        birth_dt = datetime.strptime(date, '%Y-%m-%d')
        birth_time_dt = datetime.strptime(time, '%H:%M').time()
        
        # Get timezone
        tf = TimezoneFinder()
        timezone_str = tf.timezone_at(lat=latitude, lng=longitude)
        
        if not timezone_str:
            timezone_str = 'UTC'
        
        # Create timezone-aware datetime
        local_tz = pytz.timezone(timezone_str)
        birth_datetime = local_tz.localize(
            datetime.combine(birth_dt.date(), birth_time_dt)
        )
        
        # Convert to UTC
        utc_datetime = birth_datetime.astimezone(pytz.UTC)
        
        # Calculate Julian day
        julian_day = swe.julday(
            utc_datetime.year,
            utc_datetime.month, 
            utc_datetime.day,
            utc_datetime.hour + utc_datetime.minute/60.0
        )
        
        # Calculate planetary positions
        sun_pos = swe.calc_ut(julian_day, swe.SUN)[0][0]
        moon_pos = swe.calc_ut(julian_day, swe.MOON)[0][0]
        
        # Calculate Ascendant
        houses = swe.houses(julian_day, latitude, longitude)[1]
        ascendant = houses[0]
        
        # Calculate lunar nodes
        north_node_pos = swe.calc_ut(julian_day, swe.MEAN_NODE)[0][0]
        south_node_pos = (north_node_pos + 180) % 360
        
        # Convert positions to signs
        def degree_to_sign(degree):
            signs = ["Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo",
                    "Libra", "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces"]
            sign_index = int(degree // 30)
            return signs[sign_index]
        
        result = {
            'sun_sign': degree_to_sign(sun_pos),
            'moon_sign': degree_to_sign(moon_pos),
            'rising_sign': degree_to_sign(ascendant),
            'north_node': {
                'sign': degree_to_sign(north_node_pos),
                'degree': north_node_pos % 30
            },
            'south_node': {
                'sign': degree_to_sign(south_node_pos),
                'degree': south_node_pos % 30
            }
        }
        
        print(f"Chart calculation successful: {result}")
        return result
        
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
    north_node_sign = chart_data.get('north_node_sign', 'Unknown')
    south_node_sign = chart_data.get('south_node_sign', 'Unknown')
    
    prompt = f"""Write a personalized astrological report for {first_name} with these placements:
Sun in {sun_sign}, Moon in {moon_sign}, Rising {rising_sign}, North Node {north_node_sign}, South Node {south_node_sign}

Create exactly these HTML sections:
<h2>Your Cosmic Blueprint</h2>
<p>[2-3 paragraphs introducing {first_name} to their unique chart combination]</p>

<h2>Your Inner Light: Sun in {sun_sign}</h2>
<p>[2 paragraphs about {first_name}'s core identity and {sun_sign} traits]</p>

<h2>Your Emotional Nature: Moon in {moon_sign}</h2>
<p>[2 paragraphs about {first_name}'s emotional patterns and {moon_sign} qualities]</p>

<h2>Your Rising Persona: {rising_sign} Ascending</h2>
<p>[2 paragraphs about how {first_name} presents to the world]</p>

<h2>Your Soul's Journey: The Nodal Pathway</h2>
<p>[3 paragraphs about {first_name}'s growth from {south_node_sign} to {north_node_sign}]</p>

<h2>Integration and Growth</h2>
<p>[2-3 paragraphs of guidance for {first_name}]</p>

Use {first_name}'s name naturally throughout. Professional counseling tone."""

    try:
        response = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=2500,
            temperature=0.7
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        print(f"OpenAI error: {e}")
        return f"<h2>Your Personal Report</h2><p>Hello {first_name}, please contact support.</p>"

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

def create_html_report(chart_data, ai_content, first_name):
    """Generate HTML report using AI content and app-inspired styling"""
    try:
        # Create chart basics section
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
        
        # Create the complete HTML with app-inspired styling
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <title>Nodal Pathways Report - {first_name}</title>
            <style>
                @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600&family=Playfair+Display:wght@400;500;600&display=swap');
                
                * {{
                    margin: 0;
                    padding: 0;
                    box-sizing: border-box;
                }}
                
                @page {{
                    size: A4;
                    margin: 0.75in;
                }}
                
                body {{
                    font-family: 'Inter', sans-serif;
                    font-size: 16px;
                    line-height: 1.7;
                    background: linear-gradient(135deg, #4a5568 0%, #2d3748 30%, #1a202c 100%);
                    color: #ffffff;
                    min-height: 100vh;
                    padding: 30px 0;
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
                    padding: 50px 40px;
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
                    font-size: 3.2em;
                    color: #edd598;
                    margin-bottom: 20px;
                    font-weight: 500;
                    letter-spacing: -1px;
                    position: relative;
                    z-index: 1;
                }}
                
                .header .subtitle {{
                    font-size: 1.3em;
                    color: #cbd5e0;
                    font-weight: 400;
                    position: relative;
                    z-index: 1;
                    opacity: 0.9;
                    text-align: center;
                }}
                
                .chart-basics {{
                    margin: 40px;
                    padding: 0;
                }}
                
                .chart-basics h3 {{
                    font-family: 'Playfair Display', serif;
                    color: #edd598;
                    text-align: center;
                    margin-bottom: 30px;
                    font-size: 1.8em;
                    font-weight: 500;
                }}
                
                .basics-grid {{
                    display: grid;
                    grid-template-columns: 1fr 1fr;
                    gap: 15px;
                }}
                
                .basic-item {{
                    background: rgba(255, 255, 255, 0.05);
                    border: 1px solid rgba(237, 213, 152, 0.2);
                    padding: 18px 22px;
                    border-radius: 12px;
                    font-size: 1.1em;
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
                    padding: 40px;
                }}
                
                h2 {{
                    font-family: 'Playfair Display', serif;
                    color: #edd598;
                    font-size: 2.2em;
                    margin: 45px 0 30px 0;
                    text-align: center;
                    font-weight: 500;
                    position: relative;
                    letter-spacing: -0.5px;
                }}
                
                h2::before,
                h2::after {{
                    content: "✦";
                    margin: 0 20px;
                    font-size: 0.7em;
                    opacity: 0.7;
                    color: #edd598;
                }}
                
                p {{
                    margin-bottom: 22px;
                    color: #e2e8f0;
                    text-align: justify;
                    font-size: 1.15em;
                    line-height: 1.8;
                    text-indent: 1.5em;
                    font-weight: 400;
                }}
                
                p:first-of-type {{
                    margin-top: 20px;
                }}
                
                .footer {{
                    text-align: center;
                    padding: 40px;
                    background: linear-gradient(135deg, #2d3748 0%, #1a202c 100%);
                    color: #a0aec0;
                    font-size: 1em;
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
                    font-size: 1.4em;
                    margin-bottom: 15px;
                    font-weight: 500;
                }}
                
                .disclaimer {{
                    background: rgba(237, 213, 152, 0.1);
                    border: 1px solid rgba(237, 213, 152, 0.3);
                    border-radius: 16px;
                    padding: 30px;
                    margin: 40px;
                    color: #cbd5e0;
                    text-align: center;
                    line-height: 1.7;
                    font-size: 0.95em;
                    backdrop-filter: blur(10px);
                }}
                
                .disclaimer strong {{
                    color: #edd598;
                    font-weight: 600;
                }}
                
                /* Mobile responsiveness */
                @media screen and (max-width: 768px) {{
                    body {{
                        font-size: 18px;
                        padding: 20px 10px;
                    }}
                    
                    .container {{
                        border-radius: 16px;
                        margin: 0;
                    }}
                    
                    .header {{
                        padding: 40px 30px;
                    }}
                    
                    .header h1 {{
                        font-size: 2.8em;
                    }}
                    
                    .header .subtitle {{
                        font-size: 1.2em;
                    }}
                    
                    .basics-grid {{
                        grid-template-columns: 1fr;
                        gap: 15px;
                    }}
                    
                    .basic-item {{
                        font-size: 1.2em;
                        padding: 22px;
                    }}
                    
                    .chart-basics,
                    .report-content,
                    .disclaimer {{
                        margin: 25px 20px;
                        padding: 30px 25px;
                    }}
                    
                    h2 {{
                        font-size: 2em;
                        margin: 35px 0 25px 0;
                    }}
                    
                    h2::before,
                    h2::after {{
                        display: none;
                    }}
                    
                    p {{
                        font-size: 1.25em;
                        line-height: 1.9;
                        margin-bottom: 25px;
                    }}
                }}
                
                @media screen and (max-width: 480px) {{
                    body {{
                        font-size: 20px;
                    }}
                    
                    .header h1 {{
                        font-size: 2.4em;
                    }}
                    
                    p {{
                        font-size: 1.3em;
                        line-height: 2;
                    }}
                    
                    .basic-item {{
                        font-size: 1.3em;
                    }}
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>⭐ Nodal Pathways ⭐</h1>
                    <div class="subtitle">Personalized Astrological Report for {first_name}</div>
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
                    <div class="logo">⭐ Nodal Pathways ⭐</div>
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
        data = request.json
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
@app.route('/process-form', methods=['POST'])
def process_form():
    """Process Google Form submission and email report"""
    print("=== PROCESS FORM STARTED ===")
    try:
        data = request.json
        print(f"Received data: {data}")
        
        print("=== ABOUT TO CALCULATE CHART DATA ===")
        city = data.get('City', '')
        state = data.get('State', '')  
        country = data.get('Country', '')

        if state:
            full_location = f"{city}, {state}, {country}"
        else:
            full_location = f"{city}, {country}"

        chart_data = calculate_nodes_and_big_three(
            data['Birth Date'],
            data.get('Birth Time', '12:00'),
            full_location
        )

        print(f"Chart calculation completed: {chart_data}")
        
        print("=== ABOUT TO GENERATE AI REPORT ===")
        first_name = data.get('First Name', 'Friend')
        ai_content = generate_ai_report(chart_data, first_name)
        html_content = create_html_report(chart_data, ai_content, first_name)
        
        print("=== ABOUT TO CREATE PDF FROM HTML ===")
        pdf_bytes = generate_pdf_with_playwright(html_content)
        pdf_path = f"report_{uuid.uuid4()}.pdf"
        with open(pdf_path, 'wb') as f:
             f.write(pdf_bytes)
        
        print("=== ABOUT TO SEND EMAIL ===")
        send_report_email(
            data['Email'],
            html_content,
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
