import asyncio
import logging
import json
import os
import sys
import requests
from dotenv import load_dotenv

# Ajout du dossier racine pour l'import des modèles partagés
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from shared_models.conjecture import Conjecture

# Importation des structures clientes officielles du SDK MCP
from mcp import StdioServerParameters
from mcp.client.stdio import stdio_client
from mcp.client.session import ClientSession

# Chargement de la configuration d'environnement
load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] Orchestrateur: %(message)s",
    stream=sys.stdout
)
logger = logging.getLogger("agent-controller")

class GraphResearchOrchestrator:
    def __init__(self):
        self.ollama_url = os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434")
        self.model_name = os.getenv("LLM_MODEL", "gemma2:2b")
        
        # Définition des paramètres de lancement standardisés pour chaque microservice
        self.invalidator_params = StdioServerParameters(
            command="python3",
            args=["mcp-invalidator/server.py"]
        )
        self.tools_params = StdioServerParameters(
            command="python3",
            args=["mcp-graph-tools/server.py"]
        )
        self.prover_params = StdioServerParameters(
            command="python3",
            args=["mcp-prover/server.py"]
        )

    def generate_conjecture_via_llm(self) -> dict:
        """Fait appel au LLM local (Ollama) pour concevoir une nouvelle hypothèse de recherche."""
        logger.info(f"Interrogation du modèle LLM '{self.model_name}' pour concevoir une conjecture...")
        
        prompt = (
            "Tu es un chercheur d'élite en théorie des graphes. Tu devez générer une conjecture mathématique "
            "FAUSSE mais subtile, sous la forme d'un objet JSON strict respectant exactement ce schéma :\n"
            "{\n"
            "  \"id\": \"CONJ-2026-001\",\n"
            "  \"graph_class\": \"connected\",\n"
            "  \"left_invariant\": \"diam\",\n"
            "  \"relation\": \"<=\",\n"
            "  \"right_expression\": \"rad / 2.0\",\n"
            "  \"max_order\": 15,\n"
            "  \"timeout_seconds\": 10\n"
            "}\n"
            "Ne renvoie RIEN d'autre que le JSON brut. Pas d'explications, pas de balises markdown."
        )

        try:
            res = requests.post(
                f"{self.ollama_url}/api/generate",
                json={"model": self.model_name, "prompt": prompt, "stream": False},
                timeout=5
            )
            if res.status_code == 200:
                text_response = res.json().get("response", "").strip()
                text_response = text_response.replace("```json", "").replace("```", "").strip()
                return json.loads(text_response)
        except Exception as e:
            logger.warning("Ollama indisponible ou timeout atteint. Utilisation de la conjecture de repli mathématique.")
        
        # Fallback mathématique déterministe
        return {
            "id": "CONJ-FALLBACK-01",
            "graph_class": "connected",
            "left_invariant": "diam",
            "relation": "<=",
            "right_expression": "rad / 2.0",
            "max_order": 15,
            "timeout_seconds": 5
        }

    async def execute_scientific_loop(self):
        """Lance le cycle de recherche en se connectant via le SDK client officiel."""
        
        # Étape 1 : Génération de l'hypothèse (indépendante des serveurs MCP)
        raw_conjecture = self.generate_conjecture_via_llm()
        logger.info(f"🔬 Conjecture cible chargée : {json.dumps(raw_conjecture, indent=2)}")

        logger.info("Connexion simultanée aux infrastructures MCP et initialisation des protocoles...")
        
        # Étape 2 : Ouverture des trois tunnels de communication stdio officiels
        async with stdio_client(self.invalidator_params) as (read_inv, write_inv), \
                   stdio_client(self.tools_params) as (read_tools, write_tools), \
                   stdio_client(self.prover_params) as (read_prov, write_prov):
                   
            # Étape 3 : Initialisation des sessions MCP avec poignée de main (handshake) automatique
            async with ClientSession(read_inv, write_inv) as session_inv, \
                       ClientSession(read_tools, write_tools) as session_tools, \
                       ClientSession(read_prov, write_prov) as session_prov:
                       
                # Exécution formelle de l'initialisation requise par la spécification MCP
                await session_inv.initialize()
                await session_tools.initialize()
                await session_prov.initialize()
                logger.info("🚀 Tous les serveurs MCP sont correctement initialisés et synchronisés.")

                try:
                    # Étape 4 : Soumission de la conjecture à l'invalidateur heuristique
                    logger.info("Soumission de la conjecture à l'outil 'invalidate_conjecture'...")
                    inv_response = await session_inv.call_tool(
                        name="invalidate_conjecture",
                        arguments=raw_conjecture
                    )
                    
                    # Extraction et décodage de la réponse texte
                    inv_result = json.loads(inv_response.content[0].text)
                    
                    if inv_result.get("status") == "counterexample_found":
                        g6_graph = inv_result["graph"]["value"]
                        logger.info(f"🔴 Contre-exemple trouvé par l'invalidateur : {g6_graph}. Lancement de l'audit indépendant...")

                        # Étape 5 : Double-Vérification Indépendante via Graph Tools
                        audit_args = {
                            "conjecture": raw_conjecture,
                            "graph6_value": g6_graph
                        }
                        audit_response = await session_tools.call_tool(
                            name="verify_counterexample",
                            arguments=audit_args
                        )
                        audit_result = json.loads(audit_response.content[0].text)
                        
                        if audit_result.get("verified") is True:
                            logger.info("✅ ALERTE : Le contre-exemple est CERTIFIÉ conforme par l'audit indépendant ! Conjecture réfutée.")
                            output_path = f"./data/false_conjectures/{raw_conjecture['id']}.json"
                            with open(output_path, "w", encoding="utf-8") as f:
                                json.dump({"conjecture": raw_conjecture, "audit": audit_result}, f, indent=4)
                            logger.info(f"Fichier d'archivage scientifique sauvegardé sous : {output_path}")
                        else:
                            logger.error("❌ CRITIQUE : Le serveur d'audit a détecté un FAUX POSITIF produit par l'invalidateur !")
                    
                    elif inv_result.get("status") == "no_counterexample_found":
                        logger.info("Ici, aucun contre-exemple n'a pu détruire l'hypothèse. Passage à la preuve formelle...")

                        # Étape 6 : Génération et enregistrement de la preuve Lean 4
                        prover_response = await session_prov.call_tool(
                            name="prove_conjecture",
                            arguments=raw_conjecture
                        )
                        prover_result = json.loads(prover_response.content[0].text)
                        
                        output_path = f"./data/true_conjectures/{raw_conjecture['id']}.json"
                        with open(output_path, "w", encoding="utf-8") as f:
                            json.dump({"conjecture": raw_conjecture, "prover": prover_result}, f, indent=4)
                        logger.info(f"Fichier de théorème potentiel archivé sous : {output_path}")

                except Exception as e:
                    logger.exception(f"Erreur au cours de l'exécution d'un outil MCP : {str(e)}")

if __name__ == "__main__":
    orchestrator = GraphResearchOrchestrator()
    asyncio.run(orchestrator.execute_scientific_loop())
