import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
import requests
import os
from dotenv import load_dotenv
import openai
import glob
import hashlib
import time
import concurrent.futures

# Configuration MUST be the first Streamlit command
st.set_page_config(
    page_title="🌤️ Agent Météo Premium Maroc & Monde",
    page_icon="🌤️",
    layout="wide",
    initial_sidebar_state="expanded"
)

load_dotenv()

# ============================================================================
# CSS OPTIMISÉ - VERSION LIGHT & PASTEL
# ============================================================================

st.markdown("""
<style>
    /* Style général - Dégradé doux */
    .stApp {
        background: linear-gradient(135deg, #a8e6cf 0%, #d4edfa 100%);
    }
    
    /* Cartes météo - Style glassmorphisme léger */
    .weather-card {
        background: rgba(255, 255, 255, 0.85);
        border-radius: 25px;
        padding: 25px;
        box-shadow: 0 20px 40px rgba(0, 0, 0, 0.05);
        backdrop-filter: blur(10px);
        margin: 10px 0;
        border: 1px solid rgba(255, 255, 255, 0.6);
        transition: all 0.3s ease;
    }
    
    .weather-card:hover {
        transform: translateY(-5px);
        box-shadow: 0 30px 50px rgba(0, 0, 0, 0.1);
        background: rgba(255, 255, 255, 0.95);
    }
    
    /* Titres - Doux et élégants */
    .title {
        color: #2c3e50;
        text-align: center;
        font-size: 3em;
        font-weight: 600;
        text-shadow: 2px 2px 4px rgba(255,255,255,0.5);
        margin-bottom: 30px;
        background: linear-gradient(45deg, #2c3e50, #3498db);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }
    
    /* Température - Pastel */
    .temp-big {
        font-size: 4em;
        font-weight: bold;
        color: #2c3e50;
        text-shadow: 2px 2px 4px rgba(255,255,255,0.3);
    }
    
    /* Boutons - Tons pastel */
    .stButton > button {
        background: linear-gradient(45deg, #ffb6b9, #ffd5b5);
        color: #2c3e50;
        border: none;
        border-radius: 50px;
        padding: 10px 30px;
        font-weight: 600;
        transition: all 0.3s;
        border: 1px solid rgba(255, 255, 255, 0.8);
    }
    
    .stButton > button:hover {
        transform: translateY(-2px);
        box-shadow: 0 10px 30px rgba(255,182,185,0.3);
        background: linear-gradient(45deg, #ffc3c6, #ffe0c5);
    }
    
    /* Sidebar - Douce et légère */
    .css-1d391kg {
        background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%);
    }
    
    /* Messages chat */
    .chat-message-user {
        background: linear-gradient(135deg, #b8e1ff 0%, #d4f0ff 100%);
        color: #2c3e50;
        border-radius: 20px 20px 5px 20px;
        padding: 15px;
        margin: 10px 0;
        max-width: 70%;
        float: right;
        clear: both;
        box-shadow: 0 2px 10px rgba(0,0,0,0.05);
    }
    
    .chat-message-bot {
        background: linear-gradient(135deg, #ffffff 0%, #f8f9fa 100%);
        color: #2c3e50;
        border-radius: 20px 20px 20px 5px;
        padding: 15px;
        margin: 10px 0;
        max-width: 70%;
        float: left;
        clear: both;
        box-shadow: 0 2px 10px rgba(0,0,0,0.05);
        border: 1px solid rgba(255,255,255,0.8);
    }
    
    /* Statut de mise à jour */
    .update-status {
        font-size: 0.9em;
        color: #2c3e50;
        text-align: center;
        padding: 10px;
        background: rgba(255, 255, 255, 0.3);
        border-radius: 50px;
        margin-top: 10px;
        backdrop-filter: blur(5px);
        border: 1px solid rgba(255,255,255,0.5);
    }
    
    /* Métriques - Style épuré */
    .metric-card {
        background: rgba(255, 255, 255, 0.3);
        border-radius: 15px;
        padding: 15px;
        text-align: center;
        backdrop-filter: blur(5px);
        border: 1px solid rgba(255,255,255,0.5);
    }
    
    /* Légende carte */
    .legend-item {
        display: inline-block;
        padding: 5px 15px;
        border-radius: 50px;
        margin: 2px;
        font-size: 0.9em;
        background: rgba(255,255,255,0.3);
        backdrop-filter: blur(5px);
    }
    
    /* Footer */
    .footer {
        text-align: center;
        color: #2c3e50;
        padding: 20px;
        background: rgba(255, 255, 255, 0.2);
        border-radius: 50px;
        backdrop-filter: blur(5px);
        margin-top: 30px;
    }
</style>
""", unsafe_allow_html=True)

