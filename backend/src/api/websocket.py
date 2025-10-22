"""
WebSocket handler for real-time chat communication.
"""
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from typing import Dict, Set
import json
from datetime import datetime

from ..database.operations import DatabaseOperations
from ..agents.agent_factory import AgentFactory

router = APIRouter()

# Active WebSocket connections
active_connections: Dict[str, WebSocket] = {}


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
    
    # Verify session exists
    session = DatabaseOperations.get_session(session_id)
    if not session:
        await websocket.send_json({
            "type": "error",
            "message": "Session not found"
        })
        await websocket.close()
        return
    
    # Get agent
    agent = AgentFactory.create_agent()
    
    try:
        while True:
            # Receive message from client
            data = await websocket.receive_json()
            
            message_type = data.get('type')
            
            if message_type == 'chat':
                # Handle chat message
                await handle_chat_message(session_id, session, data, agent)
            
            elif message_type == 'activity_chat':
                # Handle activity-specific chat message
                await handle_activity_chat(session_id, session, data, agent)
            
            elif message_type == 'activity_start':
                # Handle activity start
                await handle_activity_start(session_id, session, data, agent)
            
            elif message_type == 'activity_event':
                # Handle activity event (wrong answer, completion, etc.)
                await handle_activity_event(session_id, session, data, agent)
                
            elif message_type == 'game_event':
                # Handle game event (legacy - wrong answer, etc.)
                await handle_game_event(session_id, session, data, agent)
                
            elif message_type == 'hint_request':
                # Handle hint request
                await handle_hint_request(session_id, session, data, agent)
                
            else:
                # Unknown message type
                await manager.send_message(session_id, {
                    "type": "error",
                    "message": f"Unknown message type: {message_type}"
                })
    
    except WebSocketDisconnect:
        manager.disconnect(session_id)
    except Exception as e:
        print(f"WebSocket error for session {session_id}: {str(e)}")
        manager.disconnect(session_id)


async def handle_chat_message(session_id: str, session, data: dict, agent):
    """Handle a chat message from the student"""
    student_message = data.get('message', '')
    
    # Save student message to database
    DatabaseOperations.save_chat_message(
        session_id=session_id,
        agent_type='tutor',
        sender='student',
        message=student_message
    )
    
    # Get agent response
    agent_response = agent.respond_to_chat(
        student_message,
        session.student.name
    )
    
    # Save agent response to database
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


async def handle_game_event(session_id: str, session, data: dict, agent):
    """Handle a game event (e.g., wrong answer)"""
    event = data.get('event')
    context = data.get('context', {})
    
    # Log the event
    print(f"Game event in session {session_id}: {event}")
    
    # Determine if agent should respond
    should_respond = False
    response = None
    
    if event == 'wrong_answer':
        # Check if student has made multiple mistakes
        attempts = context.get('attempts', 1)
        if attempts >= 2:
            should_respond = True
            response = agent.provide_encouragement(
                context.get('activity', 'exercise'),
                attempts
            )
    
    elif event == 'frustration_detected':
        should_respond = True
        response = agent.provide_encouragement(
            context.get('activity', 'exercise'),
            context.get('attempts', 3)
        )
    
    # Send response if needed
    if should_respond and response:
        # Save to database
        DatabaseOperations.save_chat_message(
            session_id=session_id,
            agent_type=context.get('activity', 'tutor'),
            sender='agent',
            message=response
        )
        
        # Send to client
        await manager.send_message(session_id, {
            "type": "chat",
            "sender": "agent",
            "agent_type": context.get('activity', 'tutor'),
            "message": response,
            "timestamp": datetime.utcnow().isoformat(),
            "triggered_by": event
        })


async def handle_hint_request(session_id: str, session, data: dict, agent):
    """Handle a hint request"""
    context = data.get('context', {})
    activity = context.get('activity', 'exercise')
    
    # Get hint from agent
    hint = agent.provide_hint(
        activity,
        context
    )
    
    # Save to database
    DatabaseOperations.save_chat_message(
        session_id=session_id,
        agent_type=activity,
        sender='agent',
        message=f"Hint: {hint}"
    )
    
    # Send to client
    await manager.send_message(session_id, {
        "type": "hint",
        "hint": hint,
        "hint_level": "medium",
        "timestamp": datetime.utcnow().isoformat()
    })


