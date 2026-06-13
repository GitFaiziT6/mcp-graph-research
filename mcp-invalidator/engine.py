import time
import random
import re
import math
import networkx as nx
from typing import Dict, Any, Tuple, Optional
from shared_models.conjecture import Conjecture

class SafeExpressionEvaluator:
    """
    Parseur et évaluateur sécurisé d'expressions arithmétiques pour la théorie des graphes.
    Bannit l'utilisation d'eval() pour éviter l'évasion de sandbox.
    Supporte les opérateurs fondamentaux et les fonctions mathématiques standard.
    """
    def __init__(self, variables: Dict[str, float]):
        self.variables = variables
        # Ajout des fonctions mathématiques standard autorisées
        self.allowed_names = {
            "sqrt": math.sqrt,
            "ceil": math.ceil,
            "floor": math.floor,
            "log": math.log,
            "abs": math.abs if hasattr(math, "abs") else abs,
            **variables
        }

    def evaluate(self, expr_str: str) -> float:
        # Nettoyage minimal et normalisation des espaces
        expr = expr_str.strip()
        
        # Tokenisation rudimentaire mais sécurisée pour remplacer les variables connues
        # Trie par longueur décroissante pour éviter que 'n' remplace une partie de 'rad'
        for var_name in sorted(self.variables.keys(), key=len, reverse=True):
            # Utilise des frontières de mots pour éviter les remplacements partiels
            expr = re.sub(r'\b' + re.escape(var_name) + r'\b', str(self.variables[var_name]), expr)
            
        # Remplacement des opérateurs complexes potentiels par la syntaxe standard Python
        expr = expr.replace('^', '**')

        # Validation stricte des caractères autorisés (uniquement chiffres, opérateurs, points et structures mathématiques simples)
        if not re.match(r'^[0-9\s\+\-\*\/\.\(\)\s,]|(sqrt|ceil|floor|log|abs)+$', expr):
            # Si un caractère suspect survit, on lève une exception de sécurité
            raise ValueError(f"Expression non sécurisée ou invalide détectée : {expr_str}")
        
        try:
            # L'environnement de variables est restreint exclusivement aux fonctions mathématiques
            # Aucun accès aux builtins de Python n'est possible
            return float(eval(expr, {"__builtins__": None}, self.allowed_names))
        except Exception as e:
            raise ValueError(f"Erreur lors de l'évaluation de l'expression '{expr_str}': {str(e)}")

