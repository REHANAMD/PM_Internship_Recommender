"""
Authentication Module - JWT-based authentication system
"""
import jwt
import bcrypt
from datetime import datetime, timedelta
from typing import Dict, Optional, Tuple
import logging
from database import Database
from utils import Utils

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class AuthManager:
    def __init__(self, secret_key: str = None):
        """Initialize authentication manager"""
        self.secret_key = secret_key or "your-secret-key-change-in-production-2024"
        self.algorithm = "HS256"
        self.token_expiry_hours = 24
        self.db = Database()
    
    def hash_password_bcrypt(self, password: str) -> str:
        """Hash password using bcrypt"""
        salt = bcrypt.gensalt()
        hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
        return hashed.decode('utf-8')
    
    def verify_password_bcrypt(self, password: str, hashed: str) -> bool:
        """Verify password against bcrypt hash"""
        return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))
    
    def generate_token(self, user_id: int, email: str) -> str:
        """Generate JWT token for authenticated user"""
        payload = {
            'user_id': user_id,
            'email': email,
            'exp': datetime.utcnow() + timedelta(hours=self.token_expiry_hours),
            'iat': datetime.utcnow()
        }
        
        token = jwt.encode(payload, self.secret_key, algorithm=self.algorithm)
        logger.info(f"Generated token for user {email}")
        return token
    
    def verify_token(self, token: str) -> Optional[Dict]:
        """Verify and decode JWT token"""
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            return payload
        except jwt.ExpiredSignatureError:
            logger.warning("Token has expired")
            return None
        except jwt.InvalidTokenError as e:
            logger.warning(f"Invalid token: {e}")
            return None
    
    def register_user(self, user_data: Dict) -> Tuple[bool, str, Optional[int]]:
        """Register a new user"""
        # Validate required fields
        required_fields = ['email', 'password', 'name']
        for field in required_fields:
            if field not in user_data or not user_data[field]:
                return False, f"Missing required field: {field}", None
        
        # Validate email format
        if not Utils.validate_email(user_data['email']):
            return False, "Invalid email format", None
        
        # Check if user already exists
        existing_user = self.db.get_candidate(email=user_data['email'])
        if existing_user:
            return False, "User with this email already exists", None
        
        # Validate password strength
        password = user_data['password']
        if len(password) < 6:
            return False, "Password must be at least 6 characters long", None
        
        # Hash password
        user_data['password_hash'] = self.hash_password_bcrypt(password)
        del user_data['password']  # Remove plain password
        
        # Validate optional fields
        if 'phone' in user_data and user_data['phone']:
            if not Utils.validate_phone(user_data['phone']):
                return False, "Invalid phone number format", None
        
        # Sanitize inputs
        for field in ['name', 'education', 'skills', 'location']:
            if field in user_data:
                user_data[field] = Utils.sanitize_input(user_data[field])
        
        # Add user to database
        user_id = self.db.add_candidate(user_data)
        
        if user_id:
            logger.info(f"Successfully registered user: {user_data['email']}")
            return True, "Registration successful", user_id
        else:
            return False, "Failed to register user", None
    
    def login_user(self, email: str, password: str) -> Tuple[bool, str, Optional[str], Optional[Dict]]:
        """Authenticate user and return token"""
        # Validate email format
        if not Utils.validate_email(email):
            return False, "Invalid email format", None, None
        
        # Get user from database
        user = self.db.get_candidate(email=email)
        
        if not user:
            return False, "User not found", None, None
        
        # Verify password
        if not self.verify_password_bcrypt(password, user['password_hash']):
            return False, "Invalid password", None, None
        
        # Generate token
        token = self.generate_token(user['id'], user['email'])
        
        # Remove sensitive data from user object
        user_data = {
            'id': user['id'],
            'email': user['email'],
            'name': user['name'],
            'education': user.get('education'),
            'skills': user.get('skills'),
            'location': user.get('location'),
            'experience_years': user.get('experience_years', 0),
            'phone': user.get('phone'),
            'linkedin': user.get('linkedin'),
            'github': user.get('github')
        }
        
        logger.info(f"User {email} logged in successfully")
        return True, "Login successful", token, user_data
    
    def update_password(self, user_id: int, old_password: str, new_password: str) -> Tuple[bool, str]:
        """Update user password"""
        # Get user from database
        user = self.db.get_candidate(candidate_id=user_id)
        
        if not user:
            return False, "User not found"
        
        # Verify old password
        if not self.verify_password_bcrypt(old_password, user['password_hash']):
            return False, "Invalid current password"
        
        # Validate new password
        if len(new_password) < 6:
            return False, "New password must be at least 6 characters long"
        
        # Hash new password
        new_password_hash = self.hash_password_bcrypt(new_password)
        
        # Update in database
        success = self.db.update_candidate(user_id, {'password_hash': new_password_hash})
        
        if success:
            logger.info(f"Password updated for user {user_id}")
            return True, "Password updated successfully"
        else:
            return False, "Failed to update password"
    
    def reset_password_request(self, email: str) -> Tuple[bool, str, Optional[str]]:
        """Generate password reset token"""
        # Check if user exists
        user = self.db.get_candidate(email=email)
        
        if not user:
            return False, "User not found", None
        
        # Generate reset token with short expiry
        payload = {
            'user_id': user['id'],
            'email': user['email'],
            'type': 'password_reset',
            'exp': datetime.utcnow() + timedelta(hours=1),
            'iat': datetime.utcnow()
        }
        
        reset_token = jwt.encode(payload, self.secret_key, algorithm=self.algorithm)
        
        logger.info(f"Password reset token generated for {email}")
        return True, "Reset token generated", reset_token
    
    def reset_password_confirm(self, reset_token: str, new_password: str) -> Tuple[bool, str]:
        """Reset password using reset token"""
        # Verify reset token
        try:
            payload = jwt.decode(reset_token, self.secret_key, algorithms=[self.algorithm])
            
            if payload.get('type') != 'password_reset':
                return False, "Invalid reset token"
            
            user_id = payload.get('user_id')
            
        except jwt.ExpiredSignatureError:
            return False, "Reset token has expired"
        except jwt.InvalidTokenError:
            return False, "Invalid reset token"
        
        # Validate new password
        if len(new_password) < 6:
            return False, "Password must be at least 6 characters long"
        
        # Hash new password
        new_password_hash = self.hash_password_bcrypt(new_password)
        
        # Update in database
        success = self.db.update_candidate(user_id, {'password_hash': new_password_hash})
        
        if success:
            logger.info(f"Password reset successful for user {user_id}")
            return True, "Password reset successful"
        else:
            return False, "Failed to reset password"
    
    def get_user_from_token(self, token: str) -> Optional[Dict]:
        """Get user data from token"""
        payload = self.verify_token(token)
        
        if not payload:
            return None
        
        user_id = payload.get('user_id')
        user = self.db.get_candidate(candidate_id=user_id)
        
        if user:
            # Remove sensitive data
            return {
                'id': user['id'],
                'email': user['email'],
                'name': user['name'],
                'education': user.get('education'),
                'skills': user.get('skills'),
                'location': user.get('location'),
                'experience_years': user.get('experience_years', 0),
                'phone': user.get('phone'),
                'linkedin': user.get('linkedin'),
                'github': user.get('github')
            }
        
        return None
    
    def refresh_token(self, old_token: str) -> Optional[str]:
        """Refresh an existing valid token"""
        payload = self.verify_token(old_token)
        
        if not payload:
            return None
        
        # Generate new token with same user data
        new_token = self.generate_token(
            payload.get('user_id'),
            payload.get('email')
        )
        
        logger.info(f"Token refreshed for user {payload.get('email')}")
        return new_token

