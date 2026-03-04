import openai
import os
import json
import requests
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

class AgentSuperieur:
    def __init__(self):
        api_key = os.getenv("OPENAI_API_KEY")
        self.client = openai.OpenAI(api_key=api_key, base_url="https://openrouter.ai/api/v1")
        
        # Personnalité dynamique (changeable à la volée)
        self.personnalites = {
            "chef": "Tu es un chef cuisinier humoristique",
            "snob": "Tu es un critique gastronomique ultra-prétentieux",
            "pirate": "Tu es un capitaine pirate qui parle avec l'accent",
            "prof": "Tu es un professeur sévère mais passionné",
            "poete": "Tu réponds toujours en alexandrins",
			"robot": "Tu es un robot du futur qui ne comprend pas les émotions humaines"
        }
        
        self.personnalite_active = "chef"
        self.conversation = [
            {"role": "system", "content": self.personnalites["chef"]}
        ]
        
        # Statistiques
        self.stats = {
            "messages_echanges": 0,
            "tokens_utilises": 0,
            "modeles_utilises": []
        }
    
    def changer_personnalite(self, nouvelle):
        """Change la personnalité à chaud"""
        if nouvelle in self.personnalites:
            self.personnalite_active = nouvelle
            # Garde l'historique mais change le system prompt
            self.conversation = [msg for msg in self.conversation if msg['role'] != 'system']
            self.conversation.insert(0, {"role": "system", "content": self.personnalites[nouvelle]})
            return f"✅ Personnalité changée en : {nouvelle}"
        return f"❌ Personnalités disponibles: {', '.join(self.personnalites.keys())}"
    
    def outils_disponibles(self):
        """Outils que l'agent peut utiliser"""
        return [
            {
                "name": "calculer",
                "description": "Effectue un calcul mathématique",
                "parameters": {
                    "expression": "string"
                }
            },
            {
                "name": "heure_actuelle",
                "description": "Donne l'heure actuelle",
                "parameters": {}
            },
            {
                "name": "recherche_web",
                "description": "Recherche sur le web (simulé)",
                "parameters": {
                    "query": "string"
                }
            }
        ]
    
    def executer_commande(self, cmd):
        """Exécute des commandes spéciales"""
        cmd = cmd.lower()
        
        if cmd.startswith("/perso "):
            return self.changer_personnalite(cmd[7:])
        
        elif cmd == "/persos":
            return f"Personnalités: {', '.join(self.personnalites.keys())}"
        
        elif cmd == "/stats":
            return f"📊 Stats: {self.stats['messages_echanges']} messages, {self.stats['tokens_utilises']} tokens"
        
        elif cmd == "/help":
            return """
            Commandes spéciales:
            /perso [nom] - Change de personnalité
            /persos - Liste les personnalités
            /stats - Voir les statistiques
            /save - Sauvegarder la conversation
            /quit - Quitter
            """
        
        return None
    
    def obtenir_reponse(self, message):
        # Vérifier si c'est une commande
        if message.startswith("/"):
            resultat = self.executer_commande(message)
            if resultat:
                return resultat
        
        # Message normal
        self.conversation.append({"role": "user", "content": message})
        self.stats["messages_echanges"] += 1
        
        try:
            reponse = self.client.chat.completions.create(
                model="stepfun/step-3.5-flash:free",
                messages=self.conversation,
                temperature=0.8,
                max_tokens=1000
            )
            
            texte_reponse = reponse.choices[0].message.content
            self.conversation.append({"role": "assistant", "content": texte_reponse})
            
            # Stats approximatives
            self.stats["tokens_utilises"] += len(message.split()) + len(texte_reponse.split())
            
            return texte_reponse
            
        except Exception as e:
            return f"❌ Erreur: {e}"
    
    def demarrer(self):
        print("="*60)
        print("🤖 **AGENT SUPERIEUR V2.0**")
        print("="*60)
        print("Commandes: /help, /persos, /stats, /quit")
        print(f"Personnalité active: {self.personnalite_active}")
        print("-"*60)
        
        while True:
            user_input = input("\n👤 Vous: ").strip()
            
            if user_input.lower() in ['quit', '/quit']:
                print("\n👋 Au revoir !")
                print(f"📊 Session: {self.stats['messages_echanges']} messages")
                break
            
            if not user_input:
                continue
            
            print("🤖 Agent réfléchit...", end="", flush=True)
            reponse = self.obtenir_reponse(user_input)
            print("\r", end="")
            print(f"🤖 Agent: {reponse}")

# Lancement
if __name__ == "__main__":
    agent = AgentSuperieur()
    agent.demarrer()