"""
Activity-specific instructions and rules for the LLM agents.
Provides context about how each activity works at different difficulty levels.
"""

# Difficulty level mapping
DIFFICULTY_MAP = {
    '3': 'easy',
    '4': 'medium',
    '5': 'hard',
    'easy': 'easy',
    'medium': 'medium',
    'hard': 'hard',
    'moderate': 'medium'  # Alias for medium
}


def normalize_difficulty(difficulty: str) -> str:
    """
    Normalize difficulty level to standard format.
    
    Args:
        difficulty: Difficulty as string ('3', '4', '5', 'easy', 'medium', 'hard')
        
    Returns:
        Normalized difficulty ('easy', 'medium', or 'hard')
    """
    return DIFFICULTY_MAP.get(str(difficulty).lower(), 'medium')


ACTIVITY_INSTRUCTIONS = {
    'spelling': {
        'easy': {
            'intro': "Read the definition and spell the word correctly. I'll help you if you get stuck - you can try as many times as you need!",
            'mechanics': "You'll see a definition, and you need to type the correct spelling of the word.",
            'rules': [
                "Type your answer in the text box",
                "I'll give you feedback right away after each answer",
                "If you make a mistake, I'll give you hints to help",
                "You can try as many times as you need",
                "Don't worry about mistakes - that's how we learn!"
            ],
            'support_level': "I'll give you immediate feedback and unlimited hints. If you're stuck, just ask me for help!",
            'encouragement': "Take your time and don't worry about mistakes. I'm here to help you learn!"
        },
        'medium': {
            'intro': "Read the definition and spell the word. I'll give you one helpful hint if you need it.",
            'mechanics': "You'll see a definition, and you need to type the correct spelling of the word.",
            'rules': [
                "Type your answer in the text box",
                "I'll give you feedback after each answer",
                "If you make a mistake, I can give you one hint",
                "Use your hint wisely - you only get one per word",
                "Try your best on the first attempt"
            ],
            'support_level': "I'll give you one hint per word if you need it. Think carefully before answering!",
            'encouragement': "You've got this! Remember, you get one hint if you need help."
        },
        'hard': {
            'intro': "Read each definition and spell the word. I'll check all your answers when you're finished.",
            'mechanics': "You'll see definitions for multiple words, and you need to spell each one correctly.",
            'rules': [
                "Type your answer for each word",
                "I won't give hints during the activity",
                "You'll see all your results at the end",
                "Focus and do your best on each word",
                "Trust what you've learned"
            ],
            'support_level': "I'll check your answers at the end. No hints during the activity - show me what you know!",
            'encouragement': "You know these words! Trust yourself and do your best."
        }
    },
    
    'fill_in_the_blank': {
        'easy': {
            'intro': "Drag the right word into each blank to match the definitions. All the words you need are in the word bank!",
            'mechanics': "You'll see sentences with blanks and a word bank. Drag words from the bank to fill in the blanks.",
            'rules': [
                "Drag words from the word bank to the blanks",
                "The word bank has exactly the words you need",
                "You can move words around if you change your mind",
                "I'll help you right away if you make a mistake",
                "Click on a word in a blank to move it back to the bank"
            ],
            'support_level': "I'll give you immediate feedback and unlimited hints. The word bank only has the words you need!",
            'encouragement': "Take your time matching the words. I'm here to help if you need it!"
        },
        'moderate': {
            'intro': "Drag the right word into each blank. The word bank has extra words, so choose carefully!",
            'mechanics': "You'll see sentences with blanks and a word bank with all vocabulary words. Choose the right ones!",
            'rules': [
                "Drag words from the word bank to the blanks",
                "The word bank has MORE words than you need",
                "Think carefully about which word fits each definition",
                "I can give you one hint if you're stuck",
                "You can move words around before checking"
            ],
            'support_level': "I'll give you one hint if you need it. The word bank has extra words, so think carefully!",
            'encouragement': "Read each definition carefully. You can do this!"
        },
        'hard': {
            'intro': "Drag the right word into each blank. I'll check all your answers when you're done.",
            'mechanics': "You'll see sentences with blanks and a word bank with all vocabulary words.",
            'rules': [
                "Drag words from the word bank to the blanks",
                "The word bank has MORE words than you need",
                "No hints during the activity",
                "Check all your answers before submitting",
                "You'll see results at the end"
            ],
            'support_level': "I'll check your answers at the end. No hints - show me what you've learned!",
            'encouragement': "You know these words! Match them carefully."
        }
    },
    
    'multiple_choice': {
        'easy': {
            'intro': "Read each definition and pick the right word from the choices. I'll help you if you're not sure!",
            'mechanics': "You'll see a definition and multiple word choices. Click the word that matches the definition.",
            'rules': [
                "Read the definition carefully",
                "Click on the word you think is correct",
                "I'll tell you right away if you're right",
                "If you're wrong, I'll give you hints",
                "You can try again as many times as you need"
            ],
            'support_level': "I'll give you immediate feedback and unlimited hints. Don't worry about mistakes!",
            'encouragement': "Take your time and read carefully. I'm here to help!"
        },
        'medium': {
            'intro': "Read each definition and choose the correct word. I'll give you one hint if you need it.",
            'mechanics': "You'll see a definition and multiple word choices. Pick the right one!",
            'rules': [
                "Read the definition carefully",
                "Click on the word you think is correct",
                "I'll give you feedback after each answer",
                "You get one hint if you make a mistake",
                "Think before you answer"
            ],
            'support_level': "I'll give you one hint per question if you need it. Choose carefully!",
            'encouragement': "You've got this! Think about what each word means."
        },
        'hard': {
            'intro': "Read each definition and choose the correct word. I'll check all your answers at the end.",
            'mechanics': "You'll see definitions and word choices. Select your answers for all questions.",
            'rules': [
                "Read each definition carefully",
                "Click on the word you think is correct",
                "No hints during the activity",
                "You'll see all results at the end",
                "Trust what you've learned"
            ],
            'support_level': "I'll check your answers at the end. No hints - show me what you know!",
            'encouragement': "You know these words! Trust yourself."
        }
    },
    
    'bubble_pop': {
        'easy': {
            'intro': "Pop bubbles with correctly spelled words! Hover over a bubble and press Q to pop it.",
            'mechanics': "Words float across the screen in bubbles. Pop the ones that are spelled correctly!",
            'rules': [
                "Hover your mouse over a bubble",
                "Press Q to pop bubbles with CORRECT spelling",
                "Don't pop bubbles with wrong spelling - let them float away",
                "The game gets faster as you go",
                "Press ESC to pause and ask me questions"
            ],
            'support_level': "Press ESC anytime to pause and ask me for help. I'm here if you need me!",
            'encouragement': "Have fun! Remember, Q is for correctly spelled words."
        },
        'moderate': {
            'intro': "Pop bubbles with misspelled words! Hover over a bubble and press R to pop it.",
            'mechanics': "Words float across the screen in bubbles. Pop the ones that are spelled WRONG!",
            'rules': [
                "Hover your mouse over a bubble",
                "Press R to pop bubbles with WRONG spelling",
                "Don't pop correctly spelled words - let them float away",
                "The game gets faster as you go",
                "Press ESC to pause and ask me questions"
            ],
            'support_level': "Press ESC anytime to pause and ask me for help!",
            'encouragement': "You can spot the mistakes! R is for wrong spelling."
        },
        'hard': {
            'intro': "Pop bubbles based on their spelling! Use Q for correct words and R for misspelled words.",
            'mechanics': "Words float across the screen. Pop them with the right key based on their spelling!",
            'rules': [
                "Hover your mouse over a bubble",
                "Press Q for CORRECTLY spelled words",
                "Press R for WRONG spelling",
                "The game gets faster as you go",
                "Press ESC to pause and ask me questions"
            ],
            'support_level': "Press ESC anytime to pause and ask me for help. This is the challenge mode!",
            'encouragement': "You've got this! Q for correct, R for wrong."
        }
    },
    
    'fluent_reading': {
        'easy': {
            'intro': "Read the story as words scroll across the screen. Click words to highlight them!",
            'mechanics': "Words stream from right to left. As they exit, they appear in the reading area above.",
            'rules': [
                "Watch words scroll in the bottom zone",
                "Words appear in the reading area as they pass",
                "Click any word to highlight its whole sentence",
                "Read at a comfortable pace",
                "Press ESC to pause and ask questions"
            ],
            'support_level': "Press ESC anytime to pause and ask me about words you don't understand!",
            'encouragement': "Take your time and enjoy the story!"
        },
        'moderate': {
            'intro': "Read the story as it scrolls. Try to keep up with the pace!",
            'mechanics': "Words stream across the screen at a steady pace. Read along as they appear above.",
            'rules': [
                "Words scroll in the bottom zone",
                "They appear in the reading area as they pass",
                "Click words to highlight sentences",
                "Try to keep up with the scrolling",
                "Press ESC to pause if needed"
            ],
            'support_level': "Press ESC to pause and ask me questions. Challenge yourself to keep up!",
            'encouragement': "You're doing great! Keep reading along."
        },
        'hard': {
            'intro': "Read the story at a faster pace. Can you keep up?",
            'mechanics': "Words stream quickly across the screen. Read along and try to keep pace!",
            'rules': [
                "Words scroll faster in this mode",
                "They appear in the reading area as they pass",
                "Click words to highlight sentences",
                "Challenge yourself to read quickly",
                "Press ESC to pause if you need to"
            ],
            'support_level': "Press ESC to pause and ask questions. This is the speed reading challenge!",
            'encouragement': "You can do this! Focus and read along."
        }
    }
}


