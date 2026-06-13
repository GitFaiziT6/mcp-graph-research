import networkx as nx
from typing import Dict

class GraphConverter:
    """Fournit des primitives de décodage et d'extraction de métriques pour la théorie des graphes."""
    
    @staticmethod
    def from_graph6(g6_str: str) -> nx.Graph:
        """Décode une chaîne graph6 standardisée en un objet réseau NetworkX."""
        try:
            # Nettoyage de la chaîne de caractères (suppression des sauts de ligne ou espaces)
            clean_str = g6_str.strip()
            return nx.from_graph6_bytes(clean_str.encode('ascii'))
        except Exception as e:
            raise ValueError(f"Échec du décodage du format graph6 ('{g6_str}'): {str(e)}")

    @staticmethod
    def verify_graph_invariants(G: nx.Graph) -> Dict[str, float]:
        """
        Recalcule les invariants fondamentaux requis pour la double-vérification.
        Garantit l'exactitude scientifique des calculs.
        """
        n = float(G.number_of_nodes())
        m = float(G.number_of_edges())
        
        if n == 0:
            return {"n": 0, "m": 0, "density": 0, "rad": 0, "diam": 0, "max_deg": 0, "min_deg": 0}

        degrees = [d for _, d in G.degree()]
        max_deg = float(max(degrees)) if degrees else 0.0
        min_deg = float(min(degrees)) if degrees else 0.0
        density = float(nx.density(G))

        # Les métriques de distance ne sont calculables que sur un graphe connexe
        is_connected = nx.is_connected(G)
        rad = float(nx.radius(G)) if is_connected and n > 0 else 0.0
        diam = float(nx.diameter(G)) if is_connected and n > 0 else 0.0

        return {
            "n": n,
            "m": m,
            "density": density,
            "rad": rad,
            "diam": diam,
            "max_deg": max_deg,
            "min_deg": min_deg
        }
