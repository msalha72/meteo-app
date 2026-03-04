import openai
import os
import json
import requests
from datetime import datetime
from tabulate import tabulate
import time
from dotenv import load_dotenv
import urllib.parse

load_dotenv()

class AgentMeteoSpecialiste:
    def __init__(self):
        api_key = os.getenv("OPENAI_API_KEY")
        self.client = openai.OpenAI(api_key=api_key, base_url="https://openrouter.ai/api/v1")
        
        # Configuration météo
        self.sources_meteo = {
            "wttr": self.meteo_wttr,
            "openweather": self.meteo_openweather,
        }
        self.source_active = "wttr"
        
        # Cache pour ne pas surcharger les APIs
        self.cache = {}
        self.cache_duree = 30 * 60
        
        # Personnalité météo
        self.conversation = [
            {"role": "system", "content": """Tu es un météorologue expert, passionné et pédagogue. 
            Tu donnes des informations météo précises avec :
            - Température, ressenti, humidité, vent, pression
            - Prévisions sur plusieurs jours
            - Alertes éventuelles
            - Explications des phénomènes météo
            Tu utilises un langage clair mais technique quand nécessaire.
            Tu peux comparer la météo entre différentes villes."""}
        ]
        
        self.stats = {
            "requetes": 0,
            "villes_consultees": set(),
            "sources_utilisees": {}
        }
    
    def meteo_wttr(self, lieu, jours=1):
        """Source: wttr.in avec meilleure gestion d'erreurs"""
        try:
            lieu_encoded = urllib.parse.quote(lieu)
            
            urls = [
                f"https://wttr.in/{lieu_encoded}?format=j1&lang=fr",
                f"https://wttr.in/{lieu_encoded}?format=%c+%t+%w+%h&lang=fr",
                f"https://wttr.dromozoa.com/{lieu_encoded}?format=j1&lang=fr"
            ]
            
            for url in urls:
                try:
                    response = requests.get(url, timeout=15)
                    if response.status_code == 200:
                        if "j1" in url:
                            data = response.json()
                            current = data['current_condition'][0]
                            
                            meteo = {
                                "ville": lieu,
                                "temp": current['temp_C'],
                                "ressenti": current['FeelsLikeC'],
                                "humidite": current['humidity'],
                                "vent_kmh": current['windspeedKmph'],
                                "vent_dir": current['winddir16Point'],
                                "pression": current['pressure'],
                                "condition": current['lang_fr'][0]['value'],
                                "visibilite": current['visibility'],
                                "uv": current['uvIndex'],
                                "heure": datetime.now().strftime("%H:%M")
                            }
                            
                            previsions = []
                            for i in range(1, min(jours, 3)):
                                jour = data['weather'][i]
                                previsions.append({
                                    "date": jour['date'],
                                    "min": jour['mintempC'],
                                    "max": jour['maxtempC'],
                                    "condition": jour['hourly'][0]['lang_fr'][0]['value']
                                })
                            
                            meteo["previsions"] = previsions
                            return self.formater_meteo(meteo)
                        else:
                            return f"📍 **{lieu}**\n{response.text.strip()}"
                except:
                    continue
            
            return self.meteo_fallback(lieu)
            
        except Exception as e:
            return self.meteo_fallback(lieu)
    
    def meteo_openmeteo(self, lieu, jours=1):
        """Source Open-Meteo (fiable, gratuite, mondiale)"""
        try:
            villes_coords = {
                "casablanca": (33.5731, -7.5898),
                "casa": (33.5731, -7.5898),
                "rabat": (34.0209, -6.8416),
                "marrakech": (31.6295, -7.9811),
                "marrakesh": (31.6295, -7.9811),
                "tanger": (35.7595, -5.8340),
                "tangier": (35.7595, -5.8340),
                "agadir": (30.4278, -9.5981),
                "fes": (34.0331, -5.0003),
                "fès": (34.0331, -5.0003),
                "essaouira": (31.5125, -9.7700),
                "oujda": (34.6867, -1.9114),
                "laayoune": (27.1500, -13.2000),
                "dakhla": (23.6848, -15.9580),
                "paris": (48.8566, 2.3522),
                "lyon": (45.7640, 4.8357),
                "marseille": (43.2965, 5.3698),
            }
            
            # Nettoyer le nom de la ville (enlever accents, caractères spéciaux)
            lieu_clean = lieu.lower().split()[0]
            # Remplacer les caractères accentués
            lieu_clean = (lieu_clean.replace('é', 'e').replace('è', 'e').replace('ê', 'e')
                                   .replace('à', 'a').replace('â', 'a')
                                   .replace('ù', 'u').replace('û', 'u')
                                   .replace('ç', 'c'))
            
            if lieu_clean not in villes_coords:
                print(f"Ville '{lieu_clean}' non trouvée, fallback")
                return self.meteo_fallback(lieu)
            
            lat, lon = villes_coords[lieu_clean]
            
            url = "https://api.open-meteo.com/v1/forecast"
            params = {
                "latitude": lat,
                "longitude": lon,
                "current": ["temperature_2m", "relative_humidity_2m", "weather_code", "wind_speed_10m", "wind_direction_10m"],
                "daily": ["weather_code", "temperature_2m_max", "temperature_2m_min"],
                "timezone": "auto",
                "forecast_days": jours
            }
            
            response = requests.get(url, params=params, timeout=10)
            
            if response.status_code == 200:
                try:
                    data = response.json()
                except json.JSONDecodeError as e:
                    print(f"Erreur JSON: {e}")
                    return self.meteo_fallback(lieu)
                
                weather_codes = {
                    0: "☀️ Ciel dégagé", 1: "🌤️ Principalement dégagé", 2: "⛅ Partiellement nuageux",
                    3: "☁️ Nuageux", 45: "🌫️ Brouillard", 48: "🌫️ Brouillard givrant",
                    51: "🌧️ Bruine légère", 53: "🌧️ Bruine modérée", 55: "🌧️ Bruine dense",
                    61: "🌧️ Pluie légère", 63: "🌧️ Pluie modérée", 65: "🌧️ Pluie forte",
                    71: "❄️ Neige légère", 73: "❄️ Neige modérée", 75: "❄️ Neige forte",
                    80: "🌧️ Averses légères", 81: "🌧️ Averses modérées", 82: "🌧️ Averses violentes",
                    95: "⛈️ Orage", 96: "⛈️ Orage avec grêle", 99: "⛈️ Orage violent"
                }
                
                # Vérifier que les données existent
                if 'current' not in data:
                    return self.meteo_fallback(lieu)
                
                current = data.get('current', {})
                current_weather_code = current.get('weather_code', 0)
                condition = weather_codes.get(current_weather_code, "🌤️ Inconnu")
                
                meteo = {
                    "ville": lieu,
                    "temp": current.get('temperature_2m', 'N/A'),
                    "ressenti": current.get('temperature_2m', 'N/A'),
                    "humidite": current.get('relative_humidity_2m', 'N/A'),
                    "vent_kmh": current.get('wind_speed_10m', 'N/A'),
                    "vent_dir": self.wind_deg_to_dir(current.get('wind_direction_10m', 0)),
                    "condition": condition,
                    "heure": datetime.now().strftime("%H:%M"),
                    "source": "Open-Meteo"
                }
                
                if 'daily' in data and jours > 1:
                    previsions = []
                    for i in range(min(jours, 7)):
                        previsions.append({
                            "date": data['daily']['time'][i],
                            "min": data['daily']['temperature_2m_min'][i],
                            "max": data['daily']['temperature_2m_max'][i],
                            "condition": weather_codes.get(data['daily']['weather_code'][i], "🌤️")
                        })
                    meteo["previsions"] = previsions
                
                return self.formater_meteo(meteo)
            else:
                print(f"HTTP {response.status_code} pour {lieu}")
                return self.meteo_fallback(lieu)
                
        except Exception as e:
            print(f"Erreur Open-Meteo: {e}")
            return self.meteo_fallback(lieu)

    def wind_deg_to_dir(self, deg):
        """Convertit les degrés de vent en direction cardinale"""
        if deg is None:
            return "N/A"
        directions = ["N", "NNE", "NE", "ENE", "E", "ESE", "SE", "SSE",
                      "S", "SSW", "SW", "WSW", "W", "WNW", "NW", "NNW"]
        ix = round(deg / (360.0 / len(directions))) % len(directions)
        return directions[ix]

    def diagnostic_meteo(self, lieu):
        """Diagnostique pourquoi une ville ne fonctionne pas"""
        print(f"\n🔍 DIAGNOSTIC pour {lieu}:")
        
        # Dictionnaire des coordonnées (à garder synchronisé avec meteo_openmeteo)
        villes_coords = {
            "casablanca": (33.5731, -7.5898),
            "rabat": (34.0209, -6.8416),
            "marrakech": (31.6295, -7.9811),
            "tanger": (35.7595, -5.8340),
            "agadir": (30.4278, -9.5981),
            "fès": (34.0331, -5.0003),
            "essaouira": (31.5125, -9.7700),
            "oujda": (34.6867, -1.9114),
            "laayoune": (27.1500, -13.2000),
            "dakhla": (23.6848, -15.9580),
            "paris": (48.8566, 2.3522),
            "lyon": (45.7640, 4.8357),
            "marseille": (43.2965, 5.3698),
        }
        
        # Test 1: La ville est-elle dans le dictionnaire ?
        lieu_clean = lieu.lower().split()[0]
        print(f"  Ville normalisée: '{lieu_clean}'")
        
        if lieu_clean in villes_coords:
            print(f"  ✅ Ville trouvée dans le dictionnaire")
            lat, lon = villes_coords[lieu_clean]
            print(f"  Coordonnées: {lat}, {lon}")
            
            # Test 2: L'API Open-Meteo répond-elle ?
            try:
                url = "https://api.open-meteo.com/v1/forecast"
                params = {
                    "latitude": lat,
                    "longitude": lon,
                    "current": ["temperature_2m"],
                    "timezone": "auto"
                }
                response = requests.get(url, params=params, timeout=5)
                print(f"  Statut HTTP: {response.status_code}")
                if response.status_code == 200:
                    print("  ✅ API Open-Meteo OK")
                    data = response.json()
                    temp = data.get('current', {}).get('temperature_2m', 'N/A')
                    print(f"  Température actuelle: {temp}°C")
                    return True
                else:
                    print(f"  ❌ API Open-Meteo a répondu {response.status_code}")
            except Exception as e:
                print(f"  ❌ Erreur connexion: {e}")
        else:
            print(f"  ❌ Ville '{lieu_clean}' pas dans le dictionnaire")
            print(f"  Villes disponibles: {list(villes_coords.keys())}")
        
        return False

    def meteo_fallback(self, lieu):
        """Donne des infos climatiques générales quand l'API est indisponible"""
        if lieu is None:
            lieu = "inconnue"
            
        climats = {
            "paris": {"pays": "France", "type": "océanique", "ete": "18-25°C", "hiver": "3-8°C"},
            "lyon": {"pays": "France", "type": "continental", "ete": "20-28°C", "hiver": "1-6°C"},
            "marseille": {"pays": "France", "type": "méditerranéen", "ete": "22-30°C", "hiver": "5-12°C"},
            "londres": {"pays": "Royaume-Uni", "type": "océanique", "ete": "15-23°C", "hiver": "2-7°C"},
            "new york": {"pays": "USA", "type": "continental humide", "ete": "22-30°C", "hiver": "-2-5°C"},
            "tokyo": {"pays": "Japon", "type": "subtropical humide", "ete": "24-31°C", "hiver": "2-10°C"},
            "dubai": {"pays": "EAU", "type": "désertique", "ete": "32-45°C", "hiver": "15-25°C"},
            "casablanca": {"pays": "Maroc", "type": "méditerranéen", "ete": "22-28°C", "hiver": "9-17°C"},
            "rabat": {"pays": "Maroc", "type": "méditerranéen", "ete": "22-28°C", "hiver": "8-16°C"},
            "marrakech": {"pays": "Maroc", "type": "semi-aride", "ete": "28-38°C", "hiver": "7-19°C"},
            "tanger": {"pays": "Maroc", "type": "méditerranéen", "ete": "22-28°C", "hiver": "9-16°C"},
            "agadir": {"pays": "Maroc", "type": "semi-aride", "ete": "22-28°C", "hiver": "9-20°C"},
        }
        
        # Sécuriser le traitement du lieu
        try:
            lieu_clean = lieu.lower().split()[0] if lieu else "inconnue"
        except:
            lieu_clean = "inconnue"
            
        if lieu_clean in climats:
            c = climats[lieu_clean]
            return f"""
📍 **{lieu}** - Données climatiques générales
🌍 Climat {c['type']} ({c['pays']})

🌡️ **Températures typiques:**
   • Été: {c['ete']}
   • Hiver: {c['hiver']}

💡 **Conseil:** Les données en temps réel sont temporairement indisponibles.
   Consultez Météo-France ou Windy pour les conditions actuelles.
"""
        else:
            return f"""
📍 **{lieu}** - Informations climatiques générales
🌍 Climat tempéré (zone méditerranéenne)

💡 **Conseil:** Les données en temps réel sont temporairement indisponibles.
   Pour {lieu}, consultez un service météo local.
"""
    
    def meteo_openweather(self, lieu, jours=1):
        """Source alternative (à configurer avec clé API)"""
        api_key = os.getenv("OPENWEATHER_API_KEY")
        if not api_key:
            return "⚠️ Clé OpenWeatherMap non configurée, utilisation de wttr.in"
        return self.meteo_wttr(lieu, jours)
    
    def formater_meteo(self, data):
        """Formate les données météo en texte lisible"""
        if not data:
            return "Données météo indisponibles"
        
        condition = data['condition'].lower()
        if "soleil" in condition or "ensoleil" in condition:
            emoji = "☀️"
        elif "nuage" in condition:
            emoji = "☁️"
        elif "pluie" in condition or "averse" in condition:
            emoji = "🌧️"
        elif "orage" in condition:
            emoji = "⛈️"
        elif "neige" in condition:
            emoji = "❄️"
        elif "brouillard" in condition:
            emoji = "🌫️"
        else:
            emoji = "🌤️"
        
        message = f"""
📍 **{data['ville'].upper()}** - {data['heure']}
{emoji} **{data['condition']}**
🌡️ Température: {data['temp']}°C (ressenti {data['ressenti']}°C)
💧 Humidité: {data['humidite']}%
🌬️ Vent: {data['vent_kmh']} km/h ({data['vent_dir']})
📊 Pression: {data['pression']} hPa
👁️ Visibilité: {data['visibilite']} km
☀️ UV: {data['uv']}
"""
        
        if data.get('previsions'):
            message += "\n📅 **Prévisions:**\n"
            for prev in data['previsions']:
                message += f"   • {prev['date']}: {prev['min']}°C → {prev['max']}°C, {prev['condition']}\n"
        
        return message
    
    def comparer_villes(self, villes):
        """Compare la météo de plusieurs villes"""
        tableau = []
        for ville in villes:
            data = self.meteo_wttr(ville)
            tableau.append([ville, data[:50] + "..."])
        return tabulate(tableau, headers=["Ville", "Météo"], tablefmt="grid")
    
    def alerte_meteo(self, lieu):
        """Vérifie les conditions dangereuses"""
        data = self.meteo_wttr(lieu)
        if "orage" in data.lower() or "tempête" in data.lower():
            return f"⚠️ **ALERTE** à {lieu}: Conditions dangereuses détectées!"
        return f"✅ Aucune alerte particulière pour {lieu}"
    
    def outils_disponibles(self):
        """Outils météo disponibles"""
        return [
            {
                "type": "function",
                "function": {
                    "name": "meteo_actuelle",
                    "description": "Obtenir la météo actuelle pour une ville",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "ville": {"type": "string", "description": "Nom de la ville"},
                            "jours": {"type": "integer", "description": "Nombre de jours de prévision (1-3)", "default": 1}
                        },
                        "required": ["ville"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "comparer_villes",
                    "description": "Comparer la météo de plusieurs villes",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "villes": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "Liste des villes à comparer"
                            }
                        },
                        "required": ["villes"]
                    }
                }
            }
        ]
    
    def meteo_actuelle(self, ville, jours=1):
        """Wrapper pour appeler la météo"""
        return self.meteo_wttr(ville, jours)
    
    def executer_outil(self, nom_outil, arguments):
        """Exécute l'outil demandé"""
        if nom_outil == "meteo_actuelle":
            return self.meteo_actuelle(arguments.get("ville"), arguments.get("jours", 1))
        elif nom_outil == "comparer_villes":
            return self.comparer_villes(arguments.get("villes", []))
        else:
            return f"Outil {nom_outil} inconnu"
    def sauvegarder_retour_meteo(self, ville, reponse):
        """Sauvegarde un retour météo dans un fichier"""
        try:
            # Nom du fichier avec la date du jour
            date_jour = datetime.now().strftime("%Y-%m-%d")
            filename = f"meteo_{date_jour}.txt"
            
            # Formater l'entrée
            timestamp = datetime.now().strftime("%H:%M:%S")
            entree = f"""
{'='*60}
📅 Date: {date_jour} à {timestamp}
📍 Ville: {ville}
{'='*60}
{reponse}
{'-'*60}

"""
            # Sauvegarder dans le fichier
            with open(filename, "a", encoding="utf-8") as f:
                f.write(entree)
            
            print(f"💾 Retour météo sauvegardé dans {filename}")
            return True
        except Exception as e:
            print(f"❌ Erreur sauvegarde: {e}")
            return False
    def obtenir_reponse(self, message):
        """Méthode principale avec appel API et outils"""
        self.conversation.append({"role": "user", "content": message})
        self.stats["requetes"] += 1
        
        try:
            reponse = self.client.chat.completions.create(
                model="openrouter/free",
                messages=self.conversation,
                tools=self.outils_disponibles(),
                tool_choice="auto",
                temperature=0.7,
                max_tokens=1000
            )
            
            message_reponse = reponse.choices[0].message
            
            if message_reponse.tool_calls:
                self.conversation.append(message_reponse)
                
                for tool_call in message_reponse.tool_calls:
                    nom_outil = tool_call.function.name
                    arguments = json.loads(tool_call.function.arguments)
                    
                    resultat = self.executer_outil(nom_outil, arguments)
                    
                    self.conversation.append({
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "name": nom_outil,
                        "content": resultat
                    })
                    
                    if nom_outil == "meteo_actuelle":
                        self.stats["villes_consultees"].add(arguments.get("ville"))
                
                reponse_finale = self.client.chat.completions.create(
                    model="openrouter/free",
                    messages=self.conversation,
                    temperature=0.7
                )
                texte_reponse = reponse_finale.choices[0].message.content
            else:
                texte_reponse = message_reponse.content
            
            self.conversation.append({"role": "assistant", "content": texte_reponse})
            
            # 🔥 NOUVEAU : Sauvegarder automatiquement les retours météo
            if "météo" in message.lower() or "temp" in message.lower() or "climat" in message.lower():
                # Extraire la ville mentionnée (simplifié)
                mots = message.lower().split()
                ville_trouvee = None
                villes_connues = ["casablanca", "rabat", "marrakech", "tanger", "agadir", "fès", 
                                 "paris", "lyon", "marseille", "londres", "new york", "tokyo", "dubai"]
                
                for mot in mots:
                    if mot in villes_connues:
                        ville_trouvee = mot
                        break
                
                if ville_trouvee:
                    self.sauvegarder_retour_meteo(ville_trouvee, texte_reponse)
            
            return texte_reponse
            
        except Exception as e:
            return f"❌ Erreur: {e}"
    def meteo_weatherapi(self, lieu, jours=1):
        """Source alternative: WeatherAPI (gratuit, 1M requêtes/mois)"""
        # Nécessite une inscription gratuite sur https://www.weatherapi.com/
        api_key = os.getenv("WEATHERAPI_KEY")  # À ajouter dans .env
        if not api_key:
            return self.meteo_fallback(lieu)
            
        try:
            url = f"http://api.weatherapi.com/v1/current.json?key={api_key}&q={lieu}&lang=fr"
            response = requests.get(url, timeout=10)
            if response.status_code == 200:
                data = response.json()
                current = data['current']
                return f"""
📍 **{lieu}** - WeatherAPI
🌡️ Température: {current['temp_c']}°C (ressenti {current['feelslike_c']}°C)
💧 Humidité: {current['humidity']}%
🌬️ Vent: {current['wind_kph']} km/h ({current['wind_dir']})
👁️ Visibilité: {current['vis_km']} km
☀️ UV: {current['uv']}
"""
        except:
            return self.meteo_fallback(lieu)
    def demarrer(self):
        print("="*60)
        print("🌤️ **AGENT MÉTÉO SPÉCIALISTE**")
        print("="*60)
        print("Commandes spéciales:")
        print("  /alerte [ville] - Vérifier les alertes")
        print("  /compare [ville1,ville2] - Comparer des villes")
        print("  /stats - Voir les statistiques")
        print("  /help - Aide")
        print("="*60)
        
        while True:
            user_input = input("\n👤 Vous: ").strip()
            
            if user_input.lower() in ['quit', '/quit']:
                print("\n👋 À bientôt ! N'oubliez pas votre parapluie !")
                print(f"📊 Stats: {len(self.stats['villes_consultees'])} villes consultées")
                break
            
            if user_input.startswith("/alerte"):
                ville = user_input[8:].strip()
                if ville:
                    print(self.alerte_meteo(ville))
                continue
                
            elif user_input.startswith("/compare"):
                villes_str = user_input[9:].strip()
                villes = [v.strip() for v in villes_str.split(',')]
                print(self.comparer_villes(villes))
                continue
                
            elif user_input == "/stats":
                print(f"📊 Statistiques:")
                print(f"   Requêtes: {self.stats['requetes']}")
                print(f"   Villes consultées: {', '.join(self.stats['villes_consultees'])}")
                continue
                
            elif user_input == "/help":
                print("""
                Commandes:
                /alerte Paris     - Vérifier les alertes
                /compare Paris, Lyon - Comparer 2 villes
                /stats            - Voir les statistiques
                /help             - Cette aide
                /quit             - Quitter
                
                Ou posez simplement une question comme:
                "Quel temps fait-il à Marseille ?"
                "Météo à Tokyo pour 3 jours"
                "Y a-t-il des alertes à Bordeaux ?"
                """)
                continue
            
            if not user_input:
                continue
            
            print("🌤️ MétéoSpécialiste réfléchit...", end="", flush=True)
            reponse = self.obtenir_reponse(user_input)
            print("\r", end="")
            print(f"🌤️ MétéoSpécialiste:\n{reponse}")

if __name__ == "__main__":
    agent = AgentMeteoSpecialiste()
    agent.demarrer()