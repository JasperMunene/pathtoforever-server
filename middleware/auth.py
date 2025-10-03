import os
import logging
from functools import wraps
from flask import request, current_app
import jwt
from jwt import PyJWKClient
from utils.response import error_response

logger = logging.getLogger(__name__)


class AuthMiddleware:
    def __init__(self):
        self.clerk_jwks_url = f"https://{os.getenv('CLERK_FRONTEND_API')}/.well-known/jwks.json"
        self.jwt_audience = os.getenv('CLERK_JWT_AUDIENCE')

    def clerk_required(self, f):
        @wraps(f)
        def decorated(*args, **kwargs):
            auth_header = request.headers.get("Authorization", "")

            if not auth_header.startswith("Bearer "):
                logger.warning("Missing or malformed Authorization header")
                return error_response("Unauthorized - No Bearer token", 401)

            token = auth_header.split("Bearer ")[1]

            try:
                jwks_client = PyJWKClient(self.clerk_jwks_url)
                signing_key = jwks_client.get_signing_key_from_jwt(token).key

                payload = jwt.decode(
                    token,
                    key=signing_key,
                    algorithms=["RS256"],
                    audience=self.jwt_audience,
                    options={"verify_exp": True},
                    leeway=60  # Allow 60 seconds of clock skew
                )

                request.user = payload
                logger.debug("JWT validated for user: %s", payload.get("sub"))

            except jwt.ExpiredSignatureError:
                logger.warning("JWT token expired")
                return error_response("Token expired", 401)
            except jwt.InvalidTokenError as e:
                logger.warning("Invalid JWT token: %s", str(e))
                return error_response("Invalid token", 401)
            except Exception as e:
                logger.error("JWT validation error: %s", str(e))
                return error_response("Authentication failed", 500)

            return f(*args, **kwargs)

        return decorated


# Global instance
auth_middleware = AuthMiddleware()
clerk_required = auth_middleware.clerk_required