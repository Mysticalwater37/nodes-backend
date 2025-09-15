from flask import Flask, request, jsonify, send_file
import swisseph as swe
from geopy.geocoders import Nominatim
from timezonefinder import TimezoneFinder
from datetime import datetime
import pytz
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
import uuid
import os
import resend

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

def calculate_nodes(date, time, city, country):
    """Calculate North and South Node positions"""
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
        sign_index = int(node_long // 30)
        sign = SIGNS[sign_index]
        degree = node_long % 30
        
        # Houses (Placidus)
        houses, ascmc = swe.houses_ex(jd, lat, lon, b'P')
        house = None
        for i in range(12):
            start = houses[i]
            end = houses[(i + 1) % 12]
            if start <= node_long < end or (end < start and (node_long >= start or node_long < end)):
                house = i + 1
                break
        
        # South Node (opposite sign and house)
        opp_sign = SIGNS[(sign_index + 6) % 12]
        opp_house = (house + 6 - 1) % 12 + 1 if house else None
        
        return {
            "north_node": {"sign": sign, "degree": round(degree, 2), "house": house},
            "south_node": {"sign": opp_sign, "degree": round(degree, 2), "house": opp_house}
        }
    except Exception as e:
        raise Exception(f"Node calculation error: {str(e)}")

def generate_full_report(nodes_data):
    """Generate complete report text using knowledge base"""
    try:
        north_node = nodes_data["north_node"]
        south_node = nodes_data["south_node"]
        
        report = []
        report.append("NODAL PATHWAYS REPORT")
        report.append("=" * 50)
        report.append("")
        
        # North Node section
        report.append("NORTH NODE GUIDANCE")
        report.append("-" * 20)
        north_sign_data = KNOWLEDGE_BASE["north_nodes"][north_node["sign"]]
        report.append(f"North Node in {north_node['sign']}: {north_sign_data['meaning']}")
        report.append("")
        
        report.append("Guidance for your North Node:")
        for guidance in north_sign_data["guidance"]:
            report.append(f"• {guidance}")
        report.append("")
        
        # House guidance if available
        if north_node.get("house"):
            house_data = KNOWLEDGE_BASE["houses"][str(north_node["house"])]
            report.append(f"North Node in House {north_node['house']}: {house_data['focus']}")
            report.append("")
            report.append("House guidance:")
            for guidance in house_data["guidance"]:
                report.append(f"• {guidance}")
            report.append("")
        
        # South Node section
        report.append("SOUTH NODE AWARENESS")
        report.append("-" * 20)
        south_sign_data = KNOWLEDGE_BASE["south_nodes"][south_node["sign"]]
        report.append(f"South Node in {south_node['sign']}: {south_sign_data['patterns']}")
        report.append("")
        
        report.append("Areas to be mindful of:")
        for guidance in south_sign_data["guidance"]:
            report.append(f"• {guidance}")
        report.append("")
        
        # Combined insight
        report.append("COMBINED INSIGHT")
        report.append("-" * 15)
        report.append(f"Your journey involves moving from {south_node['sign']} patterns toward {north_node['sign']} growth.")
        report.append("Use your South Node experience as a foundation, but avoid getting stuck in old patterns.")
        report.append("")
        
        report.append("Astrology is interpretive and meant for reflection only.")
        
        return "\n".join(report)
    except Exception as e:
        raise Exception(f"Report generation error: {str(e)}")

def create_pdf_report(report_text):
    """Create PDF from report text"""
    filename = f"nodal_report_{uuid.uuid4()}.pdf"
    filepath = f"/tmp/{filename}"
    
    styles = getSampleStyleSheet()
    doc = SimpleDocTemplate(filepath)
    story = []
    
    for paragraph in report_text.split("\n"):
        if paragraph.strip():
            story.append(Paragraph(paragraph, styles['Normal']))
        story.append(Spacer(1, 12))
    
    doc.build(story)
    return filepath

def send_report_email(email, report_text, pdf_path):
    """Send report via email"""
    try:
        with open(pdf_path, 'rb') as f:
            pdf_content = f.read()
        
        email_response = resend.Emails.send({
            "from": "onboarding@resend.dev",  # Change to your domain later
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
        
        # Clean up temp file
        try:
            os.remove(pdf_path)
        except:
            pass
            
        return email_response
    except Exception as e:
        raise Exception(f"Email sending error: {str(e)}")

# Your existing endpoints
@app.route('/nodes', methods=['POST'])
def get_nodes():
    try:
        data = request.json
        nodes_data = calculate_nodes(
            data['date'], 
            data.get('time', '12:00'),
            data['city'],
            data['country']
        )
        return jsonify(nodes_data)
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
        
        # Calculate nodes
        nodes_data = calculate_nodes(
            data['date'],
            data.get('time', '12:00'),
            data['city'],
            data['country']
        )
        
        # Generate full report
        report_text = generate_full_report(nodes_data)
        
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
