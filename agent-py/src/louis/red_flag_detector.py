"""Red-flag detector for Talk to Louis.

Simple keyword-based detection for dangerous symptoms that require immediate escalation.
No ML, no embeddings, no API calls. Just fast, reliable pattern matching.

Red flags trigger immediate escalation to NHS 111.
Non-negotiable safety rule: Check red flags EVERY turn, FIRST, before any other logic.
"""

import logging

logger = logging.getLogger("red_flag_detector")


class RedFlagDetector:
    """Detects red-flag symptoms that require immediate escalation."""
    
    # Hard-coded red-flag keywords (must match lower-case input)
    RED_FLAGS = [
        # Vision emergencies
        "flashing lights",
        "floaters",
        "curtain",
        "sudden blindness",
        "sudden vision loss",
        "vision loss",
        "blind spot",
        "field defect",
        
        # Pain
        "pain in eye",
        "eye pain",
        "eye hurts",
        "sharp pain",
        
        # System words (patient knows it's serious)
        "emergency",
        "help",
        "ambulance",
        "hospital",
        "999",
        "111",
        
        # Trauma/accidents
        "accident",
        "trauma",
        "hit in eye",
        "poked in eye",
        "chemical",
        "burn",
    ]
    
    @staticmethod
    def check(user_input: str) -> bool:
        """Check if input contains any red-flag keyword.
        
        Args:
            user_input: Patient's spoken or typed input (can be None)
            
        Returns:
            True if red flag detected, False otherwise
            
        Note:
            - Case-insensitive matching
            - Whitespace-trimmed
            - Returns False if input is None/empty
        """
        # Guard: empty input is not a red flag
        if not user_input:
            return False
        
        # Normalize: lowercase, trim whitespace
        text = user_input.lower().strip()
        
        # Empty after normalization? Not a red flag
        if not text:
            return False
        
        # Check all red-flag keywords
        for flag in RedFlagDetector.RED_FLAGS:
            if flag in text:
                logger.warning(f"🚨 RED FLAG DETECTED: '{flag}' in '{text}'")
                return True
        
        return False
    
    @staticmethod
    def get_flag_type(user_input: str) -> str:
        """Identify which red flag matched (for logging/analytics).
        
        Args:
            user_input: Patient input
            
        Returns:
            The matched red-flag keyword, or None if no match
        """
        if not user_input:
            return None
        
        text = user_input.lower().strip()
        
        for flag in RedFlagDetector.RED_FLAGS:
            if flag in text:
                return flag
        
        return None
    
    @staticmethod
    def count_matches(user_input: str) -> int:
        """Count how many red-flag keywords appear in input.
        
        Args:
            user_input: Patient input
            
        Returns:
            Number of distinct red flags found (0 if none)
        """
        if not user_input:
            return 0
        
        text = user_input.lower().strip()
        count = 0
        
        for flag in RedFlagDetector.RED_FLAGS:
            if flag in text:
                count += 1
        
        return count
    
    @staticmethod
    def list_all_keywords() -> list:
        """Return full list of red-flag keywords.
        
        Useful for testing, documentation, and configuration updates.
        """
        return RedFlagDetector.RED_FLAGS.copy()


# For quick testing
if __name__ == "__main__":
    # Test cases
    test_cases = [
        ("I'm seeing flashing lights", True),
        ("flashing lights in my vision", True),
        ("I'm worried", False),
        ("What happens next?", False),
        ("Help, I can't see", True),
        ("", False),
        (None, False),
        ("EMERGENCY", True),
        ("sudden vision loss", True),
        ("pain in my eye", True),
    ]
    
    detector = RedFlagDetector()
    for user_input, expected in test_cases:
        result = detector.check(user_input)
        status = "✅" if result == expected else "❌"
        flag_type = detector.get_flag_type(user_input) or "None"
        print(f"{status} Input: {user_input!r:40} | Red-flag: {result:5} | Type: {flag_type}")