# ============================================================================
# DONNÉES (CONSTANTES)
# ============================================================================

# Villes marocaines - 30 villes
MAROC_CITIES = (
    # Grandes villes
    ("Casablanca", 33.5731, -7.5898, "🌆", "Capitale économique"),
    ("Rabat", 34.0209, -6.8416, "🏛️", "Capitale administrative"),
    ("Marrakech", 31.6295, -7.9811, "🏜️", "Ville ocre"),
    ("Fès", 34.0331, -5.0003, "🏺", "Capitale spirituelle"),
    ("Tanger", 35.7595, -5.8340, "🌊", "Perle du détroit"),
    ("Agadir", 30.4278, -9.5981, "🏖️", "Station balnéaire"),
    ("Meknès", 33.8950, -5.5545, "🏰", "Ville impériale"),
    ("Oujda", 34.6867, -1.9114, "🏰", "Porte de l'Orient"),
    ("Kenitra", 34.2610, -6.5802, "🌾", "Ville du Sebou"),
    ("Tétouan", 35.5785, -5.3750, "🎨", "Ville d'art"),
    
    # Villes côtières
    ("Essaouira", 31.5125, -9.7700, "🎨", "Cité des alizés"),
    ("El Jadida", 33.2541, -8.5088, "🏰", "Cité portugaise"),
    ("Safi", 32.2994, -9.2372, "🏺", "Capitale de la poterie"),
    ("Larache", 35.1933, -6.1557, "🌊", "Ville andalouse"),
    ("Al Hoceima", 35.2446, -3.9375, "🏖️", "Perle méditerranéenne"),
    ("Nador", 35.1688, -2.9335, "🌊", "Ville méditerranéenne"),
    ("Mohammedia", 33.6835, -7.3831, "🏖️", "Ville balnéaire"),
    
    # Villes historiques
    ("Ifrane", 33.5333, -5.1167, "🏔️", "Petite Suisse"),
    ("Chefchaouen", 35.1717, -5.2697, "💙", "Ville bleue"),
    ("Beni Mellal", 32.3394, -6.3608, "⛰️", "Ville du Moyen Atlas"),
    ("Khouribga", 32.8860, -6.9213, "⛏️", "Capitale des phosphates"),
    ("Settat", 33.0010, -7.6167, "🌾", "Ville agricole"),
    ("Taza", 34.2144, -4.0189, "⛰️", "Porte du Rif"),
    
    # Villes du Sud
    ("Laâyoune", 27.1500, -13.2000, "🐪", "Capitale du Sahara"),
    ("Dakhla", 23.6848, -15.9580, "🪁", "Paradis du kitesurf"),
    ("Guelmim", 28.9870, -10.0674, "🐪", "Porte du désert"),
    ("Tan-Tan", 28.4375, -11.0967, "🐪", "Ville saharienne"),
    ("Tarfaya", 27.9375, -12.9286, "🌊", "Ville côtière du sud"),
    ("Boujdour", 26.1257, -14.4726, "🐪", "Cité saharienne"),
    ("Smara", 26.7418, -11.6788, "🏜️", "Ville sainte")
)

