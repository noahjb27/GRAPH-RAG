"""
Question loader for integrating with the existing question taxonomy
"""

import sys
from typing import List, Dict, Any, Optional
from pathlib import Path

# Add project root to path to import question taxonomy
project_root = Path(__file__).parent.parent.parent
sys.path.append(str(project_root))

# Import the existing question taxonomy
try:
    from question_taxonomy.initial_question_taxonomy import (
        ExtendedBerlinTransportQuestionTaxonomy,
        EvaluationQuestion
    )
    TAXONOMY_AVAILABLE = True
except ImportError as e:
    print(f"Warning: Could not import question taxonomy: {e}")
    EvaluationQuestion = Any  # Fallback type
    ExtendedBerlinTransportQuestionTaxonomy = None
    TAXONOMY_AVAILABLE = False

class QuestionLoader:
    """Loads and manages evaluation questions from the taxonomy"""
    
    def __init__(self):
        self.taxonomy = None
        self.questions = []
        self._load_questions()
    
    def _load_questions(self):
        """Load questions from the taxonomy"""
        if ExtendedBerlinTransportQuestionTaxonomy:
            self.taxonomy = ExtendedBerlinTransportQuestionTaxonomy()
            self.questions = self.taxonomy.get_all_questions()
        else:
            print("Warning: Question taxonomy not available, using empty question set")
            self.questions = []
    
    def get_all_questions(self) -> List[Any]:
        """Get all evaluation questions"""
        return self.questions
    
    def get_questions_by_category(self, category: str) -> List[Any]:
        """Get questions filtered by category"""
        return [q for q in self.questions if q.category == category]
    
    def get_questions_by_difficulty(self, difficulty: int) -> List[Any]:
        """Get questions filtered by difficulty level"""
        return [q for q in self.questions if q.difficulty == difficulty]
    
    def get_questions_by_capability(self, capability: str) -> List[Any]:
        """Get questions that require a specific capability"""
        return [
            q for q in self.questions 
            if capability in q.required_capabilities
        ]
    
    def get_question_by_id(self, question_id: str) -> Optional[Any]:
        """Get a specific question by ID"""
        for question in self.questions:
            if question.question_id == question_id:
                return question
        return None
    
    def get_sample_questions(
        self,
        count: int = 5,
        categories: Optional[List[str]] = None,
        max_difficulty: int = 5
    ) -> List[Any]:
        """Get a sample of questions for testing"""
        
        filtered_questions = self.questions
        
        # Filter by categories if specified
        if categories:
            filtered_questions = [
                q for q in filtered_questions 
                if q.category in categories
            ]
        
        # Filter by difficulty
        filtered_questions = [
            q for q in filtered_questions 
            if q.difficulty <= max_difficulty
        ]
        
        # Return sample (up to count)
        return filtered_questions[:count]
    
    def get_taxonomy_summary(self) -> Dict[str, Any]:
        """Get summary statistics of the question taxonomy"""
        if not self.questions:
            return {
                "total_questions": 0,
                "categories": {},
                "difficulties": {},
                "evaluation_methods": {}
            }
        
        summary = {
            "total_questions": len(self.questions),
            "categories": {},
            "difficulties": {},
            "evaluation_methods": {},
            "capabilities": {}
        }
        
        for question in self.questions:
            # Count by category
            summary["categories"][question.category] = summary["categories"].get(question.category, 0) + 1
            
            # Count by difficulty
            summary["difficulties"][question.difficulty] = summary["difficulties"].get(question.difficulty, 0) + 1
            
            # Count by evaluation method
            summary["evaluation_methods"][question.evaluation_method] = summary["evaluation_methods"].get(question.evaluation_method, 0) + 1
            
            # Count capabilities
            for capability in question.required_capabilities:
                summary["capabilities"][capability] = summary["capabilities"].get(capability, 0) + 1
        
        return summary
    
    def validate_questions(self) -> Dict[str, Any]:
        """Validate questions for completeness and consistency"""
        
        validation_results = {
            "valid": True,
            "issues": [],
            "statistics": {
                "questions_with_cypher": 0,
                "questions_with_ground_truth": 0,
                "questions_with_context": 0
            }
        }
        
        for question in self.questions:
            # Check for required fields
            if not question.question_text:
                validation_results["issues"].append(f"Question {question.question_id} missing text")
                validation_results["valid"] = False
            
            if not question.cypher_query:
                validation_results["issues"].append(f"Question {question.question_id} missing Cypher query")
            else:
                validation_results["statistics"]["questions_with_cypher"] += 1
            
            if question.ground_truth is not None:
                validation_results["statistics"]["questions_with_ground_truth"] += 1
            
            if question.historical_context:
                validation_results["statistics"]["questions_with_context"] += 1
        
        return validation_results
    
    def reload_questions(self):
        """Reload questions from taxonomy (useful for development)"""
        self._load_questions() 