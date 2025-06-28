from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import sentry_sdk
import uvicorn
from prometheus_fastapi_instrumentator import Instrumentator
from sentry_sdk.integrations.asgi import SentryAsgiMiddleware

# Importer la dépendance de la base de données
import app.api.routes.auth_routes as auth_endpoints
from app.core.config import settings

app = FastAPI(
    title="Auralys API",
    description="API REST pour le suivi du bien-être mental - authentification, suivi d'humeur, chatbot et recommandations personnalisées.",
    version="0.0.1",
)

app.include_router(auth_endpoints.router)

if settings.PROMETHEUS_ENABLED:
    # Instrumentation pour Prometheus
    Instrumentator().instrument(app).expose(app)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Lancer l'application si le fichier est exécuté directement
if __name__ == "__main__":
    uvicorn.run("app.api.main:app", host="0.0.0.0", port=8000, reload=True)
