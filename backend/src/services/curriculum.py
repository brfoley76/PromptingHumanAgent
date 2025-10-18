"""
Curriculum Service - Fetches curriculum from Learning Module Platform.
Does NOT store curriculum - only caches temporarily for session duration.
"""
import json
from pathlib import Path
from typing import Dict, Optional, List


class CurriculumService:
    """
    Service to fetch curriculum from Learning Module Platform.
    Implements caching for performance.
    """
    
    # In-memory cache for session duration
    _cache: Dict[str, Dict] = {}
    
    # Path to Learning Module curriculum (for filesystem access)
    CURRICULUM_PATH = Path(__file__).parent.parent.parent / "test_data"
    
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
        curriculum_file = CurriculumService.CURRICULUM_PATH / f"{module_id}.json"
        
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
        for file in CurriculumService.CURRICULUM_PATH.glob("*.json"):
            modules.append(file.stem)
        return modules
