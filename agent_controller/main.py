import asyncio
import logging
import json
import os
import time
import random
import requests
from dotenv import load_dotenv
from mcp import StdioServerParameters
from mcp.client.stdio import stdio_client
from mcp.client.session import ClientSession

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] Orchestrateur: %(message)s"
)

logger = logging.getLogger("agent-controller")


class GraphResearchOrchestrator:
    def __init__(self):
        self.running = False

        self.ollama_url = os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434")
        self.model_name = os.getenv("LLM_MODEL", "gemma2:2b")

        # Racine du projet
        root_dir = os.path.dirname(os.path.abspath(__file__))

        self.invalidator_params = StdioServerParameters(
            command="python3",
            args=[os.path.join(root_dir, "mcp-invalidator/server.py")]
        )

        self.tools_params = StdioServerParameters(
            command="python3",
            args=[os.path.join(root_dir, "mcp-graph-tools/server.py")]
        )

        self.prover_params = StdioServerParameters(
            command="python3",
            args=[os.path.join(root_dir, "mcp-prover/server.py")]
        )

    # -----------------------------
    # Tracking fichiers
    # -----------------------------
    def log_in_progress(self, conjecture):
        data_dir = os.path.abspath(
            os.path.join(os.path.dirname(__file__), "../data/in_progress")
        )

        os.makedirs(data_dir, exist_ok=True)

        path = os.path.join(data_dir, f"{conjecture['id']}.json")

        with open(path, "w") as f:
            json.dump(
                {
                    "conjecture": conjecture,
                    "status": "processing"
                },
                f,
                indent=4
            )

    def cleanup_in_progress(self, conjecture_id):
        data_dir = os.path.abspath(
            os.path.join(os.path.dirname(__file__), "../data/in_progress")
        )

        path = os.path.join(data_dir, f"{conjecture_id}.json")

        if os.path.exists(path):
            os.remove(path)

    def log_result(self, conjecture, is_true):
        # Détermine le dossier cible
        folder = "true_conjectures" if is_true else "false_conjectures"

        target_dir = os.path.abspath(
            os.path.join(
                os.path.dirname(__file__),
                f"../data/{folder}"
            )
        )

        os.makedirs(target_dir, exist_ok=True)

        # Écriture du fichier final
        path = os.path.join(
            target_dir,
            f"{conjecture['id']}.json"
        )

        with open(path, "w") as f:
            json.dump(
                {
                    "conjecture": conjecture,
                    "status": "validated"
                },
                f,
                indent=4
            )

        # Nettoyage du dossier in_progress
        self.cleanup_in_progress(conjecture["id"])

    def stop(self):
        self.running = False
        logger.info("⏹ Arrêt demandé.")

    # -----------------------------
    # Boucle scientifique
    # -----------------------------
    async def execute_scientific_loop(self):
        self.running = True
        logger.info("🚀 Boucle de recherche démarrée")

        while self.running:
            try:
                # 1. Création d'une conjecture
                conjecture = {
                    "id": f"TEST-{time.time_ns() % 1000}",
                    "invariant": "diam",
                    "relation": "<=",
                    "value": "2.0"
                }

                logger.info(
                    f"Nouvelle conjecture générée : {conjecture['id']}"
                )

                # 2. Ajout dans in_progress
                self.log_in_progress(conjecture)

                # 3. Traitement simulé
                # (remplacer plus tard par les appels MCP)
                await asyncio.sleep(5)

                # 4. Décision simulée
                est_vrai = random.choice([True, False])

                # 5. Archivage du résultat
                self.log_result(conjecture, est_vrai)

                logger.info(
                    f"Conjecture {conjecture['id']} classée dans "
                    f"{'true_conjectures' if est_vrai else 'false_conjectures'}"
                )

                await asyncio.sleep(2)

            except Exception as e:
                logger.error(f"❌ ERREUR DANS LA BOUCLE : {e}")
                self.running = False

        logger.info("🛑 Boucle de recherche arrêtée.")


# -----------------------------
# MODE CONTRÔLÉ
# -----------------------------
if __name__ == "__main__":
    orchestrator = GraphResearchOrchestrator()

    print("Orchestrateur prêt (mode contrôlé).")

    # Ne pas lancer automatiquement :
    # asyncio.run(orchestrator.execute_scientific_loop())