# Session Manager for maintaining user sessions
class SessionManager:
    def __init__(self):
        """Initialize session manager"""
        self.sessions = {}  # In-memory session store
        self.auth_manager = AuthManager()
    
    def create_session(self, token: str, user_data: Dict) -> str:
        """Create a new session"""
        session_id = Utils.generate_random_string(32)
        self.sessions[session_id] = {
            'token': token,
            'user_data': user_data,
            'created_at': datetime.utcnow(),
            'last_activity': datetime.utcnow()
        }
        return session_id
    
    def get_session(self, session_id: str) -> Optional[Dict]:
        """Get session data"""
        session = self.sessions.get(session_id)
        
        if not session:
            return None
        
        # Check if session is expired (24 hours)
        if datetime.utcnow() - session['created_at'] > timedelta(hours=24):
            del self.sessions[session_id]
            return None
        
        # Update last activity
        session['last_activity'] = datetime.utcnow()
        
        # Verify token is still valid
        if not self.auth_manager.verify_token(session['token']):
            del self.sessions[session_id]
            return None
        
        return session
    
    def destroy_session(self, session_id: str) -> bool:
        """Destroy a session (logout)"""
        if session_id in self.sessions:
            del self.sessions[session_id]
            return True
        return False
    
    def cleanup_expired_sessions(self):
        """Clean up expired sessions"""
        current_time = datetime.utcnow()
        expired_sessions = []
        
        for session_id, session in self.sessions.items():
            if current_time - session['created_at'] > timedelta(hours=24):
                expired_sessions.append(session_id)
        
        for session_id in expired_sessions:
            del self.sessions[session_id]
        
        if expired_sessions:
            logger.info(f"Cleaned up {len(expired_sessions)} expired sessions")

# Testing
if __name__ == "__main__":
    auth = AuthManager()
    
    # Test user registration
    test_user = {
        'email': 'test@example.com',
        'password': 'testpass123',
        'name': 'Test User',
        'education': "Bachelor's",
        'skills': 'Python, Product Management, SQL',
        'location': 'Bangalore',
        'phone': '9876543210'
    }
    
    print("Testing Authentication System:")
    print("-" * 50)
    
    # Register user
    success, message, user_id = auth.register_user(test_user)
    print(f"Registration: {message}")
    
    if success:
        # Test login
        success, message, token, user_data = auth.login_user(
            test_user['email'], 
            test_user['password']
        )
        print(f"Login: {message}")
        
        if success:
            print(f"Token generated: {token[:20]}...")
            print(f"User data: {user_data['name']}")
            
            # Test token verification
            payload = auth.verify_token(token)
            print(f"Token valid: {payload is not None}")
            
            # Test session management
            session_mgr = SessionManager()
            session_id = session_mgr.create_session(token, user_data)
            print(f"Session created: {session_id[:10]}...")
            
            session = session_mgr.get_session(session_id)
            print(f"Session retrieved: {session is not None}")