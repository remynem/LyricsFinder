# LyricFinder 🎵

> Type any lyric fragment — any language, typos allowed — and find the song instantly.

Mobile app (iOS & Android) built with React Native + Expo, powered by a FastAPI backend using hybrid semantic search (Qdrant embeddings + Elasticsearch BM25) and a multilingual cross-encoder reranker.

**Repo:** https://github.com/remynem/LyricsFinder

---

## Table of contents

1. [Run locally in 5 minutes](#run-locally)
2. [Project structure](#project-structure)
3. [Architecture](#architecture)
4. [Environment variables](#environment-variables)
5. [API reference](#api-reference)
6. [Ingesting a corpus](#ingesting-a-corpus)
7. [Mobile app](#mobile-app)
8. [Running tests](#running-tests)
9. [CI/CD](#cicd)
10. [Store publishing](#store-publishing)
11. [Lyrics licence compliance](#lyrics-licence)
12. [Performance & scaling](#performance)

---

## Run locally

### Prerequisites

| Tool | Version | Install |
|---|---|---|
| Docker Desktop | ≥ 4.x | https://www.docker.com/products/docker-desktop |
| Node.js | ≥ 20 | https://nodejs.org |
| Git | any | https://git-scm.com |

### Step 1 — Clone the repo

```bash
git clone https://github.com/remynem/LyricsFinder.git
cd LyricsFinder
```

### Step 2 — Create your environment file

```bash
cp .env.example .env
```

The defaults in `.env.example` work out-of-the-box for local development
(sentence-transformers embeddings, no external API keys needed).

### Step 3 — Start all backend services

```bash
docker compose up --build
```

This starts 5 containers. Wait until you see `Application startup complete` in the logs (~60s first run).

| Service | URL | What it does |
|---|---|---|
| FastAPI backend | http://localhost:8000 | REST API |
| Swagger UI | http://localhost:8000/docs | Interactive API docs |
| Qdrant | http://localhost:6333/dashboard | Vector DB dashboard |
| Elasticsearch | http://localhost:9200 | BM25 lexical search |
| PostgreSQL | localhost:5432 | Song metadata |
| Redis | localhost:6379 | Query cache |

### Step 4 — Initialise the database

```bash
docker compose exec backend python -m app.db.init
```

### Step 5 — Load 1 000 sample songs

```bash
docker compose exec backend python scripts/ingest_sample.py
```

Output: `Done: 1000 songs, ~8000 segments ingested.`

### Step 6 — Test a search

```bash
curl -X POST http://localhost:8000/search \
  -H "X-API-Key: dev-key" \
  -H "Content-Type: application/json" \
  -d '{"query_text": "comme un petit coeur qui bat", "top_k": 3}'
```

Expected response: JSON with `results[0].title = "Le Temps de l'Amour"`, `confidence_score > 0.9`.

### Step 7 — Run the mobile app

```bash
cd mobile
npm install
npx expo start
```

Press `i` for iOS simulator, `a` for Android emulator, or scan the QR code with the **Expo Go** app on your phone.

### Stop everything

```bash
docker compose down
```

---

## Project structure

```
LyricsFinder/
├── backend/                    # FastAPI Python backend
│   ├── app/
│   │   ├── main.py             # App entry point
│   │   ├── api/routes/         # Endpoint handlers
│   │   │   ├── search.py       # POST /search  ← core pipeline
│   │   │   ├── ingest.py       # POST /ingest
│   │   │   ├── track.py        # GET /track/{id}
│   │   │   └── feedback.py     # POST /feedback
│   │   ├── core/
│   │   │   ├── config.py       # All env vars
│   │   │   └── auth.py         # API key / JWT
│   │   ├── services/
│   │   │   ├── embeddings.py   # OpenAI / sentence-transformers adapter
│   │   │   ├── vector_db.py    # Qdrant / Pinecone adapter
│   │   │   ├── lexical.py      # Elasticsearch BM25
│   │   │   ├── reranker.py     # Cross-encoder reranker
│   │   │   ├── text.py         # Normalise, segment, deduplicate
│   │   │   ├── language.py     # Language detection
│   │   │   ├── spotify.py      # Preview URL lookup
│   │   │   └── cache.py        # Redis cache
│   │   ├── db/
│   │   │   ├── models.py       # SQLAlchemy models
│   │   │   ├── session.py      # Async DB session
│   │   │   └── repos/          # DB access layer
│   │   └── models/             # Pydantic schemas
│   ├── scripts/
│   │   └── ingest_sample.py    # Load 1 000 test songs
│   ├── tests/
│   │   ├── conftest.py
│   │   └── test_search.py
│   ├── pytest.ini
│   ├── requirements.txt
│   └── Dockerfile
│
├── mobile/                     # React Native (Expo) app
│   ├── src/
│   │   ├── screens/
│   │   │   ├── SearchScreen.tsx
│   │   │   ├── ResultsScreen.tsx
│   │   │   └── TrackScreen.tsx
│   │   ├── components/         # Reusable UI components
│   │   ├── services/
│   │   │   └── api.ts          # Typed API client
│   │   ├── hooks/
│   │   │   └── useSearch.ts
│   │   ├── i18n/               # Translations (react-i18next)
│   │   └── constants/
│   ├── eas.json                # Expo build profiles
│   └── package.json
│
├── docs/
│   └── LICENCE_COMPLIANCE.md   # Lyrics licensing & store checklist
│
├── .github/workflows/
│   ├── backend-test.yml        # Pytest CI on every push
│   └── mobile-submit.yml       # EAS build + store submit on tag
│
├── docker-compose.yml          # All services
├── .env.example                # All env vars documented
└── README.md
```

---

## Architecture

```
Mobile app (React Native / Expo)
          │  HTTPS + X-API-Key
          ▼
  FastAPI backend (:8000)
          │
  ┌───────┴────────────────────────┐
  │                                │
POST /search                  POST /ingest
  │                                │
  ├─ 1. Detect language            ├─ 1. Normalise text
  ├─ 2. Generate embedding         ├─ 2. Segment into 1-3 line chunks
  ├─ 3. ANN search → Qdrant        ├─ 3. Batch embed (OpenAI / ST)
  ├─ 4. BM25 search → Elasticsearch├─ 4. Upsert Qdrant + index ES
  ├─ 5. RRF hybrid merge           └─ 5. Store metadata in PostgreSQL
  ├─ 6. Cross-encoder rerank
  ├─ 7. Aggregate by track
  └─ 8. Enrich with Spotify preview URL
          │
  ┌───────┼──────────────────┐
  │       │                  │
PostgreSQL Qdrant        Elasticsearch
(metadata) (vectors/HNSW) (BM25 index)
```

---

## Environment variables

Copy `.env.example` → `.env`. The defaults work locally without any API keys.

### Required for local dev (already set in .env.example)

| Variable | Default | Description |
|---|---|---|
| `API_KEY` | `dev-key` | Auth header value (`X-API-Key`) |
| `SECRET_KEY` | `change-me-...` | JWT signing secret |
| `DATABASE_URL` | points to Docker PostgreSQL | PostgreSQL connection string |
| `QDRANT_URL` | `http://qdrant:6333` | Qdrant vector DB |
| `ELASTICSEARCH_URL` | `http://elasticsearch:9200` | Elasticsearch |
| `EMBEDDING_PROVIDER` | `sentence_transformers` | No API key needed |

### To enable OpenAI embeddings (better quality)

```env
EMBEDDING_PROVIDER=openai
OPENAI_API_KEY=sk-...
EMBEDDING_DIM=3072
```

### Optional integrations

| Variable | Description |
|---|---|
| `SPOTIFY_CLIENT_ID` + `SPOTIFY_CLIENT_SECRET` | Audio preview URLs in results |
| `MUSIXMATCH_API_KEY` | Licensed lyrics provider |
| `DEEPL_API_KEY` | Query translation for multilingual search |
| `SENTRY_DSN` | Error reporting |
| `PINECONE_API_KEY` | Alternative vector DB (set `VECTOR_DB=pinecone`) |

---

## API reference

Full interactive docs at **http://localhost:8000/docs** when running locally.

### POST /search

```bash
curl -X POST http://localhost:8000/search \
  -H "X-API-Key: dev-key" \
  -H "Content-Type: application/json" \
  -d '{
    "query_text": "comme un petit coeur qui bat",
    "top_k": 5,
    "filter_language": "fr"
  }'
```

<details>
<summary>Response example</summary>

```json
{
  "query_id": "3fa85f64-...",
  "detected_language": "fr",
  "results": [
    {
      "track_id": "abc123",
      "title": "Le Temps de l'Amour",
      "artist": "Françoise Hardy",
      "release_year": 1963,
      "confidence_score": 0.97,
      "best_segment": {
        "text": "Comme un petit cœur qui bat",
        "line_offset": 3,
        "context": "Ça dure toujours\nComme un petit cœur qui bat\nTu t'en vas déjà"
      },
      "audio_preview": {
        "spotify_preview_url": "https://p.scdn.co/mp3-preview/...",
        "spotify_track_url": "https://open.spotify.com/track/..."
      }
    }
  ],
  "total": 3,
  "latency_ms": 142
}
```
</details>

### POST /ingest

```bash
curl -X POST http://localhost:8000/ingest \
  -H "X-API-Key: dev-key" \
  -H "Content-Type: application/json" \
  -d '{
    "songs": [{
      "track_id": "unique-id",
      "title": "Song Title",
      "artist": "Artist Name",
      "language": "fr",
      "lyrics": "line one\nline two\nline three"
    }]
  }'
```

### GET /track/{track_id}

```bash
curl http://localhost:8000/track/abc123 -H "X-API-Key: dev-key"
```

### POST /feedback

```bash
curl -X POST http://localhost:8000/feedback \
  -H "X-API-Key: dev-key" \
  -H "Content-Type: application/json" \
  -d '{"query_id": "...", "track_id": "abc123", "is_correct": true}'
```

---

## Ingesting a corpus

### Sample data (quickstart)

```bash
docker compose exec backend python scripts/ingest_sample.py
```

### Your own CSV

CSV must have columns: `track_id, title, artist, album, release_year, language, lyrics`

```bash
# Copy your file into the container
docker compose cp my_songs.csv backend:/data/my_songs.csv

# Run ingestion
docker compose exec backend python scripts/ingest_csv.py --file /data/my_songs.csv
```

### Your own JSON

```bash
docker compose cp songs.json backend:/data/songs.json
docker compose exec backend python scripts/ingest_json.py --file /data/songs.json
```

---

## Mobile app

### Run on your phone (no simulator needed)

1. Install **Expo Go** from the App Store or Google Play
2. Run:
   ```bash
   cd mobile
   npm install
   npx expo start --tunnel
   ```
3. Scan the QR code with your phone

### Run on iOS simulator (Mac only)

```bash
cd mobile && npx expo start
# Press i
```

### Run on Android emulator

```bash
cd mobile && npx expo start
# Press a
```

### Build for stores (requires Expo account)

```bash
npm install -g eas-cli
eas login
eas build --platform ios     # TestFlight
eas build --platform android # Play Store AAB
```

---

## Running tests

```bash
# From the repo root
docker compose exec backend pytest -v --cov=app

# Or without Docker (from backend/ folder)
cd backend
pip install -r requirements.txt
pytest -v
```

---

## CI/CD

| Workflow | Trigger | What happens |
|---|---|---|
| `backend-test.yml` | Every push / PR | Runs pytest against real Qdrant + ES + PostgreSQL |
| `mobile-submit.yml` | Git tag `v1.2.3` | EAS builds iOS + Android, submits to TestFlight + Play Internal |

To trigger a store release:
```bash
git tag v1.0.0
git push origin v1.0.0
```

---

## Store publishing

### App Store (iOS)
- [ ] Apple Developer account — https://developer.apple.com ($99/year)
- [ ] App Store Connect listing with screenshots, icon, privacy policy URL
- [ ] `NSMicrophoneUsageDescription` in Info.plist (voice search)
- [ ] TestFlight beta before submission

### Google Play (Android)
- [ ] Google Play Console account ($25 one-time)
- [ ] Target SDK ≥ 34, AAB format, Play App Signing enrolled
- [ ] Data safety section completed
- [ ] Internal → Closed → Open → Production track

Full checklist: [`docs/LICENCE_COMPLIANCE.md`](docs/LICENCE_COMPLIANCE.md)

---

## Lyrics licence

**Do not display full lyrics without a signed licence agreement.**

| Mode | What to display | Attribution required |
|---|---|---|
| Prototype (no licence) | Max 4 lines | `© Artist. Excerpt via Musixmatch.` |
| Musixmatch licence | Full lyrics | Musixmatch badge |
| LyricFind licence | Full lyrics | LyricFind attribution |

Contact: licensing@musixmatch.com or sales@lyricfind.com

---

## Performance & scaling

| Metric | Target |
|---|---|
| Search latency p50 | < 150 ms |
| Search latency p99 | < 500 ms |
| Corpus size | Up to 10 M segments |

Key tuning variables in `.env`:
```env
SEARCH_CANDIDATE_LIMIT=200   # Pre-rerank pool size
QDRANT_HNSW_EF=128           # Recall vs speed trade-off
CACHE_TTL_SECONDS=300        # Redis hot-query cache
INGEST_BATCH_SIZE=64         # Embedding batch size
```
