import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
import requests
import json
import os
from dotenv import load_dotenv
import openai
import urllib.parse

load_dotenv()

# Configuration de la page
st.set_page_config(
    page_title="🌤️ Agent Météo Maroc & Monde",
    page_icon="🌤️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# CSS personnalisé pour un design moderne
st.markdown("""
<style>
    /* Style général */
    .stApp {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    }
    
    /* Cartes météo */
    .weather-card {
        background: rgba(255, 255, 255, 0.9);
        border-radius: 20px;
        padding: 25px;
        box-shadow: 0 10px 30px rgba(0,0,0,0.2);
        backdrop-filter: blur(10px);
        margin: 10px 0;
    }
    
    /* Titres */
    .title {
        color: white;
        text-align: center;
        font-size: 3em;
        font-weight: bold;
        text-shadow: 2px 2px 4px rgba(0,0,0,0.3);
        margin-bottom: 30px;
    }
    
    /* Température */
    .temp-big {
        font-size: 4em;
        font-weight: bold;
        color: #2c3e50;
    }
    
    /* Info bulle */
    .info-badge {
        background: #f0f2f6;
        border-radius: 10px;
        padding: 10px;
        text-align: center;
        margin: 5px;
    }
    
    /* Boutons personnalisés */
    .stButton > button {
        background: linear-gradient(45deg, #FF6B6B, #FF8E53);
        color: white;
        border: none;
        border-radius: 50px;
        padding: 10px 30px;
        font-weight: bold;
        transition: all 0.3s;
    }
    
    .stButton > button:hover {
        transform: translateY(-2px);
        box-shadow: 0 5px 20px rgba(255,107,107,0.4);
    }
    
    /* Messages du chatbot */
    .chat-message-user {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        border-radius: 20px 20px 5px 20px;
        padding: 15px;
        margin: 10px 0;
        max-width: 70%;
        float: right;
        clear: both;
    }
    
    .chat-message-bot {
        background: white;
        border-radius: 20px 20px 20px 5px;
        padding: 15px;
        margin: 10px 0;
        max-width: 70%;
        float: left;
        clear: both;
        box-shadow: 0 2px 5px rgba(0,0,0,0.1);
    }
    
    /* Sidebar stylisée */
    .css-1d391kg {
        background: linear-gradient(180deg, #2c3e50 0%, #3498db 100%);
    }
</style>
""", unsafe_allow_html=True)

# Initialisation du client OpenAI
@st.cache_resource
def init_client():
    api_key = os.getenv("OPENAI_API_KEY")
    return openai.OpenAI(api_key=api_key, base_url="https://openrouter.ai/api/v1")

client = init_client()

# Dictionnaire des villes marocaines avec coordonnées et infos
VILLES_MAROC = {
    "Casablanca": {
        "coords": (33.5731, -7.5898),
        "region": "Grand Casablanca",
        "description": "Capitale économique, ville côtière dynamique",
        "image": "🌆"
    },
    "Rabat": {
        "coords": (34.0209, -6.8416),
        "region": "Rabat-Salé-Kénitra",
        "description": "Capitale administrative, ville impériale",
        "image": "🏛️"
    },
    "Marrakech": {
        "coords": (31.6295, -7.9811),
        "region": "Marrakech-Safi",
        "description": "Ville ocre, destination touristique majeure",
        "image": "🏜️"
    },
    "Tanger": {
        "coords": (35.7595, -5.8340),
        "region": "Tanger-Tétouan-Al Hoceïma",
        "description": "Perle du détroit, porte de l'Afrique",
        "image": "🌊"
    },
    "Agadir": {
        "coords": (30.4278, -9.5981),
        "region": "Souss-Massa",
        "description": "Station balnéaire, climat doux toute l'année",
        "image": "🏖️"
    },
    "Fès": {
        "coords": (34.0331, -5.0003),
        "region": "Fès-Meknès",
        "description": "Capitale spirituelle et culturelle",
        "image": "🏺"
    },
    "Essaouira": {
        "coords": (31.5125, -9.7700),
        "region": "Marrakech-Safi",
        "description": "Cité des alizés, ville portuaire charmante",
        "image": "🎨"
    },
    "Oujda": {
        "coords": (34.6867, -1.9114),
        "region": "Oriental",
        "description": "Porte de l'Orient marocain",
        "image": "🏰"
    },
    "Laâyoune": {
        "coords": (27.1500, -13.2000),
        "region": "Laâyoune-Sakia El Hamra",
        "description": "Capitale du Sahara marocain",
        "image": "🐪"
    },
    "Dakhla": {
        "coords": (23.6848, -15.9580),
        "region": "Dakhla-Oued Ed-Dahab",
        "description": "Paradis du kitesurf, lagunes magnifiques",
        "image": "🪁"
    }
}

# Villes internationales
VILLES_MONDE = {
    "Paris": (48.8566, 2.3522),
    "Londres": (51.5074, -0.1278),
    "New York": (40.7128, -74.0060),
    "Tokyo": (35.6762, 139.6503),
    "Dubai": (25.2048, 55.2708),
}

# Fonction pour obtenir la météo
@st.cache_data(ttl=1800)  # Cache 30 minutes
def get_weather(city, coords):
    """Récupère la météo depuis Open-Meteo"""
    try:
        lat, lon = coords
        url = "https://api.open-meteo.com/v1/forecast"
        params = {
            "latitude": lat,
            "longitude": lon,
            "current": ["temperature_2m", "relative_humidity_2m", "weather_code", "wind_speed_10m", "wind_direction_10m"],
            "daily": ["weather_code", "temperature_2m_max", "temperature_2m_min"],
            "timezone": "auto",
            "forecast_days": 7
        }
        
        response = requests.get(url, params=params, timeout=10)
        if response.status_code == 200:
            return response.json()
    except:
        pass
    return None

# Mapping des codes météo
WEATHER_CODES = {
    0: {"text": "Ciel dégagé", "emoji": "☀️", "color": "#FFD700"},
    1: {"text": "Principalement dégagé", "emoji": "🌤️", "color": "#FFE55C"},
    2: {"text": "Partiellement nuageux", "emoji": "⛅", "color": "#C0C0C0"},
    3: {"text": "Nuageux", "emoji": "☁️", "color": "#808080"},
    45: {"text": "Brouillard", "emoji": "🌫️", "color": "#A9A9A9"},
    48: {"text": "Brouillard givrant", "emoji": "🌫️", "color": "#A9A9A9"},
    51: {"text": "Bruine légère", "emoji": "🌧️", "color": "#4682B4"},
    61: {"text": "Pluie légère", "emoji": "🌧️", "color": "#4682B4"},
    95: {"text": "Orage", "emoji": "⛈️", "color": "#4B0082"},
}

# Interface principale
st.markdown("<h1 class='title'>🌤️ Agent Météo Intelligent</h1>", unsafe_allow_html=True)

# Sidebar personnalisée
with st.sidebar:
    st.markdown("## 🎯 Navigation")
    
    menu = st.radio(
    "Choisissez une section",
    ["🏠 Accueil", "🇲🇦 Villes du Maroc", "🗺️ Carte interactive", "🌍 Villes du Monde", "💬 Chat Météo", "📊 Comparateur", "📁 Historique"]
)
    
    st.markdown("---")
    st.markdown("## ⚙️ Paramètres")
    
    units = st.selectbox("Unités", ["°C", "°F"])
    days = st.slider("Jours de prévision", 1, 7, 3)
    
    st.markdown("---")
    st.markdown("### 🌟 Fonctionnalités")
    st.markdown("""
    - ✅ Météo en temps réel
    - ✅ Prévisions 7 jours
    - ✅ Comparaison de villes
    - ✅ Chat intelligent
    - ✅ Interface intuitive
    - ✅ Sauvegarde automatique
    """)

# Page Accueil
if menu == "🏠 Accueil":
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown("""
        <div class='weather-card'>
            <h2 style='text-align: center;'>🇲🇦 10 Villes</h2>
            <p style='text-align: center; font-size: 2em;'>🏙️</p>
            <p style='text-align: center;'>Explorez la météo des principales villes marocaines</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown("""
        <div class='weather-card'>
            <h2 style='text-align: center;'>🌍 International</h2>
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
    
    cols = st.columns(3)
    for i, (city, info) in enumerate(list(VILLES_MAROC.items())[:3]):
        with cols[i]:
            data = get_weather(city, info["coords"])
            if data and 'current' in data:
                temp = data['current']['temperature_2m']
                weather_code = data['current'].get('weather_code', 0)
                weather_info = WEATHER_CODES.get(weather_code, {"text": "Inconnu", "emoji": "🌤️"})
                
                st.markdown(f"""
                <div class='weather-card'>
                    <h3>{info['image']} {city}</h3>
                    <p class='temp-big'>{temp}°C</p>
                    <p>{weather_info['emoji']} {weather_info['text']}</p>
                    <p>{info['description']}</p>
                </div>
                """, unsafe_allow_html=True)

# Page Villes du Maroc
elif menu == "🇲🇦 Villes du Maroc":
    st.markdown("## 🇲🇦 Météo des Villes Marocaines")
    
    # Sélection de la ville
    col1, col2 = st.columns([1, 3])
    
    with col1:
        selected_city = st.selectbox("Choisissez une ville", list(VILLES_MAROC.keys()))
    
    if selected_city:
        info = VILLES_MAROC[selected_city]
        data = get_weather(selected_city, info["coords"])
        
        if data:
            current = data['current']
            daily = data['daily']
            
            # Cartes d'information
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.markdown(f"""
                <div class='weather-card'>
                    <h3>🌡️ Température</h3>
                    <p class='temp-big'>{current['temperature_2m']}°C</p>
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
                    <p class='temp-big'>{current['wind_speed_10m']} km/h</p>
                </div>
                """, unsafe_allow_html=True)
            
            with col4:
                weather_code = current.get('weather_code', 0)
                weather_info = WEATHER_CODES.get(weather_code, {"text": "Inconnu", "emoji": "🌤️"})
                st.markdown(f"""
                <div class='weather-card'>
                    <h3>☁️ État</h3>
                    <p style='font-size: 3em;'>{weather_info['emoji']}</p>
                </div>
                """, unsafe_allow_html=True)
            
            # Graphique des prévisions
            st.markdown("### 📅 Prévisions 7 jours")
            
            df = pd.DataFrame({
                'Date': daily['time'],
                'Min (°C)': daily['temperature_2m_min'],
                'Max (°C)': daily['temperature_2m_max']
            })
            
            fig = go.Figure()
            fig.add_trace(go.Scatter(x=df['Date'], y=df['Max (°C)'], name='Max', line=dict(color='red')))
            fig.add_trace(go.Scatter(x=df['Date'], y=df['Min (°C)'], name='Min', line=dict(color='blue')))
            
            fig.update_layout(
                title=f"Évolution des températures - {selected_city}",
                xaxis_title="Date",
                yaxis_title="Température (°C)",
                hovermode='x'
            )
            
            st.plotly_chart(fig, use_container_width=True)
# [Après votre page "🌍 Villes du Monde", avant "💬 Chat Météo"]

# ---- NOUVELLE PAGE : CARTE INTERACTIVE ----
elif menu == "🗺️ Carte interactive":
    st.markdown("## 🗺️ Carte Météo Interactive du Maroc")
    
    # Import des bibliothèques pour la carte
    import folium
    from streamlit_folium import st_folium
    from folium.plugins import MarkerCluster
    
    col1, col2 = st.columns([3, 1])
    
    with col2:
        st.markdown("### 🎨 Légende")
        
        # Options de personnalisation
        st.markdown("**Couleurs par température :**")
        st.markdown("""
        - 🔵 **Bleu** : < 15°C
        - 🟢 **Vert** : 15-20°C  
        - 🟡 **Jaune** : 20-25°C
        - 🟠 **Orange** : 25-30°C
        - 🔴 **Rouge** : > 30°C
        """)
        
        # Option pour afficher/masquer les noms
        show_names = st.checkbox("Afficher les noms des villes", value=True)
        
        # Option pour le type de carte
        map_type = st.selectbox(
            "Type de carte",
            ["OpenStreetMap", "Satellite", "Relief"]
        )
        
        st.markdown("---")
        st.markdown("### ℹ️ Informations")
        st.markdown("Cliquez sur un marqueur pour voir les détails météo en temps réel !")
    
    # Création de la carte Folium
    if map_type == "OpenStreetMap":
        tiles = "OpenStreetMap"
    elif map_type == "Satellite":
        tiles = "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}"
        attr = "Tiles © Esri"
    else:  # Relief
        tiles = "Stamen Terrain"
    
    m = folium.Map(
        location=[31.7917, -7.0926],  # Centre du Maroc
        zoom_start=6,
        tiles=tiles,
        attr=attr if map_type == "Satellite" else None
    )
    
    # Ajout d'un cluster pour regrouper les marqueurs si besoin
    marker_cluster = MarkerCluster().add_to(m)
    
    # Récupération des données météo pour chaque ville
    with st.spinner("Chargement des données météo..."):
        for city, info in VILLES_MAROC.items():
            data = get_weather(city, info["coords"])
            
            if data and 'current' in data:
                temp = data['current']['temperature_2m']
                weather_code = data['current'].get('weather_code', 0)
                weather_info = WEATHER_CODES.get(weather_code, {"text": "Inconnu", "emoji": "🌤️"})
                
                # Déterminer la couleur selon la température
                if temp < 15:
                    color = 'blue'
                elif temp < 20:
                    color = 'green'
                elif temp < 25:
                    color = 'yellow'
                elif temp < 30:
                    color = 'orange'
                else:
                    color = 'red'
                
                # Création du popup HTML riche
                popup_html = f"""
                <div style="font-family: Arial; min-width: 200px;">
                    <h3 style="margin: 0; color: #333;">{info['image']} {city}</h3>
                    <p style="color: #666; font-size: 12px;">{info['region']}</p>
                    <hr style="margin: 5px 0;">
                    <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 5px;">
                        <div style="text-align: center;">
                            <span style="font-size: 20px;">🌡️</span><br>
                            <strong>{temp}°C</strong>
                        </div>
                        <div style="text-align: center;">
                            <span style="font-size: 20px;">{weather_info['emoji']}</span><br>
                            <span>{weather_info['text']}</span>
                        </div>
                        <div style="text-align: center;">
                            <span style="font-size: 20px;">💧</span><br>
                            <strong>{data['current']['relative_humidity_2m']}%</strong>
                        </div>
                        <div style="text-align: center;">
                            <span style="font-size: 20px;">💨</span><br>
                            <strong>{data['current']['wind_speed_10m']} km/h</strong>
                        </div>
                    </div>
                    <hr style="margin: 5px 0;">
                    <p style="margin: 5px 0; font-style: italic;">{info['description']}</p>
                </div>
                """
                
                # Création du marqueur
                iframe = folium.IFrame(popup_html, width=250, height=250)
                popup = folium.Popup(iframe, max_width=300)
                
                # Choix de l'icône
                if color == 'red':
                    icon = 'fire'
                elif color == 'orange':
                    icon = 'warning'
                elif color == 'yellow':
                    icon = 'cloud-sun'
                elif color == 'green':
                    icon = 'leaf'
                else:
                    icon = 'snowflake'
                
                folium.Marker(
                    location=info["coords"],
                    popup=popup,
                    tooltip=f"{info['image']} {city} - {temp}°C" if show_names else None,
                    icon=folium.Icon(color=color, icon=icon, prefix='fa')
                ).add_to(marker_cluster if len(VILLES_MAROC) > 15 else m)
                
    with col1:
        # Affichage de la carte
        map_data = st_folium(
            m,
            width=800,
            height=600,
            returned_objects=["last_object_clicked", "last_clicked"]
        )
        
        # Si une ville est cliquée, afficher plus de détails
        if map_data and map_data["last_object_clicked"]:
            st.success("✅ Ville sélectionnée ! Consultez les détails ci-dessous.")
            
            # Trouver la ville cliquée (simplifié - dans un cas réel, il faudrait identifier précisément)
            clicked_coords = (
                map_data["last_object_clicked"]["lat"],
                map_data["last_object_clicked"]["lng"]
            )
            
            # Recherche de la ville la plus proche
            min_distance = float('inf')
            closest_city = None
            
            for city, info in VILLES_MAROC.items():
                dist = ((info["coords"][0] - clicked_coords[0])**2 + 
                       (info["coords"][1] - clicked_coords[1])**2)**0.5
                if dist < min_distance and dist < 0.5:  # Seuil de 0.5 degrés
                    min_distance = dist
                    closest_city = city
            
            if closest_city:
                st.info(f"**Ville sélectionnée : {closest_city}**")
                
                # Afficher les prévisions pour cette ville
                data = get_weather(closest_city, VILLES_MAROC[closest_city]["coords"])
                if data and 'daily' in data:
                    df = pd.DataFrame({
                        'Date': data['daily']['time'][:5],
                        'Min': data['daily']['temperature_2m_min'][:5],
                        'Max': data['daily']['temperature_2m_max'][:5]
                    })
                    
                    fig = px.line(df, x='Date', y=['Min', 'Max'],
                                 title=f"Prévisions 5 jours - {closest_city}",
                                 labels={'value': 'Température (°C)', 'variable': ''})
                    st.plotly_chart(fig, use_container_width=True)
# Page Villes du Monde
elif menu == "🌍 Villes du Monde":
    st.markdown("## 🌍 Météo des Villes Internationales")
    
    # Sélection de la ville
    col1, col2 = st.columns([1, 3])
    
    with col1:
        selected_city = st.selectbox("Choisissez une ville", list(VILLES_MONDE.keys()))
    
    if selected_city:
        coords = VILLES_MONDE[selected_city]
        data = get_weather(selected_city, coords)
        
        if data:
            current = data['current']
            daily = data['daily']
            
            # Cartes d'information
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.markdown(f"""
                <div class='weather-card'>
                    <h3>🌡️ Température</h3>
                    <p class='temp-big'>{current['temperature_2m']}°C</p>
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
                    <p class='temp-big'>{current['wind_speed_10m']} km/h</p>
                </div>
                """, unsafe_allow_html=True)
            
            with col4:
                weather_code = current.get('weather_code', 0)
                weather_info = WEATHER_CODES.get(weather_code, {"text": "Inconnu", "emoji": "🌤️"})
                st.markdown(f"""
                <div class='weather-card'>
                    <h3>☁️ État</h3>
                    <p style='font-size: 3em;'>{weather_info['emoji']}</p>
                </div>
                """, unsafe_allow_html=True)
            
            # Graphique des prévisions
            st.markdown("### 📅 Prévisions 7 jours")
            
            df = pd.DataFrame({
                'Date': daily['time'],
                'Min (°C)': daily['temperature_2m_min'],
                'Max (°C)': daily['temperature_2m_max']
            })
            
            fig = go.Figure()
            fig.add_trace(go.Scatter(x=df['Date'], y=df['Max (°C)'], name='Max', line=dict(color='red')))
            fig.add_trace(go.Scatter(x=df['Date'], y=df['Min (°C)'], name='Min', line=dict(color='blue')))
            
            fig.update_layout(
                title=f"Évolution des températures - {selected_city}",
                xaxis_title="Date",
                yaxis_title="Température (°C)",
                hovermode='x'
            )
            
            st.plotly_chart(fig, use_container_width=True)
            
            # Informations supplémentaires
            with st.expander("ℹ️ Informations sur la ville"):
                st.markdown(f"""
                - **Ville** : {selected_city}
                - **Coordonnées** : {coords[0]:.2f}°N, {coords[1]:.2f}°E
                - **Fuseau horaire** : {data.get('timezone', 'N/A')}
                """)
        else:
            st.error(f"Impossible de récupérer les données météo pour {selected_city}")					
# Page Chat Météo
elif menu == "💬 Chat Météo":
    st.markdown("## 💬 Discutez avec votre Expert Météo")
    
    # Initialisation de l'historique
    if "messages" not in st.session_state:
        st.session_state.messages = [
            {"role": "assistant", "content": "Bonjour ! Je suis votre expert météo. Posez-moi toutes vos questions sur le climat, les températures, ou comparez des villes ! 🌤️"}
        ]
    
    # Affichage des messages
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
    
    # Input utilisateur
    if prompt := st.chat_input("Posez votre question météo..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)
        
        with st.chat_message("assistant"):
            with st.spinner("Analyse météo en cours..."):
                # Appel à l'API
                response = client.chat.completions.create(
                    model="openrouter/free",
                    messages=[
                        {"role": "system", "content": "Tu es un expert météorologue spécialiste du Maroc et des grandes villes mondiales."},
                        *st.session_state.messages
                    ],
                    temperature=0.7
                )
                
                reply = response.choices[0].message.content
                st.markdown(reply)
                st.session_state.messages.append({"role": "assistant", "content": reply})

# Page Comparateur
elif menu == "📊 Comparateur":
    st.markdown("## 📊 Comparez les Villes")
    
    col1, col2 = st.columns(2)
    
    with col1:
        city1 = st.selectbox("Ville 1", list(VILLES_MAROC.keys()), index=0)
    
    with col2:
        city2 = st.selectbox("Ville 2", list(VILLES_MAROC.keys()), index=1)
    
    if st.button("Comparer", use_container_width=True):
        data1 = get_weather(city1, VILLES_MAROC[city1]["coords"])
        data2 = get_weather(city2, VILLES_MAROC[city2]["coords"])
        
        if data1 and data2:
            comparison_data = {
                "Ville": [city1, city2],
                "Température (°C)": [data1['current']['temperature_2m'], data2['current']['temperature_2m']],
                "Humidité (%)": [data1['current']['relative_humidity_2m'], data2['current']['relative_humidity_2m']],
                "Vent (km/h)": [data1['current']['wind_speed_10m'], data2['current']['wind_speed_10m']]
            }
            
            df = pd.DataFrame(comparison_data)
            
            fig = px.bar(df, x='Ville', y=['Température (°C)', 'Humidité (%)', 'Vent (km/h)'],
                        title="Comparaison Météo",
                        barmode='group')
            
            st.plotly_chart(fig, use_container_width=True)
            
            # Tableau détaillé
            st.dataframe(df, use_container_width=True)

# Page Historique
elif menu == "📁 Historique":
    st.markdown("## 📁 Historique des Recherches")
    
    # Afficher les fichiers de sauvegarde
    import glob
    
    files = glob.glob("meteo_*.txt")
    if files:
        selected_file = st.selectbox("Sélectionnez une date", files)
        
        if selected_file:
            with open(selected_file, "r", encoding="utf-8") as f:
                content = f.read()
            st.text_area("Contenu", content, height=400)
    else:
        st.info("Aucun historique disponible")

# Footer
st.markdown("---")
st.markdown("""
<div style='text-align: center; color: white; padding: 20px;'>
    Développé avec ❤️ pour le Maroc | Agent Météo Intelligent © 2026
</div>
""", unsafe_allow_html=True)