"""
Utilities Module - Helper functions for the recommendation engine
"""
import hashlib
import secrets
import string
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import json
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class Utils:
    @staticmethod
    def hash_password(password: str) -> str:
        """Hash password using SHA256"""
        return hashlib.sha256(password.encode()).hexdigest()
    
    @staticmethod
    def verify_password(password: str, password_hash: str) -> bool:
        """Verify password against hash"""
        return Utils.hash_password(password) == password_hash
    
    @staticmethod
    def generate_random_string(length: int = 32) -> str:
        """Generate random string for tokens"""
        alphabet = string.ascii_letters + string.digits
        return ''.join(secrets.choice(alphabet) for _ in range(length))
    
    @staticmethod
    def validate_email(email: str) -> bool:
        """Basic email validation"""
        import re
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return re.match(pattern, email) is not None
    
    @staticmethod
    def validate_phone(phone: str) -> bool:
        """Validate Indian phone number"""
        import re
        # Remove any non-digit characters
        phone_digits = re.sub(r'\D', '', phone)
        # Check if it's a valid 10-digit Indian number
        return len(phone_digits) == 10 and phone_digits[0] in '6789'
    
    @staticmethod
    def sanitize_input(text: str) -> str:
        """Sanitize user input to prevent injection attacks"""
        if not text:
            return ""
        # Remove potentially harmful characters
        sanitized = text.strip()
        # Remove HTML tags
        import re
        sanitized = re.sub(r'<[^>]+>', '', sanitized)
        # Limit length
        return sanitized[:5000]
    
    @staticmethod
    def format_skills_list(skills: str) -> List[str]:
        """Format skills string into a clean list"""
        if not skills:
            return []
        
        import re
        # Split by common delimiters
        skills_list = re.split(r'[,;|•\n]+', skills)
        # Clean and filter
        cleaned = []
        for skill in skills_list:
            skill = skill.strip()
            if skill and len(skill) > 1:
                cleaned.append(skill)
        return cleaned
    
    @staticmethod
    def format_date(date_str: str) -> str:
        """Format date string to readable format"""
        try:
            if isinstance(date_str, str):
                # Try parsing ISO format
                dt = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
                return dt.strftime('%B %d, %Y')
            return date_str
        except:
            return date_str
    
    @staticmethod
    def calculate_match_percentage(score: float) -> str:
        """Convert score to percentage with color coding"""
        percentage = int(score * 100)
        if percentage >= 80:
            return f"🟢 {percentage}% Match"
        elif percentage >= 60:
            return f"🟡 {percentage}% Match"
        else:
            return f"🔴 {percentage}% Match"
    
    @staticmethod
    def format_stipend(stipend: str) -> str:
        """Format stipend for display"""
        if not stipend:
            return "Not specified"
        
        stipend_lower = stipend.lower()
        if 'unpaid' in stipend_lower or stipend_lower == '0':
            return "Unpaid"
        elif 'variable' in stipend_lower or 'performance' in stipend_lower:
            return "Performance-based"
        else:
            # Try to format as currency
            import re
            numbers = re.findall(r'\d+', stipend)
            if numbers:
                amount = numbers[0]
                if len(amount) >= 4:
                    # Format with commas for Indian numbering
                    return f"₹{int(amount):,}/month"
            return stipend
    
    @staticmethod
    def generate_welcome_message(name: str) -> str:
        """Generate personalized welcome message"""
        hour = datetime.now().hour
        if hour < 12:
            greeting = "Good morning"
        elif hour < 17:
            greeting = "Good afternoon"
        else:
            greeting = "Good evening"
        
        return f"{greeting}, {name}! 👋"
    
    @staticmethod
    def load_sample_data() -> Dict:
        """Load sample data for testing"""
        sample_internships = [
            {
                "title": "Product Management Intern",
                "company": "TechCorp India",
                "location": "Bangalore",
                "description": "Join our product team to help build innovative solutions for millions of users.",
                "required_skills": "Product Management, User Research, Analytics, SQL, JIRA",
                "preferred_skills": "A/B Testing, Figma, Python, Market Research",
                "duration": "6 months",
                "stipend": "25000",
                "min_education": "Bachelor's",
                "experience_required": 0
            },
            {
                "title": "Associate Product Manager Intern",
                "company": "StartupHub",
                "location": "Mumbai",
                "description": "Work directly with founders to shape product strategy and roadmap.",
                "required_skills": "Product Strategy, Agile, User Stories, Competitive Analysis",
                "preferred_skills": "Wireframing, SQL, Data Analysis, Stakeholder Management",
                "duration": "3 months",
                "stipend": "20000",
                "min_education": "Bachelor's",
                "experience_required": 0
            },
            {
                "title": "Product Analyst Intern",
                "company": "DataDriven Solutions",
                "location": "Pune",
                "description": "Analyze user behavior and product metrics to drive data-informed decisions.",
                "required_skills": "Data Analysis, SQL, Excel, Analytics, Statistics",
                "preferred_skills": "Python, Tableau, Product Management, A/B Testing",
                "duration": "4 months",
                "stipend": "18000",
                "min_education": "Bachelor's",
                "experience_required": 0
            },
            {
                "title": "Technical Product Manager Intern",
                "company": "CloudTech Systems",
                "location": "Hyderabad",
                "description": "Bridge the gap between engineering and business teams for cloud products.",
                "required_skills": "Product Management, Technical Documentation, API, Cloud Computing",
                "preferred_skills": "AWS, Python, Agile, System Design",
                "duration": "6 months",
                "stipend": "30000",
                "min_education": "Bachelor's",
                "experience_required": 0
            },
            {
                "title": "Growth Product Manager Intern",
                "company": "E-Commerce Giants",
                "location": "Delhi",
                "description": "Focus on user acquisition, retention, and growth metrics.",
                "required_skills": "Growth Marketing, Analytics, A/B Testing, User Research",
                "preferred_skills": "SQL, Python, SEO, Social Media Marketing",
                "duration": "3 months",
                "stipend": "22000",
                "min_education": "Bachelor's",
                "experience_required": 0
            },
            {
                "title": "Product Design Intern",
                "company": "DesignFirst Studio",
                "location": "Remote",
                "description": "Collaborate with product and design teams to create user-centered experiences.",
                "required_skills": "Figma, User Research, Wireframing, Prototyping",
                "preferred_skills": "Product Management, HTML, CSS, User Testing",
                "duration": "4 months",
                "stipend": "15000",
                "min_education": "Bachelor's",
                "experience_required": 0
            },
            {
                "title": "Product Operations Intern",
                "company": "FinTech Innovations",
                "location": "Chennai",
                "description": "Optimize product processes and support cross-functional teams.",
                "required_skills": "Project Management, Process Optimization, Data Analysis, Communication",
                "preferred_skills": "JIRA, Confluence, SQL, Product Management",
                "duration": "5 months",
                "stipend": "20000",
                "min_education": "Bachelor's",
                "experience_required": 0
            },
            {
                "title": "Product Marketing Intern",
                "company": "SaaS Dynamics",
                "location": "Noida",
                "description": "Develop go-to-market strategies and product positioning.",
                "required_skills": "Marketing, Content Writing, Market Research, Communication",
                "preferred_skills": "Product Management, Analytics, SEO, Social Media",
                "duration": "3 months",
                "stipend": "18000",
                "min_education": "Bachelor's",
                "experience_required": 0
            }
        ]
        
        sample_candidates = [
            {
                "email": "john.doe@example.com",
                "password": "password123",
                "name": "John Doe",
                "education": "Bachelor's",
                "skills": "Product Management, Python, SQL, Data Analysis, Agile, JIRA",
                "location": "Bangalore",
                "experience_years": 0,
                "phone": "9876543210",
                "linkedin": "linkedin.com/in/johndoe",
                "github": "github.com/johndoe"
            },
            {
                "email": "jane.smith@example.com",
                "password": "password123",
                "name": "Jane Smith",
                "education": "Master's",
                "skills": "User Research, Figma, Analytics, A/B Testing, Product Strategy",
                "location": "Mumbai",
                "experience_years": 1,
                "phone": "9876543211",
                "linkedin": "linkedin.com/in/janesmith"
            }
        ]
        
        return {
            "internships": sample_internships,
            "candidates": sample_candidates
        }
    
    @staticmethod
    def create_sample_files():
        """Create sample JSON files for testing"""
        import os
        
        # Create data directory if it doesn't exist
        os.makedirs('data', exist_ok=True)
        
        sample_data = Utils.load_sample_data()
        
        # Save internships.json
        with open('data/internships.json', 'w') as f:
            json.dump(sample_data['internships'], f, indent=2)
        
        # Save candidates.json
        with open('data/candidates.json', 'w') as f:
            json.dump(sample_data['candidates'], f, indent=2)
        
        logger.info("Sample data files created successfully")
    
    @staticmethod
    def format_recommendation_card(recommendation: Dict) -> Dict:
        """Format recommendation for display card"""
        return {
            'internship_id': recommendation.get('internship_id', 0),
            'title': recommendation.get('title', 'Unknown Position'),
            'company': recommendation.get('company', 'Unknown Company'),
            'location': recommendation.get('location', 'Not specified'),
            'match_percentage': Utils.calculate_match_percentage(recommendation.get('score', 0)),
            'stipend': Utils.format_stipend(recommendation.get('stipend')),
            'duration': recommendation.get('duration', 'Not specified'),
            'explanation': recommendation.get('explanation', ''),
            'matched_skills': recommendation.get('matched_skills', []),
            'skill_gaps': recommendation.get('skill_gaps', []),
            'description': recommendation.get('description', '')[:200] + '...' 
                          if len(recommendation.get('description', '')) > 200 
                          else recommendation.get('description', '')
        }

