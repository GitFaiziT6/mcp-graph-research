from pydantic import BaseModel, Field
from typing import Dict, Any, Optional

class KnownCounterExample(BaseModel):
    """
    Représente un contre-exemple mathématique déjà découvert pour cette conjecture.
    Conforme aux spécifications du format g6 (graph6) ou NetworkX JSON.
    """
    format: str = Field(
        ..., 
        description="Le format d'encodage du graphe, typiquement 'graph6' ou 'adjacency_json'"
    )
    value: str = Field(
        ..., 
        description="La représentation textuelle ou sérialisée du contre-exemple"
    )

class Conjecture(BaseModel):
    """
    Modèle de données central traduisant une conjecture en théorie des graphes.
    Valide la structure JSON de la Tâche 2 avant toute soumission aux serveurs MCP.
    """
    id: str = Field(
        ..., 
        description="Identifiant unique de la conjecture, ex: CONJ-2026-001"
    )
    domain: str = Field(
        "graph_theory", 
        description="Domaine mathématique de la conjecture"
    )
    graph_class: str = Field(
        ..., 
        description="Classe de graphe restrictive imposée par la conjecture (ex: connected, bipartite, planar)"
    )
    left_invariant: str = Field(
        ..., 
        description="L'invariant de gauche calculé sur le graphe (ex: independence_number, chromatic_number)"
    )
    relation: str = Field(
        ..., 
        description="L'opérateur relationnel de la conjecture (ex: '<=', '>=', '==', '<')"
    )
    right_expression: str = Field(
        ..., 
        description="L'expression mathématique de droite sous forme de chaîne symbolique évaluable (ex: '2 * core_number + 1')"
    )
    parameters: Dict[str, Any] = Field(
        default_factory=dict, 
        description="Paramètres optionnels nécessaires à l'évaluation des invariants ou des fonctions"
    )
    max_order: int = Field(
        default=30, 
        ge=3, 
        le=100, 
        description="Ordre maximal (nombre de sommets) des graphes à tester lors de la recherche de contre-exemples"
    )
    timeout_seconds: int = Field(
        default=1200, 
        ge=1, 
        description="Temps maximum alloué en secondes pour invalider cette conjecture algorithmiquement"
    )
    known_counterexample: Optional[KnownCounterExample] = Field(
        default=None, 
        description="Contre-exemple connu si la conjecture a déjà été invalidée au cours d'une session précédente"
    )

    class Config:
        """Configuration Pydantic pour garantir l'immutabilité et la propreté du schéma."""
        frozen = True
        populate_by_name = True