async def handle_activity_start(session_id: str, session, data: dict, agent):
    """Handle activity start event"""
    activity = data.get('activity', 'unknown')
    difficulty = data.get('difficulty', 'medium')
    
    print(f"Activity started in session {session_id}: {activity} ({difficulty})")
    
    # Optional: Send welcome message for activity
    # This could be customized based on activity type and difficulty
    # For now, we'll just log it


async def handle_activity_chat(session_id: str, session, data: dict, agent):
    """Handle activity-specific chat message"""
    activity = data.get('activity', 'unknown')
    difficulty = data.get('difficulty', 'medium')
    student_message = data.get('message', '')
    
    # Save student message to database
    DatabaseOperations.save_chat_message(
        session_id=session_id,
        agent_type=f'activity_{activity}',
        sender='student',
        message=student_message
    )
    
    # Get agent response (context-aware for the activity)
    agent_response = agent.respond_to_chat(
        student_message,
        session.student.name,
        context={
            'activity': activity,
            'difficulty': difficulty
        }
    )
    
    # Save agent response to database
    DatabaseOperations.save_chat_message(
        session_id=session_id,
        agent_type=f'activity_{activity}',
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


async def handle_activity_event(session_id: str, session, data: dict, agent):
    """Handle activity-specific events"""
    activity = data.get('activity', 'unknown')
    difficulty = data.get('difficulty', 'medium')
    event = data.get('event', 'unknown')
    context = data.get('context', {})
    
    print(f"Activity event in session {session_id}: {activity}/{difficulty}/{event}")
    
    response = None
    
    if event == 'wrong_answer':
        # Handle wrong answer based on difficulty behavior
        behavior = context.get('behavior', 'end_only')
        
        if behavior == 'immediate_hint':
            # Easy mode: provide immediate, detailed hint
            question = context.get('question', '')
            user_answer = context.get('userAnswer', '')
            correct_answer = context.get('correctAnswer', '')
            
            response = agent.provide_hint(
                activity,
                {
                    'question': question,
                    'user_answer': user_answer,
                    'correct_answer': correct_answer,
                    'hint_level': 'detailed'
                }
            )
            
            # Add encouraging message
            response = f"Let's think about this together. {response}\n\nTake your time and try again!"
        
        elif behavior == 'single_hint':
            # Medium mode: provide one concise hint
            question = context.get('question', '')
            correct_answer = context.get('correctAnswer', '')
            
            response = agent.provide_hint(
                activity,
                {
                    'question': question,
                    'correct_answer': correct_answer,
                    'hint_level': 'brief'
                }
            )
        
        # Hard mode (end_only): no response during exercise
    
    elif event == 'correct_answer':
        # Confirm correct answers (for easy/medium modes)
        response = "Great job! That's correct! 🎉"
    
    elif event == 'activity_complete':
        # Handle activity completion with metacognitive prompts
        prompts = context.get('prompts', [])
        score = context.get('score', 0)
        total = context.get('total', 0)
        
        if prompts:
            # Send metacognitive prompts
            response = f"You completed the activity! Score: {score}/{total}\n\n"
            response += "Let's reflect on your experience:\n\n"
            for i, prompt in enumerate(prompts, 1):
                response += f"{i}. {prompt}\n"
            response += "\nTake a moment to think about these questions. Feel free to share your thoughts!"
    
    # Send response if generated
    if response:
        # Save to database
        DatabaseOperations.save_chat_message(
            session_id=session_id,
            agent_type=f'activity_{activity}',
            sender='agent',
            message=response
        )
        
        # Determine response type
        response_type = 'activity_hint' if event == 'wrong_answer' else 'activity_feedback'
        if event == 'activity_complete':
            response_type = 'activity_chat'
        
        # Send to client
        await manager.send_message(session_id, {
            "type": response_type,
            "sender": "agent",
            "message": response if response_type == 'activity_chat' else None,
            "hint": response if response_type == 'activity_hint' else None,
            "feedback": response if response_type == 'activity_feedback' else None,
            "timestamp": datetime.utcnow().isoformat(),
            "triggered_by": event
        })
