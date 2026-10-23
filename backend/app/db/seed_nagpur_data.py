import os
import asyncio
from supabase import create_client, Client

SUPABASE_URL = os.getenv("SUPABASE_URL", "YOUR_SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "YOUR_SUPABASE_KEY")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# Extracted Real Nagpur Hotspots & Incidents (2005-2026)
NAGPUR_HEAT_POINTS = [
    {"hazard_type": "high_crime_zone", "intensity": 0.95, "lat": 21.1580, "lng": 79.1415, "locality": "Pardi / Zone V"},
    {"hazard_type": "homicide_and_assault", "intensity": 0.90, "lat": 21.1021, "lng": 79.1121, "locality": "Hudkeshwar"},
    {"hazard_type": "gang_conflict_area", "intensity": 0.85, "lat": 21.1730, "lng": 79.1350, "locality": "Kalamna"},
    {"hazard_type": "historical_violence_spot", "intensity": 0.80, "lat": 21.1550, "lng": 79.0920, "locality": "Mominpura"},
    {"hazard_type": "gang_clash_reported", "intensity": 0.85, "lat": 21.1850, "lng": 79.0820, "locality": "Jaripatka"},
    {"hazard_type": "road_rage_stabbing", "intensity": 0.75, "lat": 21.1920, "lng": 79.1010, "locality": "Kapil Nagar / Mhada Colony"},
    {"hazard_type": "shooting_incident", "intensity": 0.88, "lat": 21.1410, "lng": 79.0580, "locality": "Ram Nagar - Laxmi Bhuvan Sq"},
    {"hazard_type": "crowded_transit_theft", "intensity": 0.60, "lat": 21.1462, "lng": 79.0849, "locality": "Sitabuldi Market / Bus Stand"},
    {"hazard_type": "poor_lighting_corridor", "intensity": 0.70, "lat": 21.1050, "lng": 79.0040, "locality": "Hingna Road Industrial Belt"},
    {"hazard_type": "deserted_night_corridor", "intensity": 0.75, "lat": 21.0510, "lng": 79.0040, "locality": "Butibori MIDC Road"}
]

NAGPUR_COMMUNITY_REPORTS = [
    {
        "description": "Pardi Police Station area recorded multiple serious offences and high crime density in recent police audits.",
        "category": "High Crime Area",
        "lat": 21.1580,
        "lng": 79.1415,
        "llm_credibility_score": 0.95,
        "is_verified": True,
        "status": "approved"
    },
    {
        "description": "Ram Nagar to Laxmi Bhuvan Square corridor: Reported gang-related shooting incident near Gokulpeth.",
        "category": "Severe Violence Risk",
        "lat": 21.1410,
        "lng": 79.0580,
        "llm_credibility_score": 0.92,
        "is_verified": True,
        "status": "approved"
    },
    {
        "description": "Hingna Road Industrial Corridor: Complete absence of street lights after 10 PM. High harassment risk for shift workers.",
        "category": "Dark / Unlit Streetlight",
        "lat": 21.1050,
        "lng": 79.0040,
        "llm_credibility_score": 0.90,
        "is_verified": True,
        "status": "approved"
    },
    {
        "description": "Kapil Nagar Mhada Colony: Road rage stabbing reported near water tank area. Isolated stretch at night.",
        "category": "Isolated Walkway",
        "lat": 21.1920,
        "lng": 79.1010,
        "llm_credibility_score": 0.88,
        "is_verified": True,
        "status": "approved"
    }
]

def seed_database():
    print("Seeding Nagpur Heat Points into Supabase...")
    for hp in NAGPUR_HEAT_POINTS:
        point_wkt = f"POINT({hp['lng']} {hp['lat']})"
        supabase.table("heat_points").insert({
            "hazard_type": hp["hazard_type"],
            "intensity": hp["intensity"],
            "location": point_wkt
        }).execute()

    print("Seeding Verified Nagpur Safety Reports into Supabase...")
    for rep in NAGPUR_COMMUNITY_REPORTS:
        point_wkt = f"POINT({rep['lng']} {rep['lat']})"
        supabase.table("community_reports").insert({
            "description": rep["description"],
            "category": rep["category"],
            "location": point_wkt,
            "llm_credibility_score": rep["llm_credibility_score"],
            "is_verified": rep["is_verified"],
            "status": rep["status"]
        }).execute()

    print("Successfully seeded Nagpur public safety data!")

if __name__ == "__main__":
    seed_database()