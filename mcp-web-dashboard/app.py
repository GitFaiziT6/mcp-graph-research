import os
import sys
import json
import asyncio
import threading
from flask import Flask, render_template, jsonify

# --- CORRECTION DU CHEMIN D'IMPORT ---
# On remonte d'un dossier pour accéder à la racine du projet
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from agent_controller.main import GraphResearchOrchestrator

app = Flask(__name__)
# On pointe vers le dossier data qui est à la racine
BASE_DATA = os.path.abspath(os.path.join(os.path.dirname(__file__), '../data'))
orchestrator = GraphResearchOrchestrator()

def load_data(folder):
    items = []
    path = os.path.join(BASE_DATA, folder)
    if os.path.exists(path):
        for f in os.listdir(path):
            file_path = os.path.join(path, f)
            if f.endswith('.json') and os.path.getsize(file_path) > 0:
                try:
                    with open(file_path, 'r') as file:
                        items.append(json.load(file))
                except json.JSONDecodeError:
                    pass
    return items

@app.route('/')
def index():
    return render_template('index.html', 
        true_conjectures=load_data('true_conjectures'),
        in_progress=load_data('in_progress'),
        false_conjectures=load_data('false_conjectures')
    )

@app.route('/api/start', methods=['POST'])
def start():
    if not orchestrator.running:
        threading.Thread(target=lambda: asyncio.run(orchestrator.execute_scientific_loop()), daemon=True).start()
        return jsonify({"status": "started"})
    return jsonify({"status": "already running"})

@app.route('/api/stop', methods=['POST'])
def stop():
    orchestrator.stop()
    return jsonify({"status": "stopped"})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)