"""
FastAPI Backend - RESTful API for the recommendation engine
"""
from fastapi import FastAPI, HTTPException, Depends, File, UploadFile, Header
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List, Dict
import os
import shutil
from datetime import datetime
import logging

from database import Database
from resume_parser import ResumeParser
from recommender import RecommendationEngine
from auth import AuthManager
from utils import Utils

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="PM Internship Recommendation Engine API",
    description="API for matching candidates with PM internship opportunities",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify actual origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize components
db = Database()
parser = ResumeParser()
recommender = RecommendationEngine(db)
auth_manager = AuthManager()

# Pydantic models for request/response
class UserRegistration(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=6)
    name: str = Field(..., min_length=2, max_length=100)
    education: Optional[str] = None
    skills: Optional[str] = None
    location: Optional[str] = None
    experience_years: Optional[int] = Field(default=0, ge=0, le=50)
    phone: Optional[str] = None
    linkedin: Optional[str] = None
    github: Optional[str] = None

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class CandidateProfile(BaseModel):
    name: str = Field(..., min_length=2, max_length=100)
    education: Optional[str] = None
    skills: Optional[str] = None
    location: Optional[str] = None
    experience_years: Optional[int] = Field(default=0, ge=0, le=50)
    phone: Optional[str] = None
    linkedin: Optional[str] = None
    github: Optional[str] = None

class CandidateProfileUpdate(CandidateProfile):
    current_password: Optional[str] = None

class PasswordUpdate(BaseModel):
    old_password: str
    new_password: str = Field(..., min_length=6)

class PasswordReset(BaseModel):
    email: EmailStr

class PasswordResetConfirm(BaseModel):
    reset_token: str
    new_password: str = Field(..., min_length=6)

# Dependency to get current user from token
async def get_current_user(authorization: str = Header(None)):
    """Extract and verify user from JWT token"""
    if not authorization:
        raise HTTPException(status_code=401, detail="Authorization header missing")
    
    try:
        # Extract token from "Bearer <token>" format
        token = authorization.split(" ")[1] if " " in authorization else authorization
        user = auth_manager.get_user_from_token(token)
        
        if not user:
            raise HTTPException(status_code=401, detail="Invalid or expired token")
        
        return user
    except Exception as e:
        logger.error(f"Authentication error: {e}")
        raise HTTPException(status_code=401, detail="Authentication failed")

# API Endpoints

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "PM Internship Recommendation Engine API",
        "version": "1.0.0",
        "endpoints": {
            "auth": "/auth/*",
            "candidates": "/candidates/*",
            "internships": "/internships/*",
            "recommendations": "/recommendations/*"
        }
    }

# Authentication endpoints
@app.post("/auth/register")
async def register(user_data: UserRegistration):
    """Register a new user"""
    try:
        success, message, user_id = auth_manager.register_user(user_data.dict())
        
        if success:
            # Auto-login after registration
            _, _, token, user_info = auth_manager.login_user(
                user_data.email, 
                user_data.password
            )
            return {
                "success": True,
                "message": message,
                "user_id": user_id,
                "token": token,
                "user": user_info
            }
        else:
            raise HTTPException(status_code=400, detail=message)
    except HTTPException as exc:
        # Preserve intended HTTP errors (e.g., 400 Already exists)
        raise exc
    except Exception as e:
        logger.error(f"Registration error: {e}")
        raise HTTPException(status_code=500, detail="Registration failed")

@app.post("/auth/login")
async def login(credentials: UserLogin):
    """Login user and return JWT token"""
    try:
        success, message, token, user_data = auth_manager.login_user(
            credentials.email,
            credentials.password
        )
        
        if success:
            return {
                "success": True,
                "message": message,
                "token": token,
                "user": user_data
            }
        else:
            raise HTTPException(status_code=401, detail=message)
    
    except Exception as e:
        logger.error(f"Login error: {e}")
        raise HTTPException(status_code=500, detail="Login failed")

@app.post("/auth/refresh")
async def refresh_token(current_user: dict = Depends(get_current_user)):
    """Refresh JWT token"""
    try:
        # Get current token from header
        authorization = Header()
        token = authorization.split(" ")[1] if " " in authorization else authorization
        
        new_token = auth_manager.refresh_token(token)
        
        if new_token:
            return {
                "success": True,
                "token": new_token
            }
        else:
            raise HTTPException(status_code=401, detail="Failed to refresh token")
    
    except Exception as e:
        logger.error(f"Token refresh error: {e}")
        raise HTTPException(status_code=500, detail="Token refresh failed")

@app.post("/auth/password/update")
async def update_password(
    password_data: PasswordUpdate,
    current_user: dict = Depends(get_current_user)
):
    """Update user password"""
    try:
        success, message = auth_manager.update_password(
            current_user['id'],
            password_data.old_password,
            password_data.new_password
        )
        
        if success:
            return {"success": True, "message": message}
        else:
            raise HTTPException(status_code=400, detail=message)
    
    except Exception as e:
        logger.error(f"Password update error: {e}")
        raise HTTPException(status_code=500, detail="Password update failed")

