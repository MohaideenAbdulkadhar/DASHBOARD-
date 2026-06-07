import random
import time
import requests

from database import SessionLocal
from models import Lead, Call

WEBHOOK_URL = "http://127.0.0.1:8000/api/v1/inbound/webhook"


def run_lifecycle_simulation():
    db = SessionLocal()

    # 1. Generate a completely unique Vapi Call ID and pick a lead
    mock_call_sid = f"vapi-live-{random.randint(10000, 99999)}"

    target_lead = db.query(Lead).filter(Lead.status == "pending").first()
    if not target_lead:
        print("💡 No pending leads found. Please drop a CSV on the UI first, or run seed_db.py!")
        db.close()
        return

    print(f"🎬 [STEP 1/4] Initiating simulated call for {target_lead.name} ({target_lead.phone_number})...")

    new_call = Call(
        campaign_id=target_lead.campaign_id,
        phone_number=target_lead.phone_number,
        direction="outbound",
        telephony_call_id=mock_call_sid,
        status="ringing",
    )
    db.add(new_call)
    target_lead.status = "processing"
    db.commit()

    print(f"📡 Call record generated with ID: {mock_call_sid}. Status: RINGING.")
    print("⏳ Pausing for 5 seconds... Look at your dashboard UI now to see the live call appear.")
    time.sleep(5)

    print("\n📞 [STEP 2/4] Simulating active conversation on the line...")
    new_call.status = "in-progress"
    db.commit()
    print("⏳ Conversation active... Pausing another 4 seconds.")
    time.sleep(4)

    print("\n🏁 [STEP 3/4] Customer hung up. Triggering Vapi End-of-Call Webhook Report...")
    payload = {
        "message": {
            "type": "end-of-call-report",
            "call": {"id": mock_call_sid, "status": "ended"},
            "customer": {"number": target_lead.phone_number},
            "transcript": (
                f"AI Agent: Hello {target_lead.name}, confirming our conversation regarding the commercial asset?\n"
                f"Customer: Yes, please send over the pricing documentation via email.\n"
                f"AI Agent: Understood! Sending that over right now. Have a great day!"
            ),
            "analysis": {
                "summary": (
                    f"Successful contact. {target_lead.name} requested immediate pricing documentation. Follow-up email sent."
                )
            },
            "recordingUrl": "https://actions.vapi.ai/mock-recording.mp3",
        }
    }

    try:
        response = requests.post(WEBHOOK_URL, json=payload)
        if response.status_code == 200:
            target_lead.status = "completed"
            db.commit()
            print("✨ Webhook synchronization accepted! Check the dashboard for completed call status and transcript details.")
            print(f"Response: {response.json()}")
        else:
            print(f"❌ Webhook rejected: {response.status_code} - {response.text}")
    except Exception as exc:
        print(f"❌ Request failed: {exc}")
    finally:
        db.close()


if __name__ == "__main__":
    run_lifecycle_simulation()
