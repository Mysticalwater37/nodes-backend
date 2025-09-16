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

app = Flask(__name__)

# Path to Swiss Ephemeris data files
swe.set_ephe_path('.')  

# Set your Resend API key from environment variable
resend.api_key = os.getenv("RESEND_API_KEY")

SIGNS = [
    "Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo",
    "Libra", "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces"
]

# Hardcoded knowledge base (from your JSON file)
KNOWLEDGE_BASE = {
    "north_nodes": {
        "Aries": {
            "meaning": "Growth through independence, courage, and initiating new paths.",
            "guidance": [
                "Take initiative in daily decisions without seeking approval.",
                "Pursue solo projects where you set the direction.",
                "Speak up for what you want, even in low-stakes situations."
            ]
        },
        "Taurus": {
            "meaning": "Growth through stability, patience, and building lasting value.",
            "guidance": [
                "Create grounding daily rituals.",
                "Spend intentional time in nature.",
                "Focus on long-term projects rather than quick wins."
            ]
        },
        "Gemini": {
            "meaning": "Growth through curiosity, communication, and learning.",
            "guidance": [
                "Ask open questions in conversations.",
                "Read or explore a new subject regularly.",
                "Share what you learn with others in simple ways."
            ]
        },
        "Cancer": {
            "meaning": "Growth through nurturing, emotional connection, and creating a sense of home.",
            "guidance": [
                "Cook or prepare meals with intention.",
                "Spend quality time with family or chosen family.",
                "Allow yourself to feel emotions without judgment."
            ]
        },
        "Leo": {
            "meaning": "Growth through creativity, joy, and self-expression.",
            "guidance": [
                "Do something playful without worrying about outcomes.",
                "Express yourself through art, music, or performance.",
                "Celebrate your achievements without minimizing them."
            ]
        },
        "Virgo": {
            "meaning": "Growth through service, refinement, and practical mastery.",
            "guidance": [
                "Organize a small part of your environment.",
                "Improve a skill through steady practice.",
                "Support someone with thoughtful, practical help."
            ]
        },
        "Libra": {
            "meaning": "Growth through relationships, fairness, and cooperation.",
            "guidance": [
                "Listen deeply before responding in conversation.",
                "Seek compromise instead of insisting on control.",
                "Invest time in building balanced partnerships."
            ]
        },
        "Scorpio": {
            "meaning": "Growth through transformation, depth, and shared power.",
            "guidance": [
                "Reflect on what you need to release to move forward.",
                "Practice honesty in moments of vulnerability.",
                "Lean into change rather than resisting it."
            ]
        },
        "Sagittarius": {
            "meaning": "Growth through exploration, wisdom, and expanding horizons.",
            "guidance": [
                "Learn from people with different worldviews.",
                "Travel physically or through books and ideas.",
                "Reflect on your personal beliefs and how they guide you."
            ]
        },
        "Capricorn": {
            "meaning": "Growth through discipline, responsibility, and building legacy.",
            "guidance": [
                "Set one achievable long-term goal.",
                "Track your progress steadily without rushing.",
                "Take ownership of your role in group efforts."
            ]
        },
        "Aquarius": {
            "meaning": "Growth through innovation, community, and forward vision.",
            "guidance": [
                "Contribute to a cause bigger than yourself.",
                "Experiment with new tools or technology.",
                "Connect with communities that share your values."
            ]
        },
        "Pisces": {
            "meaning": "Growth through compassion, spirituality, and trust in flow.",
            "guidance": [
                "Spend time in stillness or meditation.",
                "Engage with music, art, or practices that connect you to spirit.",
                "Allow intuition to guide one small choice today."
            ]
        }
    },
    "south_nodes": {
        "Aries": {
            "patterns": "Over-focus on self, impulsivity, neglect of cooperation.",
            "guidance": [
                "Pause before acting on impulse.",
                "Consider how your choices affect others.",
                "Share leadership instead of insisting on control."
            ]
        },
        "Taurus": {
            "patterns": "Over-attachment to comfort, resistance to change.",
            "guidance": [
                "Notice when routine becomes stagnation.",
                "Experiment with small changes in daily habits.",
                "Release possessions that no longer serve you."
            ]
        },
        "Gemini": {
            "patterns": "Scattered focus, gossip, overthinking.",
            "guidance": [
                "Choose one topic to focus on instead of multitasking.",
                "Notice when curiosity turns into distraction.",
                "Practice active listening more than talking."
            ]
        },
        "Cancer": {
            "patterns": "Clinging to the past, emotional overdependence.",
            "guidance": [
                "Notice when nostalgia prevents present action.",
                "Practice emotional independence in small ways.",
                "Release responsibility for others' feelings."
            ]
        },
        "Leo": {
            "patterns": "Attention-seeking, ego-driven validation.",
            "guidance": [
                "Ask yourself if your actions are for joy or applause.",
                "Practice generosity without expectation.",
                "Celebrate others' successes with sincerity."
            ]
        },
        "Virgo": {
            "patterns": "Perfectionism, over-criticism, being stuck in details.",
            "guidance": [
                "Allow small imperfections without fixing them.",
                "Notice when helpfulness becomes control.",
                "Practice rest instead of endless productivity."
            ]
        },
        "Libra": {
            "patterns": "People-pleasing, indecision, losing self in relationships.",
            "guidance": [
                "Check in with your own needs before agreeing.",
                "Take small actions without waiting for consensus.",
                "Practice saying no with kindness."
            ]
        },
        "Scorpio": {
            "patterns": "Over-identification with secrecy, control, and drama.",
            "guidance": [
                "Share a truth you usually keep hidden.",
                "Notice when intensity substitutes for connection.",
                "Practice trust instead of control."
            ]
        },
        "Sagittarius": {
            "patterns": "Dogmatism, escapism, restless avoidance.",
            "guidance": [
                "Notice when optimism avoids responsibility.",
                "Engage with details instead of only big ideas.",
                "Commit to consistency in small ways."
            ]
        },
        "Capricorn": {
            "patterns": "Overworking, fear of vulnerability, rigid ambition.",
            "guidance": [
                "Allow yourself downtime without guilt.",
                "Share emotions instead of hiding behind tasks.",
                "Ask for help when it feels uncomfortable."
            ]
        },
        "Aquarius": {
            "patterns": "Detachment, aloofness, over-focus on intellect.",
            "guidance": [
                "Engage with emotions instead of analyzing them.",
                "Connect personally, not only in groups.",
                "Allow yourself to be influenced by others' feelings."
            ]
        },
        "Pisces": {
            "patterns": "Escapism, avoidance, lack of boundaries.",
            "guidance": [
                "Notice when daydreaming becomes avoidance.",
                "Set one clear boundary with compassion.",
                "Ground spiritual insight in practical action."
            ]
        }
    },
    "houses": {
        "1": {
            "focus": "Growth through identity, self-discovery, and authenticity.",
            "guidance": [
                "Notice moments where you feel most yourself.",
                "Experiment with self-expression in appearance or action.",
                "Prioritize personal goals before accommodating others."
            ]
        },
        "2": {
            "focus": "Growth through values, stability, and resources.",
            "guidance": [
                "Track your spending and reflect on alignment with values.",
                "Build daily habits that create security.",
                "Identify what truly feels valuable versus obligatory."
            ]
        },
        "3": {
            "focus": "Growth through communication, curiosity, and connection.",
            "guidance": [
                "Practice expressing ideas simply and clearly.",
                "Ask questions instead of assuming.",
                "Engage in active listening with people close to you."
            ]
        },
        "4": {
            "focus": "Growth through family, roots, and emotional security.",
            "guidance": [
                "Reflect on your sense of home and belonging.",
                "Create a nurturing environment for yourself.",
                "Spend time strengthening family or chosen family ties."
            ]
        },
        "5": {
            "focus": "Growth through creativity, play, and joy.",
            "guidance": [
                "Engage in an activity purely for fun.",
                "Express creativity without worrying about judgment.",
                "Celebrate small wins with childlike joy."
            ]
        },
        "6": {
            "focus": "Growth through work, health, and service.",
            "guidance": [
                "Commit to one small daily wellness habit.",
                "Organize part of your routine for clarity.",
                "Offer practical support to someone in need."
            ]
        },
        "7": {
            "focus": "Growth through relationships and cooperation.",
            "guidance": [
                "Notice patterns in your closest partnerships.",
                "Balance giving with receiving.",
                "Strengthen relationships through honest communication."
            ]
        },
        "8": {
            "focus": "Growth through intimacy, shared resources, and transformation.",
            "guidance": [
                "Allow yourself to be open in trusted relationships.",
                "Reflect on what shared resources mean to you.",
                "Explore ways to let go of control gracefully."
            ]
        },
        "9": {
            "focus": "Growth through philosophy, wisdom, and expansion.",
            "guidance": [
                "Read or listen to new perspectives.",
                "Explore cultural or spiritual practices different from your own.",
                "Reflect on your personal worldview."
            ]
        },
        "10": {
            "focus": "Growth through career, responsibility, and contribution.",
            "guidance": [
                "Clarify long-term goals that feel meaningful.",
                "Take ownership of your role in public life.",
                "Act in ways aligned with the legacy you want to build."
            ]
        },
        "11": {
            "focus": "Growth through community, innovation, and collective vision.",
            "guidance": [
                "Connect with groups that inspire you.",
                "Contribute your unique perspective to community efforts.",
                "Experiment with forward-thinking ideas."
            ]
        },
        "12": {
            "focus": "Growth through spirituality, solitude, and release.",
            "guidance": [
                "Spend quiet time in reflection or meditation.",
                "Notice unconscious patterns that hold you back.",
                "Let go of what no longer serves your inner growth."
            ]
        }
    }
}

