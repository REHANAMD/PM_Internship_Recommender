"""
Recommendation Engine Module - Hybrid recommendation system with rule-based and ML approaches
"""
import re
from typing import List, Dict, Tuple, Set
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np
import logging
from database import Database

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class RecommendationEngine:
    def __init__(self, db: Database = None):
        """Initialize recommendation engine"""
        self.db = db or Database()
        self.tfidf_vectorizer = TfidfVectorizer(
            max_features=500,
            stop_words='english',
            ngram_range=(1, 2)
        )
        
        # Skill normalization dictionary
        self.skill_synonyms = {
            'ml': 'machine learning',
            'ai': 'artificial intelligence',
            'dl': 'deep learning',
            'js': 'javascript',
            'ts': 'typescript',
            'py': 'python',
            'golang': 'go',
            'nodejs': 'node.js',
            'node': 'node.js',
            'react.js': 'react',
            'vue.js': 'vue',
            'angular.js': 'angular',
            'postgres': 'postgresql',
            'mongo': 'mongodb',
            'k8s': 'kubernetes',
            'gcp': 'google cloud platform',
            'aws': 'amazon web services',
            'azure': 'microsoft azure',
            'pm': 'product management',
            'ux': 'user experience',
            'ui': 'user interface',
            'ci/cd': 'continuous integration continuous deployment',
            'devops': 'development operations',
            'backend': 'back-end',
            'frontend': 'front-end',
            'fullstack': 'full-stack',
            'db': 'database',
            'ds': 'data science',
            'bi': 'business intelligence',
            'ba': 'business analysis',
            'qa': 'quality assurance',
            'api': 'application programming interface',
            'rest': 'representational state transfer',
            'graphql': 'graph query language',
            'nosql': 'non-relational database',
            'sql': 'structured query language',
            'etl': 'extract transform load',
            'nlp': 'natural language processing',
            'cv': 'computer vision',
            'iot': 'internet of things',
            'saas': 'software as a service',
            'paas': 'platform as a service',
            'iaas': 'infrastructure as a service'
        }
        
        # Education level hierarchy
        self.education_hierarchy = {
            'high school': 1,
            'diploma': 2,
            'certificate': 2,
            "bachelor's": 3,
            'bachelor': 3,
            'btech': 3,
            'be': 3,
            'bca': 3,
            'bba': 3,
            "master's": 4,
            'master': 4,
            'mtech': 4,
            'me': 4,
            'mca': 4,
            'mba': 4,
            'phd': 5,
            'doctorate': 5
        }
    
    def normalize_skills(self, skills_text: str) -> str:
        """Normalize skills text by expanding abbreviations and standardizing terms"""
        if not skills_text:
            return ""
        
        normalized = skills_text.lower()
        
        # Replace synonyms and abbreviations
        for abbr, full in self.skill_synonyms.items():
            pattern = r'\b' + re.escape(abbr) + r'\b'
            normalized = re.sub(pattern, full, normalized)
        
        return normalized
    
    def extract_skill_set(self, skills_text: str) -> Set[str]:
        """Extract individual skills from skills text"""
        if not skills_text:
            return set()
        
        # Normalize first
        normalized = self.normalize_skills(skills_text)
        
        # Split by common delimiters
        skills = re.split(r'[,;|•\n]+', normalized)
        
        # Clean and filter
        skill_set = set()
        for skill in skills:
            skill = skill.strip()
            if skill and len(skill) > 1:
                skill_set.add(skill)
        
        return skill_set
    
    def calculate_skill_match_score(self, candidate_skills: str, 
                                   required_skills: str, 
                                   preferred_skills: str = "") -> Tuple[float, List[str]]:
        """Calculate skill matching score using TF-IDF and cosine similarity"""
        if not candidate_skills or not required_skills:
            return 0.0, []
        
        # Extract skill sets
        candidate_set = self.extract_skill_set(candidate_skills)
        required_set = self.extract_skill_set(required_skills)
        preferred_set = self.extract_skill_set(preferred_skills) if preferred_skills else set()
        
        # Direct matching
        required_matches = candidate_set.intersection(required_set)
        preferred_matches = candidate_set.intersection(preferred_set)
        
        # Calculate base score
        if not required_set:
            base_score = 0.0
        else:
            required_score = len(required_matches) / len(required_set)
            preferred_score = len(preferred_matches) / len(preferred_set) if preferred_set else 0
            base_score = (required_score * 0.7) + (preferred_score * 0.3)
        
        # TF-IDF similarity for semantic matching
        try:
            # Combine all skills for vectorization
            all_skills = [
                ' '.join(candidate_set),
                ' '.join(required_set.union(preferred_set))
            ]
            
            if all([s.strip() for s in all_skills]):
                tfidf_matrix = self.tfidf_vectorizer.fit_transform(all_skills)
                similarity = cosine_similarity(tfidf_matrix[0:1], tfidf_matrix[1:2])[0][0]
                
                # Combine direct matching and similarity scores
                final_score = (base_score * 0.6) + (similarity * 0.4)
            else:
                final_score = base_score
        except:
            final_score = base_score
        
        # Prepare matched skills for explanation
        matched_skills = list(required_matches.union(preferred_matches))[:5]
        
        return min(final_score, 1.0), matched_skills
    
    def check_location_match(self, candidate_location: str, 
                           internship_location: str) -> Tuple[bool, float]:
        """Check if candidate location matches internship location"""
        if not candidate_location or not internship_location:
            return True, 0.5  # Neutral score if location not specified
        
        candidate_loc = candidate_location.lower().strip()
        internship_loc = internship_location.lower().strip()
        
        # Check for remote opportunities
        if 'remote' in internship_loc or 'anywhere' in internship_loc:
            return True, 1.0
        
        # Direct match
        if candidate_loc == internship_loc:
            return True, 1.0
        
        # Partial match (e.g., NCR region)
        ncr_cities = ['delhi', 'gurgaon', 'gurugram', 'noida', 'faridabad', 'ghaziabad', 'ncr']
        if any(city in candidate_loc for city in ncr_cities) and \
           any(city in internship_loc for city in ncr_cities):
            return True, 0.9
        
        # Check if cities are in same state (simplified)
        major_city_groups = [
            ['mumbai', 'pune', 'nashik', 'nagpur'],  # Maharashtra
            ['bangalore', 'bengaluru', 'mysore'],  # Karnataka
            ['chennai', 'coimbatore', 'madurai'],  # Tamil Nadu
            ['hyderabad', 'vijayawada', 'visakhapatnam'],  # Telangana/Andhra
            ['kolkata', 'howrah', 'durgapur']  # West Bengal
        ]
        
        for group in major_city_groups:
            if any(city in candidate_loc for city in group) and \
               any(city in internship_loc for city in group):
                return True, 0.7
        
        return False, 0.0
    
    def check_education_eligibility(self, candidate_education: str, 
                                   min_education: str) -> Tuple[bool, float]:
        """Check if candidate meets education requirements"""
        if not min_education:
            return True, 1.0
        
        if not candidate_education:
            return False, 0.0
        
        candidate_level = self.education_hierarchy.get(
            candidate_education.lower().strip(), 0
        )
        required_level = self.education_hierarchy.get(
            min_education.lower().strip(), 0
        )
        
        if candidate_level >= required_level:
            # Higher education gets bonus score
            bonus = min((candidate_level - required_level) * 0.1, 0.3)
            return True, min(1.0, 0.7 + bonus)
        
        return False, 0.0
    
    def check_experience_eligibility(self, candidate_exp: int, 
                                    required_exp: int) -> Tuple[bool, float]:
        """Check if candidate meets experience requirements"""
        if required_exp == 0:
            return True, 1.0
        
        if candidate_exp >= required_exp:
            # More experience gets bonus score
            bonus = min((candidate_exp - required_exp) * 0.05, 0.2)
            return True, min(1.0, 0.8 + bonus)
        
        # Allow candidates with slightly less experience
        if candidate_exp >= required_exp - 1:
            return True, 0.6
        
        return False, 0.0
    
    def calculate_hybrid_score(self, candidate: Dict, 
                             internship: Dict) -> Tuple[float, str, List[str]]:
        """Calculate hybrid recommendation score combining multiple factors"""
        score_components = []
        explanations = []
        matched_skills = []
        
        # 1. Skill matching (40% weight)
        skill_score, matched = self.calculate_skill_match_score(
            candidate.get('skills', ''),
            internship.get('required_skills', ''),
            internship.get('preferred_skills', '')
        )
        score_components.append(('skills', skill_score * 0.4))
        matched_skills = matched
        
        # 2. Location matching (25% weight)
        loc_match, loc_score = self.check_location_match(
            candidate.get('location'),
            internship.get('location')
        )
        score_components.append(('location', loc_score * 0.25))
        
        # 3. Education eligibility (20% weight)
        edu_eligible, edu_score = self.check_education_eligibility(
            candidate.get('education'),
            internship.get('min_education')
        )
        score_components.append(('education', edu_score * 0.2))
        
        # 4. Experience matching (15% weight)
        exp_eligible, exp_score = self.check_experience_eligibility(
            candidate.get('experience_years', 0),
            internship.get('experience_required', 0)
        )
        score_components.append(('experience', exp_score * 0.15))
        
        # Calculate total score
        total_score = sum(score for _, score in score_components)
        
        # Disqualify if doesn't meet hard requirements
        if not edu_eligible or not exp_eligible:
            total_score *= 0.3  # Heavily penalize but don't completely exclude
        
        # Generate explanation
        explanation_parts = []
        
        if matched_skills:
            explanation_parts.append(f"Skills match: {', '.join(matched_skills[:3])}")
        
        if loc_match and candidate.get('location'):
            if 'remote' in internship.get('location', '').lower():
                explanation_parts.append("Remote opportunity")
            elif candidate.get('location', '').lower() == internship.get('location', '').lower():
                explanation_parts.append(f"Location match: {candidate.get('location')}")
        
        if edu_eligible and edu_score > 0.7:
            explanation_parts.append(f"Education: {candidate.get('education', 'Qualified')}")
        
        if exp_eligible and candidate.get('experience_years', 0) > 0:
            explanation_parts.append(f"Experience: {candidate.get('experience_years')} years")
        
        explanation = " | ".join(explanation_parts) if explanation_parts else "General match"
        
        return total_score, explanation, matched_skills
    
    def identify_skill_gaps(self, candidate_skills: str, 
                           internship: Dict) -> List[str]:
        """Identify skills candidate should learn to qualify better"""
        if not internship.get('required_skills'):
            return []
        
        candidate_set = self.extract_skill_set(candidate_skills)
        required_set = self.extract_skill_set(internship.get('required_skills', ''))
        preferred_set = self.extract_skill_set(internship.get('preferred_skills', ''))
        
        # Find missing required skills
        missing_required = required_set - candidate_set
        missing_preferred = preferred_set - candidate_set
        
        # Prioritize required skills over preferred
        skill_gaps = list(missing_required)[:3] + list(missing_preferred)[:2]
        
        return skill_gaps[:5]  # Return top 5 skill gaps
    
    def get_recommendations(self, candidate_id: int, 
                          top_n: int = 5,
                          use_cache: bool = True) -> List[Dict]:
        """Get top N internship recommendations for a candidate"""
        # Check cache first
        if use_cache:
            cached = self.db.get_cached_recommendations(candidate_id, hours=24)
            if len(cached) >= top_n:
                logger.info(f"Using cached recommendations for candidate {candidate_id}")
                return cached[:top_n]
        
        # Get candidate data
        candidate = self.db.get_candidate(candidate_id=candidate_id)
        if not candidate:
            logger.error(f"Candidate {candidate_id} not found")
            return []
        
        # Get all active internships
        internships = self.db.get_all_internships(active_only=True)
        
        # Calculate scores for each internship
        recommendations = []
        for internship in internships:
            score, explanation, matched_skills = self.calculate_hybrid_score(
                candidate, internship
            )
            
            # Add skill gap suggestions
            skill_gaps = self.identify_skill_gaps(
                candidate.get('skills', ''),
                internship
            )
            
            recommendation = {
                'internship_id': internship['id'],
                'title': internship['title'],
                'company': internship['company'],
                'location': internship['location'],
                'description': internship['description'],
                'required_skills': internship['required_skills'],
                'preferred_skills': internship['preferred_skills'],
                'duration': internship['duration'],
                'stipend': internship['stipend'],
                'score': score,
                'explanation': explanation,
                'matched_skills': matched_skills,
                'skill_gaps': skill_gaps
            }
            
            recommendations.append(recommendation)
            
            # Save to cache (per internship)
            self.db.save_recommendation(
                candidate_id, 
                internship['id'],
                score,
                explanation
            )
        
        # Sort by score and return top N
        recommendations.sort(key=lambda x: x['score'], reverse=True)
        top_recommendations = recommendations[:top_n]
        
        logger.info(f"Generated {len(top_recommendations)} recommendations for candidate {candidate_id}")
        return top_recommendations
    
    def get_similar_candidates(self, candidate_id: int, top_n: int = 5) -> List[Dict]:
        """Find similar candidates based on skills and profile (for networking)"""
        # This could be extended for a networking feature
        pass

# Testing
if __name__ == "__main__":
    engine = RecommendationEngine()
    
    # Test skill normalization
    test_skills = "ML, JS, Python, React.js, k8s, AWS"
    print(f"Original: {test_skills}")
    print(f"Normalized: {engine.normalize_skills(test_skills)}")
    
    # Test skill matching
    candidate_skills = "Python, Machine Learning, React, Node.js"
    required_skills = "Python, ML, JavaScript"
    score, matched = engine.calculate_skill_match_score(
        candidate_skills, required_skills
    )
    print(f"\nSkill Match Score: {score:.2f}")
    print(f"Matched Skills: {matched}")