# Villes internationales - 25 villes
WORLD_CITIES = (
    # Europe
    ("Paris", 48.8566, 2.3522, "🗼", "France"),
    ("Londres", 51.5074, -0.1278, "🇬🇧", "Royaume-Uni"),
    ("Madrid", 40.4168, -3.7038, "💃", "Espagne"),
    ("Rome", 41.9028, 12.4964, "🏛️", "Italie"),
    ("Berlin", 52.5200, 13.4050, "🇩🇪", "Allemagne"),
    ("Moscou", 55.7558, 37.6173, "🇷🇺", "Russie"),
    ("Istanbul", 41.0082, 28.9784, "🕌", "Turquie"),
    
    # Amériques
    ("New York", 40.7128, -74.0060, "🗽", "États-Unis"),
    ("Los Angeles", 34.0522, -118.2437, "🎬", "États-Unis"),
    ("Miami", 25.7617, -80.1918, "🏖️", "États-Unis"),
    ("Toronto", 43.6532, -79.3832, "🍁", "Canada"),
    ("Mexico", 19.4326, -99.1332, "🌮", "Mexique"),
    ("Rio", -22.9068, -43.1729, "⛰️", "Brésil"),
    ("Buenos Aires", -34.6037, -58.3816, "💃", "Argentine"),
    
    # Asie
    ("Tokyo", 35.6762, 139.6503, "🗼", "Japon"),
    ("Shanghai", 31.2304, 121.4737, "🏙️", "Chine"),
    ("Pékin", 39.9042, 116.4074, "🏯", "Chine"),
    ("Séoul", 37.5665, 126.9780, "🏛️", "Corée"),
    ("Bangkok", 13.7563, 100.5018, "🙏", "Thaïlande"),
    ("Mumbai", 19.0760, 72.8777, "🎬", "Inde"),
    ("Dubai", 25.2048, 55.2708, "🌇", "Émirats"),
    
    # Afrique
    ("Le Caire", 30.0444, 31.2357, "🔺", "Égypte"),
    ("Le Cap", -33.9249, 18.4241, "🏔️", "Afrique du Sud"),
    ("Dakar", 14.7167, -17.4677, "🌊", "Sénégal"),
    ("Lagos", 6.5244, 3.3792, "🏙️", "Nigeria")
)

# Mapping des codes météo - Version light
WEATHER_CODES = {
    0: ("☀️", "Ciel dégagé", "#FFE5B4"),  # Peach
    1: ("🌤️", "Principalement dégagé", "#FFFACD"),  # Lemon chiffon
    2: ("⛅", "Partiellement nuageux", "#E0FFFF"),  # Light cyan
    3: ("☁️", "Nuageux", "#D3D3D3"),  # Light grey
    45: ("🌫️", "Brouillard", "#F0F0F0"),  # White smoke
    48: ("🌫️", "Brouillard givrant", "#F0F8FF"),  # Alice blue
    51: ("🌧️", "Bruine légère", "#E6E6FA"),  # Lavender
    61: ("🌧️", "Pluie légère", "#B0E0E6"),  # Powder blue
    95: ("⛈️", "Orage", "#D8BFD8"),  # Thistle
}

# ============================================================================
# FONCTIONS OPTIMISÉES AVEC CACHE
# ============================================================================

@st.cache_resource
def get_openai_client():
    """Client OpenAI en cache"""
    api_key = os.getenv("OPENAI_API_KEY")
    if api_key:
        return openai.OpenAI(api_key=api_key, base_url="https://openrouter.ai/api/v1")
    return None

@st.cache_data(ttl=1800, show_spinner=False)
def get_weather_batch_parallel(cities_data):
    """Récupère la météo en parallèle pour toutes les villes"""
    
    def fetch_city(city_data):
        city, lat, lon, _, _ = city_data
        try:
            url = "https://api.open-meteo.com/v1/forecast"
            params = {
                "latitude": lat,
                "longitude": lon,
                "current": "temperature_2m,relative_humidity_2m,weather_code,wind_speed_10m,apparent_temperature",
                "daily": "temperature_2m_max,temperature_2m_min",
                "timezone": "auto",
                "forecast_days": 3
            }
            response = requests.get(url, params=params, timeout=3)
            if response.status_code == 200:
                return city, response.json()
        except:
            pass
        return city, None
    
    results = {}
    with concurrent.futures.ThreadPoolExecutor(max_workers=15) as executor:
        futures = [executor.submit(fetch_city, city_data) for city_data in cities_data]
        for future in concurrent.futures.as_completed(futures):
            city, data = future.result()
            results[city] = data
    
    return results

