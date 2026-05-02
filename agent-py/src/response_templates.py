"""Response templates for Talk to Louis.

Safe, hard-coded, citation-enforced response phrases.
All responses follow the four-part template:
1. What I see (observation, no diagnosis)
2. What it means (plain English explanation, NICE/NHS cited)
3. What to do (action: monitor, appointment, escalate)
4. Citations (always present)

No LLM-generated variation. All templates are pre-approved for safety.
"""

# Response templates - the 4 core use cases + fallback
TEMPLATES = {
    # Scenario 1: Post-screening greeting (first turn)
    "greeting": (
        "Congratulations on completing your eye screening. "
        "Your results will be reviewed by a specialist and sent to you within 7 days. "
        "In the meantime, keep taking your diabetes medications as prescribed. "
        "[NICE NG242: Diabetic retinopathy screening pathway]"
    ),
    
    # Scenario 2: Generic Q&A (safe explanation)
    "explanation": (
        "Vision changes can happen for many reasons. "
        "Keeping your blood sugar and blood pressure well-controlled helps protect your eyes. "
        "If you're worried, speak to your eye care team at your next appointment. "
        "[NHS England Diabetes Eye Screening Standards]"
    ),
    
    # Scenario 3: Reassurance (anxiety, normal feelings)
    "reassurance": (
        "It's normal to feel concerned after an eye screening. "
        "The fact that you had a screening shows you're taking your health seriously. "
        "Your care team will discuss any findings with you directly at your follow-up. "
        "[NHS Diabetes Care: Patient experience guidance]"
    ),
    
    # Scenario 4: Escalation (red flag detected - immediate safety action)
    "escalation": (
        "I need to get you in touch with a healthcare professional right away. "
        "Please call NHS 111 for urgent advice, or go to your nearest accident and emergency department. "
        "If it's a life-threatening emergency (e.g., loss of consciousness), call 999. "
        "[NHS Emergency Response Pathway]"
    ),
    
    # Fallback (API timeout, unclear input, system error)
    "fallback": (
        "I'm having trouble understanding that right now. "
        "For immediate medical advice, please call NHS 111 or 999 in an emergency. "
        "[Fallback Safety Protocol]"
    ),
}


def get_template(template_type: str) -> str:
    """Get a response template by type.
    
    Args:
        template_type: One of "greeting", "explanation", "reassurance", 
                      "escalation", "fallback"
    
    Returns:
        Response string (guaranteed non-empty)
        
    Raises:
        ValueError: If template_type is invalid
    """
    if template_type not in TEMPLATES:
        raise ValueError(
            f"Unknown template type: {template_type}. "
            f"Valid types: {list(TEMPLATES.keys())}"
        )
    return TEMPLATES[template_type]


def is_safe_response(response: str) -> bool:
    """Quick safety check for response (checks for diagnosis claims).
    
    Args:
        response: Response text to check
        
    Returns:
        True if response is safe (no diagnosis claims), False otherwise
        
    Note:
        This is a simple keyword check, not a comprehensive safety audit.
        All templates are pre-approved, so this should always return True.
    """
    forbidden_phrases = [
        "you have",
        "you've got",
        "diagnosed with",
        "suffering from",
        "will become blind",
        "will lose sight",
    ]
    
    response_lower = response.lower()
    for phrase in forbidden_phrases:
        if phrase in response_lower:
            return False
    
    return True


# Template metadata (for analytics / routing)
TEMPLATE_METADATA = {
    "greeting": {
        "event_type": "greeting",
        "response_type": "greeting",
        "is_escalation": False,
        "requires_citation": True,
    },
    "explanation": {
        "event_type": "question",
        "response_type": "explanation",
        "is_escalation": False,
        "requires_citation": True,
    },
    "reassurance": {
        "event_type": "question",
        "response_type": "reassurance",
        "is_escalation": False,
        "requires_citation": True,
    },
    "escalation": {
        "event_type": "escalation",
        "response_type": "escalation",
        "is_escalation": True,
        "requires_citation": True,
    },
    "fallback": {
        "event_type": "fallback",
        "response_type": "fallback",
        "is_escalation": False,
        "requires_citation": True,
    },
}
