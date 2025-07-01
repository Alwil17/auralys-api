from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
from prometheus_fastapi_instrumentator import Instrumentator

# Importer la dépendance de la base de données
import app.api.routes.health_routes as health_endpoints
import app.api.routes.auth_routes as auth_endpoints
import app.api.routes.mood_routes as mood_endpoints
import app.api.routes.chat_routes as chat_endpoints
import app.api.routes.recommendation_routes as recommendation_endpoints
import app.api.routes.stats_routes as stats_endpoints
from app.core.config import settings

# Define tags metadata for Swagger documentation
tags_metadata = [
    {
        "name": "Authentication",
        "description": "User authentication, registration, and account management including GDPR compliance endpoints.",
    },
    {
        "name": "Mood Tracking",
        "description": "Daily mood entries, statistics, and mental wellness tracking features.",
    },
    {
        "name": "Chat & NLP",
        "description": "AI chatbot interactions with sentiment analysis and mood detection.",
    },
    {
        "name": "Recommendations",
        "description": "Personalized wellness activity recommendations based on mood data.",
    },
    {
        "name": "Statistics",
        "description": "Analytics, trends, and insights from user wellness data.",
    },
    {
        "name": "Health Check",
        "description": "System status and health monitoring endpoints.",
    },
]

app = FastAPI(
    title="Auralys API",
    description="""
    **Auralys** is a mental wellness tracking API that provides:
    
    * **Mood Tracking**: Daily mood entries with sleep, stress, and activity data
    * **AI Chatbot**: Conversational AI with sentiment analysis and mood detection
    * **Smart Recommendations**: Personalized wellness activities based on user data
    * **Analytics**: Comprehensive statistics and trend analysis
    * **GDPR Compliance**: Full data export and account deletion capabilities
    
    ## Authentication
    Most endpoints require JWT authentication. Get your token from `/auth/token`.
    
    ## Data Privacy
    This API is GDPR compliant and respects user privacy with explicit consent management.
    """,
    version="1.0.0",
    contact={
        "name": "Auralys Support",
        "email": "willialfred24@gmail.com",
    },
    license_info={
        "name": "MIT License",
        "url": "https://opensource.org/licenses/MIT",
    },
    openapi_tags=tags_metadata,
)

app.include_router(health_endpoints.router)
app.include_router(auth_endpoints.router)
app.include_router(mood_endpoints.router)
app.include_router(chat_endpoints.router)
app.include_router(recommendation_endpoints.router)
app.include_router(stats_endpoints.router)

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
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
