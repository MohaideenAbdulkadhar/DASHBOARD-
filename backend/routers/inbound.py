from fastapi import APIRouter, Depends, Response, HTTPException
from sqlalchemy.orm import Session
from database import get_db
from models import Campaign, Call
from pydantic import BaseModel

router = APIRouter()

@router.post("/webhook")
async def handle_vapi_inbound(payload: dict, db: Session = Depends(get_db)):
    """
    Handles Vapi's assistantRequest webhook for real-time inbound routing.
    """
    # Vapi sends event data wrapped in a message object
    message = payload.get("message", {})
    event_type = message.get("type")
    
    # 1. Handle Assistant Configuration Request
    if event_type == "assistantRequest":
        # Extract the phone number the user dialed
        called_number = message.get("phoneNumber", {}).get("number")
        call_id = message.get("call", {}).get("id")
        customer_number = message.get("customer", {}).get("number", "Unknown")

        # Query database for an active inbound campaign tied to this platform number
        campaign = db.query(Campaign).filter(
            Campaign.direction == "inbound",
            Campaign.allocated_phone_number == called_number,
            Campaign.status == "active"
        ).first()

        # Fallback to general inbound campaign if a specific number match isn't found
        if not campaign:
            campaign = db.query(Campaign).filter(Campaign.direction == "inbound").first()

        if not campaign:
            # Tell Vapi to say a fallback error message if your DB is completely empty
            return {
                "assistant": {
                    "firstMessage": "Hello, thank you for calling. Our servers are currently undergoing maintenance.",
                    "model": {"provider": "openai", "model": "gpt-4o", "messages": [{"role": "system", "content": "Tell the user goodbye."}]}
                }
            }

        # Log the live inbound call tracking record
        new_call = Call(
            campaign_id=campaign.id,
            phone_number=customer_number,
            direction="inbound",
            telephony_call_id=call_id,
            status="in-progress"
        )
        db.add(new_call)
        db.commit()

        # Respond to Vapi dynamically with the exact prompt and voice from PostgreSQL
        return {
            "assistant": {
                "firstMessage": f"Hello! Thanks for calling. How can I help you today?",
                "model": {
                    "provider": "openai",
                    "model": "gpt-4o",
                    "temperature": 0.7,
                    "messages": [
                        {
                            "role": "system",
                            "content": campaign.system_prompt or "You are a helpful AI voice assistant."
                        }
                    ]
                },
                "voice": {
                    "provider": campaign.voice_provider,
                    "voiceId": campaign.voice_id or "jBpfwMwrlv6462CDreEM"
                }
            }
        }

    # 2. Handle End of Call Webhook (Save logs, transcripts, costs)
    elif event_type in ["endOfCallReport", "end-of-call-report"]:
        call_id = message.get("call", {}).get("id")
        transcript = message.get("transcript", "")
        analysis = message.get("analysis", {})
        summary = analysis.get("summary", "No summary generated.")
        recording_url = payload.get("recordingUrl") or message.get("recordingUrl", "")

        existing_call = db.query(Call).filter(Call.telephony_call_id == call_id).first()
        if existing_call:
            existing_call.status = "completed"
            existing_call.transcript = transcript
            existing_call.ai_summary = summary
            existing_call.recording_url = recording_url
            db.commit()
            return {"status": "success", "message": "Call log synchronized successfully."}

        customer_phone = message.get("customer", {}).get("number")
        existing_call_by_phone = db.query(Call).filter(
            Call.phone_number == customer_phone,
            Call.status == "ringing"
        ).first()

        if existing_call_by_phone:
            existing_call_by_phone.telephony_call_id = call_id
            existing_call_by_phone.status = "completed"
            existing_call_by_phone.transcript = transcript
            existing_call_by_phone.ai_summary = summary
            existing_call_by_phone.recording_url = recording_url
            db.commit()
            return {"status": "success", "message": "Call log synchronized via phone fallback."}

        return {"status": "ignored", "message": "No matching active call found in platform database."}

    return {"status": "received"}


class ProvisionNumberRequest(BaseModel):
    allocated_phone_number: str
    system_prompt: str
    voice_id: str


@router.get("/available-numbers")
async def list_available_platform_numbers():
    """
    Simulates fetching available unassigned numbers from Vapi/Twilio inventory
    so your clients can choose one inside the dashboard UI.
    """
    return [
        {"id": "num_1", "phone_number": "+18555019001", "location": "Toll-Free, US"},
        {"id": "num_2", "phone_number": "+18555019002", "location": "Toll-Free, US"},
        {"id": "num_3", "phone_number": "+12125550193", "location": "New York, NY"},
    ]


@router.post("/campaign/{campaign_id}/assign-number")
async def assign_number_to_campaign(
    campaign_id: int,
    payload: ProvisionNumberRequest,
    db: Session = Depends(get_db),
):
    """
    Binds an inbound phone number configuration and agent persona profile
    to a designated campaign block.
    """
    campaign = db.query(Campaign).filter(Campaign.id == campaign_id).first()
    if not campaign:
        raise HTTPException(status_code=404, detail="Target campaign configuration not found.")

    # Update database properties to convert or lock this campaign for inbound traffic routing
    campaign.direction = "inbound"
    campaign.allocated_phone_number = payload.allocated_phone_number
    campaign.system_prompt = payload.system_prompt
    campaign.voice_id = payload.voice_id
    campaign.status = "active"

    db.commit()

    return {
        "status": "success",
        "message": f"Successfully routed {payload.allocated_phone_number} to Inbound Campaign: '{campaign.name}'.",
    }
