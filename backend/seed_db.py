import os
from database import engine, SessionLocal, Base
from models import Campaign, Lead, Call


def seed_development_database():
    print("🔄 Initializing voice platform development database schema...")

    # 1. Ensure all structural tables exist in PostgreSQL
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    try:
        # 2. Flush any old conflicting test items safely
        print("🧼 Cleaning up old tracking records...")
        db.query(Call).delete()
        db.query(Lead).delete()
        db.query(Campaign).delete()
        db.commit()

        print("🌱 Seeding Campaign #1: Real Estate Outbound...")

        # 3. Insert Campaign 1 explicitly so the Next.js dashboard targets it perfectly
        outbound_campaign = Campaign(
            id=1,  # Hardcoded for development synchronization
            name="Real Estate Outbound Blast",
            direction="outbound",
            status="active",
            system_prompt=(
                "You are a warm, highly consultative real estate acquisitions agent representing "
                "OMR Holdings. Your goal is to see if the property owner is interested in an all-cash "
                "offer for their asset. Keep your tone professional, relaxed, and concise."
            ),
            voice_provider="11labs",
            voice_id="jBpfwMwrlv6462CDreEM"
        )
        db.add(outbound_campaign)
        db.commit()

        print("👥 Populating mock tracking leads...")
        mock_leads = [
            Lead(campaign_id=1, name="Tony Stark", phone_number="+15550198234", status="completed"),
            Lead(campaign_id=1, name="Natasha Romanoff", phone_number="+15550143829", status="queued"),
            Lead(campaign_id=1, name="Steve Rogers", phone_number="+15550172344", status="pending")
        ]
        db.add_all(mock_leads)
        db.commit()

        print("📞 Populating historical agent call logs...")
        mock_call = Call(
            campaign_id=1,
            phone_number="+15550198234",
            direction="outbound",
            telephony_call_id="vapi-mock-call-99823",
            status="completed",
            transcript=(
                "Agent: Hi Tony, calling to see if you want to sell your Malibu property? "
                "Customer: Only if the price makes sense. Let's talk tomorrow."
            ),
            ai_summary="Customer interested in selling Malibu asset. Requested follow-up callback tomorrow afternoon.",
            recording_url="https://actions.vapi.ai/mock-recording.mp3"
        )
        db.add(mock_call)
        db.commit()

        print("✨ Database successfully seeded! Campaign ID 1 is now active and ready for UI uploads.")

    except Exception as e:
        db.rollback()
        print(f"❌ Database initialization failed: {str(e)}")
    finally:
        db.close()


if __name__ == "__main__":
    seed_development_database()
