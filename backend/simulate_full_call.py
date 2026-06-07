import random
import time
import requests
from datetime import datetime, timedelta, timezone

from database import SessionLocal
from models import Lead, Call

WEBHOOK_URL = "http://127.0.0.1:8000/api/v1/inbound/webhook"


def run_production_telemetry_simulation():
    db = SessionLocal()

    target_lead = db.query(Lead).filter(Lead.status == "pending").first()
    if not target_lead:
        target_lead = db.query(Lead).first()

    if not target_lead:
        print("💡 Database leads empty. Please upload a CSV via the dashboard or run seed_db.py first!")
        db.close()
        return

    mock_call_sid = f"vapi-prod-hash-{random.randint(100000, 999999)}"
    print(f"🎬 [STEP 1/2] Simulating call network handshake for {target_lead.name}...")

    new_call = Call(
        campaign_id=target_lead.campaign_id,
        phone_number=target_lead.phone_number,
        direction="outbound",
        telephony_call_id=mock_call_sid,
        status="ringing"
    )
    db.add(new_call)
    db.commit()

    print(f"📡 Call tracing active on pipeline ID: {mock_call_sid}. Look at your Next.js feed now!")
    time.sleep(4)

    simulated_duration_seconds = random.randint(45, 280)
    now_utc = datetime.now(timezone.utc)
    started_utc = now_utc - timedelta(seconds=simulated_duration_seconds)

    started_at_iso = started_utc.strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"
    ended_at_iso = now_utc.strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"

    print(f"\n🏁 [STEP 2/2] Call disconnected by consumer. Compiling Vapi production payload...\nDuration: {simulated_duration_seconds}s | startedAt: {started_at_iso}")

    payload = {
        "message": {
            "type": "end-of-call-report",
            "call": {
                "id": mock_call_sid,
                "status": "ended",
                "duration": simulated_duration_seconds,
                "startedAt": started_at_iso,
                "endedAt": ended_at_iso
            },
            "customer": {
                "number": target_lead.phone_number
            },
            "transcript": (
                f"AI Agent (Divya): Greetings {target_lead.name}, thank you for taking the time to speak today.\n"
                f"Customer: Sure thing. I was curious about the pricing framework for your automation options.\n"
                f"AI Agent (Divya): Wonderful. Our core configuration starts at tiered monthly scales. Let's arrange a deep-dive call.\n"
                f"Customer: Excellent. Let's book it for next Tuesday. Goodbye."
            ),
            "analysis": {
                "summary": f"Inbound inquiry follow-up. Lead expressed solid alignment. Booked technical deep-dive slot for next Tuesday morning."
            },
            "recordingUrl": "https://actions.vapi.ai/mock-recording.mp3"
        }
    }

    try:
        response = requests.post(WEBHOOK_URL, json=payload)
        if response.status_code == 200:
            target_lead.status = "completed"
            db.commit()
            print("\n✨ Webhook payload fully parsed and accepted by target FastAPI schema!")
            print(f"📊 Synthesized Telemetry Metrics Transmitted -> Duration: {simulated_duration_seconds}s | Started: {started_at_iso}")
        else:
            print(f"❌ Webhook mapping broken: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"❌ Connection crash: {str(e)}")
    finally:
        db.close()


if __name__ == "__main__":
    run_production_telemetry_simulation()
