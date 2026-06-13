import asyncio
import logging
import json
import sys
import os

# Ajustement du path pour l'importation du module partagé au runtime
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from mcp.server import Server
from mcp.server.stdio import stdio_server
import mcp.types as types
from shared_models.conjecture import Conjecture
from engine import GraphLocalSearchEngine

# Configuration d'un logging structuré sur stderr (car stdout est réservé au protocole MCP)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    stream=sys.stderr
)
logger = logging.getLogger("mcp-invalidator-server")

# Initialisation du serveur MCP
app = Server("mcp-invalidator")
search_engine = GraphLocalSearchEngine()

@app.list_tools()
async def handle_list_tools() -> list[types.Tool]:
    """Déclare les outils mathématiques disponibles pour l'agent LLM."""
    logger.info("L'agent LLM a demandé la liste des outils disponibles.")
    return [
        types.Tool(
            name="invalidate_conjecture",
            description=(
                "Prend en entrée une conjecture mathématique formalisée en JSON. "
                "Exécute une recherche locale heuristique via des mutations de graphes (NetworkX) "
                "pour tenter de trouver un contre-exemple qui falsifie la conjecture. "
                "Retourne un échec ou un succès avec le graphe au format graph6 (g6)."
            ),
            inputSchema=Conjecture.model_json_schema()
        )
    ]

@app.call_tool()
async def handle_call_tool(name: str, arguments: dict | None) -> list[types.TextContent]:
    """Exécute l'outil demandé par le contrôleur avec validation stricte."""
    if name != "invalidate_conjecture":
        logger.error(f"Tentative d'appel d'un outil inconnu : {name}")
        raise ValueError(f"Outil inconnu : {name}")

    if not arguments:
        logger.error("Arguments manquants pour l'outil 'invalidate_conjecture'")
        raise ValueError("Arguments requis manquants.")

    logger.info(f"Exécution de l'invalidation pour la conjecture ID: {arguments.get('id')}")
    
    try:
        # Validation immédiate par le modèle Pydantic
        conjecture = Conjecture(**arguments)
        
        # Lancement de la recherche locale
        import networkx as nx
        result = search_engine.search_counterexample(conjecture)
        
        if result:
            G, metrics = result
            # Conversion du graphe NetworkX au format standardisé graph6 exigé
            g6_bytes = nx.to_graph6_bytes(G, header=False)
            g6_str = g6_bytes.decode('ascii').strip()
            
            response_payload = {
                "status": "counterexample_found",
                "conjecture_id": conjecture.id,
                "graph": {
                    "format": "graph6",
                    "value": g6_str
                },
                "metrics": metrics
            }
            logger.info(f"🔴 Contre-exemple TROUVÉ pour {conjecture.id} après {metrics['iterations']} itérations.")
        else:
            response_payload = {
                "status": "no_counterexample_found",
                "conjecture_id": conjecture.id,
                "message": f"Aucun contre-exemple trouvé dans la limite des {conjecture.timeout_seconds}s."
            }
            logger.info(f"🟢 Aucun contre-exemple détecté pour {conjecture.id} (Conjecture potentiellement vraie).")

        return [
            types.TextContent(
                type="text",
                text=json.dumps(response_payload, indent=2, ensure_ascii=False)
            )
        ]

    except Exception as e:
        logger.exception(f"Erreur critique lors du traitement de l'outil : {str(e)}")
        error_payload = {
            "status": "error",
            "message": str(e)
        }
        return [
            types.TextContent(
                type="text",
                text=json.dumps(error_payload, indent=2)
            )
        ]

async def main():
    """Point d'entrée du serveur communiquant via les flux standards d'E/S (stdio)."""
    logger.info("Démarrage du serveur MCP Invalidator en mode STDIO...")
    async with stdio_server() as (read_stream, write_stream):
        await app.run(
            read_stream,
            write_stream,
            app.create_initialization_options()
        )

if __name__ == "__main__":
    asyncio.run(main())