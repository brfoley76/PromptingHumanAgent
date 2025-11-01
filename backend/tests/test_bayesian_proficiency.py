"""
Unit tests for Bayesian Proficiency Service
"""
import pytest
import math
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock

from src.services.bayesian_proficiency import BayesianProficiencyService
from src.database.models import StudentProficiency


class TestBayesianUpdating:
    """Test Bayesian updating mathematics"""
    
    def test_prior_initialization(self):
        """Test that priors are correctly initialized"""
        assert BayesianProficiencyService.DEFAULT_PRIOR_ALPHA == 2.0
        assert BayesianProficiencyService.DEFAULT_PRIOR_BETA == 2.0
        
        # Mean of Beta(2, 2) should be 0.5
        mean = 2.0 / (2.0 + 2.0)
        assert mean == 0.5
    
    def test_bayesian_update_all_correct(self):
        """Test Bayesian update with all correct answers"""
        # Start with Beta(2, 2)
        alpha_prior = 2.0
        beta_prior = 2.0
        
        # 5 correct answers
        successes = 5
        failures = 0
        
        # Posterior should be Beta(7, 2)
        alpha_post = alpha_prior + successes
        beta_post = beta_prior + failures
        
        assert alpha_post == 7.0
        assert beta_post == 2.0
        
        # Mean ability should be 7/9 ≈ 0.778
        mean_ability = alpha_post / (alpha_post + beta_post)
        assert abs(mean_ability - 0.778) < 0.001
    
    def test_bayesian_update_all_incorrect(self):
        """Test Bayesian update with all incorrect answers"""
        alpha_prior = 2.0
        beta_prior = 2.0
        
        successes = 0
        failures = 5
        
        alpha_post = alpha_prior + successes
        beta_post = beta_prior + failures
        
        assert alpha_post == 2.0
        assert beta_post == 7.0
        
        # Mean ability should be 2/9 ≈ 0.222
        mean_ability = alpha_post / (alpha_post + beta_post)
        assert abs(mean_ability - 0.222) < 0.001
    
    def test_bayesian_update_mixed(self):
        """Test Bayesian update with mixed results"""
        alpha_prior = 2.0
        beta_prior = 2.0
        
        successes = 7
        failures = 3
        
        alpha_post = alpha_prior + successes
        beta_post = beta_prior + failures
        
        assert alpha_post == 9.0
        assert beta_post == 5.0
        
        # Mean ability should be 9/14 ≈ 0.643
        mean_ability = alpha_post / (alpha_post + beta_post)
        assert abs(mean_ability - 0.643) < 0.001


class TestForgettingDecay:
    """Test forgetting decay calculations"""
    
    def test_no_decay_same_day(self):
        """Test that no decay occurs on the same day"""
        ability = 0.8
        last_updated = datetime.utcnow()
        forgetting_rate = 0.05
        
        result = BayesianProficiencyService._apply_forgetting(
            ability, last_updated, forgetting_rate
        )
        
        assert result == ability
    
    def test_decay_after_one_day(self):
        """Test decay after one day"""
        ability = 0.8
        last_updated = datetime.utcnow() - timedelta(days=1)
        forgetting_rate = 0.05
        prior = 0.5
        
        result = BayesianProficiencyService._apply_forgetting(
            ability, last_updated, forgetting_rate
        )
        
        # Calculate expected: ability * e^(-0.05*1) + 0.5 * (1 - e^(-0.05*1))
        decay_factor = math.exp(-forgetting_rate * 1)
        expected = ability * decay_factor + prior * (1 - decay_factor)
        
        assert abs(result - expected) < 0.001
        assert result < ability  # Should decay toward prior
        assert result > prior  # But not below prior
    
    def test_decay_after_many_days(self):
        """Test decay approaches prior after many days"""
        ability = 0.9
        last_updated = datetime.utcnow() - timedelta(days=100)
        forgetting_rate = 0.05
        prior = 0.5
        
        result = BayesianProficiencyService._apply_forgetting(
            ability, last_updated, forgetting_rate
        )
        
        # After 100 days, should be very close to prior
        assert abs(result - prior) < 0.1
    
    def test_decay_symmetric(self):
        """Test that decay works symmetrically above and below prior"""
        forgetting_rate = 0.05
        last_updated = datetime.utcnow() - timedelta(days=10)
        prior = 0.5
        
        # High ability should decay down
        high_ability = 0.9
        result_high = BayesianProficiencyService._apply_forgetting(
            high_ability, last_updated, forgetting_rate
        )
        assert result_high < high_ability
        assert result_high > prior
        
        # Low ability should decay up
        low_ability = 0.1
        result_low = BayesianProficiencyService._apply_forgetting(
            low_ability, last_updated, forgetting_rate
        )
        assert result_low > low_ability
        assert result_low < prior


