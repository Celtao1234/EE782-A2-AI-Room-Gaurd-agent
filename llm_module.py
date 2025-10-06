import google.generativeai as genai
import os
from typing import Optional
import time

# Configure API key from environment variable (more secure)
API_KEY = os.getenv("")
if not API_KEY:
    print("[LLM] ⚠️  WARNING: GEMINI_API_KEY not found in environment variables!")
    print("[LLM] Please set it with: export GEMINI_API_KEY='your-key-here'")
    print("[LLM] Using fallback responses only...")
    API_KEY = None

if API_KEY:
    genai.configure(api_key=API_KEY)
    
    # Initialize model with safety settings
    try:
        model = genai.GenerativeModel(
            "gemini-2.0-flash-exp",
            safety_settings={
                "HARASSMENT": "BLOCK_NONE",
                "HATE_SPEECH": "BLOCK_NONE", 
                "SEXUALLY_EXPLICIT": "BLOCK_NONE",
                "DANGEROUS_CONTENT": "BLOCK_NONE",
            }
        )
        print("[LLM] ✅ Gemini model initialized")
    except Exception as e:
        print(f"[LLM] ⚠️  Failed to initialize Gemini: {e}")
        model = None
else:
    model = None


class GuardEscalationFSM:
    """Finite State Machine for managing guard escalation levels."""
    
    def __init__(self):
        self.level = 0
        self.max_level = 4
        self.interaction_count = 0
        self.last_escalation_time = time.time()
        
        # Escalation rules with personality
        self.escalation_rules = {
            0: {
                "tone": "polite and friendly",
                "instruction": "Greet the visitor warmly but inform them this is a private room. Politely ask who they are and request they leave.",
                "max_words": 25
            },
            1: {
                "tone": "firm but professional",
                "instruction": "The visitor hasn't left. Be more direct and assertive. State clearly this room is off-limits and they must leave now.",
                "max_words": 20
            },
            2: {
                "tone": "stern and authoritative",
                "instruction": "The visitor is still here. Issue a warning that continued presence is unauthorized. Mention consequences.",
                "max_words": 20
            },
            3: {
                "tone": "serious and urgent",
                "instruction": "Final warning. State that security measures will be activated and the owner will be notified immediately.",
                "max_words": 18
            },
            4: {
                "tone": "alert mode",
                "instruction": "Alarm triggered. Inform that authorities have been alerted and this incident is being recorded.",
                "max_words": 15
            }
        }
    
    def escalate(self):
        """Move to next escalation level."""
        if self.level < self.max_level:
            self.level += 1
            self.last_escalation_time = time.time()
            print(f"[FSM] Escalated to level {self.level}")
    
    def de_escalate(self):
        """Reduce escalation level (if visitor cooperates)."""
        if self.level > 0:
            self.level -= 1
            print(f"[FSM] De-escalated to level {self.level}")
    
    def get_level(self) -> int:
        """Get current escalation level."""
        return self.level
    
    def get_rule(self) -> dict:
        """Get current escalation rule."""
        return self.escalation_rules[self.level]
    
    def should_trigger_alarm(self) -> bool:
        """Check if alarm should be triggered."""
        return self.level >= self.max_level
    
    def reset(self):
        """Reset FSM to initial state."""
        self.level = 0
        self.interaction_count = 0
        print("[FSM] Reset to level 0")


def analyze_visitor_intent(visitor_text: str) -> dict:
    """Analyze visitor's message for intent and sentiment."""
    visitor_lower = visitor_text.lower()
    
    intent = {
        "leaving": any(word in visitor_lower for word in ["leave", "leaving", "bye", "exit", "go", "sorry"]),
        "aggressive": any(word in visitor_lower for word in ["no", "shut up", "make me", "whatever", "don't care", "fuck", "screw"]),
        "questioning": any(word in visitor_lower for word in ["who", "what", "why", "how", "where", "?"]),
        "compliant": any(word in visitor_lower for word in ["okay", "ok", "fine", "alright", "understand", "sorry"]),
        "confused": any(word in visitor_lower for word in ["confused", "lost", "mistake", "wrong room", "accident"])
    }
    
    return intent