def get_activity_instructions(activity_type: str, difficulty: str) -> dict:
    """
    Get instructions for a specific activity and difficulty level.
    
    Args:
        activity_type: Type of activity (e.g., 'spelling', 'fill_in_the_blank')
        difficulty: Difficulty level (e.g., 'easy', 'medium', 'hard')
        
    Returns:
        Dictionary with instruction details, or None if not found
    """
    activity_instructions = ACTIVITY_INSTRUCTIONS.get(activity_type, {})
    return activity_instructions.get(difficulty)


def get_activity_intro_text(activity_type: str, difficulty: str) -> str:
    """
    Get just the intro text for an activity.
    
    Args:
        activity_type: Type of activity
        difficulty: Difficulty level
        
    Returns:
        Intro text string, or generic message if not found
    """
    instructions = get_activity_instructions(activity_type, difficulty)
    if instructions:
        return instructions.get('intro', '')
    return f"Let's start the {activity_type.replace('_', ' ')} activity!"


def get_activity_rules_text(activity_type: str, difficulty: str) -> str:
    """
    Get formatted rules text for an activity.
    
    Args:
        activity_type: Type of activity
        difficulty: Difficulty level
        
    Returns:
        Formatted rules string
    """
    instructions = get_activity_instructions(activity_type, difficulty)
    if instructions and 'rules' in instructions:
        rules = instructions['rules']
        return "\n".join([f"• {rule}" for rule in rules])
    return ""