def save_search(city, temp, humidity, wind):
    """Sauvegarde rapide dans l'historique"""
    try:
        filename = f"meteo_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        with open(filename, "w", encoding="utf-8") as f:
            f.write(f"{city}|{temp}|{humidity}|{wind}|{datetime.now().isoformat()}")
        return True
    except:
        return False

# ============================================================================
# INITIALISATION SESSION STATE
# ============================================================================

if 'app_data' not in st.session_state:
    st.session_state.app_data = {
        'maroc_weather': None,
        'world_weather': None,
        'last_update': None,
        'update_in_progress': False
    }

if 'client' not in st.session_state:
    st.session_state.client = get_openai_client()

# ============================================================================
# FONCTION DE MISE À JOUR INTELLIGENTE
# ============================================================================

def refresh_weather_data(force=False):
    """Met à jour les données seulement si nécessaire"""
    now = datetime.now()
    
    # Vérifier si mise à jour nécessaire
    need_update = force
    if not need_update and st.session_state.app_data['last_update']:
        time_diff = (now - st.session_state.app_data['last_update']).seconds
        need_update = time_diff > 1800  # 30 minutes
    
    if need_update and not st.session_state.app_data['update_in_progress']:
        st.session_state.app_data['update_in_progress'] = True
        
        with st.spinner("🌤️ Mise à jour des données météo..."):
            # Charger les deux en parallèle
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future_maroc = executor.submit(get_weather_batch_parallel, MAROC_CITIES)
                future_world = executor.submit(get_weather_batch_parallel, WORLD_CITIES)
                
                st.session_state.app_data['maroc_weather'] = future_maroc.result()
                st.session_state.app_data['world_weather'] = future_world.result()
            
            st.session_state.app_data['last_update'] = now
            st.session_state.app_data['update_in_progress'] = False
            return True
    return False

# ============================================================================
# INTERFACE PRINCIPALE
# ============================================================================

st.markdown("<h1 class='title'>🌤️ Agent Météo Premium</h1>", unsafe_allow_html=True)

# Sidebar avec menu
with st.sidebar:
    st.markdown("## 🎯 Navigation")
    
    menu = st.radio(
        "Choisissez une section",
        ["🏠 Accueil", "🇲🇦 Villes du Maroc", "🗺️ Carte interactive", "🌍 Villes du Monde", "💬 Chat Météo", "📊 Comparateur", "📈 Statistiques", "📁 Historique"]
    )
    
    st.markdown("---")
    st.markdown("## ⚙️ Paramètres")
    
    units = st.selectbox("Unités", ["°C", "°F"])
    
    # Statut de mise à jour
    if st.session_state.app_data['last_update']:
        update_time = st.session_state.app_data['last_update'].strftime("%H:%M:%S")
        st.markdown(f"<div class='update-status'>🔄 Mis à jour à {update_time}</div>", unsafe_allow_html=True)
    else:
        st.markdown("<div class='update-status'>⏳ Premier chargement...</div>", unsafe_allow_html=True)
    
    if st.button("🔄 Forcer mise à jour"):
        refresh_weather_data(force=True)
        st.rerun()

# ============================================================================
# CHARGEMENT DES DONNÉES
# ============================================================================

if st.session_state.app_data['maroc_weather'] is None:
    refresh_weather_data(force=True)

# ============================================================================
# PAGE ACCUEIL
# ============================================================================

