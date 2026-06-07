import time
import json
import os
import redis
import requests
from database import SessionLocal
from models import Campaign, Call, Lead

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
redis_client = redis.Redis.from_url(REDIS_URL)

# Vapi credentials (Set these in docker-compose environment later)
VAPI_API_KEY = os.getenv("VAPI_API_KEY", "YOUR_VAPI_API_KEY")
VAPI_PHONE_NUMBER_ID = os.getenv("VAPI_PHONE_NUMBER_ID", "YOUR_VAPI_PHONE_NUMBER_ID")


def trigger_vapi_outbound_call(phone_number: str, campaign: Campaign):
    """
    Instructs Vapi via API to dial an outbound customer using a specific agent config.
    """
    url = "https://api.vapi.ai/call/phone"
    headers = {
        "Authorization": f"Bearer {VAPI_API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "phoneNumberId": VAPI_PHONE_NUMBER_ID,
        "customer": {
            "number": phone_number
        },
        "assistant": {
            "firstMessage": "Hi there! I am calling from the automation team. Is this a good time to chat?",
            "model": {
                "provider": "openai",
                "model": "gpt-4o",
                "messages": [
                    {"role": "system", "content": campaign.system_prompt or "You are a cold outreach AI agent."}
                ]
            },
            "voice": {
                "provider": campaign.voice_provider,
                "voiceId": campaign.voice_id or "jBpfwMwrlv6462CDreEM"
            }
        }
    }
    
    try:
        response = requests.post(url, headers=headers, json=payload)
        if response.status_code in [200, 201]:
            return response.json().get("id")
        else:
            print(f"Vapi API Error: {response.text}")
            return None
    except Exception as e:
        print(f"Failed to communicate with Vapi: {str(e)}")
        return None


def process_outbound_queue():
    print("Outbound Voice Worker running... tracking Redis queue 'outbound_voice_queue'")
    db = SessionLocal()
    
    try:
        while True:
            # Pull a lead from the queue (blocks until a job arrives)
            result = redis_client.blpop("outbound_voice_queue", timeout=5)
            if not result:
                continue
                
            _, raw_job = result
            job = json.loads(raw_job)
            
            campaign_id = job.get("campaign_id")
            phone_number = job.get("phone_number")
            lead_id = job.get("lead_id")
            
            # Fetch campaign rules from DB
            campaign = db.query(Campaign).filter(Campaign.id == campaign_id).first()
            if not campaign:
                print(f"Skipping job: Campaign {campaign_id} not found in DB.")
                continue

            # Mark lead as processing when available
            lead = None
            if lead_id:
                lead = db.query(Lead).filter(Lead.id == lead_id).first()
                if lead:
                    lead.status = 'processing'
                    db.commit()

            print(f"Launching outbound AI call to {phone_number} for campaign: {campaign.name}")

            # Trigger the actual voice carrier
            telephony_id = trigger_vapi_outbound_call(phone_number, campaign)

            # Record call history state inside our dashboard environment
            new_call = Call(
                campaign_id=campaign.id,
                phone_number=phone_number,
                direction="outbound",
                telephony_call_id=telephony_id,
                status="ringing" if telephony_id else "failed"
            )
            db.add(new_call)
            db.commit()

            # Update lead status to reflect call state
            if lead:
                lead.status = 'queued' if telephony_id else 'failed'
                db.commit()
            
            # Protect API rate limits
            time.sleep(1)
            
    except KeyboardInterrupt:
        print("Worker stopped manually.")
    finally:
        db.close()


if __name__ == "__main__":
    process_outbound_queue()
