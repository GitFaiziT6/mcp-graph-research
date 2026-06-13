import asyncio
import logging
import json
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from mcp.server import Server
from mcp.server.stdio import stdio_server
import mcp.types as types
from shared_models.conjecture import Conjecture
from converter import GraphConverter

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    stream=sys.stderr
)
logger = logging.getLogger("mcp-graph-tools-server")

app = Server("mcp-graph-tools")

@app.list_tools()
async def handle_list_tools() -> list[types.Tool]:
    """Déclare l'outil de vérification cryptographique / mathématique indépendant."""
    return [
        types.Tool(
            name="verify_counterexample",
            description=(
                "Prend en entrée une conjecture formalisée ET un contre-exemple proposé au format graph6. "
                "Décode le graphe de manière indépendante, recalcule ses invariants et certifie si "
                "le contre-exemple brise effectivement la conjecture ou s'il s'agit d'un faux positif."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "conjecture": Conjecture.model_json_schema(),
                    "graph6_value": {
                        "type": "string",
                        "description": "La chaîne de caractères représentant le graphe à auditer."
                    }
                },
                "required": ["conjecture", "graph6_value"]
            }
        )
    ]

@app.call_tool()
async def handle_call_tool(name: str, arguments: dict | None) -> list[types.TextContent]:
    if name != "verify_counterexample":
        raise ValueError(f"Outil inconnu : {name}")

    if not arguments or "conjecture" not in arguments or "graph6_value" not in arguments:
        raise ValueError("Arguments 'conjecture' et 'graph6_value' requis.")

    try:
        conjecture = Conjecture(**arguments["conjecture"])
        g6_str = arguments["graph6_value"]

        # 1. Décodage du graphe via le Converter indépendant
        G = GraphConverter.from_graph6(g6_str)
        
        # 2. Recalcul indépendant des invariants
        invariants = GraphConverter.verify_graph_invariants(G)
        
        # 3. Ré-évaluation de la relation de la conjecture
        left_val = invariants.get(conjecture.left_invariant)
        
        # Import dynamique et sécurisé du parseur d'expressions de l'invalidateur pour ré-évaluation
        sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../mcp-invalidator')))
        from engine import SafeExpressionEvaluator, GraphLocalSearchEngine
        
        evaluator = SafeExpressionEvaluator(invariants)
        right_val = evaluator.evaluate(conjecture.right_expression)
        
        engine_helper = GraphLocalSearchEngine()
        is_relation_valid = engine_helper.evaluate_relation(left_val, conjecture.relation, right_val)
        is_class_valid = engine_helper.is_in_graph_class(G, conjecture.graph_class)

        # Le contre-exemple est certifié VALIDE si le graphe respecte la classe ET brise la relation
        is_counterexample_valid = is_class_valid and (not is_relation_valid)

        response_payload = {
            "verified": is_counterexample_valid,
            "conjecture_id": conjecture.id,
            "analysis": {
                "belongs_to_class": is_class_valid,
                "left_invariant_value": left_val,
                "right_expression_value": right_val,
                "relation_satisfied_by_graph": is_relation_valid
            },
            "invariants": invariants
        }

        logger.info(f"Audit terminé pour {conjecture.id}. Certifié : {is_counterexample_valid}")
        return [
            types.TextContent(
                type="text",
                text=json.dumps(response_payload, indent=2, ensure_ascii=False)
            )
        ]

    except Exception as e:
        logger.exception("Erreur lors de la double-vérification du graphe.")
        return [
            types.TextContent(
                type="text",
                text=json.dumps({"verified": False, "error": str(e)}, indent=2)
            )
        ]

async def main():
    logger.info("Démarrage du serveur MCP Graph Tools (stdio)...")
    async with stdio_server() as (read_stream, write_stream):
        await app.run(read_stream, write_stream, app.create_initialization_options())

if __name__ == "__main__":
    asyncio.run(main())
