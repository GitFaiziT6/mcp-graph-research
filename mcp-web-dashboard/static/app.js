function startTests() {
    console.log("Démarrage du cycle...");
    document.getElementById('sys-status').innerText = "Exécution";
}

const source = new EventSource("/stream");
source.onmessage = function(event) {
    const data = JSON.parse(event.data);
    // Mise à jour du DOM en temps réel
    console.log("Nouvel événement:", data);
};