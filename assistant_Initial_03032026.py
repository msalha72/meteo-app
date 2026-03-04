import openai
import os
from dotenv import load_dotenv

# Charge la clé API depuis .env
load_dotenv()

class AssistantPersonnel:
    def __init__(self):
        # Récupère la clé API
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("Clé API non trouvée. Vérifie le fichier .env")
        
        self.client = openai.OpenAI(api_key=api_key,base_url="https://openrouter.ai/api/v1")
        self.conversation = [{"role": "system", "content": "Tu es un critique gastronomique très snob qui donne des recettes simples mais en les décrivant avec un langage ultra-prétentieux"}]
		#self.conversation = [{"role": "system", "content": "Tu es un critique gastronomique très snob qui donne des recettes simples mais en les décrivant avec un langage ultra-prétentieux"}]
		#self.conversation = [{"role": "system", "content": "Tu es un critique gastronomique très snob qui donne des recettes simples mais en les décrivant avec un langage ultra-prétentieux"}]	
		# Un professeur de maths sévère
		#self.conversation = [{"role": "system", "content": "Tu es un professeur de mathématiques sévère qui refuse de donner les réponses directement, mais guide l'élève"}]
		# Un guide touristique enthousiaste
		#self.conversation = [{"role": "system", "content": "Tu es un guide touristique qui s'extasie sur chaque détail et donne des anecdotes historiques farfelues"}]

		# Un poète maudit
		#self.conversation = [{"role": "system", "content": "Tu es un poète romantique du 19ème siècle, tu réponds toujours en alexandrins"}]

		# Un pirate des caraïbes
		#self-conversation = [{"role": "system", "content": "Tu es un vieux loup de mer, capitaine de bateau pirate, tu parles avec l'accent et les expressions des pirates"}]
		

		
        
    def sauvegarder_conversation(self, filename="conversations_chef.txt"):
        """Sauvegarde toute la conversation dans un fichier texte"""
        with open(filename, "a", encoding="utf-8") as f:
            f.write("\n" + "="*60 + "\n")
            f.write(f"NOUVELLE CONVERSATION - {__import__('datetime').datetime.now()}\n")
            f.write("="*60 + "\n")
            for msg in self.conversation:
                if msg['role'] == 'system':
                    f.write(f"⚙️ System: {msg['content']}\n")
                elif msg['role'] == 'user':
                    f.write(f"👤 Vous: {msg['content']}\n")
                else:
                    f.write(f"🤖 Assistant: {msg['content']}\n")
            f.write("="*60 + "\n\n")
    
    def demarrer(self):
        print("\n" + "="*50)
        print("🤖 Chef IA - Tape 'quit' pour quitter")
        print("📝 Tape 'save' pour sauvegarder")
        print("="*50 + "\n")
        
        while True:
            user_input = input("Vous: ").strip()
            
            if user_input.lower() == 'quit':
                self.sauvegarder_conversation()
                print("\nAu revoir ! 👋")
                print(f"💾 Conversation sauvegardée dans conversations_chef.txt")
                break
                
            elif user_input.lower() == 'save':
                self.sauvegarder_conversation()
                print("💾 Conversation sauvegardée !")
                continue
                
            if not user_input:
                continue
                
            print("\nChef réfléchit...", end="", flush=True)
            try:
                reponse = self.obtenir_reponse(user_input)
                print("\r", end="")
                print(f"Chef: {reponse}\n")
            except Exception as e:
                print(f"\rErreur: {e}\n")
    
    def obtenir_reponse(self, message):
        self.conversation.append({"role": "user", "content": message})
        
        reponse = self.client.chat.completions.create(
            model="stepfun/step-3.5-flash:free",
            messages=self.conversation,
            temperature=0.7,
            max_tokens=800
        )
        
        texte_reponse = reponse.choices[0].message.content
        self.conversation.append({"role": "assistant", "content": texte_reponse})
        
        if len(self.conversation) > 10:
            self.conversation = self.conversation[-10:]
            
        return texte_reponse

if __name__ == "__main__":
    try:
        assistant = AssistantPersonnel()
        assistant.demarrer()
    except ValueError as e:
        print(f"❌ Erreur: {e}")
        print("\n💡 Solution: Vérifie que ta clé API est bien dans .env")
    except Exception as e:
        print(f"❌ Erreur inattendue: {e}")