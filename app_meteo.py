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

# Configuration MUST be the first Streamlit command
st.set_page_config(
    page_title="🌤️ Agent Météo Maroc & Monde",
    page_icon="🌤️",
    layout="wide",
    initial_sidebar_state="expanded"
)

load_dotenv()

# ============================================================================
# CONSTANTES ET CONFIGURATIONS (chargées une seule fois)
# ============================================================================

# CSS personnalisé optimisé (moins de sélecteurs, plus spécifique)
st.markdown("""
<style>
    /* Style général optimisé */
    .main > div {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 1rem;
    }
    
    /* Cartes météo avec transitions optimisées */
    .weather-card {
        background: rgba(255, 255, 255, 0.95);
        border-radius: 20px;
        padding: 20px;
        box-shadow: 0 8px 20px rgba(0,0,0,0.15);
        margin: 10px 0;
        transition: transform 0.2s ease;
    }
    
    .weather-card:hover {
        transform: translateY(-3px);
        box-shadow: 0 12px 28px rgba(0,0,0,0.2);
    }
    
    /* Température */
    .temp-big {
        font-size: 3.5em;
        font-weight: bold;
        color: #2c3e50;
        line-height: 1.2;
    }
    
    /* Boutons optimisés */
    .stButton > button {
        background: linear-gradient(45deg, #FF6B6B, #FF8E53);
        color: white;
        border: none;
        border-radius: 50px;
        padding: 10px 25px;
        font-weight: 600;
        transition: all 0.2s;
        width: 100%;
    }
    
    /* Cache les éléments inutiles */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
</style>
""", unsafe_allow_html=True)

# ============================================================================
# DONNÉES EN CONSTANTES (jamais recalculées)
# ============================================================================

# Villes marocaines - données optimisées
MAROC_CITIES = (
    ("Casablanca", 33.5731, -7.5898, "🌆", "Capitale économique"),
    ("Rabat", 34.0209, -6.8416, "🏛️", "Capitale administrative"),
    ("Marrakech", 31.6295, -7.9811, "🏜️", "Ville ocre"),
    ("Tanger", 35.7595, -5.8340, "🌊", "Perle du détroit"),
    ("Agadir", 30.4278, -9.5981, "🏖️", "Station balnéaire"),
    ("Fès", 34.0331, -5.0003, "🏺", "Capitale spirituelle"),
    ("Essaouira", 31.5125, -9.7700, "🎨", "Cité des alizés"),
    ("Oujda", 34.6867, -1.9114, "🏰", "Porte de l'Orient"),
    ("Laâyoune", 27.1500, -13.2000, "🐪", "Capitale du Sahara"),
    ("Dakhla", 23.6848, -15.9580, "🪁", "Paradis du kitesurf")
)

# Villes internationales
WORLD_CITIES = (
    ("Paris", 48.8566, 2.3522, "🗼"),
    ("Londres", 51.5074, -0.1278, "🇬🇧"),
    ("New York", 40.7128, -74.0060, "🗽"),
    ("Tokyo", 35.6762, 139.6503, "🗼"),
    ("Dubai", 25.2048, 55.2708, "🌇")
)

# Mapping des codes météo optimisé
WEATHER_CODES = {
    0: ("☀️", "Ciel dégagé", "#FFD700"),
    1: ("🌤️", "Principalement dégagé", "#FFE55C"),
    2: ("⛅", "Partiellement nuageux", "#C0C0C0"),
    3: ("☁️", "Nuageux", "#808080"),
    45: ("🌫️", "Brouillard", "#A9A9A9"),
    48: ("🌫️", "Brouillard givrant", "#A9A9A9"),
    51: ("🌧️", "Bruine légère", "#4682B4"),
    61: ("🌧️", "Pluie légère", "#4682B4"),
    95: ("⛈️", "Orage", "#4B0082")
}

# ============================================================================
# FONCTIONS CACHEES OPTIMISEES
# ============================================================================

@st.cache_resource
def get_openai_client():
    """Client OpenAI en cache (une seule instance)"""
    api_key = os.getenv("OPENAI_API_KEY")
    if api_key:
        return openai.OpenAI(api_key=api_key, base_url="https://openrouter.ai/api/v1")
    return None

