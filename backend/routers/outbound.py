from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session
from sqlalchemy import func
import csv
import io
import json
import redis
import os
from database import get_db
from models import Campaign, Lead, Call

router = APIRouter()
redis_client = redis.Redis.from_url(os.getenv("REDIS_URL", "redis://localhost:6379/0"))

@router.post("/campaign/{campaign_id}/upload-csv")
async def upload_campaign_leads(
    campaign_id: int, 
    file: UploadFile = File(...), 
    db: Session = Depends(get_db)
):
    """
    Accepts a raw CSV file, maps 'phone' and 'name' columns, saves records to Postgres,
    and publishes task blocks directly into the Redis queue.
    """
    # 1. Verify Campaign existence
    campaign = db.query(Campaign).filter(Campaign.id == campaign_id).first()
    if not campaign:
        raise HTTPException(status_code=404, detail="Target campaign configuration not found.")

    # 2. Read and parse incoming file buffer
    try:
        contents = await file.read()
        buffer = io.StringIO(contents.decode('utf-8'))
        reader = csv.DictReader(buffer)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid CSV format or encoding error.")

    # Clean up column spaces dynamically to avoid user input formatting bugs
    headers = [h.strip().lower() for h in reader.fieldnames] if reader.fieldnames else []
    
    # Simple semantic mapping matching normal variations
    phone_key = next((h for h in reader.fieldnames if h.strip().lower() in ['phone', 'phone_number', 'telephone', 'number']), None)
    name_key = next((h for h in reader.fieldnames if h.strip().lower() in ['name', 'first_name', 'full_name', 'customer']), None)

    if not phone_key:
        raise HTTPException(status_code=400, detail="Missing required 'phone' column in CSV header.")

    leads_to_insert = []

    # 3. Process records
    for row in reader:
        phone = row.get(phone_key, "").strip()
        name = row.get(name_key, "").strip() if name_key else "Valued Customer"

        if not phone:
            continue # Skip blank rows safely

        # Stage database record instances
        lead_record = Lead(
            campaign_id=campaign_id,
            phone_number=phone,
            name=name,
            status="queued"
        )
        leads_to_insert.append(lead_record)

    if not leads_to_insert:
        return {"status": "success", "message": "No valid leads found in file."}

    # 4. Batch commit to Postgres for instant UI visibility
    db.add_all(leads_to_insert)
    db.commit()

    # 5. Push task configurations to Redis pipeline for asynchronous worker execution
    for lead in leads_to_insert:
        job_data = {
            "campaign_id": campaign_id,
            "lead_id": lead.id,
            "phone_number": lead.phone_number,
            "name": lead.name
        }
        redis_client.rpush("outbound_voice_queue", json.dumps(job_data))

    return {
        "status": "success",
        "campaign_id": campaign_id,
        "total_imported": len(leads_to_insert),
        "message": f"Successfully injected {len(leads_to_insert)} leads directly into dialing matrix."
    }


@router.get("/campaign/{campaign_id}/metrics")
async def get_campaign_metrics(campaign_id: int, db: Session = Depends(get_db)):
    """
    Returns live tracking statistics, processing velocities, and completion metrics for a designated campaign block.
    """
    total_leads = db.query(func.count(Lead.id)).filter(Lead.campaign_id == campaign_id).scalar() or 0

    status_counts = db.query(Call.status, func.count(Call.id)) \
        .filter(Call.campaign_id == campaign_id) \
        .group_by(Call.status).all()

    metrics = {status: count for status, count in status_counts}
    queued = metrics.get("queued", 0)
    ringing = metrics.get("ringing", 0)
    in_progress = metrics.get("in-progress", 0)
    completed = metrics.get("completed", 0)
    failed = metrics.get("failed", 0)

    total_processed = completed + failed
    progress_percentage = (total_processed / total_leads * 100) if total_leads > 0 else 0

    return {
        "campaign_id": campaign_id,
        "total_leads": total_leads,
        "progress_bar_percentage": round(progress_percentage, 1),
        "counters": {
            "queued": queued,
            "ringing": ringing,
            "in_progress": in_progress,
            "completed": completed,
            "failed": failed
        }
    }


@router.get("/campaign/{campaign_id}/leads-detail")
async def get_campaign_leads_detail(campaign_id: int, db: Session = Depends(get_db)):
    """
    Returns all leads for a campaign with their associated call outcomes, transcripts, and summaries.
    """
    leads = db.query(Lead).filter(Lead.campaign_id == campaign_id).order_by(Lead.created_at.desc()).all()

    result = []
    for lead in leads:
        # Fetch call records associated with this lead's phone number
        calls = db.query(Call).filter(
            Call.campaign_id == campaign_id,
            Call.phone_number == lead.phone_number
        ).all()

        # Get the most recent call if multiple exist
        latest_call = calls[0] if calls else None

        lead_detail = {
            "lead_id": lead.id,
            "phone_number": lead.phone_number,
            "name": lead.name,
            "lead_status": lead.status,
            "call_status": latest_call.status if latest_call else "pending",
            "transcript": latest_call.transcript if latest_call else None,
            "ai_summary": latest_call.ai_summary if latest_call else None,
            "recording_url": latest_call.recording_url if latest_call else None,
            "created_at": lead.created_at.isoformat() if lead.created_at else None
        }
        result.append(lead_detail)

    return {
        "campaign_id": campaign_id,
        "total_leads": len(result),
        "leads": result
    }


@router.get("/lead/{lead_id}/details")
async def get_lead_call_details(lead_id: int, db: Session = Depends(get_db)):
    """
    Fetches the concrete call performance metrics, transcript block,
    and systemic tracking parameters linked to a targeted consumer row.
    """
    lead = db.query(Lead).filter(Lead.id == lead_id).first()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead record not found.")

    call_record = db.query(Call) \
        .filter(Call.campaign_id == lead.campaign_id, Call.phone_number == lead.phone_number) \
        .order_by(Call.created_at.desc()) \
        .first()

    if not call_record:
        return {
            "name": lead.name,
            "phone_number": lead.phone_number,
            "status": lead.status,
            "call_status": "pending",
            "transcript": "This lead is currently queued or awaiting automated worker execution.",
            "ai_summary": "—",
            "recording_url": None
        }

    return {
        "name": lead.name,
        "phone_number": lead.phone_number,
        "status": call_record.status,
        "call_status": call_record.status,
        "transcript": call_record.transcript or "Transcript generation underway...",
        "ai_summary": call_record.ai_summary or "Parsing conversation details...",
        "recording_url": call_record.recording_url
    }

