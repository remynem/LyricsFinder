# LyricFinder 🎵

Search any song from a lyric fragment — any language, any spelling. Mobile-first app with a FastAPI backend, hybrid semantic + lexical search, and multilingual reranking.

---

## Table of contents

1. [Architecture overview](#architecture)
2. [Quick start (Docker)](#quick-start)
3. [Environment variables](#environment-variables)
4. [Backend API reference](#backend-api)
5. [Ingesting a corpus](#ingesting-a-corpus)
6. [Mobile app setup](#mobile-app)
7. [CI/CD & Fastlane](#cicd)
8. [Store publishing checklist](#store-publishing)
9. [Lyrics licence compliance](#lyrics-licence)
10. [Performance & scaling](#performance)

---

## Architecture

```
Mobile (React Native / Expo)
        │
        ▼
API Gateway (FastAPI + JWT)
        │
  ┌─────┴──────────────────┐
  │                        │
POST /search            POST /ingest
  │                        │
  ├─ Language detect       ├─ Normalise text
  ├─ Embedding (OpenAI)    ├─ Segment lyrics
  ├─ ANN (Qdrant HNSW)     ├─ Batch embeddings
  ├─ BM25 (Elasticsearch)  └─ Index ES + Qdrant
  ├─ Hybrid merge
  └─ Cross-encoder rerank
        │
   ┌────┴────┐
PostgreSQL  Qdrant  Elasticsearch  S3
```

---

## Quick start

### Prerequisites

- Docker & Docker Compose v2
- Node.js ≥ 20 (for mobile)
- Python ≥ 3.11 (optional, for local dev without Docker)

### 1. Clone and configure

```bash
git clone https://github.com/your-org/lyricfinder.git
cd lyricfinder
cp .env.example .env
# Edit .env with your keys (see Environment variables below)
```

### 2. Start all services

```bash
docker compose up --build
```

Services started:
| Service | URL |
|---|---|
| FastAPI backend | http://localhost:8000 |
| API docs (Swagger) | http://localhost:8000/docs |
| Qdrant dashboard | http://localhost:6333/dashboard |
| Elasticsearch | http://localhost:9200 |
| PostgreSQL | localhost:5432 |

### 3. Initialise the database

```bash
docker compose exec backend python -m app.db.init
```

### 4. Ingest the sample corpus (1 000 songs)

```bash
docker compose exec backend python scripts/ingest_sample.py
```

### 5. Run a test search

```bash
curl -X POST http://localhost:8000/search \
  -H "X-API-Key: dev-key" \
  -H "Content-Type: application/json" \
  -d '{"query_text": "comme un petit coeur qui bat", "top_k": 5}'
```

---

## Environment variables

Copy `.env.example` to `.env` and fill in the values below.

### Required

| Variable | Description |
|---|---|
| `SECRET_KEY` | Random secret for JWT signing (run `openssl rand -hex 32`) |
| `API_KEY` | Simple API key for prototype auth |
| `DATABASE_URL` | PostgreSQL DSN e.g. `postgresql+asyncpg://user:pass@db:5432/lyricfinder` |
| `QDRANT_URL` | Qdrant host e.g. `http://qdrant:6333` |
| `ELASTICSEARCH_URL` | Elasticsearch host e.g. `http://elasticsearch:9200` |

### Embeddings (choose one)

| Variable | Description |
|---|---|
| `OPENAI_API_KEY` | OpenAI key (uses `text-embedding-3-large`) |
| `EMBEDDING_PROVIDER` | `openai` (default) or `sentence_transformers` |
| `SENTENCE_TRANSFORMERS_MODEL` | Default: `paraphrase-multilingual-MiniLM-L12-v2` |

### Optional integrations

| Variable | Description |
|---|---|
| `SPOTIFY_CLIENT_ID` | Spotify Web API client ID |
| `SPOTIFY_CLIENT_SECRET` | Spotify Web API secret |
| `MUSIXMATCH_API_KEY` | Musixmatch lyrics API key |
| `LYRICFIND_API_KEY` | LyricFind API key (alternative) |
| `DEEPL_API_KEY` | DeepL for query translation (optional) |
| `GOOGLE_TRANSLATE_KEY` | Google Translate fallback |
| `SENTRY_DSN` | Sentry error reporting |
| `S3_BUCKET` | AWS S3 bucket for album art |
| `AWS_ACCESS_KEY_ID` | AWS credentials |
| `AWS_SECRET_ACCESS_KEY` | AWS credentials |
| `RERANKER_MODEL` | HuggingFace model ID or `openai` |
| `PINECONE_API_KEY` | Alternative to Qdrant (set `VECTOR_DB=pinecone`) |

---

## Backend API

Full OpenAPI spec: `http://localhost:8000/docs`

### POST /ingest

Ingest a JSON or CSV corpus of songs.

**Request body:**
```json
{
  "songs": [
    {
      "track_id": "abc123",
      "title": "Le Temps de l'Amour",
      "artist": "Françoise Hardy",
      "album": "Tous les garçons et les filles",
      "release_year": 1963,
      "language": "fr",
      "lyrics": "Le temps de l'amour\nC'est long et c'est court…",
      "external_ids": {
        "spotify_id": "3n3Ppam7vgaVa1iaRUIOKE",
        "musixmatch_id": "12345"
      }
    }
  ]
}
```

**Response:**
```json
{
  "songs_ingested": 1,
  "segments_created": 24,
  "embeddings_generated": 24,
  "duration_seconds": 3.2
}
```

### POST /search

Search by lyric fragment.

**Request body:**
```json
{
  "query_text": "comme un petit coeur qui bat",
  "top_k": 10,
  "language_hint": "fr",
  "use_translation": false,
  "filter_year_min": 1960,
  "filter_year_max": 1970,
  "filter_language": "fr"
}
```

**Response:**
```json
{
  "query_id": "q_abc123",
  "detected_language": "fr",
  "results": [
    {
      "track_id": "abc123",
      "title": "Le Temps de l'Amour",
      "artist": "Françoise Hardy",
      "album": "Tous les garçons et les filles",
      "release_year": 1963,
      "language": "fr",
      "confidence_score": 0.97,
      "best_segment": {
        "text": "Comme un petit cœur qui bat",
        "line_offset": 8,
        "context": "C'est long et c'est court\nCa dure toujours\nComme un petit cœur qui bat"
      },
      "audio_preview": {
        "spotify_preview_url": "https://p.scdn.co/mp3-preview/…",
        "spotify_track_url": "https://open.spotify.com/track/…"
      }
    }
  ],
  "total": 3,
  "latency_ms": 142
}
```

### GET /track/{track_id}

Returns full metadata and a licensed excerpt (or full lyrics if licence available).

### POST /feedback

```json
{
  "query_id": "q_abc123",
  "track_id": "abc123",
  "is_correct": true,
  "clicked_position": 1
}
```

---

## Ingesting a corpus

### From a CSV file

```bash
# CSV must have columns: track_id, title, artist, album, release_year, language, lyrics
docker compose exec backend python scripts/ingest_csv.py --file /data/my_corpus.csv
```

### From JSON

```bash
docker compose exec backend python scripts/ingest_json.py --file /data/songs.json
```

### Batch size and performance

For large corpora (>100k songs), tune:
```env
INGEST_BATCH_SIZE=64          # Embedding batch size
INGEST_WORKERS=4              # Parallel workers
QDRANT_HNSW_M=16              # HNSW construction param
QDRANT_HNSW_EF_CONSTRUCT=100  # Higher = better recall, slower build
```

---

## Mobile app

### Prerequisites

```bash
npm install -g expo-cli eas-cli
```

### Install dependencies

```bash
cd mobile
npm install
```

### Configure

```bash
cp mobile/.env.example mobile/.env
# Set EXPO_PUBLIC_API_URL=http://localhost:8000
# Set EXPO_PUBLIC_API_KEY=dev-key
# Set EXPO_PUBLIC_SPOTIFY_CLIENT_ID=...
```

### Run on simulator

```bash
cd mobile
npx expo start
# Press i for iOS, a for Android
```

### Run on device (Expo Go)

```bash
npx expo start --tunnel
# Scan the QR code with the Expo Go app
```

---

## CI/CD

### GitHub Actions

Workflows in `.github/workflows/`:

| Workflow | Trigger | Action |
|---|---|---|
| `backend-test.yml` | Push to main/PR | Run pytest |
| `backend-deploy.yml` | Push to main | Build & push Docker image |
| `mobile-preview.yml` | PR | EAS build preview channel |
| `mobile-submit.yml` | Tag `v*` | EAS submit to TestFlight + Play Internal |

### Fastlane

```bash
cd mobile/ios
fastlane beta        # Build and upload to TestFlight
fastlane release     # Submit to App Store review

cd mobile/android
fastlane beta        # Upload to Play internal track
fastlane release     # Promote to production
```

See `mobile/fastlane/README.md` for signing setup.

---

## Store publishing

### App Store (iOS)

- [ ] Apple Developer account ($99/year)
- [ ] Bundle ID registered in App Store Connect
- [ ] Provisioning profile + distribution certificate
- [ ] App Store Connect listing: name, subtitle, description, keywords
- [ ] Screenshots: 6.7", 6.1", 5.5", iPad Pro 12.9"
- [ ] App icon: 1024×1024 PNG, no alpha
- [ ] App Privacy: declare data types collected (search queries, device ID)
- [ ] Usage description strings in `Info.plist`:
  - `NSMicrophoneUsageDescription` — for voice search
  - `NSUserTrackingUsageDescription` — if using ATT
- [ ] Age rating: 4+
- [ ] Privacy policy URL (required)
- [ ] Support URL
- [ ] TestFlight beta test before submission

### Google Play (Android)

- [ ] Google Play Developer account ($25 one-time)
- [ ] App signing enrolled (Play App Signing recommended)
- [ ] AAB (Android App Bundle) — NOT APK
- [ ] Play Console listing: title, short desc, full desc
- [ ] Feature graphic: 1024×500
- [ ] Screenshots: phone, 7" tablet, 10" tablet
- [ ] Content rating questionnaire
- [ ] Data safety section: disclose search history, no selling
- [ ] Target SDK ≥ 34 (Android 14)
- [ ] Internal test → Closed test → Open test → Production

---

## Lyrics licence

**Never display full lyrics without a licence.**

| Provider | Type | URL |
|---|---|---|
| Musixmatch | Commercial API + revenue share | https://developer.musixmatch.com |
| LyricFind | Commercial API | https://www.lyricfind.com |
| Genius | Display only, no commercial | https://docs.genius.com |

### Prototype mode (no licence)

Display up to 4 lines as an excerpt. Show attribution:
```
© [Artist] / [Composer]. Excerpt via Musixmatch. All rights reserved.
```

### Compliance checklist

- [ ] No full lyrics display without signed licence agreement
- [ ] Attribution shown on every lyric display
- [ ] Deep links to licensed platforms (Spotify, Apple Music, Genius)
- [ ] Rate limits respected (Musixmatch: 2000 calls/day on free tier)
- [ ] Lyrics not cached server-side beyond allowed duration
- [ ] GDPR / CCPA consent flow in app
- [ ] Privacy policy covers search query logging

---

## Performance & scaling

### Targets

| Metric | Target |
|---|---|
| Search latency (p50) | < 150ms |
| Search latency (p99) | < 500ms |
| QPS (single instance) | > 50 |
| Corpus size | Up to 10M segments |

### Tuning knobs

```env
QDRANT_HNSW_M=16
QDRANT_HNSW_EF=128          # Higher = better recall at search time
SEARCH_CANDIDATE_LIMIT=200  # Pre-rerank candidates
RERANKER_BATCH_SIZE=32
CACHE_TTL_SECONDS=300       # Hot query cache (Redis)
```

### Scaling

- Backend is stateless — scale horizontally behind a load balancer
- Qdrant supports sharding for corpora > 5M segments
- Use managed Qdrant Cloud or Pinecone for production
- Elasticsearch: 3-node cluster for production
- Separate embedding generation service for burst ingestion

---

## Running tests

```bash
# Backend unit + integration tests
docker compose exec backend pytest tests/ -v --cov=app

# Load test (requires k6)
k6 run tests/load/search_load_test.js
```

---

## Metrics exposed

`GET /metrics` returns Prometheus-compatible metrics:

- `lyricfinder_search_latency_ms` — histogram
- `lyricfinder_precision_at_1` — gauge (from feedback)
- `lyricfinder_precision_at_5` — gauge
- `lyricfinder_qps` — counter
- `lyricfinder_ingested_songs_total` — counter