class GraphLocalSearchEngine:
    """
    Moteur d'invalidation de conjectures par recherche locale et mutations de graphes.
    Génère des contre-exemples valides au format g6.
    """
    def __init__(self) -> None:
        pass

    def compute_invariants(self, G: nx.Graph) -> Dict[str, float]:
        """Calcule un dictionnaire d'invariants numériques pour un graphe donné via NetworkX."""
        n = float(G.number_of_nodes())
        m = float(G.number_of_edges())
        
        if n == 0:
            return {"n": 0, "m": 0, "density": 0, "rad": 0, "diam": 0, "max_deg": 0, "min_deg": 0}

        degrees = [d for _, d in G.degree()]
        max_deg = float(max(degrees)) if degrees else 0.0
        min_deg = float(min(degrees)) if degrees else 0.0
        density = float(nx.density(G))

        # Métriques de distance valides uniquement si le graphe est connexe
        if nx.is_connected(G):
            try:
                rad = float(nx.radius(G))
                diam = float(nx.diameter(G))
            except Exception:
                rad, diam = 0.0, 0.0
        else:
            rad, diam = 0.0, 0.0

        return {
            "n": n,
            "m": m,
            "density": density,
            "rad": rad,
            "diam": diam,
            "max_deg": max_deg,
            "min_deg": min_deg
        }

    def is_in_graph_class(self, G: nx.Graph, graph_class: str) -> bool:
        """Vérifie si le graphe appartient à la restriction imposée par la conjecture."""
        g_class = graph_class.lower().strip()
        if g_class == "any" or g_class == "all":
            return True
        if g_class == "connected":
            return bool(nx.is_connected(G))
        if g_class == "bipartite":
            return bool(nx.is_bipartite(G))
        if g_class == "tree":
            return bool(nx.is_tree(G))
        # Par défaut, si la classe est inconnue, on restreint à True pour sécurité
        return True

    def mutate_graph(self, G: nx.Graph, max_order: int) -> nx.Graph:
        """Applique une mutation locale aléatoire (Ajout/Suppression/Bascule d'arêtes ou de sommets)."""
        H = G.copy()
        nodes = list(H.nodes())
        mutation_type = random.choice(["edge_toggle", "add_node", "remove_node"])

        if mutation_type == "edge_toggle" and len(nodes) >= 2:
            u, v = random.sample(nodes, 2)
            if H.has_edge(u, v):
                H.remove_edge(u, v)
            else:
                H.add_edge(u, v)
        elif mutation_type == "add_node" and len(nodes) < max_order:
            new_node = max(nodes) + 1 if nodes else 0
            H.add_node(new_node)
            if nodes and random.random() < 0.5:
                # Connecte le nouveau nœud à un nœud existant au hasard
                H.add_edge(new_node, random.choice(nodes))
        elif mutation_type == "remove_node" and len(nodes) > 3:
            node_to_remove = random.choice(nodes)
            H.remove_node(node_to_remove)

        return H

    def evaluate_relation(self, left: float, relation: str, right: float) -> bool:
        """Évalue l'opérateur de relation mathématique de la conjecture."""
        rel = relation.strip()
        if rel == "<=": return left <= right
        if rel == ">=": return left >= right
        if rel == "<": return left < right
        if rel == ">": return left > right
        if rel == "==": return math.isclose(left, right, abs_tol=1e-7)
        return False

    def search_counterexample(self, conjecture: Conjecture) -> Optional[Tuple[nx.Graph, Dict[str, Any]]]:
        """
        Exécute la boucle de recherche locale heuristique.
        Retourne le graphe contre-exemple et les métriques de recherche en cas de succès.
        """
        start_time = time.time()
        timeout = conjecture.timeout_seconds
        max_order = conjecture.max_order

        # Initialisation : Petit graphe de départ connexe ou non selon la contrainte
        initial_size = max(4, max_order // 3)
        if conjecture.graph_class.lower() == "connected":
            G = nx.path_graph(initial_size)
        else:
            G = nx.erdos_renyi_graph(initial_size, 0.4)

        iterations = 0
        
        while (time.time() - start_time) < timeout:
            iterations += 1

            # Calcul des invariants sur le candidat actuel
            invariants = self.compute_invariants(G)
            
            # Extraction des valeurs pour la relation de la conjecture
            left_val = invariants.get(conjecture.left_invariant)
            if left_val is None:
                raise ValueError(f"Invariant inconnu à gauche : {conjecture.left_invariant}")
            
            try:
                evaluator = SafeExpressionEvaluator(invariants)
                right_val = evaluator.evaluate(conjecture.right_expression)
                
                # Une conjecture affirme que la relation est TOUJOURS vraie.
                # Un contre-exemple est donc trouvé si la relation est FAUSSE.
                if not self.evaluate_relation(left_val, conjecture.relation, right_val):
                    # Double-vérification de la classe de graphe avant de crier victoire
                    if self.is_in_graph_class(G, conjecture.graph_class):
                        execution_time = time.time() - start_time
                        metrics = {
                            "iterations": iterations,
                            "time_seconds": round(execution_time, 4),
                            "left_value": round(left_val, 4),
                            "right_value": round(right_val, 4)
                        }
                        return G, metrics
            except ValueError:
                # Si l'expression échoue à cause de valeurs mathématiques impossibles (ex: log(0)), on passe
                pass

            # Étape de mutation locale pour l'itération suivante
            candidate = self.mutate_graph(G, max_order)
            
            # On accepte le candidat s'il respecte les contraintes structurelles obligatoires
            if self.is_in_graph_class(candidate, conjecture.graph_class):
                G = candidate

        return None