# Multi-language support dictionary
TRANSLATIONS = {
    'en': {
        'welcome': 'Welcome',
        'login': 'Login',
        'signup': 'Sign Up',
        'email': 'Email',
        'password': 'Password',
        'name': 'Name',
        'education': 'Education',
        'skills': 'Skills',
        'location': 'Location',
        'experience': 'Experience (years)',
        'phone': 'Phone',
        'linkedin': 'LinkedIn Profile',
        'github': 'GitHub Profile',
        'submit': 'Submit',
        'recommendations': 'Your Recommendations',
        'upload_resume': 'Upload Resume',
        'auto_fill': 'Auto-fill with Resume',
        'profile': 'Profile',
        'logout': 'Logout',
        'apply': 'Apply',
        'learn_more': 'Learn More',
        'skill_gaps': 'Skills to Learn',
        'matched_skills': 'Matched Skills'
    },
    'hi': {
        'welcome': 'स्वागत',
        'login': 'लॉग इन',
        'signup': 'साइन अप',
        'email': 'ईमेल',
        'password': 'पासवर्ड',
        'name': 'नाम',
        'education': 'शिक्षा',
        'skills': 'कौशल',
        'location': 'स्थान',
        'experience': 'अनुभव (वर्ष)',
        'phone': 'फोन',
        'linkedin': 'लिंक्डइन प्रोफाइल',
        'github': 'गिटहब प्रोफाइल',
        'submit': 'जमा करें',
        'recommendations': 'आपकी सिफारिशें',
        'upload_resume': 'रिज्यूमे अपलोड करें',
        'auto_fill': 'रिज्यूमे से ऑटो-फिल करें',
        'profile': 'प्रोफाइल',
        'logout': 'लॉग आउट',
        'apply': 'आवेदन करें',
        'learn_more': 'और जानें',
        'skill_gaps': 'सीखने के लिए कौशल',
        'matched_skills': 'मिलान कौशल'
    }
}

def get_translation(key: str, language: str = 'en') -> str:
    """Get translated text for given key and language"""
    return TRANSLATIONS.get(language, TRANSLATIONS['en']).get(key, key)

# Testing
if __name__ == "__main__":
    utils = Utils()
    
    # Test password hashing
    password = "test123"
    hashed = utils.hash_password(password)
    print(f"Password hash: {hashed}")
    print(f"Verification: {utils.verify_password(password, hashed)}")
    
    # Test email validation
    print(f"Valid email: {utils.validate_email('test@example.com')}")
    print(f"Invalid email: {utils.validate_email('invalid-email')}")
    
    # Test phone validation
    print(f"Valid phone: {utils.validate_phone('9876543210')}")
    print(f"Invalid phone: {utils.validate_phone('1234567890')}")
    
    # Create sample files
    utils.create_sample_files()
    print("Sample files created in data/ directory")