from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import Optional, List
import json
import os

from app.config import settings

router = APIRouter()


def load_loads_data():
    path = settings.LOADS_FILE
    if not os.path.exists(path):
        raise FileNotFoundError(f"Loads file not found: {path}")
    with open(path, "r") as f:
        return json.load(f)


class Load(BaseModel):
    load_id: str
    origin: str
    destination: str
    pickup_datetime: str
    delivery_datetime: str
    equipment_type: str
    loadboard_rate: float
    notes: str
    weight: float
    commodity_type: str
    num_of_pieces: int
    miles: float
    dimensions: str


class LoadSearchResponse(BaseModel):
    found: bool
    loads: List[Load]
    message: str


@router.get("/search", response_model=LoadSearchResponse)
def search_loads(
    origin: Optional[str] = Query(None, description="Origin city or state"),
    destination: Optional[str] = Query(None, description="Destination city or state"),
    equipment_type: Optional[str] = Query(None, description="Equipment type needed"),
):
    """
    Search available loads by origin, destination, and/or equipment type.
    Called by the HappyRobot agent during a carrier call.
    """
    try:
        loads = load_loads_data()
    except FileNotFoundError as e:
        raise HTTPException(status_code=500, detail=str(e))

    results = loads

    if origin:
        results = [
            l for l in results
            if origin.lower() in l["origin"].lower()
        ]
    if destination:
        results = [
            l for l in results
            if destination.lower() in l["destination"].lower()
        ]
    if equipment_type:
        results = [
            l for l in results
            if equipment_type.lower() in l["equipment_type"].lower()
        ]

    if not results:
        return LoadSearchResponse(
            found=False,
            loads=[],
            message="No available loads match your criteria at this time.",
        )

    return LoadSearchResponse(
        found=True,
        loads=results[:3],  # return top 3 matches
        message=f"Found {len(results)} matching load(s). Showing top 3.",
    )


@router.get("/{load_id}", response_model=Load)
def get_load(load_id: str):
    """Get a specific load by ID."""
    try:
        loads = load_loads_data()
    except FileNotFoundError as e:
        raise HTTPException(status_code=500, detail=str(e))

    for load in loads:
        if load["load_id"] == load_id:
            return load

    raise HTTPException(status_code=404, detail=f"Load {load_id} not found")


@router.get("/", response_model=List[Load])
def list_all_loads():
    """List all available loads."""
    try:
        return load_loads_data()
    except FileNotFoundError as e:
        raise HTTPException(status_code=500, detail=str(e))