@app.post("/auth/password/reset")
async def request_password_reset(reset_data: PasswordReset):
    """Request password reset token"""
    try:
        success, message, reset_token = auth_manager.reset_password_request(
            reset_data.email
        )
        
        if success:
            # In production, send this token via email
            return {
                "success": True,
                "message": message,
                "reset_token": reset_token  # Remove in production
            }
        else:
            raise HTTPException(status_code=404, detail=message)
    
    except Exception as e:
        logger.error(f"Password reset request error: {e}")
        raise HTTPException(status_code=500, detail="Password reset request failed")

@app.post("/auth/password/reset/confirm")
async def confirm_password_reset(reset_confirm: PasswordResetConfirm):
    """Confirm password reset with token"""
    try:
        success, message = auth_manager.reset_password_confirm(
            reset_confirm.reset_token,
            reset_confirm.new_password
        )
        
        if success:
            return {"success": True, "message": message}
        else:
            raise HTTPException(status_code=400, detail=message)
    
    except Exception as e:
        logger.error(f"Password reset confirm error: {e}")
        raise HTTPException(status_code=500, detail="Password reset failed")

# Candidate endpoints
@app.get("/candidates/profile")
async def get_profile(current_user: dict = Depends(get_current_user)):
    """Get current user's profile"""
    return {
        "success": True,
        "profile": current_user
    }

@app.put("/candidates/profile")
async def update_profile(
    profile_data: CandidateProfileUpdate,
    current_user: dict = Depends(get_current_user)
):
    """Update user profile"""
    try:
        update_data = profile_data.dict(exclude_unset=True)
        # Enforce password verification for profile updates
        if not update_data.get('current_password'):
            raise HTTPException(status_code=400, detail="Current password is required to update profile")
        # Verify password
        user_record = db.get_candidate(candidate_id=current_user['id'])
        if not user_record:
            raise HTTPException(status_code=404, detail="User not found")
        if not auth_manager.verify_password_bcrypt(update_data['current_password'], user_record['password_hash']):
            raise HTTPException(status_code=401, detail="Invalid current password")
        # Remove auth-only field
        update_data.pop('current_password', None)
        logger.info(f"Updating candidate {current_user['id']} with data: {update_data}")
        success = db.update_candidate(current_user['id'], update_data)
        
        if success:
            # Get updated profile
            updated_user = db.get_candidate(candidate_id=current_user['id'])
            return {
                "success": True,
                "message": "Profile updated successfully",
                "profile": {
                    k: v for k, v in updated_user.items() 
                    if k != 'password_hash'
                }
            }
        else:
            raise HTTPException(status_code=400, detail="Failed to update profile")
    
    except Exception as e:
        logger.error(f"Profile update error: {e}")
        raise HTTPException(status_code=500, detail="Profile update failed")