client = get_openai_client()

def get_cache_key(city, coords):
    """Génère une clé de cache unique"""
    return hashlib.md5(f"{city}_{coords[0]}_{coords[1]}".encode()).hexdigest()

@st.cache_data(ttl=1800, show_spinner=False)  # Cache 30 minutes, pas de spinner
def get_weather_batch(cities_data):
    """
    Récupère la météo pour plusieurs villes en une seule requête optimisée
    """
    results = {}
    for city, lat, lon, *_ in cities_data:
        try:
            url = "https://api.open-meteo.com/v1/forecast"
            params = {
                "latitude": lat,
                "longitude": lon,
                "current": "temperature_2m,relative_humidity_2m,weather_code,wind_speed_10m",
                "daily": "weather_code,temperature_2m_max,temperature_2m_min",
                "timezone": "auto",
                "forecast_days": 7
            }
            
            response = requests.get(url, params=params, timeout=5)
            if response.status_code == 200:
                results[city] = response.json()
        except:
            results[city] = None
    
    return results

def get_weather_single(city, lat, lon):
    """Version simplifiée pour une seule ville"""
    try:
        url = "https://api.open-meteo.com/v1/forecast"
        params = {
            "latitude": lat,
            "longitude": lon,
            "current": "temperature_2m,relative_humidity_2m,weather_code,wind_speed_10m",
            "daily": "temperature_2m_max,temperature_2m_min",
            "timezone": "auto",
            "forecast_days": 3
        }
        response = requests.get(url, params=params, timeout=3)
        return response.json() if response.status_code == 200 else None
    except:
        return None

# ============================================================================
# FONCTIONS D'HISTORIQUE OPTIMISEES
# ============================================================================

def save_search(city, temp, humidity, wind):
    """Sauvegarde ultra-rapide (pas de JSON, juste du texte)"""
    try:
        filename = f"meteo_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        with open(filename, "w", encoding="utf-8") as f:
            f.write(f"{city}|{temp}|{humidity}|{wind}|{datetime.now().isoformat()}")
        return True
    except:
        return False

def load_history_fast():
    """Charge l'historique rapidement avec compréhension de liste"""
    files = glob.glob("meteo_*.txt")
    return sorted(files, reverse=True)[:50]  # Limite à 50 pour performance

# ============================================================================
# INTERFACE PRINCIPALE OPTIMISEE
# ============================================================================

# Titre avec moins de HTML
st.markdown("<h1 style='text-align:center;color:white;'>🌤️ Agent Météo Intelligent</h1>", unsafe_allow_html=True)

# Sidebar avec navigation simplifiée
with st.sidebar:
    st.markdown("## 🎯 Navigation")
    
    menu_options = ["🏠 Accueil", "🇲🇦 Maroc", "🗺️ Carte", "🌍 Monde", "💬 Chat", "📊 Comparateur", "📁 Historique"]
    menu = st.radio("", menu_options, label_visibility="collapsed")
    
    st.markdown("---")
    with st.expander("⚙️ Paramètres", expanded=False):
        units = st.selectbox("Unités", ["°C", "°F"], label_visibility="collapsed")
        days = st.slider("Jours", 1, 5, 3)

# ============================================================================
# PAGE ACCUEIL OPTIMISEE
# ============================================================================

if menu == "🏠 Accueil":
    # Chargement en arrière-plan des données pour l'accueil
    with st.spinner("🌤️ Chargement des données météo..."):
        weather_data = get_weather_batch(MAROC_CITIES[:3])
    
    cols = st.columns(3)
    for idx, (col, (city, lat, lon, emoji, desc)) in enumerate(zip(cols, MAROC_CITIES[:3])):
        with col:
            data = weather_data.get(city)
            if data and 'current' in data:
                temp = data['current']['temperature_2m']
                weather_code = data['current'].get('weather_code', 0)
                w_emoji, w_text, _ = WEATHER_CODES.get(weather_code, ("🌤️", "Inconnu", "#FFF"))
                
                st.markdown(f"""
                <div class='weather-card'>
                    <h3 style='margin:0'>{emoji} {city}</h3>
                    <p class='temp-big'>{temp:.0f}°C</p>
                    <p>{w_emoji} {w_text}</p>
                    <small>{desc}</small>
                </div>
                """, unsafe_allow_html=True)

