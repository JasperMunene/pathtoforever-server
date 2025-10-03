from typing import Any, Dict, Optional

def success_response(data: Any = None, message: str = "Success", status_code: int = 200):
    """Standard success response format for Flask-RESTful"""
    response = {
        "success": True,
        "message": message,
        "data": data
    }
    return response, status_code

def error_response(message: str = "Error", status_code: int = 400, details: Optional[Dict] = None):
    """Standard error response format for Flask-RESTful"""
    response = {
        "success": False,
        "error": {
            "message": message,
            "code": status_code,
            "details": details or {}
        }
    }
    return response, status_code

def paginated_response(data: list, total: int, page: int, per_page: int, **kwargs):
    """Standard paginated response format for Flask-RESTful"""
    response = {
        "success": True,
        "data": data,
        "pagination": {
            "total": total,
            "page": page,
            "per_page": per_page,
            "pages": (total + per_page - 1) // per_page
        },
        **kwargs
    }
    return response, 200