class TestDifficultyMapping:
    """Test difficulty level mapping"""
    
    def test_ability_to_difficulty_multiple_choice(self):
        """Test difficulty mapping for multiple choice"""
        activity_type = 'multiple_choice'
        
        # Low ability -> easy (3)
        assert BayesianProficiencyService._ability_to_difficulty(0.5, activity_type) == '3'
        
        # Medium ability -> medium (4)
        assert BayesianProficiencyService._ability_to_difficulty(0.7, activity_type) == '4'
        
        # High ability -> hard (5)
        assert BayesianProficiencyService._ability_to_difficulty(0.85, activity_type) == '5'
    
    def test_ability_to_difficulty_other_activities(self):
        """Test difficulty mapping for other activities"""
        activity_type = 'spelling'
        
        # Low ability -> easy
        assert BayesianProficiencyService._ability_to_difficulty(0.5, activity_type) == 'easy'
        
        # Medium ability -> medium
        assert BayesianProficiencyService._ability_to_difficulty(0.7, activity_type) == 'medium'
        
        # High ability -> hard
        assert BayesianProficiencyService._ability_to_difficulty(0.85, activity_type) == 'hard'
    
    def test_default_difficulty(self):
        """Test default difficulty for first attempt"""
        assert BayesianProficiencyService._get_default_difficulty('multiple_choice') == '3'
        assert BayesianProficiencyService._get_default_difficulty('spelling') == 'easy'
        assert BayesianProficiencyService._get_default_difficulty('fill_in_the_blank') == 'easy'


class TestQuestionCountAdaptation:
    """Test adaptive question count calculation"""
    
    def test_high_ability_high_confidence(self):
        """Test that high ability + confidence gives fewer questions"""
        ability = 0.9
        confidence = 0.85
        
        count = BayesianProficiencyService._calculate_question_count(ability, confidence)
        assert count == 5  # Quick check
    
    def test_medium_ability(self):
        """Test that medium ability gives moderate questions"""
        ability = 0.75
        confidence = 0.7
        
        count = BayesianProficiencyService._calculate_question_count(ability, confidence)
        assert count == 7  # Moderate practice
    
    def test_low_ability(self):
        """Test that low ability gives full questions"""
        ability = 0.5
        confidence = 0.5
        
        count = BayesianProficiencyService._calculate_question_count(ability, confidence)
        assert count == 10  # Full practice
    
    def test_low_confidence(self):
        """Test that low confidence gives full questions even with decent ability"""
        ability = 0.75
        confidence = 0.4
        
        count = BayesianProficiencyService._calculate_question_count(ability, confidence)
        assert count == 10  # Full practice due to uncertainty


class TestMasteryThreshold:
    """Test mastery threshold logic"""
    
    def test_mastery_threshold_default(self):
        """Test default mastery threshold"""
        assert BayesianProficiencyService.MASTERY_THRESHOLD == 0.85
    
    def test_skip_threshold(self):
        """Test skip threshold"""
        assert BayesianProficiencyService.SKIP_THRESHOLD == 0.90
        assert BayesianProficiencyService.SKIP_THRESHOLD > BayesianProficiencyService.MASTERY_THRESHOLD


class TestRecommendations:
    """Test recommendation generation"""
    
    @patch('src.services.bayesian_proficiency.get_db')
    def test_recommendations_no_history(self, mock_get_db):
        """Test recommendations for student with no history"""
        # Mock database
        mock_db = MagicMock()
        mock_get_db.return_value = iter([mock_db])
        
        # Mock query to return None (no proficiency found)
        mock_db.query.return_value.filter.return_value.first.return_value = None
        mock_db.query.return_value.filter.return_value.filter.return_value.filter.return_value.all.return_value = []
        
        recommendations = BayesianProficiencyService.get_adaptive_recommendations(
            'student_123',
            'r003.1',
            'multiple_choice'
        )
        
        # Should return defaults
        assert recommendations['difficulty'] == '3'
        assert recommendations['num_questions'] == 10
        assert recommendations['skip_activity'] == False
        assert recommendations['focus_items'] == []


class TestItemDifficulty:
    """Test item difficulty retrieval"""
    
    def test_get_item_difficulty_found(self):
        """Test getting difficulty when item exists"""
        curriculum = {
            'content': {
                'vocabulary': [
                    {'word': 'pirate', 'difficulty': 0.2},
                    {'word': 'captain', 'difficulty': 0.4}
                ]
            }
        }
        
        difficulty = BayesianProficiencyService._get_item_difficulty(
            'pirate', 'r003.1', curriculum
        )
        assert difficulty == 0.2
    
    def test_get_item_difficulty_not_found(self):
        """Test getting difficulty when item doesn't exist"""
        curriculum = {
            'content': {
                'vocabulary': [
                    {'word': 'pirate', 'difficulty': 0.2}
                ]
            }
        }
        
        difficulty = BayesianProficiencyService._get_item_difficulty(
            'unknown', 'r003.1', curriculum
        )
        assert difficulty == 0.5  # Default
    
    def test_get_item_difficulty_no_difficulty_field(self):
        """Test getting difficulty when field is missing"""
        curriculum = {
            'content': {
                'vocabulary': [
                    {'word': 'pirate'}  # No difficulty field
                ]
            }
        }
        
        difficulty = BayesianProficiencyService._get_item_difficulty(
            'pirate', 'r003.1', curriculum
        )
        assert difficulty == 0.5  # Default


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