# ============================================================================
# PAGE MAROC OPTIMISEE
# ============================================================================

elif menu == "🇲🇦 Maroc":
    st.markdown("## 🇲🇦 Météo Maroc")
    
    # Chargement intelligent des données
    cities_list = [c[0] for c in MAROC_CITIES]
    
    # Utilisation de selectbox avec clé pour éviter les re-rendus
    selected_idx = st.selectbox(
        "Ville",
        range(len(cities_list)),
        format_func=lambda x: cities_list[x],
        key="city_select_ma"
    )
    
    city, lat, lon, emoji, desc = MAROC_CITIES[selected_idx]
    
    # Chargement avec cache
    data = get_weather_single(city, lat, lon)
    
    if data and 'current' in data:
        current = data['current']
        w_emoji, w_text, _ = WEATHER_CODES.get(current.get('weather_code', 0), ("🌤️", "Inconnu", "#FFF"))
        
        # Affichage compact
        m_cols = st.columns(4)
        metrics = [
            ("🌡️", f"{current['temperature_2m']:.0f}°C"),
            ("💧", f"{current['relative_humidity_2m']}%"),
            ("💨", f"{current['wind_speed_10m']:.0f} km/h"),
            (w_emoji, w_text)
        ]
        
        for col, (icon, val) in zip(m_cols, metrics):
            col.metric(icon, val)
        
        # Graphique simplifié
        if 'daily' in data:
            df = pd.DataFrame({
                'Jour': [f"J-{i}" for i in range(1, 4)],
                'Min': data['daily']['temperature_2m_min'][:3],
                'Max': data['daily']['temperature_2m_max'][:3]
            })
            
            fig = px.line(df, x='Jour', y=['Min', 'Max'], 
                         title="Prévisions 3 jours",
                         labels={'value': '°C'})
            fig.update_layout(showlegend=True, height=300)
            st.plotly_chart(fig, use_container_width=True)
        
        # Sauvegarde en arrière-plan
        save_search(city, current['temperature_2m'], 
                   current['relative_humidity_2m'], 
                   current['wind_speed_10m'])

# ============================================================================
# PAGE CARTE OPTIMISEE
# ============================================================================

elif menu == "🗺️ Carte":
    st.markdown("## 🗺️ Carte Météo")
    
    # Import conditionnel pour ne charger que si nécessaire
    with st.spinner("Chargement de la carte..."):
        import folium
        from streamlit_folium import st_folium
        
        # Carte simplifiée
        m = folium.Map(location=[31.79, -7.09], zoom_start=5)
        
        # Ajout des marqueurs en batch
        weather_batch = get_weather_batch(MAROC_CITIES)
        
        for city, lat, lon, emoji, desc in MAROC_CITIES:
            data = weather_batch.get(city)
            if data and 'current' in data:
                temp = data['current']['temperature_2m']
                color = 'blue' if temp < 20 else 'green' if temp < 25 else 'orange' if temp < 30 else 'red'
                
                folium.Marker(
                    [lat, lon],
                    popup=f"{emoji} {city}: {temp:.0f}°C",
                    tooltip=city,
                    icon=folium.Icon(color=color)
                ).add_to(m)
        
        st_folium(m, width=800, height=500)

# ============================================================================
# PAGE MONDE OPTIMISEE
# ============================================================================

elif menu == "🌍 Monde":
    st.markdown("## 🌍 Météo Monde")
    
    cities_list = [c[0] for c in WORLD_CITIES]
    selected_idx = st.selectbox(
        "Ville",
        range(len(cities_list)),
        format_func=lambda x: cities_list[x],
        key="city_select_world"
    )
    
    city, lat, lon, emoji = WORLD_CITIES[selected_idx]
    data = get_weather_single(city, lat, lon)
    
    if data and 'current' in data:
        current = data['current']
        w_emoji, w_text, _ = WEATHER_CODES.get(current.get('weather_code', 0), ("🌤️", "Inconnu", "#FFF"))
        
        cols = st.columns(4)
        cols[0].metric("🌡️", f"{current['temperature_2m']:.0f}°C")
        cols[1].metric("💧", f"{current['relative_humidity_2m']}%")
        cols[2].metric("💨", f"{current['wind_speed_10m']:.0f} km/h")
        cols[3].metric(w_emoji, w_text)

