from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional, List
from sqlalchemy.orm import Session
from datetime import datetime

from database import get_db, CallRecord
from config import settings

router = APIRouter()


# ── Schemas ──────────────────────────────────────────────────────────────────

class NegotiationRequest(BaseModel):
    load_id: str
    loadboard_rate: float
    carrier_offer: float
    negotiation_round: int  # 1, 2, or 3


class NegotiationResponse(BaseModel):
    accept: bool
    counter_offer: Optional[float] = None
    message: str
    final: bool  # True if this is the last round


class CallRecordCreate(BaseModel):
    call_id: str
    mc_number: Optional[str] = None
    carrier_name: Optional[str] = None
    load_id: Optional[str] = None
    origin: Optional[str] = None
    destination: Optional[str] = None
    loadboard_rate: Optional[float] = None
    offered_rate: Optional[float] = None
    final_agreed_rate: Optional[float] = None
    negotiation_rounds: Optional[int] = 0
    outcome: Optional[str] = None
    sentiment: Optional[str] = None
    fmcsa_verified: Optional[str] = None
    call_duration_seconds: Optional[int] = None
    notes: Optional[str] = None


class CallRecordResponse(BaseModel):
    id: int
    call_id: str
    mc_number: Optional[str]
    carrier_name: Optional[str]
    load_id: Optional[str]
    origin: Optional[str]
    destination: Optional[str]
    loadboard_rate: Optional[float]
    offered_rate: Optional[float]
    final_agreed_rate: Optional[float]
    negotiation_rounds: Optional[int]
    outcome: Optional[str]
    sentiment: Optional[str]
    fmcsa_verified: Optional[str]
    call_duration_seconds: Optional[int]
    notes: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


class MetricsSummary(BaseModel):
    total_calls: int
    booked: int
    no_deal: int
    transferred: int
    abandoned: int
    booking_rate: float
    avg_final_rate: Optional[float]
    avg_discount_pct: Optional[float]
    avg_negotiation_rounds: float
    sentiment_breakdown: dict


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.post("/negotiate", response_model=NegotiationResponse)
def evaluate_negotiation(req: NegotiationRequest):
    """
    Evaluate a carrier's counter offer and respond with accept/counter/reject.
    Called by the HappyRobot agent during price negotiation.
    Max 3 rounds. Floor is MIN_RATE_FACTOR * loadboard_rate.
    """
    floor = round(req.loadboard_rate * settings.MIN_RATE_FACTOR, 2)
    max_rounds = 3

    # Carrier is offering more than or equal to loadboard rate — accept immediately
    if req.carrier_offer >= req.loadboard_rate:
        return NegotiationResponse(
            accept=True,
            message=f"We can work with that. Let's confirm the load at ${req.carrier_offer:,.0f}.",
            final=True,
        )

    # Carrier is below our floor — can't accept
    if req.carrier_offer < floor:
        if req.negotiation_round >= max_rounds:
            return NegotiationResponse(
                accept=False,
                message=(
                    f"I appreciate the back and forth, but we can't go below ${floor:,.0f} on this load. "
                    f"Unfortunately we're not able to reach a deal today."
                ),
                final=True,
            )
        # Counter at midpoint between their offer and loadboard rate
        counter = round((req.carrier_offer + req.loadboard_rate) / 2, 2)
        counter = max(counter, floor)
        return NegotiationResponse(
            accept=False,
            counter_offer=counter,
            message=(
                f"That's a bit low for us. Best I can do is ${counter:,.0f}. "
                f"Does that work for you?"
            ),
            final=req.negotiation_round >= max_rounds,
        )

    # Carrier offer is between floor and loadboard rate — accept
    return NegotiationResponse(
        accept=True,
        message=f"Alright, we can do ${req.carrier_offer:,.0f}. Let's get this booked.",
        final=True,
    )


@router.post("/record", response_model=CallRecordResponse)
def record_call(record: CallRecordCreate, db: Session = Depends(get_db)):
    """
    Save the call outcome data after a call ends.
    Called by HappyRobot workflow at the end of each call.
    """
    existing = db.query(CallRecord).filter(CallRecord.call_id == record.call_id).first()
    if existing:
        for key, value in record.model_dump(exclude_unset=True).items():
            setattr(existing, key, value)
        existing.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(existing)
        return existing

    db_record = CallRecord(**record.model_dump())
    db.add(db_record)
    db.commit()
    db.refresh(db_record)
    return db_record


@router.get("/records", response_model=List[CallRecordResponse])
def list_call_records(
    limit: int = 100,
    offset: int = 0,
    outcome: Optional[str] = None,
    db: Session = Depends(get_db),
):
    """List all call records, optionally filtered by outcome."""
    query = db.query(CallRecord)
    if outcome:
        query = query.filter(CallRecord.outcome == outcome)
    return query.order_by(CallRecord.created_at.desc()).offset(offset).limit(limit).all()


@router.get("/metrics", response_model=MetricsSummary)
def get_metrics(db: Session = Depends(get_db)):
    """
    Aggregate call metrics for the dashboard.
    """
    records = db.query(CallRecord).all()
    total = len(records)

    if total == 0:
        return MetricsSummary(
            total_calls=0, booked=0, no_deal=0, transferred=0, abandoned=0,
            booking_rate=0.0, avg_final_rate=None, avg_discount_pct=None,
            avg_negotiation_rounds=0.0,
            sentiment_breakdown={"positive": 0, "neutral": 0, "negative": 0},
        )

    booked = sum(1 for r in records if r.outcome == "booked")
    no_deal = sum(1 for r in records if r.outcome == "no_deal")
    transferred = sum(1 for r in records if r.outcome == "transferred")
    abandoned = sum(1 for r in records if r.outcome == "abandoned")

    final_rates = [r.final_agreed_rate for r in records if r.final_agreed_rate]
    avg_final = round(sum(final_rates) / len(final_rates), 2) if final_rates else None

    discounts = [
        (r.loadboard_rate - r.final_agreed_rate) / r.loadboard_rate * 100
        for r in records
        if r.final_agreed_rate and r.loadboard_rate
    ]
    avg_discount = round(sum(discounts) / len(discounts), 2) if discounts else None

    rounds = [r.negotiation_rounds for r in records if r.negotiation_rounds is not None]
    avg_rounds = round(sum(rounds) / len(rounds), 2) if rounds else 0.0

    sentiments = {"positive": 0, "neutral": 0, "negative": 0}
    for r in records:
        if r.sentiment in sentiments:
            sentiments[r.sentiment] += 1

    return MetricsSummary(
        total_calls=total,
        booked=booked,
        no_deal=no_deal,
        transferred=transferred,
        abandoned=abandoned,
        booking_rate=round(booked / total * 100, 2) if total > 0 else 0.0,
        avg_final_rate=avg_final,
        avg_discount_pct=avg_discount,
        avg_negotiation_rounds=avg_rounds,
        sentiment_breakdown=sentiments,
    )
