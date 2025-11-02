"""
WebSocket handler for real-time chat communication.
"""
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from typing import Dict, Set
import json
from datetime import datetime

from ..database.operations import DatabaseOperations
from ..agents.agent_factory import AgentFactory
from ..agents.agent_manager import AgentManager
from .routes import _build_student_context

router = APIRouter()

# Active WebSocket connections and agent managers
active_connections: Dict[str, WebSocket] = {}
agent_managers: Dict[str, AgentManager] = {}


class ConnectionManager:
    """Manages WebSocket connections"""
    
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
    
    async def connect(self, session_id: str, websocket: WebSocket):
        """Accept and store a new connection"""
        await websocket.accept()
        self.active_connections[session_id] = websocket
        print(f"✅ WebSocket connected: {session_id}")
    
    def disconnect(self, session_id: str):
        """Remove a connection"""
        if session_id in self.active_connections:
            del self.active_connections[session_id]
            print(f"❌ WebSocket disconnected: {session_id}")
    
    async def send_message(self, session_id: str, message: dict):
        """Send a message to a specific connection"""
        if session_id in self.active_connections:
            await self.active_connections[session_id].send_json(message)
    
    def is_connected(self, session_id: str) -> bool:
        """Check if a session is connected"""
        return session_id in self.active_connections


manager = ConnectionManager()


@router.websocket("/ws/{session_id}")
async def websocket_endpoint(websocket: WebSocket, session_id: str):
    """
    WebSocket endpoint for real-time chat.
    Handles student messages and agent responses.
    """
    await manager.connect(session_id, websocket)
    
    # Verify session exists and extract student name immediately
    student_name = 'Student'  # Default
    try:
        session = DatabaseOperations.get_session(session_id)
        if session and hasattr(session, 'student'):
            try:
                # Extract student name while session is still attached
                student_name = session.student.name
            except Exception as e:
                print(f"⚠️ Could not get student name: {str(e)}")
                student_name = 'Student'
    except Exception as e:
        print(f"⚠️ Error getting session {session_id}: {str(e)}")
        session = None
    
    if not session:
        print(f"⚠️ Session not found: {session_id}, continuing anyway...")
        # Don't close connection - allow it to work without database
        session = type('obj', (object,), {
            'student': type('obj', (object,), {'name': student_name, 'student_id': 'unknown'})()
        })()
    
    # Build student context for returning students
    student_context = None
    if session and hasattr(session, 'student'):
        try:
            student_id = session.student.student_id
            # Get student's progress
            progress = DatabaseOperations.get_student_progress(student_id)
            # Check if returning student (has any progress)
            is_returning = any(data.get('unlocked', False) or data.get('best_score') for data in progress.values())
            
            if is_returning:
                print(f"[WEBSOCKET] Building context for returning student: {student_name}")
                student_context = _build_student_context(student_id, 'r003.1', progress)
                print(f"[WEBSOCKET] Context built with {len(student_context)} sections")
            else:
                print(f"[WEBSOCKET] New student - no context needed")
        except Exception as e:
            print(f"[WEBSOCKET] Could not build student context: {e}")
            student_context = None
    
    # Create AgentManager for this session (manages both tutor and activity agents)
    agent_manager = AgentManager(
        student_name=student_name,
        module_id='r003.1',
        student_context=student_context
    )
    agent_managers[session_id] = agent_manager
    
    print(f"✅ AgentManager created for session {session_id}")
    
    # Send connection confirmation
    await manager.send_message(session_id, {
        "type": "connection",
        "status": "connected",
        "message": "WebSocket connected successfully"
    })
    
    print(f"🔄 WebSocket ready for session {session_id}")
    
    try:
        while True:
            # Receive message from client
            data = await websocket.receive_json()
            
            message_type = data.get('type')
            
            if message_type == 'chat':
                # Handle chat message
                await handle_chat_message(session_id, session, data)
            
            elif message_type == 'activity_chat':
                # Handle activity-specific chat message
                await handle_activity_chat(session_id, session, data)
            
            elif message_type == 'activity_start':
                # Handle activity start
                await handle_activity_start(session_id, session, data)
            
            elif message_type == 'activity_event':
                # Handle activity event (wrong answer, completion, etc.)
                await handle_activity_event(session_id, session, data)
            
            elif message_type == 'activity_end':
                # Handle activity end
                await handle_activity_end(session_id, session, data)
                
            elif message_type == 'game_event':
                # Handle game event (legacy - wrong answer, etc.)
                await handle_game_event(session_id, session, data)
                
            elif message_type == 'hint_request':
                # Handle hint request
                await handle_hint_request(session_id, session, data)
            
            elif message_type == 'exercise_complete':
                # Handle exercise completion - generate LLM summary
                await handle_exercise_complete(session_id, session, data)
                
            else:
                # Unknown message type
                await manager.send_message(session_id, {
                    "type": "error",
                    "message": f"Unknown message type: {message_type}"
                })
    
    except WebSocketDisconnect:
        print(f"🔌 WebSocket disconnected normally: {session_id}")
        manager.disconnect(session_id)
        # Clean up agent manager
        if session_id in agent_managers:
            del agent_managers[session_id]
    except Exception as e:
        print(f"❌ WebSocket error for session {session_id}: {str(e)}")
        import traceback
        traceback.print_exc()
        manager.disconnect(session_id)
        # Clean up agent manager
        if session_id in agent_managers:
            del agent_managers[session_id]


