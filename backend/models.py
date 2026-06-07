from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, JSON
from sqlalchemy.sql import func
from database import Base

class Campaign(Base):
    __tablename__ = "campaigns"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    direction = Column(String, default="outbound")  # "inbound" or "outbound"
    status = Column(String, default="active")       # "active", "paused"
    
    # Crucial for dynamic agent personas
    system_prompt = Column(Text, nullable=True)      # e.g., "You are a helpful real estate assistant..."
    voice_provider = Column(String, default="11labs") # 11labs, playht, openai
    voice_id = Column(String, nullable=True)         # e.g., "burt" or specific hash
    
    # For inbound routing verification
    allocated_phone_number = Column(String, unique=True, index=True, nullable=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class Call(Base):
    __tablename__ = "calls"

    id = Column(Integer, primary_key=True, index=True)
    campaign_id = Column(Integer, ForeignKey("campaigns.id"), nullable=True)
    phone_number = Column(String, nullable=False)
    direction = Column(String, nullable=False)      # inbound or outbound
    telephony_call_id = Column(String, unique=True, index=True, nullable=True)
    status = Column(String, default="queued")       # queued, ringing, in-progress, completed, failed
    transcript = Column(Text, nullable=True)
    ai_summary = Column(Text, nullable=True)
    recording_url = Column(Text, nullable=True)
    duration = Column(Integer, nullable=True)
    started_at = Column(DateTime(timezone=True), nullable=True)
    ended_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class Lead(Base):
    __tablename__ = "leads"

    id = Column(Integer, primary_key=True, index=True)
    campaign_id = Column(Integer, ForeignKey("campaigns.id"), nullable=False)
    phone_number = Column(String, nullable=False)
    name = Column(String, nullable=True)
    status = Column(String, default="pending")       # pending, processing, queued, completed, failed
    created_at = Column(DateTime(timezone=True), server_default=func.now())
