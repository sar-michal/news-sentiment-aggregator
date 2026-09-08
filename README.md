# News Sentiment Aggregator

A full-stack, asynchronous web application combining a FastAPI backend, a React
frontend, Elasticsearch article storage, and a Redis/Celery distributed task
queue. It features a dual-pass Natural Language Processing (NLP) pipeline for
narrative and aspect-based sentiment analysis. It automatically discovers news through the GDELT DOC 2.0 API, stores them, and executes sentiment analysis.

## Repository Layout

- `backend/` - FastAPI application, Celery workers, distributed task services, schemas, and tests.
- `frontend/` - React and TypeScript Single-Page Application (SPA) user interface.
- `ml_experiments/` - Training, hyperparameter-search, and evaluation notebooks.
- `docker-compose.yml` - Containerized infrastructure defining Elasticsearch,
  Redis, API, worker, and scheduler services.

## Prerequisites

- Docker Desktop with Docker Compose
- Node.js and npm (for frontend)
- Python 3.12+ (if running backend tests locally)

## 1. Download the project

Open a terminal and run:

```powershell
git clone https://github.com/sar-michal/news-sentiment-aggregator.git
cd news-sentiment-aggregator
```

## 2. Model Setup (Required)

The fine-tuned Aspect-Based Sentiment Analysis (ABSA) model is excluded from
source control due to its size. A clean clone requires you to download the
trained model separately before starting the backend.

1. Navigate to the project's Releases page.
2. Download `newsmtsc_distilroberta_absa.zip` from the v1.0.0 release.
3. Extract the contents directly into the following directory:
   `backend/ml_models/newsmtsc_distilroberta_absa/`

*Note: The spaCy `en_core_web_md` model is installed while the backend Docker
image is built. The narrative Hugging Face model is downloaded when the Celery
worker initializes. The fine-tuned ABSA model must be downloaded separately
from the GitHub Release.*

## 3. Environment Configuration

After cloning the repository, create the local environment configuration file by
copying the provided example:

```powershell
Copy-Item .env.example .env
```

*(On Linux/macOS use: `cp .env.example .env`)*

## 4. Running the Application

### Start the backend services

Make sure Docker Desktop is running. From the repository root, start the backend
data pipeline and containerized services:

```powershell
docker compose up --build
```

Once running, the API is accessible at `http://localhost:8000`.

### Start the frontend

Open a second terminal. From the repository root, run:

```powershell
cd frontend
npm install
npm run dev
```

The Vite development server displays the frontend address in the terminal, normally `http://localhost:5173`.

## 5. Testing

To run the backend test suite, ensure your virtual environment is active, install
the requirements, and run Pytest from the repository root:

```powershell
pip install -r backend/requirements.txt
python -m pytest backend/tests
```

## Development Notes

The `docker-compose.yml` configuration is intended for local development,
enabling FastAPI hot-reloading and running Celery in a local worker
configuration. To optimize NLP execution, the worker count can be adjusted in
the environment file.
