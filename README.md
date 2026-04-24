# Carrier Sales API

Inbound carrier load sales automation API built for the HappyRobot platform. Powers an AI voice agent that handles inbound calls from freight carriers, verifying their credentials, matching them to available loads, and negotiating pricing automatically.

---

## What it does

When a carrier calls in via HappyRobot, this API handles the full backend workflow:

1. Verifies the carrier MC number against the FMCSA database
2. Searches available loads by origin, destination, and equipment type
3. Evaluates counter offers and drives price negotiation (up to 3 rounds)
4. Records call outcomes, agreed rates, and carrier sentiment
5. Serves aggregated metrics to a live operations dashboard

---

## Tech stack

- Python 3.12 with FastAPI
- SQLite via SQLAlchemy (upgradeable to PostgreSQL)
- Docker for containerisation
- Railway for cloud deployment
- HappyRobot as the voice AI platform

---

## Project structure

```
carrier-sales-api/
├── main.py              # FastAPI app entry point and authentication
├── config.py            # Environment variables
├── database.py          # Database models and connection
├── loads.py             # Load search endpoints
├── carriers.py          # FMCSA carrier verification
├── calls.py             # Negotiation logic, call recording, metrics
├── loads.json           # Load dataset (10 loads across US and Australia)
├── Dockerfile           # Container build instructions
├── docker-compose.yml   # Local development setup
├── requirements.txt     # Python dependencies
└── .env.example         # Environment variable template
```

---

## API endpoints

| Method | Endpoint | Description | Auth |
|--------|----------|-------------|------|
| GET | `/health` | Health check | No |
| GET | `/carriers/verify` | Verify carrier MC number via FMCSA | Yes |
| GET | `/loads/search` | Search loads by origin, destination, equipment | Yes |
| GET | `/loads/{load_id}` | Get a specific load by ID | Yes |
| POST | `/calls/negotiate` | Evaluate a carrier counter offer | Yes |
| POST | `/calls/record` | Save call outcome data | Yes |
| GET | `/calls/records` | List all call records | Yes |
| GET | `/calls/metrics` | Aggregated metrics for the dashboard | Yes |

All protected endpoints require an `X-API-Key` header.

---

## Running locally

**1. Clone the repository**

```bash
git clone https://github.com/pabloalonsomartineza/carrier-sales-api
cd carrier-sales-api
```

**2. Set up environment variables**

```bash
cp .env.example .env
```

Edit `.env` and set:

```
API_KEY=your-secret-key
FMCSA_API_KEY=your-fmcsa-key
DATABASE_URL=sqlite:///./calls.db
LOADS_FILE=loads.json
MIN_RATE_FACTOR=0.85
```

**3. Run with Docker**

```bash
docker-compose up
```

The API will be available at `http://localhost:8000`. Interactive docs at `http://localhost:8000/docs`.

**4. Run without Docker**

```bash
pip install -r requirements.txt
python init_db.py
uvicorn main:app --reload
```

---

## Deploying to Railway

1. Fork or clone this repository to your GitHub account
2. Go to railway.app and create a new project
3. Select "Deploy from GitHub repo" and choose this repository
4. Go to Settings > Networking and click "Generate Domain"
5. Set port to 8000
6. Go to Variables and add the following environment variables:

```
API_KEY=your-secret-key
FMCSA_API_KEY=your-fmcsa-key
LOADS_FILE=loads.json
MIN_RATE_FACTOR=0.85
```

Railway will redeploy automatically on every push to the main branch.

---

## HappyRobot integration

The API is designed to be called by a HappyRobot inbound voice agent. Configure the following tools in your HappyRobot workflow:

| Tool | Method | Endpoint | When to call |
|------|--------|----------|--------------|
| verify_carrier | GET | /carriers/verify | At the start of every call |
| search_loads | GET | /loads/search | After understanding the carrier lane |
| evaluate_negotiation | POST | /calls/negotiate | When the carrier makes a counter offer |
| record_call | POST | /calls/record | At the end of every call |

All requests must include the `X-API-Key` header.

---

## FMCSA API

If no FMCSA API key is set, the API runs in demo mode:
- MC numbers ending in 0 are treated as inactive carriers
- All other MC numbers are treated as verified

To get a live FMCSA API key, register at ai.fmcsa.dot.gov.

---

## Negotiation logic

The minimum acceptable rate is set by `MIN_RATE_FACTOR` (default 0.85, meaning 85% of the listed loadboard rate).

- If the carrier offers above the floor, the system accepts
- If below, it counters at the midpoint between their offer and the listed rate
- After 3 rounds without agreement, the call ends

---

## Dashboard

A standalone HTML dashboard is available in the `dashboard/` folder. Open `index.html` in any browser, enter the API base URL and API key, and click "Load live data".

Metrics shown:
- Total calls and booking rate
- Average agreed rate and discount percentage
- Average negotiation rounds
- Call outcome breakdown (booked, no deal, transferred, abandoned)
- Carrier sentiment breakdown (positive, neutral, negative)
- Recent calls table

---

## Security

- All endpoints are protected with API key authentication via the `X-API-Key` header
- HTTPS is enabled automatically via Railway managed TLS in production
- Sensitive configuration is managed via environment variables, never hardcoded

---

## Author

Pablo Alonso Martinez Arroyo
