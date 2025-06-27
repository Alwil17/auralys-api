Projet : Auralys - Application de suivi du bien-être mental

Contexte :
Ce projet est le backend d'une application mobile appelée Auralys. Il est développé avec FastAPI, PostgreSQL et suit une architecture modulaire inspirée du Clean/Hexagonal Architecture.

Objectif :
Fournir une API sécurisée et performante pour :
- L’authentification utilisateur (JWT)
- Le suivi d’humeur quotidien (MoodEntry)
- Le stockage des discussions avec un chatbot (ChatHistory)
- L’analyse de sentiment (NLP via Hugging Face Transformers)
- La génération de recommandations bien-être personnalisées
- L’export, la suppression des données et la conformité RGPD

Structure :
- app/
  - api/routes/ : contient tous les endpoints REST (auth, mood, chat, reco…)
  - core/       : gestion de la sécurité (hash, JWT), configuration, logs
  - repositories/       : logique métier (accès base, création, lecture…)
  - db/models/  : modèles SQLAlchemy
  - schemas/    : modèles Pydantic pour validation I/O
  - services/   : NLP, moteur de recommandation
  - tests/      : tests avec Pytest

Technos :
- Python 3.10+
- FastAPI
- PostgreSQL
- SQLAlchemy
- Pydantic
- Hugging Face Transformers
- Docker
- Alembic
- GitHub Actions (CI)

Notes pour Copilot :
- Proposer des fonctions backend claires et typées
- Utiliser Pydantic pour la validation
- Écrire des routes RESTful (GET, POST, DELETE…)
- Suivre les standards FastAPI (async/await, Depends, response_model)
- Générer du code modulaire et testable
"""
