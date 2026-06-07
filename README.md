# AI Voice Platform

A dual-pipeline AI voice agent platform supporting both **inbound** and **outbound** calls with real-time dashboards using Vapi as the telephony provider.

## Architecture

- **Frontend**: Next.js React dashboard
- **Backend**: FastAPI Python service with Vapi webhook handling
- **Message Queue**: Redis for outbound job processing
- **Database**: PostgreSQL for campaigns, calls, and transcripts
- **Worker**: Separate background process for voice orchestration
- **Telephony**: Vapi for high-latency AI voice calls (< 200ms)

## Prerequisites

- Docker & Docker Compose installed
- 8GB RAM available
- Vapi account with API key ([sign up here](https://vapi.ai))

## Setup

### 1. Get Vapi Credentials

1. Create a [Vapi account](https://vapi.ai)
2. Create a phone number (get your `VAPI_PHONE_NUMBER_ID`)
3. Generate an API key (get your `VAPI_API_KEY`)

### 2. Configure Environment

Copy `.env.example` to `.env` and fill in your Vapi credentials:

```bash
cp .env.example .env
```

Edit `.env`:
```env
VAPI_API_KEY=your_vapi_api_key_here
VAPI_PHONE_NUMBER_ID=your_vapi_phone_number_id_here
```

### 3. Spin Up Services

```bash
docker-compose up --build
```

Wait for all services to be healthy (~30 seconds).

### 4. Seed Test Campaign

Once containers are running, seed a test campaign:

```bash
docker exec -it voice_postgres psql -U postgres -d voice_platform -c \
"INSERT INTO campaigns (name, direction, status, system_prompt, voice_provider, voice_id) VALUES \
('Real Estate Outbound', 'outbound', 'active', 'You are a warm real estate agent calling to discuss property investment opportunities.', '11labs', 'jBpfwMwrlv6462CDreEM'), \
('Inbound Support', 'inbound', 'active', 'You are a technical support specialist helping customers with billing and account issues.', '11labs', 'jBpfwMwrlv6462CDreEM');"
```

## Access Points

- **Dashboard UI**: http://localhost:3000
- **API Docs**: http://localhost:8000/docs
- **Health Check**: http://localhost:8000

## Testing the Minimum Viable Voice Loop

### Test Outbound Calling

1. Go to `http://localhost:3000`
2. Click **"Test Outbound Pipeline (Queue 2 leads)"**
3. Check logs: `docker-compose logs -f backend-worker`
4. Watch the worker:
   - Pull job from Redis queue
   - Look up campaign system prompt from PostgreSQL
   - Call Vapi API to dial the phone number
   - Record call status in database

Expected logs:
```
backend-worker | Launching outbound AI call to +1234567890 for campaign: Real Estate Outbound
```

### Test Inbound Calling

1. Configure your Vapi phone number with webhook server URL: `https://your-domain.com/api/v1/inbound/webhook`
2. When someone calls, Vapi sends assistant request
3. Backend responds with campaign configuration
4. Call is logged to database with transcript

## Project Structure

```
ai-voice-platform/
├── docker-compose.yml          # Orchestrates all services
├── .env.example                # Environment template
├── README.md                   # This file
├── backend/                    # Python FastAPI service
│   ├── main.py                # FastAPI app
│   ├── models.py              # SQLAlchemy models (Campaign, Call)
│   ├── database.py            # Database connection
│   ├── worker.py              # Redis queue processor + Vapi orchestrator
│   ├── requirements.txt        # Python dependencies
│   └── routers/
│       ├── inbound.py         # Vapi webhook handler (<200ms response)
│       └── outbound.py        # Campaign trigger endpoint
└── frontend/                  # Next.js dashboard
    ├── package.json
    ├── next.config.js
    └── src/app/
        ├── page.tsx           # Main controller UI
        ├── layout.tsx         # Root layout
        └── api/campaigns/     # API routes
```

## Core Features

### Campaigns Table
- `name`: Campaign identifier
- `direction`: "inbound" or "outbound"
- `status`: "active" or "paused"
- `system_prompt`: AI personality and instructions
- `voice_provider`: "11labs", "playht", etc.
- `voice_id`: Voice character selection
- `allocated_phone_number`: For inbound routing

### Calls Table
- Unified logging for inbound/outbound calls
- `telephony_call_id`: Vapi call identifier
- `status`: queued → ringing → in-progress → completed
- `transcript`: Full call transcript
- `ai_summary`: AI-generated summary
- `recording_url`: Call recording

## Next Steps

1. **CSV Lead Importer**: Build frontend to upload CSV files into campaigns
2. **Live Call Logs**: Display real-time call status and recordings
3. **Analytics Dashboard**: KPIs, conversion metrics, performance graphs
4. **CRM Integrations**: Sync leads from Salesforce, HubSpot, etc.
5. **Advanced AI Routing**: Conditional flows based on caller responses

## Troubleshooting

**Worker not connecting to Vapi?**
- Check `VAPI_API_KEY` and `VAPI_PHONE_NUMBER_ID` in `.env`
- Verify Vapi account has active phone numbers

**Database tables not created?**
- Check PostgreSQL logs: `docker-compose logs postgres`
- Manually seed data as shown in Setup step 4

**Next.js can't reach backend?**
- Ensure backend-api is healthy: `docker-compose logs backend-api`
- Check `NEXT_PUBLIC_API_URL` in docker-compose.yml
