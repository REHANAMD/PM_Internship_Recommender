"""Database Module - Handles SQLite database operations"""
import sqlite3
import json
import hashlib
from datetime import datetime
from typing import List, Dict, Optional, Tuple
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class Database:
    def __init__(self, db_path: str = "recommendation_engine.db"):
        """Initialize database connection"""
        self.db_path = db_path
        self.init_db()
    
    def get_connection(self):
        """Get database connection with sane defaults for concurrency"""
        conn = sqlite3.connect(self.db_path, timeout=30, check_same_thread=False)
        try:
            conn.execute("PRAGMA busy_timeout = 30000")
        except Exception:
            pass
        return conn
    
    def init_db(self):
        """Initialize database tables"""
        conn = self.get_connection()
        cursor = conn.cursor()
        # Use WAL for better concurrent read/write behavior
        try:
            cursor.execute("PRAGMA journal_mode=WAL;")
        except Exception:
            pass
        
        # Create candidates table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS candidates (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                name TEXT NOT NULL,
                education TEXT,
                skills TEXT,
                location TEXT,
                experience_years INTEGER DEFAULT 0,
                phone TEXT,
                linkedin TEXT,
                github TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Create internships table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS internships (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                company TEXT NOT NULL,
                location TEXT NOT NULL,
                description TEXT,
                required_skills TEXT,
                preferred_skills TEXT,
                duration TEXT,
                stipend TEXT,
                application_deadline TEXT,
                posted_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                is_active BOOLEAN DEFAULT 1,
                min_education TEXT,
                experience_required INTEGER DEFAULT 0
            )
        ''')
        # Add unique index to prevent exact duplicates by title + company + location
        try:
            cursor.execute('''
                CREATE UNIQUE INDEX IF NOT EXISTS idx_internships_unique
                ON internships(title, company, location, description)
            ''')
        except Exception:
            pass
        
        # Create applications table for tracking
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS applications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                candidate_id INTEGER,
                internship_id INTEGER,
                applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                status TEXT DEFAULT 'pending',
                FOREIGN KEY (candidate_id) REFERENCES candidates(id),
                FOREIGN KEY (internship_id) REFERENCES internships(id)
            )
        ''')
        
        # Create recommendations table for caching
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS recommendations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                candidate_id INTEGER,
                internship_id INTEGER,
                score REAL,
                explanation TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (candidate_id) REFERENCES candidates(id),
                FOREIGN KEY (internship_id) REFERENCES internships(id)
            )
        ''')
        
        # Create saved_internships table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS saved_internships (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                candidate_id INTEGER NOT NULL,
                internship_id INTEGER NOT NULL,
                saved_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(candidate_id, internship_id),
                FOREIGN KEY (candidate_id) REFERENCES candidates(id),
                FOREIGN KEY (internship_id) REFERENCES internships(id)
            )
        ''')
        
        conn.commit()
        conn.close()
        
        # Run cleanup and migration after table creation
        self.run_cleanup_and_migration()
        
        logger.info("Database initialized successfully")
    
    def ensure_all_tables(self) -> List[str]:
        """Ensure all expected tables exist; create missing ones. Returns list of created tables."""
        expected_tables = {
            'candidates': '''
                CREATE TABLE IF NOT EXISTS candidates (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    email TEXT UNIQUE NOT NULL,
                    password_hash TEXT NOT NULL,
                    name TEXT NOT NULL,
                    education TEXT,
                    skills TEXT,
                    location TEXT,
                    experience_years INTEGER DEFAULT 0,
                    phone TEXT,
                    linkedin TEXT,
                    github TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''',
            'internships': '''
                CREATE TABLE IF NOT EXISTS internships (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    company TEXT NOT NULL,
                    location TEXT NOT NULL,
                    description TEXT,
                    required_skills TEXT,
                    preferred_skills TEXT,
                    duration TEXT,
                    stipend TEXT,
                    application_deadline TEXT,
                    posted_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    is_active BOOLEAN DEFAULT 1,
                    min_education TEXT,
                    experience_required INTEGER DEFAULT 0
                )
            ''',
            'applications': '''
                CREATE TABLE IF NOT EXISTS applications (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    candidate_id INTEGER,
                    internship_id INTEGER,
                    applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    status TEXT DEFAULT 'pending',
                    FOREIGN KEY (candidate_id) REFERENCES candidates(id),
                    FOREIGN KEY (internship_id) REFERENCES internships(id)
                )
            ''',
            'recommendations': '''
                CREATE TABLE IF NOT EXISTS recommendations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    candidate_id INTEGER,
                    internship_id INTEGER,
                    score REAL,
                    explanation TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (candidate_id) REFERENCES candidates(id),
                    FOREIGN KEY (internship_id) REFERENCES internships(id)
                )
            ''',
            'saved_internships': '''
                CREATE TABLE IF NOT EXISTS saved_internships (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    candidate_id INTEGER NOT NULL,
                    internship_id INTEGER NOT NULL,
                    saved_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(candidate_id, internship_id),
                    FOREIGN KEY (candidate_id) REFERENCES candidates(id),
                    FOREIGN KEY (internship_id) REFERENCES internships(id)
                )
            '''
        }
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        existing = {row[0] for row in cursor.fetchall()}
        created: List[str] = []
        for name, ddl in expected_tables.items():
            if name not in existing:
                cursor.execute(ddl)
                created.append(name)
        conn.commit()
        conn.close()
        return created
    
    def seed_internships(self, json_path: str = "data/internships.json"):
        """Seed internships from JSON file"""
        import time
        attempts = 3
        while attempts > 0:
            try:
                with open(json_path, 'r') as f:
                    internships = json.load(f)
                
                conn = self.get_connection()
                cursor = conn.cursor()
                
                # Skip seeding if internships already exist
                cursor.execute('SELECT COUNT(*) FROM internships')
                count_before = cursor.fetchone()[0]
                if count_before > 0:
                    conn.close()
                    logger.info("Internships already present, skipping seeding")
                    return True

                for internship in internships:
                    cursor.execute('''
                        INSERT OR IGNORE INTO internships 
                        (title, company, location, description, required_skills, 
                         preferred_skills, duration, stipend, min_education, experience_required)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        internship.get('title'),
                        internship.get('company'),
                        internship.get('location'),
                        internship.get('description'),
                        internship.get('required_skills'),
                        internship.get('preferred_skills'),
                        internship.get('duration'),
                        internship.get('stipend'),
                        internship.get('min_education', 'Bachelor'),
                        internship.get('experience_required', 0)
                    ))
                
                conn.commit()
                conn.close()
                logger.info(f"Seeded {len(internships)} internships")
                return True
            except sqlite3.OperationalError as e:
                if 'database is locked' in str(e).lower() and attempts > 1:
                    time.sleep(1)
                    attempts -= 1
                    continue
                logger.error(f"Error seeding internships: {e}")
                return False
            except Exception as e:
                logger.error(f"Error seeding internships: {e}")
                return False
    
    def add_candidate(self, candidate_data: Dict) -> Optional[int]:
        """Add a new candidate to database"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                INSERT INTO candidates 
                (email, password_hash, name, education, skills, location, 
                 experience_years, phone, linkedin, github)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                candidate_data['email'],
                candidate_data['password_hash'],
                candidate_data['name'],
                candidate_data.get('education'),
                candidate_data.get('skills'),
                candidate_data.get('location'),
                candidate_data.get('experience_years', 0),
                candidate_data.get('phone'),
                candidate_data.get('linkedin'),
                candidate_data.get('github')
            ))
            
            conn.commit()
            candidate_id = cursor.lastrowid
            conn.close()
            logger.info(f"Added candidate {candidate_id}")
            return candidate_id
        except sqlite3.IntegrityError as e:
            logger.error(f"Candidate already exists: {e}")
            conn.close()
            return None
        except Exception as e:
            logger.error(f"Error adding candidate: {e}")
            conn.close()
            return None
    
    def get_candidate(self, email: str = None, candidate_id: int = None) -> Optional[Dict]:
        """Get candidate by email or ID"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        if email:
            cursor.execute('SELECT * FROM candidates WHERE email = ?', (email,))
        elif candidate_id:
            cursor.execute('SELECT * FROM candidates WHERE id = ?', (candidate_id,))
        else:
            conn.close()
            return None
        
        row = cursor.fetchone()
        conn.close()
        
        if row:
            columns = ['id', 'email', 'password_hash', 'name', 'education', 
                      'skills', 'location', 'experience_years', 'phone', 
                      'linkedin', 'github', 'created_at', 'updated_at']
            return dict(zip(columns, row))
        return None
    
    def update_candidate(self, candidate_id: int, update_data: Dict) -> bool:
        """Update candidate information"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # Build update query dynamically
        update_fields = []
        values = []
        for key, value in update_data.items():
            if key not in ['id', 'email', 'password_hash', 'created_at']:
                update_fields.append(f"{key} = ?")
                values.append(value)
        
        if not update_fields:
            conn.close()
            return False
        
        values.append(candidate_id)
        query = f"UPDATE candidates SET {', '.join(update_fields)}, updated_at = CURRENT_TIMESTAMP WHERE id = ?"
        
        try:
            logger.info(f"Executing query: {query}")
            logger.info(f"With values: {values}")
            cursor.execute(query, values)
            conn.commit()
            conn.close()
            logger.info(f"Updated candidate {candidate_id}")
            return True
        except Exception as e:
            logger.error(f"Error updating candidate: {e}")
            conn.close()
            return False
    
    def get_all_internships(self, active_only: bool = True) -> List[Dict]:
        """Get all internships"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        if active_only:
            cursor.execute('SELECT * FROM internships WHERE is_active = 1')
        else:
            cursor.execute('SELECT * FROM internships')
        
        rows = cursor.fetchall()
        conn.close()
        
        columns = ['id', 'title', 'company', 'location', 'description', 
                  'required_skills', 'preferred_skills', 'duration', 'stipend',
                  'application_deadline', 'posted_date', 'is_active', 
                  'min_education', 'experience_required']
        
        return [dict(zip(columns, row)) for row in rows]
    
    def get_internship(self, internship_id: int) -> Optional[Dict]:
        """Get specific internship by ID"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM internships WHERE id = ?', (internship_id,))
        row = cursor.fetchone()
        conn.close()
        
        if row:
            columns = ['id', 'title', 'company', 'location', 'description', 
                      'required_skills', 'preferred_skills', 'duration', 'stipend',
                      'application_deadline', 'posted_date', 'is_active', 
                      'min_education', 'experience_required']
            return dict(zip(columns, row))
        return None
    
    def save_recommendation(self, candidate_id: int, internship_id: int, 
                           score: float, explanation: str):
        """Save recommendation for caching"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                INSERT INTO recommendations 
                (candidate_id, internship_id, score, explanation)
                VALUES (?, ?, ?, ?)
            ''', (candidate_id, internship_id, score, explanation))
            
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            logger.error(f"Error saving recommendation: {e}")
            conn.close()
            return False
    
    def get_cached_recommendations(self, candidate_id: int, hours: int = 24) -> List[Dict]:
        """Get cached recommendations within specified hours"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT r.*, i.title, i.company, i.location, i.description, 
                   i.required_skills, i.preferred_skills, i.duration, i.stipend
            FROM recommendations r
            JOIN internships i ON r.internship_id = i.id
            WHERE r.candidate_id = ? 
            AND datetime(r.created_at) >= datetime('now', '-' || ? || ' hours')
            ORDER BY r.score DESC
        ''', (candidate_id, hours))
        
        rows = cursor.fetchall()
        conn.close()
        
        columns = ['id', 'candidate_id', 'internship_id', 'score', 'explanation', 
                  'created_at', 'title', 'company', 'location', 'description',
                  'required_skills', 'preferred_skills', 'duration', 'stipend']
        
        return [dict(zip(columns, row)) for row in rows]
    
    def clear_old_recommendations(self, days: int = 7):
        """Clear recommendations older than specified days"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            DELETE FROM recommendations 
            WHERE datetime(created_at) < datetime('now', '-' || ? || ' days')
        ''', (days,))
        
        conn.commit()
        conn.close()
        logger.info(f"Cleared recommendations older than {days} days")
    
    def save_internship(self, candidate_id: int, internship_id: int) -> bool:
        """Save an internship to user's saved list"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                INSERT INTO saved_internships (candidate_id, internship_id)
                VALUES (?, ?)
            ''', (candidate_id, internship_id))
            
            conn.commit()
            conn.close()
            logger.info(f"Saved internship {internship_id} for candidate {candidate_id}")
            return True
        except sqlite3.IntegrityError:
            # Already saved
            conn.close()
            return False
        except Exception as e:
            logger.error(f"Error saving internship: {e}")
            conn.close()
            return False
    
    def unsave_internship(self, candidate_id: int, internship_id: int) -> bool:
        """Remove internship from user's saved list"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                DELETE FROM saved_internships 
                WHERE candidate_id = ? AND internship_id = ?
            ''', (candidate_id, internship_id))
            
            conn.commit()
            rows_affected = cursor.rowcount
            conn.close()
            
            if rows_affected > 0:
                logger.info(f"Unsaved internship {internship_id} for candidate {candidate_id}")
                return True
            return False
        except Exception as e:
            logger.error(f"Error unsaving internship: {e}")
            conn.close()
            return False
    
    def get_saved_internships(self, candidate_id: int) -> List[Dict]:
        """Get all saved internships for a candidate"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT i.*, s.saved_at,
                   CASE WHEN s.id IS NOT NULL THEN 1 ELSE 0 END as is_saved
            FROM saved_internships s
            JOIN internships i ON s.internship_id = i.id
            WHERE s.candidate_id = ?
            ORDER BY s.saved_at DESC
        ''', (candidate_id,))
        
        rows = cursor.fetchall()
        conn.close()
        
        columns = ['id', 'title', 'company', 'location', 'description', 
                  'required_skills', 'preferred_skills', 'duration', 'stipend',
                  'application_deadline', 'posted_date', 'is_active', 
                  'min_education', 'experience_required', 'saved_at', 'is_saved']
        
        return [dict(zip(columns, row)) for row in rows]
    
    def is_internship_saved(self, candidate_id: int, internship_id: int) -> bool:
        """Check if an internship is saved by user"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT COUNT(*) FROM saved_internships 
            WHERE candidate_id = ? AND internship_id = ?
        ''', (candidate_id, internship_id))
        
        count = cursor.fetchone()[0]
        conn.close()
        
        return count > 0

    def remove_duplicate_internships(self) -> int:
        """Remove duplicate internships by title+company+location+description, keeping the first occurrence. Returns number removed."""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT title, company, location, description, COUNT(*) as cnt
            FROM internships
            GROUP BY title, company, location, description
            HAVING COUNT(*) > 1
        ''')
        duplicates = cursor.fetchall()
        if not duplicates:
            logger.info("No duplicate internships found")
            conn.close()
            return 0
        removed = 0
        for title, company, location, description, cnt in duplicates:
            cursor.execute('''
                DELETE FROM internships
                WHERE rowid NOT IN (
                    SELECT MIN(rowid) FROM internships 
                    WHERE title = ? AND company = ? AND location = ? AND description = ?
                ) AND title = ? AND company = ? AND location = ? AND description = ?
            ''', (title, company, location, description, title, company, location, description))
            removed += cnt - 1
        conn.commit()
        conn.close()
        logger.info(f"Removed {removed} duplicate internships")
        return removed

    def get_internship_stats(self) -> Dict[str, Dict]:
        """Get aggregate statistics about internships in the database."""
        conn = self.get_connection()
        cursor = conn.cursor()
        stats: Dict[str, Dict] = {}
        cursor.execute("SELECT COUNT(*) FROM internships")
        stats['total'] = cursor.fetchone()[0]
        cursor.execute('''
            SELECT location, COUNT(*)
            FROM internships
            GROUP BY location
        ''')
        stats['by_location'] = dict(cursor.fetchall())
        cursor.execute('''
            SELECT company, COUNT(*)
            FROM internships
            GROUP BY company
        ''')
        stats['by_company'] = dict(cursor.fetchall())
        cursor.execute('''
            SELECT COUNT(*) FROM (
                SELECT title, company
                FROM internships
                GROUP BY title, company
                HAVING COUNT(*) > 1
            )
        ''')
        stats['duplicate_groups'] = cursor.fetchone()[0]
        conn.close()
        return stats

    def run_cleanup_and_migration(self):
        """Run cleanup and migration tasks automatically"""
        try:
            # Remove duplicates based on title + company + location + description
            removed = self.remove_duplicate_internships()
            if removed > 0:
                logger.info(f"Cleaned up {removed} duplicate internships")
            
            # Ensure all tables exist (migration)
            missing = self.ensure_all_tables()
            if missing:
                logger.info(f"Created missing tables: {missing}")
                
        except Exception as e:
            logger.error(f"Error during cleanup/migration: {e}")

# Initialize database on module import
if __name__ == "__main__":
    db = Database()
    
    # Ensure all tables exist
    missing = db.ensure_all_tables()
    if missing:
        print(f"Created missing tables: {missing}")
    
    print("Database initialized successfully with all tables:")
    
    # List all tables
    conn = db.get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = cursor.fetchall()
    for table in tables:
        cursor.execute(f"SELECT COUNT(*) FROM {table[0]}")
        count = cursor.fetchone()[0]
        print(f"  - {table[0]}: {count} records")
    conn.close()