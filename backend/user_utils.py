"""
Utility functions for user management and session handling
"""
import hashlib
import secrets
from typing import Optional

def extract_user_from_auth_header(authorization: str) -> Optional[str]:
    """
    Extract user ID from Authorization header
    For now, this is a simple implementation
    In production, you'd validate JWT tokens or API keys
    """
    if not authorization:
        return "default"
    
    # Simple implementation: use the authorization value as user ID
    # In production, decode JWT or validate API key
    if authorization.startswith("Bearer "):
        token = authorization[7:]  # Remove "Bearer " prefix
        # For demo purposes, just use the token as user ID
        return token
    
    return authorization

def generate_session_id(user_id: str, project_id: str) -> str:
    """Generate a unique session ID for user-project combination"""
    combined = f"{user_id}:{project_id}:{secrets.token_hex(8)}"
    return hashlib.sha256(combined.encode()).hexdigest()[:16]

def validate_user_id(user_id: str) -> bool:
    """Validate user ID format (basic validation)"""
    if not user_id or len(user_id) < 1:
        return False
    
    # Basic alphanumeric + special chars validation
    allowed_chars = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_@.")
    return all(c in allowed_chars for c in user_id)

def sanitize_user_id(user_id: str) -> str:
    """Sanitize user ID for file system safety"""
    # Replace unsafe characters with underscores
    safe_chars = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_"
    return "".join(c if c in safe_chars else "_" for c in user_id)