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

app = Flask(__name__)

# Path to Swiss Ephemeris data files
swe.set_ephe_path('.')  

SIGNS = [
    "Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo",
    "Libra", "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces"
]

# Store for temporary files (in production, use proper storage)
temp_files = {}

@app.route('/nodes', methods=['POST'])
def get_nodes():
    try:
        data = request.json
        date = data['date']
        time = data.get('time', "12:00")
        city = data['city']
        country = data['country']
        
        # [Your existing nodes calculation code stays the same]
        geolocator = Nominatim(user_agent="node_calc")
        loc = geolocator.geocode(f"{city}, {country}")
        lat, lon = loc.latitude, loc.longitude
        
        tf = TimezoneFinder()
        tz_str = tf.timezone_at(lng=lon, lat=lat)
        tz = pytz.timezone(tz_str)
        
        dt = datetime.strptime(date + " " + time, "%Y-%m-%d %H:%M")
        utc_dt = tz.localize(dt).astimezone(pytz.utc)
        
        jd = swe.julday(
            utc_dt.year,
            utc_dt.month,
            utc_dt.day,
            utc_dt.hour + utc_dt.minute / 60.0
        )
        
        node, *_ = swe.calc_ut(jd, swe.TRUE_NODE)
        node_long = node[0] % 360.0
        sign_index = int(node_long // 30)
        sign = SIGNS[sign_index]
        degree = node_long % 30
        
        houses, ascmc = swe.houses_ex(jd, lat, lon, b'P')
        house = None
        for i in range(12):
            start = houses[i]
            end = houses[(i + 1) % 12]
            if start <= node_long < end or (end < start and (node_long >= start or node_long < end)):
                house = i + 1
                break
        
        opp_sign = SIGNS[(sign_index + 6) % 12]
        opp_house = (house + 6 - 1) % 12 + 1 if house else None
        
        return jsonify({
            "north_node": {"sign": sign, "degree": round(degree, 2), "house": house},
            "south_node": {"sign": opp_sign, "degree": round(degree, 2), "house": opp_house}
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 400

@app.route('/report', methods=['POST'])
def make_report():
    try:
        data = request.json
        report_text = data['report']
        
        # Generate unique filename
        file_id = str(uuid.uuid4())
        filename = f"nodal_report_{file_id}.pdf"
        filepath = f"/tmp/{filename}"
        
        # Create PDF
        styles = getSampleStyleSheet()
        doc = SimpleDocTemplate(filepath)
        story = []
        
        for paragraph in report_text.split("\n"):
            if paragraph.strip():  # Skip empty lines
                story.append(Paragraph(paragraph, styles['Normal']))
                story.append(Spacer(1, 12))
        
        doc.build(story)
        
        # Store file info for later retrieval
        temp_files[file_id] = filepath
        
        # Return JSON with download URL
        download_url = f"{request.url_root}download/{file_id}"
        
        return jsonify({
            "download_url": download_url,
            "filename": filename
        })
        
    except Exception as e:
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