# ============================================================================
# PAGE CHAT OPTIMISEE
# ============================================================================

elif menu == "💬 Chat":
    st.markdown("## 💬 Chat Météo")
    
    if not client:
        st.error("⚠️ Service de chat non disponible")
    else:
        if "messages" not in st.session_state:
            st.session_state.messages = [{
                "role": "assistant", 
                "content": "Bonjour ! Questions météo ? 🌤️"
            }]
        
        # Affichage des messages sans rechargement
        for msg in st.session_state.messages[-10:]:  # Derniers 10 messages seulement
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])
        
        if prompt := st.chat_input("Votre question..."):
            st.session_state.messages.append({"role": "user", "content": prompt})
            with st.chat_message("user"):
                st.markdown(prompt)
            
            with st.chat_message("assistant"):
                with st.spinner(""):
                    response = client.chat.completions.create(
                        model="openrouter/free",
                        messages=[{"role": "system", "content": "Expert météo"}] + st.session_state.messages[-6:],
                        temperature=0.7
                    )
                    reply = response.choices[0].message.content
                    st.markdown(reply)
                    st.session_state.messages.append({"role": "assistant", "content": reply})

# ============================================================================
# PAGE COMPARATEUR OPTIMISEE
# ============================================================================

elif menu == "📊 Comparateur":
    st.markdown("## 📊 Comparateur")
    
    c1, c2 = st.columns(2)
    
    with c1:
        city1_idx = st.selectbox("Ville 1", range(len(MAROC_CITIES)), 
                                format_func=lambda x: MAROC_CITIES[x][0],
                                key="comp1")
        city1, lat1, lon1, em1, _ = MAROC_CITIES[city1_idx]
    
    with c2:
        city2_idx = st.selectbox("Ville 2", range(len(MAROC_CITIES)), 
                                format_func=lambda x: MAROC_CITIES[x][0],
                                key="comp2")
        city2, lat2, lon2, em2, _ = MAROC_CITIES[city2_idx]
    
    if st.button("Comparer ⚡", use_container_width=True):
        with st.spinner(""):
            data1 = get_weather_single(city1, lat1, lon1)
            data2 = get_weather_single(city2, lat2, lon2)
            
            if data1 and data2:
                df = pd.DataFrame({
                    'Ville': [f"{em1} {city1}", f"{em2} {city2}"],
                    'Température': [data1['current']['temperature_2m'], data2['current']['temperature_2m']],
                    'Humidité': [data1['current']['relative_humidity_2m'], data2['current']['relative_humidity_2m']],
                    'Vent': [data1['current']['wind_speed_10m'], data2['current']['wind_speed_10m']]
                })
                
                fig = px.bar(df, x='Ville', y=['Température', 'Humidité', 'Vent'],
                            barmode='group', height=400)
                st.plotly_chart(fig, use_container_width=True)
                
                st.dataframe(df, use_container_width=True)

# ============================================================================
# PAGE HISTORIQUE OPTIMISEE
# ============================================================================

elif menu == "📁 Historique":
    st.markdown("## 📁 Historique")
    
    files = load_history_fast()
    
    if files:
        selected = st.selectbox("Recherche", files, 
                               format_func=lambda x: x.replace("meteo_", "").replace(".txt", ""))
        
        if selected:
            with open(selected, "r") as f:
                content = f.read()
            parts = content.split('|')
            if len(parts) >= 4:
                col1, col2, col3 = st.columns(3)
                col1.metric("Ville", parts[0])
                col2.metric("Température", f"{parts[1]}°C")
                col3.metric("Humidité", f"{parts[2]}%")
        
        if st.button("🗑️ Effacer tout"):
            for f in files:
                os.remove(f)
            st.rerun()
    else:
        st.info("📭 Aucun historique")