async def handle_chat_message(session_id: str, session, data: dict):
    """Handle a chat message from the student"""
    student_message = data.get('message', '')
    
    agent_mgr = agent_managers.get(session_id)
    if not agent_mgr:
        return
    
    # Get response from tutor agent
    agent_response = agent_mgr.handle_chat_message(
        student_message,
        context={'in_activity': False}
    )
    
    # Save to database
    DatabaseOperations.save_chat_message(
        session_id=session_id,
        agent_type='tutor',
        sender='student',
        message=student_message
    )
    DatabaseOperations.save_chat_message(
        session_id=session_id,
        agent_type='tutor',
        sender='agent',
        message=agent_response
    )
    
    # Send response to client
    await manager.send_message(session_id, {
        "type": "chat",
        "sender": "agent",
        "agent_type": "tutor",
        "message": agent_response,
        "timestamp": datetime.utcnow().isoformat()
    })


async def handle_game_event(session_id: str, session, data: dict):
    """Handle a game event (e.g., wrong answer) - legacy support"""
    event = data.get('event')
    context = data.get('context', {})
    
    print(f"Game event in session {session_id}: {event}")
    
    # Legacy events - just log for now
    # New system uses activity_event instead


async def handle_hint_request(session_id: str, session, data: dict):
    """Handle a hint request - legacy support"""
    context = data.get('context', {})
    
    print(f"Hint request in session {session_id}")
    
    # Legacy - new system uses activity_event for hints


async def handle_activity_start(session_id: str, session, data: dict):
    """Handle activity start event - creates activity agent"""
    activity = data.get('activity', 'unknown')
    difficulty = data.get('difficulty', '4')
    
    agent_mgr = agent_managers.get(session_id)
    if not agent_mgr:
        print(f"⚠️ No agent manager for session {session_id}")
        return
    
    # Start activity and get welcome message from LLM
    welcome = agent_mgr.start_activity(activity, difficulty)
    
    # Send welcome message to client
    await manager.send_message(session_id, {
        "type": "activity_chat",
        "sender": "agent",
        "message": welcome,
        "timestamp": datetime.utcnow().isoformat()
    })
    
    print(f"✅ Activity started: {activity} ({difficulty})")


async def handle_activity_end(session_id: str, session, data: dict):
    """Handle activity end event - destroys activity agent"""
    score = data.get('score')
    total = data.get('total')
    
    agent_mgr = agent_managers.get(session_id)
    if not agent_mgr:
        return
    
    # End activity and get feedback if score provided
    feedback = agent_mgr.end_activity(score, total)
    
    if feedback:
        await manager.send_message(session_id, {
            "type": "activity_chat",
            "sender": "agent",
            "message": feedback,
            "timestamp": datetime.utcnow().isoformat()
        })
    
    print(f"✅ Activity ended")


async def handle_activity_chat(session_id: str, session, data: dict):
    """Handle activity-specific chat message"""
    student_message = data.get('message', '')
    
    agent_mgr = agent_managers.get(session_id)
    if not agent_mgr:
        return
    
    # Get response from agent manager (routes to activity agent if in activity)
    agent_response = agent_mgr.handle_chat_message(
        student_message,
        context={'in_activity': agent_mgr.is_in_activity()}
    )
    
    # Save to database
    DatabaseOperations.save_chat_message(
        session_id=session_id,
        agent_type='activity',
        sender='student',
        message=student_message
    )
    DatabaseOperations.save_chat_message(
        session_id=session_id,
        agent_type='activity',
        sender='agent',
        message=agent_response
    )
    
    # Send response to client
    await manager.send_message(session_id, {
        "type": "activity_chat",
        "sender": "agent",
        "message": agent_response,
        "timestamp": datetime.utcnow().isoformat()
    })