def format_instructions_for_llm(activity_type: str, difficulty: str, student_name: str) -> str:
    """
    Format complete instructions for LLM context.
    
    Args:
        activity_type: Type of activity
        difficulty: Difficulty level
        student_name: Name of the student
        
    Returns:
        Formatted instruction text for LLM system prompt
    """
    instructions = get_activity_instructions(activity_type, difficulty)
    if not instructions:
        return f"You are helping {student_name} with {activity_type.replace('_', ' ')}."
    
    activity_name = activity_type.replace('_', ' ').title()
    
    context = f"""ACTIVITY: {activity_name} (Difficulty: {difficulty})

WHAT {student_name.upper()} WILL DO:
{instructions.get('mechanics', '')}

HOW IT WORKS:
{chr(10).join(['• ' + rule for rule in instructions.get('rules', [])])}

YOUR SUPPORT ROLE:
{instructions.get('support_level', '')}

WHEN GREETING {student_name.upper()}:
Keep it brief and warm - don't explain all the rules upfront.
Just welcome them to the activity.

YOUR ROLE DURING THIS ACTIVITY:
You will help {student_name} in TWO ways:

1. ACTIVITY MECHANICS QUESTIONS (e.g., "How does this work?", "What do I do?"):
   - Explain the rules and mechanics clearly using the information above
   - Stay focused on THIS activity - don't talk about other activities
   - Keep explanations simple and brief

2. VOCABULARY/CONTENT QUESTIONS (e.g., "What does this word mean?", "I don't know this one"):
   - Give HINTS, never direct answers
   - Use instructional methods:
     * Rhymes: "It rhymes with..."
     * Sounds like: "It sounds like..."
     * Context clues: "Think about when you..."
     * Word parts: "It starts with... and ends with..."
     * Associations: "You might see this at..."
   - Guide them to discover the answer themselves
   - Be encouraging when they're struggling

IMPORTANT RULES:
- Stay on topic with THIS activity
- Give hints, not answers, for vocabulary questions
- Use simple words {student_name} can understand
- Keep responses to 2-3 short sentences maximum
- Be warm, patient, and encouraging"""
    
    return context
