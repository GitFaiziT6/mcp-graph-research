# Utilisation d'une image de production Python ultra-légère
FROM python:3.11-alpine

# Installation des dépendances système nécessaires à la compilation de certaines extensions si besoin
RUN apk add --no-cache gcc musl-dev linux-headers

# Définition du répertoire de travail à l'intérieur du conteneur
WORKDIR /app

# Copie et installation préalable des dépendances pour maximiser l'utilisation du cache Docker
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copie de l'intégralité du code source du projet
COPY . .

# Variable d'environnement pour s'assurer que les logs Python soient transmis en temps réel
ENV PYTHONUNBUFFERED=1

# Par défaut, le Dockerfile ne spécifie pas de point d'entrée unique car il sera surchargé par le docker-compose
CMD ["python3"]
