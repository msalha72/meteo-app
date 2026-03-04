import openai
import os
from dotenv import load_dotenv

load_dotenv()

api_key = os.getenv("OPENAI_API_KEY")
print(f"Clé trouvée: {api_key[:10]}... (cachée pour sécurité)")

try:
    client = openai.OpenAI(api_key=api_key)
    # Test simple : lister les modèles disponibles
    models = client.models.list()
    print("✅ Connexion réussie ! La clé fonctionne.")
    print(f"Modèles disponibles: {len(models.data)} modèles")
except Exception as e:
    print(f"❌ Erreur: {e}")