# Store for temporary files
temp_files = {}

def calculate_nodes_and_big_three(date, time, city, country):
    """Calculate North/South Node positions and Sun/Moon/Rising signs"""
    try:
        # Geocode city
        geolocator = Nominatim(user_agent="node_calc")
        loc = geolocator.geocode(f"{city}, {country}")
        lat, lon = loc.latitude, loc.longitude
        
        # Get timezone
        tf = TimezoneFinder()
        tz_str = tf.timezone_at(lng=lon, lat=lat)
        tz = pytz.timezone(tz_str)
        
        # Build datetime
        dt = datetime.strptime(date + " " + time, "%Y-%m-%d %H:%M")
        utc_dt = tz.localize(dt).astimezone(pytz.utc)
        
        # Calculate julian day
        jd = swe.julday(
            utc_dt.year,
            utc_dt.month,
            utc_dt.day,
            utc_dt.hour + utc_dt.minute / 60.0
        )
        
        # North Node position
        node, *_ = swe.calc_ut(jd, swe.TRUE_NODE)
        node_long = node[0] % 360.0
        node_sign_index = int(node_long // 30)
        node_sign = SIGNS[node_sign_index]
        node_degree = node_long % 30
        
        # Sun position
        sun, *_ = swe.calc_ut(jd, swe.SUN)
        sun_long = sun[0] % 360.0
        sun_sign_index = int(sun_long // 30)
        sun_sign = SIGNS[sun_sign_index]
        
        # Moon position
        moon, *_ = swe.calc_ut(jd, swe.MOON)
        moon_long = moon[0] % 360.0
        moon_sign_index = int(moon_long // 30)
        moon_sign = SIGNS[moon_sign_index]
        
        # Houses (Placidus) and Rising sign
        houses, ascmc = swe.houses_ex(jd, lat, lon, b'P')
        asc_long = ascmc[0] % 360.0
        rising_sign_index = int(asc_long // 30)
        rising_sign = SIGNS[rising_sign_index]
        
        # Calculate which house the North Node is in
        node_house = None
        for i in range(12):
            start = houses[i]
            end = houses[(i + 1) % 12]
            if start <= node_long < end or (end < start and (node_long >= start or node_long < end)):
                node_house = i + 1
                break
        
        # South Node (opposite sign and house)
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
        
        # Birth Chart Overview
        report.append("YOUR ASTROLOGICAL BLUEPRINT")
        report.append("-" * 30)
        report.append(f"Sun in {sun_sign} • Moon in {moon_sign} • Rising in {rising_sign}")
        report.append(f"North Node in {north_node['sign']} • South Node in {south_node['sign']}")
        report.append("")
        
        # North Node section with rich narrative
        report.append("NORTH NODE GUIDANCE")
        report.append("-" * 20)
        north_sign_data = KNOWLEDGE_BASE["north_nodes"][north_node["sign"]]
        
        report.append(f"Your North Node in {north_node['sign']} reveals your soul's primary growth direction in this lifetime. {north_sign_data['meaning']} This placement asks you to embrace qualities that may feel unfamiliar or challenging at first, but will ultimately lead to your greatest fulfillment and spiritual evolution.")
        report.append("")
        
        report.append("To develop these qualities, focus on practical steps that gradually shift your approach to life:")
        
      # Create flowing narrative from guidance points
for i, guidance in enumerate(north_sign_data['guidance']):
    # Convert to proper verb form
    guidance_clean = guidance.rstrip('.').lower()
    if guidance_clean.startswith('take initiative'):
        guidance_clean = 'taking initiative'
    elif guidance_clean.startswith('pursue'):
        guidance_clean = guidance_clean.replace('pursue', 'pursuing')
    elif guidance_clean.startswith('speak'):
        guidance_clean = guidance_clean.replace('speak', 'speaking')
    elif guidance_clean.startswith('create'):
        guidance_clean = 'creating'
    elif guidance_clean.startswith('spend'):
        guidance_clean = 'spending'
    elif guidance_clean.startswith('focus'):
        guidance_clean = 'focusing'
    elif guidance_clean.startswith('ask'):
        guidance_clean = 'asking'
    elif guidance_clean.startswith('read'):
        guidance_clean = 'reading'
    elif guidance_clean.startswith('share'):
        guidance_clean = 'sharing'
    elif guidance_clean.startswith('cook'):
        guidance_clean = 'cooking'
    elif guidance_clean.startswith('allow'):
        guidance_clean = 'allowing'
    elif guidance_clean.startswith('do'):
        guidance_clean = guidance_clean.replace('do', 'doing')
    elif guidance_clean.startswith('express'):
        guidance_clean = 'expressing'
    elif guidance_clean.startswith('celebrate'):
        guidance_clean = 'celebrating'
    elif guidance_clean.startswith('organize'):
        guidance_clean = 'organizing'
    elif guidance_clean.startswith('improve'):
        guidance_clean = 'improving'
    elif guidance_clean.startswith('support'):
        guidance_clean = 'supporting'
    elif guidance_clean.startswith('listen'):
        guidance_clean = 'listening'
    elif guidance_clean.startswith('seek'):
        guidance_clean = 'seeking'
    elif guidance_clean.startswith('invest'):
        guidance_clean = 'investing'
    elif guidance_clean.startswith('reflect'):
        guidance_clean = 'reflecting'
    elif guidance_clean.startswith('practice'):
        guidance_clean = 'practicing'
    elif guidance_clean.startswith('lean'):
        guidance_clean = 'leaning'
    elif guidance_clean.startswith('learn'):
        guidance_clean = 'learning'
    elif guidance_clean.startswith('travel'):
        guidance_clean = 'traveling'
    elif guidance_clean.startswith('set'):
        guidance_clean = 'setting'
    elif guidance_clean.startswith('track'):
        guidance_clean = 'tracking'
    elif guidance_clean.startswith('take ownership'):
        guidance_clean = 'taking ownership'
    elif guidance_clean.startswith('contribute'):
        guidance_clean = 'contributing'
    elif guidance_clean.startswith('experiment'):
        guidance_clean = 'experimenting'
    elif guidance_clean.startswith('connect'):
        guidance_clean = 'connecting'
    elif guidance_clean.startswith('engage'):
        guidance_clean = 'engaging'
    
    if i == 0:
        report.append(f"Start by {guidance_clean}.")
    elif i == len(north_sign_data['guidance']) - 1:
        report.append(f"Most importantly, {guidance_clean}.")
    else:
        report.append(f"Additionally, {guidance_clean}.")
        
report.append("These practices will naturally strengthen your connection to your North Node energy.")
report.append("")
        
        # House guidance with context
        if north_node.get("house"):
            house_data = KNOWLEDGE_BASE["houses"][str(north_node["house"])]
            report.append(f"Your North Node's placement in the {north_node['house']}th house adds another layer of meaning. {house_data['focus']} This house placement shows the life areas where your {north_node['sign']} growth will be most important and transformative.")
            report.append("")
            
            report.append(f"The {north_node['house']}th house invites you to approach relationships and cooperation with greater intention.")
            
            # Create proper sentences for house guidance
            for i, guidance in enumerate(house_data['guidance']):
                guidance_clean = guidance.rstrip('.').lower()
                if i == 0:
                    report.append(f"Begin by learning to {guidance_clean}.")
                elif i == len(house_data['guidance']) - 1:
                    report.append(f"Most importantly, focus on how to {guidance_clean}.")
                else:
                    report.append(f"Practice {guidance_clean}.")
            
            report.append("These experiences will accelerate your spiritual development and help you embody your North Node purpose more fully.")
            report.append("")
        
        # South Node with compassionate reframing
        report.append("SOUTH NODE AWARENESS")
        report.append("-" * 20)
        south_sign_data = KNOWLEDGE_BASE["south_nodes"][south_node["sign"]]
        
        report.append(f"Your South Node in {south_node['sign']} represents the gifts and patterns you've mastered in previous lifetimes. While these qualities are natural strengths, the challenge lies in {south_sign_data['patterns'].lower()}. These tendencies, though comfortable, can prevent you from growing toward your North Node potential.")
        report.append("")
        
        # Create proper sentences for South Node guidance
        report.append("To find balance, practice developing awareness in these key areas:")
        for i, guidance in enumerate(south_sign_data['guidance']):
            guidance_clean = guidance.rstrip('.').lower()
            if guidance_clean.startswith('notice'):
                report.append(f"Pay attention to moments when you {guidance_clean}.")
            elif guidance_clean.startswith('practice'):
                report.append(f"Work on {guidance_clean}.")
            else:
                report.append(f"Learn to {guidance_clean}.")
        
        report.append("The goal isn't to eliminate these patterns entirely, but to use them consciously while expanding toward your North Node growth.")
        report.append("")
        
        # Enhanced big three interactions
        report.append("YOUR NODES AND SUN SIGN")
        report.append("-" * 25)
        
        if sun_sign == north_node['sign']:
            report.append(f"Your Sun in {sun_sign} creates a powerful alignment with your North Node purpose. Your core identity and life direction are unified, making it easier to embody the qualities you're meant to develop. You naturally radiate {north_node['sign']} energy, and others likely see you as someone who authentically lives their purpose. This alignment suggests you're here to master and teach {north_node['sign']} qualities through your very being.")
        elif sun_sign == south_node['sign']:
            report.append(f"With your Sun in {sun_sign}, the same sign as your South Node, you embody the mastered gifts from your past-life experiences. While this gives you natural confidence in {sun_sign} qualities, be mindful not to over-rely on these familiar patterns. Your challenge is to let your {north_node['sign']} North Node guide your self-expression, using your {sun_sign} strengths as a foundation rather than a limitation.")
        else:
            report.append(f"Your {sun_sign} Sun provides the core energy and vitality to fuel your {north_node['sign']} North Node development. The dynamic between these two signs creates an interesting interplay in your personality. Your {sun_sign} nature gives you the confidence and drive to step into the unfamiliar territory of your {north_node['sign']} growth, while your North Node adds depth and purpose to how you express your {sun_sign} identity.")
        report.append("")
        
        # Moon sign interaction
        report.append("YOUR NODES AND MOON SIGN")
        report.append("-" * 26)
        
        if moon_sign == north_node['sign']:
            report.append(f"Your Moon in {moon_sign} creates an intuitive understanding of your North Node path. Your emotional nature instinctively knows what you need for growth, and you likely feel most nurtured when engaging in {north_node['sign']} activities. This placement suggests that following your genuine emotional responses will guide you toward your life purpose. Trust your feelings—they're aligned with your soul's direction.")
        elif moon_sign == south_node['sign']:
            report.append(f"Your Moon in {moon_sign} connects you deeply to your South Node patterns, meaning your emotional comfort zone lies in familiar {moon_sign} territory. While this emotional foundation is valuable, be aware that your habitual responses might pull you away from {north_node['sign']} growth. Practice conscious emotional development by honoring your {moon_sign} needs while gradually expanding toward your North Node qualities.")
        else:
            report.append(f"Your {moon_sign} Moon provides emotional support for your {north_node['sign']} North Node journey. The relationship between these signs influences how you process the challenges and rewards of personal growth. Your {moon_sign} emotional nature can either support or complicate your path to {north_node['sign']} development, depending on how consciously you work with both energies.")
        report.append("")
        
        # Rising sign interaction
        report.append("YOUR NODES AND RISING SIGN")
        report.append("-" * 28)
        
        if rising_sign == north_node['sign']:
            report.append(f"Your {rising_sign} Rising sign aligns beautifully with your North Node, meaning others naturally perceive you as someone embodying your life purpose. Your outer personality and approach to new situations already reflect {rising_sign} qualities, making your North Node development feel more natural and supported by how the world responds to you. This is a gift that accelerates your spiritual growth.")
        elif rising_sign == south_node['sign']:
            report.append(f"With your Rising sign in {rising_sign}, the same as your South Node, you naturally present yourself through familiar, mastered qualities. Others see you as naturally gifted in {rising_sign} areas, which can be both a blessing and a challenge. While this gives you confidence in how you meet the world, consciously cultivate your {north_node['sign']} North Node qualities in your interactions and first impressions.")
        else:
    article = "an" if rising_sign[0].lower() in 'aeiou' else "a"
    report.append(f"Your {rising_sign} Rising provides the style and approach through which you'll develop your {north_node['sign']} North Node qualities. The way you naturally meet new people and situations has {article} {rising_sign} flavor that can either support or create tension with your North Node growth. Learning to blend these energies consciously will enhance both your personal magnetism and spiritual development.")
        
        # Integrated wisdom
        report.append("INTEGRATED GUIDANCE")
        report.append("-" * 18)
        report.append(f"Your soul's journey in this lifetime centers on the evolution from {south_node['sign']} patterns toward {north_node['sign']} mastery. This isn't about rejecting your South Node gifts—your {south_node['sign']} experience provides a valuable foundation. Instead, it's about expanding beyond what feels safe and familiar.")
        report.append("")
        report.append(f"With your {sun_sign} Sun providing core vitality, your {moon_sign} Moon offering emotional wisdom, and your {rising_sign} Rising shaping how you meet the world, you have a unique combination of tools to support this transformation. Each element of your chart contributes to your ability to grow into your {north_node['sign']} potential while honoring the gifts you've already developed.")
        report.append("")
        report.append("Remember that spiritual growth is a gradual process. Be patient with yourself as you learn to balance the familiar comfort of your South Node with the exciting challenge of your North Node development. The goal is integration—using all parts of your astrological makeup to create a rich, authentic, and purposeful life.")
        report.append("")
        
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
    try:
        # Log the raw request data for debugging
        print("Raw request data:", request.data)
        print("Request JSON:", request.json)
        
        data = request.json
        
        # Log each expected field
        print("Date:", data.get('date'))
        print("Time:", data.get('time'))
        print("City:", data.get('city'))
        print("Country:", data.get('country'))
        print("Email:", data.get('email'))
        
        # Calculate nodes and big three
        chart_data = calculate_nodes_and_big_three(
            data['date'],
            data.get('time', '12:00'),
            data['city'],
            data['country']
        )
        
        # Generate full report
        report_text = generate_full_report(chart_data)
        
        # Create PDF
        pdf_path = create_pdf_report(report_text)
        
        # Send email
        send_report_email(data['email'], report_text, pdf_path)
        
        return jsonify({"status": "success", "message": "Report sent successfully"})
        
    except Exception as e:
        print("Error in process_form:", str(e))
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
