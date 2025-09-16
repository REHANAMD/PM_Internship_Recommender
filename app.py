"""
Streamlit Frontend - Interactive UI for PM Internship Recommendation Engine
"""
import streamlit as st
import requests
import json
from typing import Dict, List, Optional
import pandas as pd
from datetime import datetime
import os

# Configuration
API_BASE_URL = "http://localhost:8000"

# Page configuration
st.set_page_config(
    page_title="PM Internship Recommender",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for better UI
st.markdown("""
<style>
    .main {
        padding: 0rem 1rem;
    }
    .stButton button {
        width: 100%;
        border-radius: 6px;
        margin: 6px 0;
    }
    .stButton button[kind="primary"] {
        background-color: #4CAF50;
        color: white;
    }
    /* Removed overly-broad column button override to prevent stray UI artifacts */
    .recommendation-card {
        background-color: #f0f2f5;
        border-radius: 10px;
        padding: 20px;
        margin: 10px 0;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
    .skill-badge {
        display: inline-block;
        background-color: #e3f2fd;
        color: #1976d2;
        padding: 4px 12px;
        border-radius: 15px;
        margin: 2px;
        font-size: 0.85em;
    }
    .skill-gap-badge {
        display: inline-block;
        background-color: #fff3e0;
        color: #f57c00;
        padding: 4px 12px;
        border-radius: 15px;
        margin: 2px;
        font-size: 0.85em;
    }
    .match-score-high {
        color: #4CAF50;
        font-weight: bold;
    }
    .match-score-medium {
        color: #FFC107;
        font-weight: bold;
    }
    .match-score-low {
        color: #f44336;
        font-weight: bold;
    }
    div[data-testid="stSidebar"] > div {
        padding-bottom: 100px;
    }
    .match-box {
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        width: 120px;
        min-width: 120px;
        height: 120px;
        border-radius: 18px;
        background: #ffffff;
        box-shadow: 0 2px 4px rgba(0,0,0,0.08);
        border: 1px solid #e6e6e6;
    }
    .match-box .percent {
        font-size: 34px;
        font-weight: 800;
        line-height: 1;
        margin-bottom: 6px;
    }
    .match-box .label {
        font-size: 14px;
        color: #666666;
    }
    .match-box.high { border-left: 6px solid #4CAF50; }
    .match-box.medium { border-left: 6px solid #FFC107; }
    .match-box.low { border-left: 6px solid #f44336; }
    /* Sidebar cards */
    .sidebar-card {
        background: #ffffff;
        border: 1px solid #e6e6e6;
        border-radius: 12px;
        padding: 12px 14px;
        box-shadow: 0 1px 2px rgba(0,0,0,0.04);
        margin: 10px 8px;
    }
    .profile-card-title {
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: 8px;
    }
    .stat-row {
        display: grid;
        grid-template-columns: 1fr 1fr;
        gap: 8px;
        margin-top: 2px;
    }
    .stat-card {
        background: #f8fafc;
        border: 1px solid #e8eef5;
        border-radius: 10px;
        padding: 10px 12px;
        text-align: left;
    }
    .stat-label {
        font-size: 12px;
        color: #667085;
        margin-bottom: 4px;
    }
    .stat-number {
        font-size: 20px;
        font-weight: 800;
        color: #111827;
    }
</style>
""", unsafe_allow_html=True)

# Session state initialization
if 'token' not in st.session_state:
    st.session_state.token = None
if 'user' not in st.session_state:
    st.session_state.user = None
if 'page' not in st.session_state:
    st.session_state.page = 'login'
if 'recommendations' not in st.session_state:
    st.session_state.recommendations = None
if 'parsed_resume' not in st.session_state:
    st.session_state.parsed_resume = None
# Signup autofill session keys
if 'signup_name' not in st.session_state:
    st.session_state.signup_name = ''
if 'signup_education' not in st.session_state:
    st.session_state.signup_education = ''
if 'signup_location' not in st.session_state:
    st.session_state.signup_location = ''
if 'signup_phone' not in st.session_state:
    st.session_state.signup_phone = ''
if 'signup_skills' not in st.session_state:
    st.session_state.signup_skills = ''
if 'signup_email' not in st.session_state:
    st.session_state.signup_email = ''
if 'signup_linkedin' not in st.session_state:
    st.session_state.signup_linkedin = ''
if 'signup_github' not in st.session_state:
    st.session_state.signup_github = ''

# Helper functions
def make_api_request(endpoint: str, method: str = "GET", data: Dict = None, files=None, headers: Dict = None):
    """Make API request with error handling"""
    url = f"{API_BASE_URL}{endpoint}"
    
    try:
        if method == "GET":
            response = requests.get(url, headers=headers)
        elif method == "POST":
            if files:
                response = requests.post(url, data=data, files=files, headers=headers)
            else:
                response = requests.post(url, json=data, headers=headers)
        elif method == "PUT":
            response = requests.put(url, json=data, headers=headers)
        elif method == "DELETE":
            response = requests.delete(url, headers=headers)
        else:
            return None
        
        if response.status_code == 200:
            return response.json()
        else:
            try:
                payload = response.json()
            except Exception:
                payload = {"detail": response.text}
            # Return structured error to caller so it can handle flow (e.g., switch to login)
            return {"status_code": response.status_code, **payload}
    except Exception as e:
        st.error(f"Connection error: {str(e)}")
        return None

def get_auth_headers():
    """Get authorization headers with token"""
    if st.session_state.token:
        return {"Authorization": f"Bearer {st.session_state.token}"}
    return {}

def save_internship(internship_id: int) -> bool:
    """Mark an internship as interested via API"""
    result = make_api_request(
        f"/internships/{internship_id}/save",
        method="POST",
        headers=get_auth_headers()
    )
    return bool(result and result.get("success"))

def unsave_internship(internship_id: int) -> bool:
    """Remove interested mark via API"""
    result = make_api_request(
        f"/internships/{internship_id}/save",
        method="DELETE",
        headers=get_auth_headers()
    )
    return bool(result and result.get("success"))

def login_page():
    """Login/Registration page"""
    st.title("🎯 PM Internship Recommendation Engine")
    st.markdown("### Find your perfect Product Management internship!")
    
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        # If we need to force-show login view (e.g., after signup detects existing user)
        if st.session_state.get('force_show_login', False):
            st.warning("User already exists. Please log in.")
            with st.form("login_form_forced"):
                default_login_email = st.session_state.get('prefill_login_email', '')
                email = st.text_input("Email", value=default_login_email, placeholder="your@email.com")
                password = st.text_input("Password", type="password")
                if st.form_submit_button("Login", type="primary"):
                    if email and password:
                        result = make_api_request(
                            "/auth/login",
                            method="POST",
                            data={"email": email, "password": password}
                        )
                        if result and result.get('success'):
                            st.session_state.token = result['token']
                            st.session_state.user = result['user']
                            st.session_state.page = 'dashboard'
                            st.session_state.prefill_login_email = ''
                            st.session_state.force_show_login = False
                            st.success("Login successful!")
                            st.rerun()
                    else:
                        st.error("Please enter both email and password")
            # Do not render tabs when forced view is active
            return
        
        tab1, tab2 = st.tabs(["Login", "Sign Up"])
        
        with tab1:
            st.markdown("#### Welcome Back!")
            with st.form("login_form"):
                # Optional prefill from signup redirect
                default_login_email = st.session_state.get('prefill_login_email', '')
                email = st.text_input("Email", value=default_login_email, placeholder="your@email.com")
                password = st.text_input("Password", type="password")
                
                if st.form_submit_button("Login", type="primary"):
                    if email and password:
                        result = make_api_request(
                            "/auth/login",
                            method="POST",
                            data={"email": email, "password": password}
                        )
                        
                        if result and result.get('success'):
                            st.session_state.token = result['token']
                            st.session_state.user = result['user']
                            st.session_state.page = 'dashboard'
                            st.success("Login successful!")
                            # Clear prefill once used
                            st.session_state.prefill_login_email = ''
                            st.rerun()
                    else:
                        st.error("Please enter both email and password")
        
        with tab2:
            st.markdown("#### Create Your Account")
            
            # Resume upload section at the top
            st.markdown("##### 📄 Auto-fill with Resume (Optional)")
            uploaded_file = st.file_uploader(
                "Upload Resume to Auto-fill (PDF/DOC/DOCX)",
                type=['pdf', 'docx', 'doc'],
                help="Upload your resume to automatically fill the form below"
            )
            
            if uploaded_file and st.button("🔍 Parse Resume & Auto-fill", type="primary"):
                with st.spinner("Parsing your resume..."):
                    files = {'file': (uploaded_file.name, uploaded_file, uploaded_file.type)}
                    result = make_api_request("/parse_resume", method="POST", files=files)
                    
                    if result and result.get('success'):
                        parsed_data = result['parsed_data']
                        # Update session state with parsed data
                        st.session_state.signup_name = parsed_data.get('name', '')
                        st.session_state.signup_email = parsed_data.get('email', '')
                        st.session_state.signup_education = parsed_data.get('education', '')
                        st.session_state.signup_location = parsed_data.get('location', '')
                        st.session_state.signup_phone = parsed_data.get('phone', '')
                        st.session_state.signup_skills = parsed_data.get('skills', '')
                        st.session_state.signup_linkedin = parsed_data.get('linkedin', '')
                        st.session_state.signup_github = parsed_data.get('github', '')
                        st.success("✅ Resume parsed successfully! Form has been auto-filled below.")
                        st.rerun()
                    else:
                        st.error("❌ Failed to parse resume. Please try again or fill manually.")
            
            st.divider()
            
            with st.form("signup_form"):
                col1, col2 = st.columns(2)
                
                with col1:
                    name = st.text_input("Full Name*", value=st.session_state.signup_name, placeholder="John Doe")
                    email = st.text_input("Email*", value=st.session_state.signup_email, placeholder="your@email.com")
                    password = st.text_input("Password*", type="password", help="Minimum 6 characters")
                
                with col2:
                    education = st.selectbox(
                        "Education",
                        ["", "High School", "Diploma", "Bachelor's", "Master's", "PhD"],
                        index=["", "High School", "Diploma", "Bachelor's", "Master's", "PhD"].index(st.session_state.signup_education)
                        if st.session_state.signup_education in ["", "High School", "Diploma", "Bachelor's", "Master's", "PhD"] else 0
                    )
                    location = st.text_input("Location", value=st.session_state.signup_location, placeholder="e.g., Bangalore")
                    phone = st.text_input("Phone", value=st.session_state.signup_phone, placeholder="9876543210")
                
                skills = st.text_area(
                    "Skills (comma-separated)",
                    value=st.session_state.signup_skills,
                    placeholder="e.g., Product Management, SQL, Python, JIRA, Analytics",
                    height=100
                )
                
                experience = st.slider("Years of Experience", 0, 10, 0)
                
                col1, col2 = st.columns(2)
                with col1:
                    linkedin = st.text_input("LinkedIn Profile (optional)", value=st.session_state.signup_linkedin, placeholder="linkedin.com/in/yourprofile")
                with col2:
                    github = st.text_input("GitHub Profile (optional)", value=st.session_state.signup_github, placeholder="github.com/yourprofile")
                

                if st.form_submit_button("Sign Up", type="primary"):
                    if name and email and password:
                        if len(password) < 6:
                            st.error("Password must be at least 6 characters long")
                        else:
                            user_data = {
                                "name": name,
                                "email": email,
                                "password": password,
                                "education": education if education else None,
                                "skills": skills if skills else None,
                                "location": location if location else None,
                                "experience_years": experience,
                                "phone": phone if phone else None,
                                "linkedin": linkedin if linkedin else None,
                                "github": github if github else None
                            }
                            
                            result = make_api_request(
                                "/auth/register",
                                method="POST",
                                data=user_data
                            )
                            
                            if result and result.get('success'):
                                st.session_state.token = result['token']
                                st.session_state.user = result['user']
                                st.session_state.page = 'dashboard'
                                st.success("Registration successful! Welcome aboard!")
                                st.rerun()
                            else:
                                # Handle structured error
                                status = result.get('status_code') if isinstance(result, dict) else None
                                detail = result.get('detail') if isinstance(result, dict) else None
                                if status == 400 and detail and 'already exists' in str(detail).lower():
                                    # Blank out signup form state
                                    st.session_state.signup_name = ''
                                    st.session_state.signup_email = ''
                                    st.session_state.signup_linkedin = ''
                                    st.session_state.signup_github = ''
                                    st.session_state.signup_location = ''
                                    st.session_state.signup_phone = ''
                                    st.session_state.signup_skills = ''
                                    # Switch to login with prefilled email and a visible warning
                                    st.session_state.prefill_login_email = email
                                    st.session_state.force_show_login = True
                                    st.experimental_set_query_params(view="login")
                                    st.rerun()
                                else:
                                    st.error("Registration failed. Please try again.")
                    else:
                        st.error("Please fill in all required fields (marked with *)")

def dashboard_page():
    """Main dashboard with profile and recommendations"""
    # Sidebar (reverted to original simple layout)
    with st.sidebar:
        # User section with inline edit button
        user_container = st.container()
        with user_container:
            col1, col2 = st.columns([5, 1])
            with col1:
                st.markdown(f"## 👤 {st.session_state.user['name']}")
            with col2:
                # Small edit button with just icon
                if st.button("✏️", key="edit_profile", help="Edit Profile"):
                    st.session_state.page = 'profile'
                    st.rerun()
            
            st.markdown(f"📧 {st.session_state.user['email']}")
        
        st.markdown("---")
        
        # Main action button
        if st.button("🔍 **Get Recommendations**", key="get_rec", type="primary", use_container_width=True):
            fetch_recommendations()
        
        st.markdown("---")
        
        # View interests button
        if st.button("💚 **View Interests**", key="view_saved", use_container_width=True):
            fetch_saved_internships()
        
        st.markdown("---")
        
        # Stats section
        st.markdown("### 📊 Your Stats")
        
        col1, col2 = st.columns(2)
        with col1:
            skills_count = len(st.session_state.user.get('skills', '').split(',')) if st.session_state.user.get('skills') else 0
            st.metric("Skills", skills_count)
        with col2:
            exp_years = st.session_state.user.get('experience_years', 0)
            st.metric("Experience", f"{exp_years} yrs")
        
        location = st.session_state.user.get('location', 'Not set')
        st.metric("📍 Location", location)
        
        # Add space before logout
        st.markdown("<br>" * 15, unsafe_allow_html=True)
        
        # Logout button at the bottom
        st.markdown("---")
        logout_container = st.container()
        with logout_container:
            if st.button("🚪 **Logout**", key="logout_btn", use_container_width=True):
                st.session_state.token = None
                st.session_state.user = None
                st.session_state.page = 'login'
                st.session_state.recommendations = None
                # Clear all signup form fields
                st.session_state.signup_name = ''
                st.session_state.signup_education = ''
                st.session_state.signup_location = ''
                st.session_state.signup_phone = ''
                st.session_state.signup_skills = ''
                st.session_state.signup_email = ''
                st.session_state.signup_linkedin = ''
                st.session_state.signup_github = ''
                st.rerun()
    
    # Main content area
    st.title("🎯 Your PM Internship Dashboard")
    
    # Welcome message
    hour = datetime.now().hour
    greeting = "Good morning" if hour < 12 else "Good afternoon" if hour < 17 else "Good evening"
    st.markdown(f"### {greeting}, {st.session_state.user['name']}! 👋")
    
    # Quick actions bar
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.info(f"**Profile:** {st.session_state.user.get('education', 'Not set')}")
    with col2:
        st.info(f"**Location:** {st.session_state.user.get('location', 'Not set')}")
    with col3:
        skills_count = len(st.session_state.user.get('skills', '').split(',')) if st.session_state.user.get('skills') else 0
        st.info(f"**Skills:** {skills_count}")
    with col4:
        st.info(f"**Experience:** {st.session_state.user.get('experience_years', 0)} years")
    
    # Recommendations section
    st.markdown("## 📋 Your Personalized Recommendations")
    
    if st.session_state.recommendations:
        display_recommendations(st.session_state.recommendations)
    else:
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            st.info("👆 Click 'Get Recommendations' in the sidebar to see your personalized internship matches!")
            if st.session_state.get('profile_updated', False):
                st.success("✨ Your profile was recently updated! Get fresh recommendations based on your new information.")

def profile_page():
    """Profile update page with resume upload"""
    # Back button at top
    if st.button("← Back to Dashboard"):
        st.session_state.page = 'dashboard'
        st.rerun()
    
    st.title("📝 Update Your Profile")
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.markdown("### Profile Information")
        
        # Resume upload section
        with st.expander("📄 Auto-fill with Resume", expanded=False):
            uploaded_file = st.file_uploader(
                "Upload your resume (PDF or Word)",
                type=['pdf', 'docx', 'doc'],
                help="Upload your resume to automatically fill the form"
            )
            
            if uploaded_file is not None:
                if st.button("Parse Resume", type="primary"):
                    with st.spinner("Parsing your resume..."):
                        files = {'file': (uploaded_file.name, uploaded_file, uploaded_file.type)}
                        
                        result = make_api_request(
                            "/candidates/upload_resume",
                            method="POST",
                            files=files,
                            headers=get_auth_headers()
                        )
                        
                        if result and result.get('success'):
                            st.session_state.parsed_resume = result['parsed_data']
                            # Immediately reflect parsed values into widget state so they show up after rerun
                            merged = {**(st.session_state.user or {}), **st.session_state.parsed_resume}
                            st.session_state['prof_name'] = merged.get('name', '')
                            st.session_state['prof_education'] = merged.get('education', "Bachelor's")
                            st.session_state['prof_location'] = merged.get('location', '')
                            st.session_state['prof_phone'] = merged.get('phone', '')
                            st.session_state['prof_experience'] = merged.get('experience_years', 0)
                            st.session_state['prof_skills'] = merged.get('skills', '')
                            st.session_state['prof_linkedin'] = merged.get('linkedin', '')
                            st.session_state['prof_github'] = merged.get('github', '')
                            st.success("Resume parsed successfully! Form has been auto-filled.")
                            st.rerun()
        
        # Profile form
        form_key = f"profile_form_{st.session_state.get('form_counter', 0)}"
        with st.form(form_key):
            # Pre-fill with parsed resume data or existing user data
            if st.session_state.parsed_resume:
                default_data = {**st.session_state.user, **st.session_state.parsed_resume}
                st.session_state.parsed_resume = None
            else:
                # Use the most up-to-date profile data
                default_data = st.session_state.profile_data if 'profile_data' in st.session_state else st.session_state.user
            
            # Initialize widget-bound session state once per form version
            form_version = st.session_state.get('form_counter', 0)
            if st.session_state.get('profile_form_version') != form_version:
                st.session_state['prof_name'] = default_data.get('name', '')
                st.session_state['prof_education'] = default_data.get('education', "Bachelor's")
                st.session_state['prof_location'] = default_data.get('location', '')
                st.session_state['prof_phone'] = default_data.get('phone', '')
                st.session_state['prof_experience'] = default_data.get('experience_years', 0)
                st.session_state['prof_skills'] = default_data.get('skills', '')
                st.session_state['prof_linkedin'] = default_data.get('linkedin', '')
                st.session_state['prof_github'] = default_data.get('github', '')
                st.session_state['prof_current_password'] = ''
                st.session_state['profile_form_version'] = form_version
            
            col1, col2 = st.columns(2)
            
            with col1:
                name = st.text_input("Full Name", key="prof_name")
                education = st.selectbox(
                    "Education",
                    ["High School", "Diploma", "Bachelor's", "Master's", "PhD"],
                    index=["High School", "Diploma", "Bachelor's", "Master's", "PhD"].index(
                        st.session_state.get('prof_education', "Bachelor's")
                    ) if st.session_state.get('prof_education', "Bachelor's") in ["High School", "Diploma", "Bachelor's", "Master's", "PhD"] else 2,
                    key="prof_education"
                )
                location = st.text_input("Location", key="prof_location")
            
            with col2:
                phone = st.text_input("Phone", key="prof_phone")
                experience = st.number_input(
                    "Years of Experience",
                    min_value=0,
                    max_value=50,
                    value=st.session_state.get('prof_experience', 0),
                    key="prof_experience"
                )
            
            skills = st.text_area(
                "Skills (comma-separated)",
                value=st.session_state.get('prof_skills', ''),
                height=150,
                help="Enter your skills separated by commas",
                key="prof_skills"
            )
            
            col1, col2 = st.columns(2)
            with col1:
                linkedin = st.text_input(
                    "LinkedIn Profile",
                    key="prof_linkedin"
                )
            with col2:
                github = st.text_input(
                    "GitHub Profile",
                    key="prof_github"
                )
            
            col1, col2, col3 = st.columns(3)
            with col2:
                current_password = st.text_input("Confirm Password", type="password", key="prof_current_password")
                if st.form_submit_button("💾 Save Profile", type="primary", use_container_width=True):
                    profile_data = {
                        "name": name,
                        "education": education,
                        "skills": skills,
                        "location": location,
                        "experience_years": experience,
                        "phone": phone,
                        "linkedin": linkedin,
                        "github": github,
                        "current_password": current_password
                    }
                    
                    result = make_api_request(
                        "/candidates/profile",
                        method="PUT",
                        data=profile_data,
                        headers=get_auth_headers()
                    )
                    
                    if result and result.get('success'):
                        # Update session state with the new profile data
                        st.session_state.user = result['profile']
                        st.session_state.profile_data = result['profile']
                        # Clear recommendations since profile changed
                        st.session_state.recommendations = []
                        # Set flag to show profile update message
                        st.session_state.profile_updated = True
                        # Increment form counter to clear and reinitialize widgets next run
                        st.session_state.form_counter = st.session_state.get('form_counter', 0) + 1
                        st.success("Profile updated successfully! Recommendations will be recalculated.")
                        # Clear the form by rerunning
                        st.rerun()
                    else:
                        detail = result.get('detail') if isinstance(result, dict) else None
                        if detail:
                            st.error(detail)
                        else:
                            st.error("Failed to update profile. Please try again.")
    
    with col2:
        st.markdown("### Profile Preview")
        preview_container = st.container()
        with preview_container:
            st.info(f"**Name:** {name if 'name' in locals() else default_data.get('name', 'Not set')}")
            st.info(f"**Education:** {education if 'education' in locals() else default_data.get('education', 'Not set')}")
            st.info(f"**Location:** {location if 'location' in locals() else default_data.get('location', 'Not set')}")
            st.info(f"**Experience:** {experience if 'experience' in locals() else default_data.get('experience_years', 0)} years")
            
            if skills if 'skills' in locals() else default_data.get('skills'):
                st.markdown("**Skills:**")
                skills_list = (skills if 'skills' in locals() else default_data.get('skills', '')).split(',')
                for skill in skills_list[:10]:
                    if skill.strip():
                        st.success(f"✓ {skill.strip()}")

def fetch_recommendations():
    """Fetch recommendations from API"""
    with st.spinner("Analyzing your profile and finding perfect matches..."):
        result = make_api_request(
            "/recommendations",
            method="GET",
            headers=get_auth_headers()
        )
        
        if result and result.get('success'):
            st.session_state.recommendations = result['recommendations']
            # Clear profile update flag since we have fresh recommendations
            st.session_state.profile_updated = False
            st.success(f"Found {len(result['recommendations'])} great matches for you!")
            st.rerun()

def display_recommendations(recommendations: List[Dict]):
    """Display recommendation cards"""
    if not recommendations:
        st.info("No recommendations found. Try updating your profile with more skills!")
        return
    
    for idx, rec in enumerate(recommendations):
        # Create a card-like container
        with st.container():
            # Left match box, middle content, right actions
            left, middle, right = st.columns([1, 5, 1])
            
            with left:
                # Extract numeric percentage and intensity for color
                match_text = rec.get('match_percentage', '')
                # Expect formats like "🟢 82% match", "🟡 58% match", "🔴 35% match"
                import re
                m = re.search(r"(\d+)%", match_text)
                percent = m.group(1) if m else "--"
                level = 'high' if '🟢' in match_text else 'medium' if '🟡' in match_text else 'low'
                st.markdown(
                    f"""
                    <div class="match-box {level}">
                        <div class="percent">{percent}%</div>
                        <div class="label">match</div>
                    </div>
                    """,
                    unsafe_allow_html=True
                )
            
            with middle:
                st.markdown(f"### {rec['title']}")
                
                # Company info in one line
                st.markdown(f"**🏢 {rec['company']}** | 📍 {rec['location']} | ⏱️ {rec['duration']}")
                
                # Stipend only (match moved to left box)
                st.info(f"💰 Stipend: {rec['stipend']}")
                
                # Description
                with st.expander("📋 Description", expanded=False):
                    st.write(rec['description'])
                
                # Skills in two columns
                skill_col1, skill_col2 = st.columns(2)
                
                with skill_col1:
                    if rec.get('matched_skills'):
                        st.markdown("**✅ Your Matching Skills:**")
                        for skill in rec['matched_skills'][:5]:
                            st.caption(f"• {skill}")
                
                with skill_col2:
                    if rec.get('skill_gaps'):
                        st.markdown("**📚 Skills to Learn:**")
                        for skill in rec['skill_gaps'][:5]:
                            st.caption(f"• {skill}")
                
                # Why it matches
                if rec.get('explanation'):
                    st.info(f"💡 {rec['explanation']}")
            
            with right:
                st.markdown("<br>", unsafe_allow_html=True)
                st.markdown("<br>", unsafe_allow_html=True)
                if st.button("Apply Now", key=f"apply_{idx}", type="primary", use_container_width=True):
                    st.balloons()
                    st.success("Great choice! Application feature coming soon!")
                
                # Smart Interested/Not Interested button
                is_saved = rec.get('is_saved', False)
                if is_saved:
                    if st.button("❌ Not Interested", key=f"unsave_{idx}", use_container_width=True):
                        if unsave_internship(rec.get('internship_id')):
                            st.rerun()
                else:
                    if st.button("💚 Interested", key=f"save_{idx}", use_container_width=True):
                        if save_internship(rec.get('internship_id')):
                            st.rerun()
            
            st.divider()

def display_saved_internships(saved_internships: List[Dict]):
    """Display saved/interested internships"""
    if not saved_internships:
        st.info("No Interests shown!")
        return
    
    for idx, internship in enumerate(saved_internships):
        with st.container():
            col1, col2 = st.columns([5, 1])
            
            with col1:
                st.markdown(f"### {internship['title']}")
                st.markdown(f"**🏢 {internship['company']}** | 📍 {internship['location']}")
                st.markdown(f"**Duration:** {internship.get('duration', 'Not specified')} | **Stipend:** ₹{internship.get('stipend', 'Not specified')}")
                
                # When marked as interested
                saved_date = internship.get('saved_at', '')
                if saved_date:
                    st.caption(f"💚 Marked interested on: {saved_date[:10]}")
                
                with st.expander("📋 Description"):
                    st.write(internship.get('description', 'No description available'))
                
                # Skills required
                if internship.get('required_skills'):
                    st.markdown("**Required Skills:**")
                    st.caption(internship['required_skills'])
            
            with col2:
                st.markdown("<br>", unsafe_allow_html=True)
                st.markdown("<br>", unsafe_allow_html=True)
                
                if st.button("Apply", key=f"apply_saved_{idx}", type="primary", use_container_width=True):
                    st.success("Application feature coming soon!")
                
                if st.button("❌ Remove", key=f"remove_saved_{idx}", use_container_width=True):
                    if unsave_internship(internship['id']):
                        st.rerun()
            
            st.divider()

# Main app logic
def main():
    """Main application"""
    # Initialize API (seed data if needed)
    if 'initialized' not in st.session_state:
        make_api_request("/seed_data", method="POST")
        st.session_state.initialized = True
    
    # Route to appropriate page
    if st.session_state.token is None:
        login_page()
    elif st.session_state.page == 'dashboard':
        dashboard_page()
    elif st.session_state.page == 'profile':
        profile_page()
    elif st.session_state.page == 'saved':
        saved_page()
    else:
        dashboard_page()

def fetch_saved_internships():
    """Fetch saved/interested internships from API and route to saved page"""
    with st.spinner("Loading your interests..."):
        result = make_api_request(
            "/saved-internships",
            method="GET",
            headers=get_auth_headers()
        )
        if result and result.get('success'):
            st.session_state.saved_internships = result.get('internships', [])
            st.session_state.page = 'saved'
            st.success(f"Loaded {len(st.session_state.saved_internships)} interests")
            st.rerun()

def saved_page():
    """Page to view all interested internships"""
    if st.button("← Back to Dashboard"):
        st.session_state.page = 'dashboard'
        st.rerun()
    st.title("💚 Your Interested Internships")
    # Always fetch fresh list so removals reflect immediately
    result = make_api_request(
        "/saved-internships",
        method="GET",
        headers=get_auth_headers()
    )
    saved_list = result.get('internships', []) if result and result.get('success') else []
    display_saved_internships(saved_list)

if __name__ == "__main__":
    main()