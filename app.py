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

SIGNS = ["Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo",
         "Libra", "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces"]

@app.route('/nodes', methods=['POST'])
def get_nodes():
    try:
        data = request.json
        date = data['date']      # e.g. "1979-01-03"
        time = data.get('time', "12:00")  # default noon if not given
        city = data['city']
        country = data['country']

        # Step 1: geocode city
        geolocator = Nominatim(user_agent="node_calc")
        loc = geolocator.geocode(f"{city}, {country}")
        lat, lon = loc.latitude, loc.longitude

        # Step 2: timezone
        tf = TimezoneFinder()
        tz_str_