def gemini_response(visitor_text: str, level: int, context: Optional[str] = None) -> str:
    """
    Generate contextual AI guard response using Gemini.
    
    Args:
        visitor_text: What the visitor said
        level: Current escalation level (0-4)
        context: Optional additional context
    
    Returns:
        AI guard's response text
    """
    # If no API key or model, use fallback
    if not model:
        print("[LLM] Using fallback response (no API)")
        intent = analyze_visitor_intent(visitor_text)
        return get_fallback_response(level, intent)
    
    fsm = GuardEscalationFSM()
    rule = fsm.escalation_rules[level]
    
    # Analyze visitor intent
    intent = analyze_visitor_intent(visitor_text)
    
    # Build context-aware prompt
    system_context = f"""You are an AI security guard protecting a private room. You are professional, assertive, and focused on getting unauthorized visitors to leave.

Current Situation:
- Escalation Level: {level}/{fsm.max_level}
- Tone: {rule['tone']}
- Instructions: {rule['instruction']}

Visitor Analysis:
- Seems to be leaving: {intent['leaving']}
- Being aggressive: {intent['aggressive']}
- Asking questions: {intent['questioning']}
- Being compliant: {intent['compliant']}
- Seems confused: {intent['confused']}

Response Guidelines:
1. Keep response under {rule['max_words']} words
2. Be {rule['tone']}
3. Focus on getting them to leave
4. Don't engage in long conversations
5. Reference the visitor's statement naturally
6. If they're leaving, acknowledge briefly but firmly
7. If they're aggressive, don't escalate emotion but stay firm
8. If confused, be slightly more helpful but still insist they leave
9. Use natural speech patterns (contractions, varied sentence structure)
10. Never use asterisks or special formatting

The visitor said: "{visitor_text}"

Respond as the AI guard (plain text only, no formatting):"""
    
    try:
        # Add retry logic
        max_retries = 3
        for attempt in range(max_retries):
            try:
                response = model.generate_content(system_context)
                
                # Check if response was blocked
                if not response.text:
                    print(f"[LLM] Response blocked, attempt {attempt + 1}")
                    if attempt < max_retries - 1:
                        time.sleep(0.5)
                        continue
                    return get_fallback_response(level, intent)
                
                # Clean and validate response
                text = response.text.strip()
                
                # Remove any formatting
                text = text.replace('"', '').replace('*', '').replace('_', '')
                text = text.replace('[', '').replace(']', '')
                
                # Remove any action descriptions in parentheses
                import re
                text = re.sub(r'\([^)]*\)', '', text)
                text = ' '.join(text.split())  # Clean up extra spaces
                
                # Ensure response isn't too long
                words = text.split()
                if len(words) > rule['max_words'] + 5:
                    text = ' '.join(words[:rule['max_words']]) + '.'
                
                # Make sure it ends with punctuation
                if text and text[-1] not in '.!?':
                    text += '.'
                
                print(f"[LLM] Generated response ({len(words)} words)")
                return text
                
            except Exception as e:
                print(f"[LLM] API error on attempt {attempt + 1}: {e}")
                if attempt < max_retries - 1:
                    time.sleep(1)
                    continue
                return get_fallback_response(level, intent)
        
        return get_fallback_response(level, intent)
        
    except Exception as e:
        print(f"[LLM] Fatal error: {e}")
        return get_fallback_response(level, intent)


def get_fallback_response(level: int, intent: dict) -> str:
    """Fallback responses if API fails."""
    
    if intent['leaving']:
        fallbacks = {
            0: "Very well. Please exit now.",
            1: "Good. Leave immediately.",
            2: "About time. Go now.",
            3: "Exit immediately!",
            4: "Security has been notified."
        }
    elif intent['aggressive']:
        fallbacks = {
            0: "This room is private. You need to leave right now.",
            1: "I'm not asking. Leave now or I'll alert security.",
            2: "This is your final warning. Leave immediately!",
            3: "The owner is being notified. Leave now!",
            4: "Security breach. Authorities have been alerted!"
        }
    elif intent['confused']:
        fallbacks = {
            0: "I understand, but this is still a private room. Please leave.",
            1: "Regardless of the reason, you must leave now.",
            2: "I don't care why you're here. Leave immediately!",
            3: "Final warning. Exit now!",
            4: "Alarm activated!"
        }
    elif intent['questioning']:
        fallbacks = {
            0: "I'm the security system for this room. You need to leave.",
            1: "That doesn't matter. This room is off-limits. Leave now.",
            2: "Stop asking questions and leave immediately!",
            3: "Last chance. Leave or face consequences!",
            4: "Intruder alert activated!"
        }
    else:
        fallbacks = {
            0: "Hello. This is a private room. Please leave now.",
            1: "You must leave this room immediately.",
            2: "Leave now. This is your last warning.",
            3: "Final warning. The owner will be alerted.",
            4: "Alarm activated. Authorities have been notified."
        }
    
    return fallbacks.get(level, "You must leave now.")


def test_llm():
    """Test function for LLM responses."""
    print("\n" + "="*60)
    print("LLM MODULE - TEST MODE")
    print("="*60 + "\n")
    
    if not model:
        print("⚠️  Running in fallback mode (no API key)")
        print()
    
    test_cases = [
        ("Hello", 0),
        ("Who are you?", 0),
        ("I'm just looking around", 1),
        ("I'm not leaving", 1),
        ("Make me leave", 2),
        ("Whatever, I don't care", 2),
        ("Okay fine, I'll go", 2),
        ("Sorry, wrong room", 0),
    ]
    
    for text, level in test_cases:
        print(f"Level {level} | Visitor: '{text}'")
        response = gemini_response(text, level)
        print(f"Guard: {response}")
        print("-" * 60)
        time.sleep(1)  # Rate limiting
    
    print("\n✅ Test complete!")


if __name__ == "__main__":
    test_llm()