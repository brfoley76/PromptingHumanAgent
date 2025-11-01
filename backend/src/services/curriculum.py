"""
Curriculum Service - Fetches curriculum from Learning Module Platform.
Does NOT store curriculum - only caches temporarily for session duration.
"""
import json
from pathlib import Path
from typing import Dict, Optional, List

from ..config import config


class CurriculumService:
    """
    Service to fetch curriculum from Learning Module Platform.
    Implements caching for performance.
    """
    
    # In-memory cache for session duration
    _cache: Dict[str, Dict] = {}
    
    # Path to Learning Module curriculum (from config)
    @staticmethod
    def get_curriculum_path() -> Path:
        """Get curriculum path from configuration"""
        return Path(config.LEARNING_MODULE_PATH)
    
    @staticmethod
    def load_curriculum(module_id: str, use_cache: bool = True) -> Dict:
        """
        Fetch curriculum from Learning Module Platform.
        
        Args:
            module_id: Curriculum module identifier (e.g., 'math_mult_001')
            use_cache: Whether to use cached data
            
        Returns:
            Curriculum dictionary
            
        Raises:
            FileNotFoundError: If curriculum module not found
        """
        # Check cache first
        if use_cache and module_id in CurriculumService._cache:
            return CurriculumService._cache[module_id]
        
        # Fetch from filesystem (simulates Learning Module)
        curriculum = CurriculumService._fetch_from_filesystem(module_id)
        
        # Cache for session duration
        CurriculumService._cache[module_id] = curriculum
        return curriculum
    
    @staticmethod
    def _fetch_from_filesystem(module_id: str) -> Dict:
        """
        Read curriculum from shared filesystem.
        In production, this would be an HTTP API call.
        """
        curriculum_path = CurriculumService.get_curriculum_path()
        curriculum_file = curriculum_path / f"{module_id}.json"
        
        if not curriculum_file.exists():
            raise FileNotFoundError(f"Curriculum module '{module_id}' not found at {curriculum_file}")
        
        with open(curriculum_file, 'r') as f:
            return json.load(f)
    
    @staticmethod
    def get_vocabulary(module_id: str) -> List[Dict]:
        """Get just the vocabulary list"""
        curriculum = CurriculumService.load_curriculum(module_id)
        return curriculum.get('content', {}).get('vocabulary', [])
    
    @staticmethod
    def get_problems(module_id: str) -> List[Dict]:
        """Get just the problems list"""
        curriculum = CurriculumService.load_curriculum(module_id)
        return curriculum.get('content', {}).get('problems', [])
    
    @staticmethod
    def get_exercises(module_id: str) -> List[str]:
        """Get available exercise types for this module"""
        curriculum = CurriculumService.load_curriculum(module_id)
        return curriculum.get('exercises', [])
    
    @staticmethod
    def clear_cache(module_id: Optional[str] = None):
        """
        Clear curriculum cache.
        Call on session end or when curriculum is updated.
        """
        if module_id:
            CurriculumService._cache.pop(module_id, None)
        else:
            CurriculumService._cache.clear()
    
    @staticmethod
    def list_available_modules() -> List[str]:
        """List all available curriculum modules"""
        modules = []
        curriculum_path = CurriculumService.get_curriculum_path()
        for file in curriculum_path.glob("*.json"):
            modules.append(file.stem)
        return modules
    
    @staticmethod
    def load_curriculum_light(module_id: str, use_cache: bool = True) -> Dict:
        """
        Load lightweight curriculum without narrative content.
        This reduces token usage for agent context.
        
        Args:
            module_id: Curriculum module identifier
            use_cache: Whether to use cached data
            
        Returns:
            Curriculum dictionary without narrative section
        """
        curriculum = CurriculumService.load_curriculum(module_id, use_cache)
        
        # Create lightweight copy without narrative
        light_curriculum = {
            'id': curriculum.get('id'),
            'title': curriculum.get('title', ''),
            'description': curriculum.get('description', ''),
            'gradeLevel': curriculum.get('gradeLevel', ''),
            'subject': curriculum.get('subject', ''),
            'goals': curriculum.get('goals', ''),
            'exercises': curriculum.get('exercises', []),
            'optional_exercises': curriculum.get('optional_exercises', []),
            'content': {
                'vocabulary': curriculum.get('content', {}).get('vocabulary', []),
                'problems': curriculum.get('content', {}).get('problems', [])
            }
        }
        
        return light_curriculum
    
    @staticmethod
    def get_activity_vocabulary(module_id: str, activity_type: str, difficulty: str) -> List[Dict]:
        """
        Get vocabulary subset relevant for a specific activity.
        Filters by difficulty and importance for token efficiency.
        
        Args:
            module_id: Curriculum module identifier
            activity_type: Type of activity (e.g., 'multiple_choice')
            difficulty: Difficulty level ('3', '4', '5')
            
        Returns:
            Filtered vocabulary list
        """
        vocabulary = CurriculumService.get_vocabulary(module_id)
        
        # Convert difficulty to float for comparison
        try:
            max_difficulty = float(difficulty) / 5.0  # Normalize to 0-1 scale
        except (ValueError, TypeError):
            max_difficulty = 1.0  # Default to all difficulties
        
        # Filter vocabulary based on difficulty and importance
        filtered_vocab = []
        for vocab in vocabulary:
            vocab_difficulty = vocab.get('difficulty', 0.5)
            vocab_importance = vocab.get('importance', 1.0)
            
            # Include if:
            # 1. Difficulty is appropriate (within range)
            # 2. High importance words (>0.8) are always included
            if vocab_difficulty <= max_difficulty or vocab_importance > 0.8:
                filtered_vocab.append(vocab)
        
        return filtered_vocab
