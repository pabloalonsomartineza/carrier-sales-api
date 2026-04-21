from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import Optional
import httpx

from config import settings

router = APIRouter()


class CarrierVerificationResponse(BaseModel):
    mc_number: str
    verified: bool
    status: str          # verified / not_found / inactive / api_error
    carrier_name: Optional[str] = None
    dot_number: Optional[str] = None
    allowed_to_operate: Optional[bool] = None
    insurance_on_file: Optional[bool] = None
    message: str


@router.get("/verify", response_model=CarrierVerificationResponse)
async def verify_carrier(
    mc_number: str = Query(..., description="MC number of the carrier to verify"),
):
    """
    Verify a carrier's MC number using the FMCSA API.
    Called by the HappyRobot agent at the start of each call.
    """
    # Clean up MC number - remove "MC" prefix if carrier says it
    clean_mc = mc_number.upper().replace("MC", "").replace("-", "").replace(" ", "").strip()

    if not clean_mc.isdigit():
        return CarrierVerificationResponse(
            mc_number=mc_number,
            verified=False,
            status="invalid_format",
            message=f"MC number format is invalid. Please provide a numeric MC number.",
        )

    if not settings.FMCSA_API_KEY:
        # Mock response for local dev / demo
        return _mock_fmcsa_response(clean_mc)

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(
                f"https://mobile.fmcsa.dot.gov/qc/services/carriers/docket-number/{clean_mc}",
                params={"webKey": settings.FMCSA_API_KEY},
            )

        if response.status_code == 404 or not response.json().get("content"):
            return CarrierVerificationResponse(
                mc_number=clean_mc,
                verified=False,
                status="not_found",
                message=f"MC number {clean_mc} was not found in the FMCSA database.",
            )

        data = response.json()["content"][0]["carrier"]
        allowed = data.get("allowedToOperate", "N") == "Y"
        insurance = data.get("bipdInsuranceOnFile", "0") != "0"

        if not allowed:
            return CarrierVerificationResponse(
                mc_number=clean_mc,
                verified=False,
                status="inactive",
                carrier_name=data.get("legalName"),
                dot_number=str(data.get("dotNumber", "")),
                allowed_to_operate=False,
                insurance_on_file=insurance,
                message=f"Carrier {data.get('legalName')} is not currently authorized to operate.",
            )

        return CarrierVerificationResponse(
            mc_number=clean_mc,
            verified=True,
            status="verified",
            carrier_name=data.get("legalName"),
            dot_number=str(data.get("dotNumber", "")),
            allowed_to_operate=True,
            insurance_on_file=insurance,
            message=f"Carrier {data.get('legalName')} is verified and authorized to operate.",
        )

    except httpx.TimeoutException:
        return CarrierVerificationResponse(
            mc_number=clean_mc,
            verified=False,
            status="api_error",
            message="FMCSA API timed out. Please try again.",
        )
    except Exception as e:
        return CarrierVerificationResponse(
            mc_number=clean_mc,
            verified=False,
            status="api_error",
            message=f"Could not verify carrier at this time.",
        )


def _mock_fmcsa_response(mc_number: str) -> CarrierVerificationResponse:
    """
    Mock FMCSA response for development/demo purposes.
    Numbers ending in 0 are treated as inactive, others as verified.
    """
    if mc_number.endswith("0"):
        return CarrierVerificationResponse(
            mc_number=mc_number,
            verified=False,
            status="inactive",
            carrier_name="Demo Carrier LLC",
            dot_number="9999990",
            allowed_to_operate=False,
            insurance_on_file=False,
            message=f"[DEMO] Carrier MC{mc_number} is not authorized to operate.",
        )

    return CarrierVerificationResponse(
        mc_number=mc_number,
        verified=True,
        status="verified",
        carrier_name="Demo Carrier LLC",
        dot_number="9999991",
        allowed_to_operate=True,
        insurance_on_file=True,
        message=f"[DEMO] Carrier MC{mc_number} is verified and authorized to operate.",
    )
