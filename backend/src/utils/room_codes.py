"""Room code generator utility."""
import random
import string


def generate_room_code(length: int = 8) -> str:
    """
    Generate a random room code.
    
    Args:
        length: Length of the code (default: 8)
        
    Returns:
        Uppercase alphanumeric room code
    """
    characters = string.ascii_uppercase + string.digits
    return ''.join(random.choices(characters, k=length))


def is_valid_room_code(code: str) -> bool:
    """
    Validate a room code format.
    
    Args:
        code: Room code to validate
        
    Returns:
        True if code is valid format
    """
    if not code or len(code) != 8:
        return False
    return code.isalnum() and code.isupper()
