"""
Authentication endpoints v1.
"""

from fastapi import APIRouter, Form, HTTPException

from core.error_handler import (
    ERR_INTERNAL_SERVER_ERROR,
    ERR_INVALID_TC,
    handle_exception,
)
from core.logger import get_correlated_logger
from core.security import sanitize_input
from infrastructure.mock_services import MockAuthService

router = APIRouter()
log = get_correlated_logger()
auth_service = MockAuthService()


@router.post("/auth")
async def authenticate_customer(
    customer_id: str = Form(...),
):
    """
    Authenticate customer by ID number (v1).

    Args:
        customer_id: 11-digit customer ID number

    Returns:
        Authentication result with customer info
    """
    try:
        # Sanitize input
        customer_id = sanitize_input(customer_id, max_length=11)

        # Validate TC Kimlik
        from core.tc_kimlik_validator import validate_tc_kimlik

        if not validate_tc_kimlik(customer_id):
            return {
                "status": "error",
                "message": "Geçersiz TC Kimlik numarası. 11 haneli geçerli bir numara giriniz.",
            }

        # Check if customer exists
        is_valid = auth_service.verify_customer(customer_id)
        if not is_valid:
            return {
                "status": "error",
                "message": "Müşteri bulunamadı.",
            }

        # Get customer info
        customer_info = auth_service.get_customer_info(customer_id)

        return {
            "status": "success",
            "authenticated": True,
            "customer_id": customer_id,
            "customer_name": (
                f"{customer_info['first_name']} {customer_info['last_name']}"
                if customer_info
                else "Müşteri"
            ),
        }

    except Exception as e:
        log.error(f"Authentication error: {e}")
        return handle_exception(
            ERR_INTERNAL_SERVER_ERROR, e, logger=log, context="authenticate_customer_v1"
        ).get("error")


@router.post("/auth/verify")
async def verify_customer_auth(
    customer_id: str = Form(...),
    password: str = Form(None),
    otp_code: str = Form(None),
):
    """
    Verify customer identity via password or SMS OTP and return JWT token (v1).

    Args:
        customer_id: 11-digit TC Kimlik number
        password: Customer password (use either password OR otp_code)
        otp_code: 6-digit SMS OTP code (use either password OR otp_code)

    Returns:
        JWT token and customer info on success
    """
    try:
        # Sanitize input
        customer_id = sanitize_input(customer_id, max_length=11)
        
        # Validate customer ID exists
        is_valid = auth_service.verify_customer(customer_id)
        if not is_valid:
            return {
                "status": "error",
                "message": "Geçersiz TC Kimlik numarası.",
            }

        # Determine auth method and verify
        auth_method = None
        if password:
            if not auth_service.verify_password(customer_id, password):
                return {
                    "status": "error",
                    "message": "Şifre hatalı. Lütfen tekrar deneyin.",
                }
            auth_method = "password"
        elif otp_code:
            if not auth_service.verify_otp(customer_id, otp_code):
                return {
                    "status": "error",
                    "message": "OTP kodu hatalı. Lütfen tekrar deneyin.",
                }
            auth_method = "otp"
        else:
            return {
                "status": "error",
                "message": "Şifre veya OTP kodu gereklidir.",
            }

        # Generate JWT token
        token = auth_service.generate_jwt_token(customer_id, auth_method=auth_method)

        # Get customer info
        customer_info = auth_service.get_customer_info(customer_id)

        return {
            "status": "success",
            "token": token,
            "token_type": "Bearer",
            "expires_in_hours": auth_service.JWT_EXPIRY_HOURS,
            "auth_method": auth_method,
            "customer": customer_info,
        }

    except Exception as e:
        log.error(f"Verify auth error: {e}")
        return handle_exception(
            ERR_INTERNAL_SERVER_ERROR, e, logger=log, context="verify_customer_auth_v1"
        ).get("error")
