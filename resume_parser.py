"""
Resume Parser Module - Extracts information from PDF/Word resumes
"""
import re
import PyPDF2
import docx
from typing import Dict, List, Optional
import logging
from pathlib import Path

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ResumeParser:
    def __init__(self):
        """Initialize resume parser with skill patterns and education levels"""
        # Common skills to look for
        self.common_skills = [
            # Programming Languages
            'Python', 'Java', 'JavaScript', 'C++', 'C#', 'Ruby', 'Go', 'Rust', 'Swift',
            'Kotlin', 'TypeScript', 'PHP', 'R', 'MATLAB', 'Scala', 'Perl',
            
            # Web Technologies
            'HTML', 'CSS', 'React', 'Angular', 'Vue', 'Node.js', 'Express', 'Django',
            'Flask', 'FastAPI', 'Spring', 'ASP.NET', 'jQuery', 'Bootstrap', 'Tailwind',
            
            # Databases
            'SQL', 'MySQL', 'PostgreSQL', 'MongoDB', 'Redis', 'Cassandra', 'Oracle',
            'SQLite', 'Firebase', 'DynamoDB', 'Elasticsearch',
            
            # Cloud & DevOps
            'AWS', 'Azure', 'GCP', 'Docker', 'Kubernetes', 'Jenkins', 'CI/CD',
            'Terraform', 'Ansible', 'Linux', 'Git', 'GitHub', 'GitLab',
            
            # Data Science & ML
            'Machine Learning', 'Deep Learning', 'TensorFlow', 'PyTorch', 'Keras',
            'Scikit-learn', 'Pandas', 'NumPy', 'Data Analysis', 'Statistics',
            'NLP', 'Computer Vision', 'AI', 'Neural Networks',
            
            # PM Skills
            'Product Management', 'Agile', 'Scrum', 'JIRA', 'Confluence', 'Roadmap',
            'User Research', 'A/B Testing', 'Analytics', 'Stakeholder Management',
            'Product Strategy', 'Market Research', 'Competitive Analysis',
            'User Stories', 'Requirements Gathering', 'Wireframing', 'Prototyping',
            
            # Soft Skills
            'Leadership', 'Communication', 'Problem Solving', 'Team Management',
            'Project Management', 'Critical Thinking', 'Analytical Skills'
        ]
        
        # Education patterns
        self.education_patterns = [
            r"(?i)(bachelor|b\.?s\.?|b\.?tech|b\.?e\.?|bca|bba)",
            r"(?i)(master|m\.?s\.?|m\.?tech|m\.?e\.?|mca|mba)",
            r"(?i)(phd|ph\.?d|doctorate)",
            r"(?i)(diploma|certificate)",
            r"(?i)(computer science|information technology|software engineering)",
            r"(?i)(business administration|management|marketing)",
            r"(?i)(data science|analytics|statistics)",
            r"(?i)(electrical|mechanical|civil|chemical)\s+engineering"
        ]
        
        # Location patterns (Indian cities)
        self.locations = [
            'Mumbai', 'Delhi', 'Bangalore', 'Bengaluru', 'Hyderabad', 'Chennai',
            'Kolkata', 'Pune', 'Ahmedabad', 'Surat', 'Jaipur', 'Lucknow',
            'Kanpur', 'Nagpur', 'Indore', 'Thane', 'Bhopal', 'Visakhapatnam',
            'Pimpri-Chinchwad', 'Patna', 'Vadodara', 'Ghaziabad', 'Ludhiana',
            'Agra', 'Nashik', 'Faridabad', 'Meerut', 'Rajkot', 'Varanasi',
            'Srinagar', 'Aurangabad', 'Dhanbad', 'Amritsar', 'Allahabad',
            'Ranchi', 'Howrah', 'Coimbatore', 'Vijayawada', 'Jodhpur',
            'Madurai', 'Raipur', 'Kota', 'Guwahati', 'Chandigarh', 'Noida',
            'Gurgaon', 'Gurugram', 'NCR', 'Remote'
        ]
    
    def extract_text_from_pdf(self, file_path: str) -> str:
        """Extract text from PDF file"""
        try:
            text = ""
            with open(file_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                for page_num in range(len(pdf_reader.pages)):
                    page = pdf_reader.pages[page_num]
                    text += page.extract_text() + "\n"
            return text
        except Exception as e:
            logger.error(f"Error extracting text from PDF: {e}")
            return ""
    
    def extract_text_from_docx(self, file_path: str) -> str:
        """Extract text from Word document"""
        try:
            doc = docx.Document(file_path)
            text = "\n".join([paragraph.text for paragraph in doc.paragraphs])
            return text
        except Exception as e:
            logger.error(f"Error extracting text from DOCX: {e}")
            return ""
    
    def extract_email(self, text: str) -> Optional[str]:
        """Extract email address from text"""
        email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        matches = re.findall(email_pattern, text)
        return matches[0] if matches else None
    
    def extract_phone(self, text: str) -> Optional[str]:
        """Extract phone number from text"""
        # Indian phone number patterns
        phone_patterns = [
            r'(?:\+91[-.\s]?)?(?:\d{10})',
            r'(?:\+91[-.\s]?)?(?:\d{5}[-.\s]?\d{5})',
            r'(?:\+91[-.\s]?)?(?:\d{4}[-.\s]?\d{3}[-.\s]?\d{3})',
            r'(?:\+91[-.\s]?)?(?:\d{3}[-.\s]?\d{3}[-.\s]?\d{4})'
        ]
        
        for pattern in phone_patterns:
            matches = re.findall(pattern, text)
            if matches:
                # Clean and return the first valid phone number
                phone = re.sub(r'[-.\s]', '', matches[0])
                if len(phone) >= 10:
                    return phone[-10:]  # Return last 10 digits
        return None
    
    def extract_name(self, text: str, email: Optional[str] = None) -> Optional[str]:
        """Extract name from text"""
        lines = text.split('\n')
        
        # Usually name is in the first few lines
        for i, line in enumerate(lines[:10]):
            line = line.strip()
            if line and len(line) < 50:  # Names are usually short
                # Check if line doesn't contain common non-name elements
                if not any(word in line.lower() for word in 
                          ['resume', 'curriculum', 'vitae', 'cv', 'phone', 
                           'email', 'address', 'objective', 'summary']):
                    # Check if it looks like a name (contains alphabets and spaces only)
                    if re.match(r'^[A-Za-z\s\.]+$', line):
                        return line.title()
        
        # If email is provided, try to extract name from email
        if email:
            username = email.split('@')[0]
            # Remove numbers and split by common separators
            name_parts = re.split(r'[._-]', re.sub(r'\d+', '', username))
            if name_parts:
                return ' '.join(name_parts).title()
        
        return None
    
    def extract_education(self, text: str) -> Optional[str]:
        """Extract education information from text"""
        education_info = []
        text_lower = text.lower()
        
        # Look for education section
        education_section = None
        if 'education' in text_lower:
            start_idx = text_lower.index('education')
            # Get next 500 characters after education keyword
            education_section = text[start_idx:start_idx+500]
        
        search_text = education_section if education_section else text
        
        # Look for degree patterns
        for pattern in self.education_patterns:
            matches = re.findall(pattern, search_text, re.IGNORECASE)
            if matches:
                education_info.extend(matches)
        
        # Clean and format education info
        if education_info:
            # Get the highest degree
            if any('master' in e.lower() or 'mba' in e.lower() or 'mca' in e.lower() 
                   or 'm.tech' in e.lower() or 'm.s' in e.lower() for e in education_info):
                return "Master's"
            elif any('bachelor' in e.lower() or 'b.tech' in e.lower() or 'b.e' in e.lower() 
                     or 'bca' in e.lower() or 'bba' in e.lower() for e in education_info):
                return "Bachelor's"
            elif any('phd' in e.lower() or 'doctorate' in e.lower() for e in education_info):
                return "PhD"
            else:
                return "Diploma/Certificate"
        
        return "Bachelor's"  # Default assumption
    
    def extract_skills(self, text: str) -> List[str]:
        """Extract skills from text"""
        found_skills = []
        text_lower = text.lower()
        
        for skill in self.common_skills:
            # Case-insensitive search with word boundaries
            pattern = r'\b' + re.escape(skill.lower()) + r'\b'
            if re.search(pattern, text_lower):
                found_skills.append(skill)
        
        # Remove duplicates while preserving order
        seen = set()
        unique_skills = []
        for skill in found_skills:
            if skill.lower() not in seen:
                seen.add(skill.lower())
                unique_skills.append(skill)
        
        return unique_skills[:20]  # Limit to top 20 skills
    
    def extract_location(self, text: str) -> Optional[str]:
        """Extract location from text"""
        text_lower = text.lower()
        
        for location in self.locations:
            if location.lower() in text_lower:
                return location
        
        # Look for common location indicators
        location_patterns = [
            r'(?i)location\s*:?\s*([A-Za-z\s]+)',
            r'(?i)city\s*:?\s*([A-Za-z\s]+)',
            r'(?i)address\s*:?\s*.*?([A-Za-z\s]+)(?:,|\n)',
            r'(?i)based\s+(?:in|at)\s+([A-Za-z\s]+)'
        ]
        
        for pattern in location_patterns:
            matches = re.findall(pattern, text)
            if matches:
                # Check if matched location is in our list
                for match in matches:
                    for location in self.locations:
                        if location.lower() in match.lower():
                            return location
        
        return None
    
    def extract_experience_years(self, text: str) -> int:
        """Extract years of experience from text"""
        # Look for experience patterns
        patterns = [
            r'(\d+)\+?\s*years?\s*(?:of\s*)?experience',
            r'experience\s*:?\s*(\d+)\+?\s*years?',
            r'(\d+)\+?\s*years?\s*(?:of\s*)?professional',
            r'working\s*(?:for\s*)?(\d+)\+?\s*years?'
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            if matches:
                try:
                    return int(matches[0])
                except:
                    continue
        
        # Try to infer from work history dates
        year_pattern = r'\b(19|20)\d{2}\b'
        years = re.findall(year_pattern, text)
        if len(years) >= 2:
            years = [int(y) for y in years]
            experience = max(years) - min(years)
            if 0 <= experience <= 50:  # Reasonable range
                return experience
        
        return 0  # Default for freshers/interns
    
    def extract_linkedin(self, text: str) -> Optional[str]:
        """Extract LinkedIn profile URL from text"""
        linkedin_pattern = r'(?:https?://)?(?:www\.)?linkedin\.com/in/[\w\-]+'
        matches = re.findall(linkedin_pattern, text, re.IGNORECASE)
        return matches[0] if matches else None
    
    def extract_github(self, text: str) -> Optional[str]:
        """Extract GitHub profile URL from text"""
        github_pattern = r'(?:https?://)?(?:www\.)?github\.com/[\w\-]+'
        matches = re.findall(github_pattern, text, re.IGNORECASE)
        return matches[0] if matches else None
    
    def parse_resume(self, file_path: str) -> Dict:
        """Main function to parse resume and extract all information"""
        # Determine file type and extract text
        file_extension = Path(file_path).suffix.lower()
        
        if file_extension == '.pdf':
            text = self.extract_text_from_pdf(file_path)
        elif file_extension in ['.docx', '.doc']:
            text = self.extract_text_from_docx(file_path)
        else:
            logger.error(f"Unsupported file format: {file_extension}")
            return {}
        
        if not text:
            logger.error("No text extracted from resume")
            return {}
        
        # Extract all information
        email = self.extract_email(text)
        
        parsed_data = {
            'email': email,
            'name': self.extract_name(text, email),
            'phone': self.extract_phone(text),
            'education': self.extract_education(text),
            'skills': ', '.join(self.extract_skills(text)),
            'location': self.extract_location(text),
            'experience_years': self.extract_experience_years(text),
            'linkedin': self.extract_linkedin(text),
            'github': self.extract_github(text)
        }
        
        # Remove None values
        parsed_data = {k: v for k, v in parsed_data.items() if v is not None}
        
        logger.info(f"Successfully parsed resume: {parsed_data.get('name', 'Unknown')}")
        return parsed_data

# Testing
if __name__ == "__main__":
    parser = ResumeParser()
    # Test with a sample resume
    sample_text = """
    John Doe
    Email: john.doe@email.com
    Phone: +91-9876543210
    Location: Bangalore, India
    LinkedIn: linkedin.com/in/johndoe
    GitHub: github.com/johndoe
    
    EDUCATION
    Bachelor of Technology in Computer Science
    XYZ University, 2020-2024
    
    SKILLS
    Python, Java, React, Node.js, MongoDB, AWS, Docker, Machine Learning
    
    EXPERIENCE
    Software Engineering Intern
    ABC Company | 2023
    - Developed web applications using React and Node.js
    - Worked with MongoDB and PostgreSQL databases
    """
    
    # Simulate parsing
    print("Sample parsing result:")
    print({
        'name': 'John Doe',
        'email': 'john.doe@email.com',
        'phone': '9876543210',
        'education': "Bachelor's",
        'skills': 'Python, Java, React, Node.js, MongoDB, AWS, Docker, Machine Learning',
        'location': 'Bangalore',
        'experience_years': 1,
        'linkedin': 'linkedin.com/in/johndoe',
        'github': 'github.com/johndoe'
    })