async def handle_activity_event(session_id: str, session, data: dict):
    """Handle activity-specific events with LLM agent"""
    event = data.get('event', 'unknown')
    context = data.get('context', {})
    
    agent_mgr = agent_managers.get(session_id)
    if not agent_mgr:
        return
    
    print(f"Activity event in session {session_id}: {event}")
    
    response = None
    
    if event == 'wrong_answer':
        # Get LLM response for wrong answer
        question_data = {
            'definition': context.get('question', ''),
            'correct_answer': context.get('correctAnswer', ''),
            'user_answer': context.get('userAnswer', ''),
            'choices': context.get('choices', [])
        }
        attempt_number = context.get('attemptNumber', 1)
        
        response = agent_mgr.handle_wrong_answer(question_data, attempt_number)
    
    elif event == 'correct_answer':
        # Get LLM response for correct answer
        question_data = {
            'correct_answer': context.get('correctAnswer', '')
        }
        is_retry = context.get('isRetry', False)
        
        response = agent_mgr.handle_correct_answer(question_data, is_retry)
    
    # Send response if generated
    if response:
        # Save to database
        DatabaseOperations.save_chat_message(
            session_id=session_id,
            agent_type='activity',
            sender='agent',
            message=response
        )
        
        # Send to client
        await manager.send_message(session_id, {
            "type": "activity_chat",
            "sender": "agent",
            "message": response,
            "timestamp": datetime.utcnow().isoformat(),
            "triggered_by": event
        })


async def handle_exercise_complete(session_id: str, session, data: dict):
    """Handle exercise completion - generate personalized LLM summary"""
    exercise_type = data.get('exercise_type', 'unknown')
    difficulty = data.get('difficulty', 'unknown')
    score = data.get('score', 0)
    total = data.get('total', 0)
    percentage = data.get('percentage', 0)
    answers = data.get('answers', [])
    
    agent_mgr = agent_managers.get(session_id)
    if not agent_mgr:
        return
    
    print(f"📊 Exercise complete: {exercise_type} - {score}/{total} ({percentage}%)")
    
    # Build detailed context for LLM
    mistakes = [a for a in answers if not a.get('isCorrect', False)]
    correct = [a for a in answers if a.get('isCorrect', False)]
    
    # Create prompt for tutor agent
    prompt = f"""The student just completed a {exercise_type.replace('_', ' ')} exercise at {difficulty} difficulty.

Results:
- Score: {score} out of {total} ({percentage}%)
- Correct answers: {len(correct)}
- Mistakes: {len(mistakes)}

"""
    
    if mistakes:
        prompt += "Mistakes made:\n"
        for i, mistake in enumerate(mistakes[:5], 1):  # Limit to 5 mistakes
            q_num = mistake.get('questionNumber', i)
            definition = mistake.get('definition', '')
            user_answer = mistake.get('userAnswer', '')
            correct_answer = mistake.get('correctAnswer', mistake.get('word', ''))
            
            prompt += f"{i}. Q{q_num}: {definition}\n"
            prompt += f"   Student answered: '{user_answer}' (Correct: '{correct_answer}')\n"
    
    prompt += f"""
Please provide a personalized summary that:
1. Congratulates them on their score (be enthusiastic if they did well!)
2. Analyzes their mistakes (if any) - identify patterns (e.g., confusing similar words, spelling errors, definition misunderstandings)
3. Provides specific, encouraging advice on how to improve
4. Motivates them to keep practicing

Keep it conversational, supportive, and age-appropriate (3rd grade level). Use 2-3 paragraphs.
"""
    
    # Get LLM summary from tutor agent
    summary = agent_mgr.get_tutor()._call_llm(prompt)
    
    # Save to database
    DatabaseOperations.save_chat_message(
        session_id=session_id,
        agent_type='tutor',
        sender='agent',
        message=summary
    )
    
    # Send summary to client
    await manager.send_message(session_id, {
        "type": "chat",
        "sender": "agent",
        "agent_type": "tutor",
        "message": summary,
        "timestamp": datetime.utcnow().isoformat(),
        "exercise_summary": True
    })
    
    print(f"✅ Exercise summary sent to {session_id}")