if menu == "🏠 Accueil":
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown("""
        <div class='weather-card'>
            <h2 style='text-align: center;'>🇲🇦 30 Villes</h2>
            <p style='text-align: center; font-size: 2em;'>🏙️</p>
            <p style='text-align: center;'>Explorez la météo des principales villes marocaines</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown("""
        <div class='weather-card'>
            <h2 style='text-align: center;'>🌍 25 Villes</h2>
            <p style='text-align: center; font-size: 2em;'>🗺️</p>
            <p style='text-align: center;'>Consultez la météo des grandes métropoles</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        st.markdown("""
        <div class='weather-card'>
            <h2 style='text-align: center;'>💬 Chat IA</h2>
            <p style='text-align: center; font-size: 2em;'>🤖</p>
            <p style='text-align: center;'>Posez vos questions à notre expert météo</p>
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown("---")
    st.markdown("## 🌟 Villes en vedette")
    
    # Afficher 6 villes aléatoires
    import random
    featured = random.sample(list(MAROC_CITIES), 6)
    weather_data = st.session_state.app_data['maroc_weather']
    
    for i in range(0, 6, 3):
        cols = st.columns(3)
        for j, col in enumerate(cols):
            if i + j < len(featured):
                city, lat, lon, emoji, desc = featured[i + j]
                data = weather_data.get(city) if weather_data else None
                
                with col:
                    if data and 'current' in data:
                        temp = data['current']['temperature_2m']
                        weather_code = data['current'].get('weather_code', 0)
                        weather_info = WEATHER_CODES.get(weather_code, ("🌤️", "Inconnu", "#FFF"))
                        
                        st.markdown(f"""
                        <div class='weather-card'>
                            <h3>{emoji} {city}</h3>
                            <p class='temp-big'>{temp:.0f}°C</p>
                            <p>{weather_info[0]} {weather_info[1]}</p>
                            <p style='color: #666;'>{desc}</p>
                        </div>
                        """, unsafe_allow_html=True)

# ============================================================================
# PAGE VILLES DU MAROC
# ============================================================================

elif menu == "🇲🇦 Villes du Maroc":
    st.markdown("## 🇲🇦 Météo des Villes Marocaines")
    
    col1, col2 = st.columns([1, 3])
    
    with col1:
        selected_city = st.selectbox("Choisissez une ville", [c[0] for c in MAROC_CITIES])
    
    if selected_city:
        for city, lat, lon, emoji, desc in MAROC_CITIES:
            if city == selected_city:
                break
        
        data = st.session_state.app_data['maroc_weather'].get(city) if st.session_state.app_data['maroc_weather'] else None
        
        if data and 'current' in data:
            current = data['current']
            weather_code = current.get('weather_code', 0)
            weather_info = WEATHER_CODES.get(weather_code, ("🌤️", "Inconnu", "#FFF"))
            
            save_search(city, current['temperature_2m'], current['relative_humidity_2m'], current['wind_speed_10m'])
            
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.markdown(f"""
                <div class='weather-card'>
                    <h3>🌡️ Température</h3>
                    <p class='temp-big'>{current['temperature_2m']:.0f}°C</p>
                </div>
                """, unsafe_allow_html=True)
            
            with col2:
                st.markdown(f"""
                <div class='weather-card'>
                    <h3>💧 Humidité</h3>
                    <p class='temp-big'>{current['relative_humidity_2m']}%</p>
                </div>
                """, unsafe_allow_html=True)
            
            with col3:
                st.markdown(f"""
                <div class='weather-card'>
                    <h3>🌬️ Vent</h3>
                    <p class='temp-big'>{current['wind_speed_10m']:.0f} km/h</p>
                </div>
                """, unsafe_allow_html=True)
            
            with col4:
                st.markdown(f"""
                <div class='weather-card'>
                    <h3>☁️ État</h3>
                    <p style='font-size: 3em;'>{weather_info[0]}</p>
                </div>
                """, unsafe_allow_html=True)

# ============================================================================
# PAGE CARTE INTERACTIVE
# ============================================================================

elif menu == "🗺️ Carte interactive":
    st.markdown("## 🗺️ Carte Météo Interactive")
    
    import folium
    from streamlit_folium import st_folium
    
    col1, col2 = st.columns([3, 1])
    
    with col2:
        st.markdown("### 🎨 Légende")
        st.markdown("""
        <span class='legend-item'>🔵 < 15°C</span>
        <span class='legend-item'>🟢 15-20°C</span>
        <span class='legend-item'>🟡 20-25°C</span>
        <span class='legend-item'>🟠 25-30°C</span>
        <span class='legend-item'>🔴 > 30°C</span>
        """, unsafe_allow_html=True)
    
    m = folium.Map(location=[31.7917, -7.0926], zoom_start=6)
    
    weather_data = st.session_state.app_data['maroc_weather']
    
    if weather_data:
        for city, lat, lon, emoji, desc in MAROC_CITIES:
            data = weather_data.get(city)
            if data and 'current' in data:
                temp = data['current']['temperature_2m']
                
                # Couleurs pastel selon température
                if temp < 15:
                    color = 'lightblue'
                elif temp < 20:
                    color = 'lightgreen'
                elif temp < 25:
                    color = 'beige'
                elif temp < 30:
                    color = 'orange'
                else:
                    color = 'lightred'
                
                folium.Marker(
                    [lat, lon],
                    popup=f"{emoji} {city}: {temp:.0f}°C",
                    tooltip=city,
                    icon=folium.Icon(color=color)
                ).add_to(m)
    
    with col1:
        st_folium(m, width=800, height=500)

# ============================================================================
# PAGE VILLES DU MONDE
# ============================================================================

elif menu == "🌍 Villes du Monde":
    st.markdown("## 🌍 Météo des Villes Internationales")
    
    col1, col2 = st.columns([1, 3])
    
    with col1:
        selected_city = st.selectbox("Choisissez une ville", [c[0] for c in WORLD_CITIES])
    
    if selected_city:
        for city, lat, lon, emoji, country in WORLD_CITIES:
            if city == selected_city:
                break
        
        data = st.session_state.app_data['world_weather'].get(city) if st.session_state.app_data['world_weather'] else None
        
        if data and 'current' in data:
            current = data['current']
            weather_code = current.get('weather_code', 0)
            weather_info = WEATHER_CODES.get(weather_code, ("🌤️", "Inconnu", "#FFF"))
            
            save_search(city, current['temperature_2m'], current['relative_humidity_2m'], current['wind_speed_10m'])
            
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.markdown(f"""
                <div class='weather-card'>
                    <h3>🌡️ Température</h3>
                    <p class='temp-big'>{current['temperature_2m']:.0f}°C</p>
                </div>
                """, unsafe_allow_html=True)
            
            with col2:
                st.markdown(f"""
                <div class='weather-card'>
                    <h3>💧 Humidité</h3>
                    <p class='temp-big'>{current['relative_humidity_2m']}%</p>
                </div>
                """, unsafe_allow_html=True)
            
            with col3:
                st.markdown(f"""
                <div class='weather-card'>
                    <h3>🌬️ Vent</h3>
                    <p class='temp-big'>{current['wind_speed_10m']:.0f} km/h</p>
                </div>
                """, unsafe_allow_html=True)
            
            with col4:
                st.markdown(f"""
                <div class='weather-card'>
                    <h3>☁️ État</h3>
                    <p style='font-size: 3em;'>{weather_info[0]}</p>
                </div>
                """, unsafe_allow_html=True)

# ============================================================================
# PAGE CHAT MÉTÉO
# ============================================================================

elif menu == "💬 Chat Météo":
    st.markdown("## 💬 Discutez avec votre Expert Météo")
    
    if not st.session_state.client:
        st.error("Service de chat non disponible")
    else:
        if "messages" not in st.session_state:
            st.session_state.messages = [
                {"role": "assistant", "content": "Bonjour ! Je suis votre expert météo. Posez-moi toutes vos questions ! 🌤️"}
            ]
        
        for message in st.session_state.messages[-10:]:
            with st.chat_message(message["role"]):
                st.markdown(message["content"])
        
        if prompt := st.chat_input("Posez votre question météo..."):
            st.session_state.messages.append({"role": "user", "content": prompt})
            with st.chat_message("user"):
                st.markdown(prompt)
            
            with st.chat_message("assistant"):
                with st.spinner("Analyse en cours..."):
                    response = st.session_state.client.chat.completions.create(
                        model="openrouter/free",
                        messages=[
                            {"role": "system", "content": "Tu es un expert météorologue."},
                            *st.session_state.messages[-6:]
                        ]
                    )
                    reply = response.choices[0].message.content
                    st.markdown(reply)
                    st.session_state.messages.append({"role": "assistant", "content": reply})

# ============================================================================
# PAGE COMPARATEUR
# ============================================================================

elif menu == "📊 Comparateur":
    st.markdown("## 📊 Comparez les Villes")
    
    col1, col2 = st.columns(2)
    
    with col1:
        city1 = st.selectbox("Ville 1", [c[0] for c in MAROC_CITIES], index=0)
        for c in MAROC_CITIES:
            if c[0] == city1:
                em1 = c[3]
                break
    
    with col2:
        city2 = st.selectbox("Ville 2", [c[0] for c in MAROC_CITIES], index=1)
        for c in MAROC_CITIES:
            if c[0] == city2:
                em2 = c[3]
                break
    
    if st.button("Comparer", use_container_width=True):
        data1 = st.session_state.app_data['maroc_weather'].get(city1) if st.session_state.app_data['maroc_weather'] else None
        data2 = st.session_state.app_data['maroc_weather'].get(city2) if st.session_state.app_data['maroc_weather'] else None
        
        if data1 and data2 and 'current' in data1 and 'current' in data2:
            df = pd.DataFrame({
                "Ville": [f"{em1} {city1}", f"{em2} {city2}"],
                "Température": [data1['current']['temperature_2m'], data2['current']['temperature_2m']],
                "Humidité": [data1['current']['relative_humidity_2m'], data2['current']['relative_humidity_2m']],
                "Vent": [data1['current']['wind_speed_10m'], data2['current']['wind_speed_10m']]
            })
            
            fig = px.bar(df, x='Ville', y=['Température', 'Humidité', 'Vent'],
                        barmode='group', title="Comparaison Météo")
            fig.update_layout(plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)')
            
            st.plotly_chart(fig, use_container_width=True)
            st.dataframe(df, use_container_width=True, hide_index=True)

# ============================================================================
# PAGE STATISTIQUES
# ============================================================================

elif menu == "📈 Statistiques":
    st.markdown("## 📈 Statistiques Météo")
    
    weather_data = st.session_state.app_data['maroc_weather']
    
    if weather_data:
        stats_data = []
        for city, lat, lon, emoji, desc in MAROC_CITIES:
            data = weather_data.get(city)
            if data and 'current' in data:
                stats_data.append({
                    'Ville': f"{emoji} {city}",
                    'Température': data['current']['temperature_2m'],
                    'Humidité': data['current']['relative_humidity_2m']
                })
        
        if stats_data:
            df_stats = pd.DataFrame(stats_data)
            
            col1, col2, col3, col4 = st.columns(4)
            col1.metric("🌡️ Moyenne", f"{df_stats['Température'].mean():.1f}°C")
            col2.metric("🔥 Maximum", f"{df_stats['Température'].max()}°C")
            col3.metric("❄️ Minimum", f"{df_stats['Température'].min()}°C")
            col4.metric("💧 Humidité moy.", f"{df_stats['Humidité'].mean():.0f}%")
            
            st.markdown("### 🔥 Top 5 des villes les plus chaudes")
            top_hot = df_stats.nlargest(5, 'Température')
            st.dataframe(top_hot, use_container_width=True, hide_index=True)

# ============================================================================
# PAGE HISTORIQUE
# ============================================================================

elif menu == "📁 Historique":
    st.markdown("## 📁 Historique des Recherches")
    
    col1, col2 = st.columns([3, 1])
    with col2:
        if st.button("🗑️ Tout effacer", use_container_width=True):
            files = glob.glob("meteo_*.txt")
            for f in files:
                try:
                    os.remove(f)
                except:
                    pass
            st.rerun()
    
    files = glob.glob("meteo_*.txt")
    files.sort(reverse=True)
    
    if files:
        st.markdown(f"**{len(files)} recherche(s)**")
        
        for file in files[:10]:
            with open(file, "r", encoding="utf-8") as f:
                content = f.read()
            
            parts = content.split('|')
            if len(parts) >= 4:
                date_str = file.replace("meteo_", "").replace(".txt", "")
                date_str = f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:8]} {date_str[9:11]}:{date_str[11:13]}"
                
                with st.expander(f"📅 {date_str} - {parts[0]}"):
                    cols = st.columns(3)
                    cols[0].metric("Ville", parts[0])
                    cols[1].metric("Température", f"{parts[1]}°C")
                    cols[2].metric("Humidité", f"{parts[2]}%")
    else:
        st.info("📭 Aucun historique disponible")

# ============================================================================
# FOOTER
# ============================================================================

st.markdown("---")
st.markdown("""
<div class='footer'>
    🌤️ 30 villes marocaines • 25 villes internationales • Design léger et aéré
</div>
""", unsafe_allow_html=True)