@app.post("/candidates/upload_resume")
async def upload_resume(
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user)
):
    """Upload and parse resume"""
    try:
        # Validate file type
        allowed_extensions = ['.pdf', '.docx', '.doc']
        file_extension = os.path.splitext(file.filename)[1].lower()
        
        if file_extension not in allowed_extensions:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid file type. Allowed: {', '.join(allowed_extensions)}"
            )
        
        # Save uploaded file temporarily
        temp_path = f"temp_{current_user['id']}_{file.filename}"
        with open(temp_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        # Parse resume
        parsed_data = parser.parse_resume(temp_path)
        
        # Clean up temp file
        os.remove(temp_path)
        
        if not parsed_data:
            raise HTTPException(status_code=400, detail="Failed to parse resume")
        
        # Don't override email from resume
        if 'email' in parsed_data:
            del parsed_data['email']
        
        return {
            "success": True,
            "message": "Resume parsed successfully",
            "parsed_data": parsed_data
        }
    
    except Exception as e:
        logger.error(f"Resume upload error: {e}")
        # Clean up temp file if it exists
        if 'temp_path' in locals() and os.path.exists(temp_path):
            os.remove(temp_path)
        raise HTTPException(status_code=500, detail="Resume processing failed")

# Public resume parse for signup auto-fill (no auth required)
@app.post("/parse_resume")
async def parse_resume_public(file: UploadFile = File(...)):
    """Parse resume without authentication for signup auto-fill"""
    try:
        # Validate file type
        allowed_extensions = ['.pdf', '.docx', '.doc']
        file_extension = os.path.splitext(file.filename)[1].lower()
        if file_extension not in allowed_extensions:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid file type. Allowed: {', '.join(allowed_extensions)}"
            )

        temp_path = f"temp_signup_{file.filename}"
        with open(temp_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        parsed_data = parser.parse_resume(temp_path)

        # Clean up temp file
        if os.path.exists(temp_path):
            os.remove(temp_path)

        if not parsed_data:
            raise HTTPException(status_code=400, detail="Failed to parse resume")

        return {
            "success": True,
            "message": "Resume parsed successfully",
            "parsed_data": parsed_data
        }
    except Exception as e:
        logger.error(f"Public resume parse error: {e}")
        # Cleanup just in case
        try:
            if 'temp_path' in locals() and os.path.exists(temp_path):
                os.remove(temp_path)
        except Exception:
            pass
        raise HTTPException(status_code=500, detail="Resume processing failed")

# Internship endpoints
@app.get("/internships")
async def get_internships(
    limit: int = 20,
    offset: int = 0
):
    """Get list of all internships"""
    try:
        internships = db.get_all_internships(active_only=True)
        
        # Apply pagination
        paginated = internships[offset:offset + limit]
        
        return {
            "success": True,
            "total": len(internships),
            "limit": limit,
            "offset": offset,
            "internships": paginated
        }
    
    except Exception as e:
        logger.error(f"Get internships error: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch internships")

@app.get("/internships/{internship_id}")
async def get_internship(internship_id: int):
    """Get specific internship details"""
    try:
        internship = db.get_internship(internship_id)
        
        if internship:
            return {
                "success": True,
                "internship": internship
            }
        else:
            raise HTTPException(status_code=404, detail="Internship not found")
    
    except Exception as e:
        logger.error(f"Get internship error: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch internship")

# Recommendation endpoints
@app.get("/recommendations")
async def get_recommendations(
    current_user: dict = Depends(get_current_user),
    limit: int = 5,
    use_cache: bool = True
):
    """Get personalized internship recommendations"""
    try:
        recommendations = recommender.get_recommendations(
            current_user['id'],
            top_n=limit,
            use_cache=use_cache
        )
        
        # Format recommendations for response
        formatted_recommendations = [
            Utils.format_recommendation_card(rec) 
            for rec in recommendations
        ]
        
        # Check which ones are saved
        for rec in formatted_recommendations:
            rec['is_saved'] = db.is_internship_saved(
                current_user['id'], 
                rec.get('internship_id', 0)
            )
        
        return {
            "success": True,
            "count": len(formatted_recommendations),
            "recommendations": formatted_recommendations
        }
    
    except Exception as e:
        logger.error(f"Get recommendations error: {e}")
        raise HTTPException(status_code=500, detail="Failed to generate recommendations")

@app.post("/internships/{internship_id}/save")
async def save_internship(
    internship_id: int,
    current_user: dict = Depends(get_current_user)
):
    """Save an internship to user's list"""
    try:
        success = db.save_internship(current_user['id'], internship_id)
        
        if success:
            return {
                "success": True,
                "message": "Internship saved successfully"
            }
        else:
            return {
                "success": False,
                "message": "Internship already saved"
            }
    
    except Exception as e:
        logger.error(f"Save internship error: {e}")
        raise HTTPException(status_code=500, detail="Failed to save internship")

@app.delete("/internships/{internship_id}/save")
async def unsave_internship(
    internship_id: int,
    current_user: dict = Depends(get_current_user)
):
    """Remove internship from user's saved list"""
    try:
        success = db.unsave_internship(current_user['id'], internship_id)
        
        if success:
            return {
                "success": True,
                "message": "Internship removed from saved list"
            }
        else:
            return {
                "success": False,
                "message": "Internship not in saved list"
            }
    
    except Exception as e:
        logger.error(f"Unsave internship error: {e}")
        raise HTTPException(status_code=500, detail="Failed to unsave internship")

@app.get("/saved-internships")
async def get_saved_internships(
    current_user: dict = Depends(get_current_user)
):
    """Get all saved internships for current user"""
    try:
        saved = db.get_saved_internships(current_user['id'])
        
        return {
            "success": True,
            "count": len(saved),
            "internships": saved
        }
    
    except Exception as e:
        logger.error(f"Get saved internships error: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch saved internships")

@app.get("/recommendations/{candidate_id}")
async def get_recommendations_for_candidate(
    candidate_id: int,
    limit: int = 5,
    current_user: dict = Depends(get_current_user)
):
    """Get recommendations for specific candidate (admin feature)"""
    try:
        # In production, check if current user has admin privileges
        recommendations = recommender.get_recommendations(
            candidate_id,
            top_n=limit,
            use_cache=False
        )
        
        return {
            "success": True,
            "candidate_id": candidate_id,
            "count": len(recommendations),
            "recommendations": recommendations
        }
    
    except Exception as e:
        logger.error(f"Get candidate recommendations error: {e}")
        raise HTTPException(status_code=500, detail="Failed to generate recommendations")

# Utility endpoints
@app.post("/seed_data")
async def seed_data():
    """Seed database with sample data (development only)"""
    try:
        # Create sample data files
        Utils.create_sample_files()
        
        # Seed internships
        success = db.seed_internships("data/internships.json")
        
        if success:
            return {
                "success": True,
                "message": "Database seeded successfully"
            }
        else:
            raise HTTPException(status_code=500, detail="Failed to seed database")
    
    except Exception as e:
        logger.error(f"Seed data error: {e}")
        raise HTTPException(status_code=500, detail="Database seeding failed")

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat()
    }

# Run the application
if __name__ == "__main__":
    import uvicorn
    
    # Initialize database and seed data
    db.init_db()
    Utils.create_sample_files()
    db.seed_internships("data/internships.json")
    
    # Run server
    uvicorn.run(
        "api:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
    