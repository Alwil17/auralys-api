# 🗂️ Roadmap API FastAPI — Kanban Sprints

## 📦 Sprint 1 – Auth & socle technique (S1)

- [x] **Init FastAPI project structure**  
  _Créer les dossiers : models, schemas, crud, api, core, db, etc._
- [x] **Add User model + Alembic migration**  
  _Modèle SQLAlchemy avec email, hashed_password, consent, created_at._
- [x] **JWT Auth implementation**  
  _Endpoints /register, /login, /me avec JWT._
- [x] **Secure password hashing**  
  _Utiliser passlib pour le hash._
- [x] **Add base Pydantic schemas**  
  _UserCreate, UserLogin, UserOut._
- [x] **Add DB session + settings**  
  _Fichier .env, SQLALCHEMY_DATABASE_URL._
- [x] **Dockerize backend**  
  _Dockerfile + image buildable localement._
- [x] **Basic CI with pytest + lint**  
  _GitHub Actions : test + black + flake8._
- [x] **Test: user registration/login**  
  _Tester succès/échec, mot de passe incorrect._

## 📦 Sprint 2 – MoodEntry & RGPD (S2)

- [x] **Create MoodEntry model**  
  _Champs : mood, stress, sleep_hours, notes, activity._
- [x] **Add MoodEntry schemas**  
  _Pydantic : MoodEntryCreate, MoodEntryOut._
- [ ] **Create endpoints /moods**  
  _GET, POST + filtre par date ou user._
- [x] **Add collected flag**  
  _Pour sync local/cloud si consentement._
- [x] **Setup test data (dummy moods)**  
  _Préparer données de test._
- [x] **Test: mood submission + listing**  
  _Vérifier insertion + format de réponse._
- [x] **Edge case: no consent = reject save**  
  _Test RGPD (user refuse collecte)._

## 📦 Sprint 3 – Chat + NLP (S3)

- [ ] **Create ChatHistory model**  
  _Messages (sender, timestamp, mood_detected…)._
- [ ] **Add ChatHistory endpoints**  
  _/chat/send, /chat/history._
- [ ] **Integrate HuggingFace NLP model**  
  _transformers, ex : distilbert-base-uncased._
- [ ] **Process mood from user message**  
  _Inference NLP → champ mood_detected._
- [ ] **Test: NLP detection pipeline**  
  _Tester analyse de sentiment sur texte._
- [ ] **Test: store & retrieve chat history**  
  _Liste de messages avec tri par date._

## 📦 Sprint 4 – Recommandations & Statistiques (S4)

- [ ] **Create Recommendation model**  
  _Champs : mood_id, activity, was_helpful._
- [ ] **Generate reco from mood entry**  
  _Endpoint /recommendation/generate._
- [ ] **Create stats endpoint**  
  _/stats/weekly : moyenne, évolution._
- [ ] **Allow feedback on reco**  
  _Champ was_helpful modifiable._
- [ ] **Test: generate reco for low mood**  
  _Vérifie bonne activité suggérée._
- [ ] **Test: weekly stats aggregation**  
  _Données sur les 7 derniers jours._

## 📦 Déploiement & RGPD (en parallèle S4)

- [ ] **Export/delete account endpoints**  
  _/user/delete, /user/export._
- [ ] **CI/CD deploy to Render/Fly.io**  
  _Pipeline déploiement auto après push._
- [ ] **Add FastAPI tags + Swagger**  
  _Doc dynamique de toutes les routes._
- [ ] **Test: full workflow**  
  _Création user → mood → reco → feedback._

