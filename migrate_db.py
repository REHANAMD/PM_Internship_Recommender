"""
Database Migration Script - Run this to ensure database is up to date
"""
from database import Database

def migrate_database():
    """Ensure database has all required tables and structure"""
    print("🔄 Starting database migration...")
    
    db = Database()
    
    # Ensure all tables exist
    missing = db.ensure_all_tables()
    
    if missing:
        print(f"✅ Created missing tables: {', '.join(missing)}")
    else:
        print("✅ All tables already exist")
    
    # Check current structure
    conn = db.get_connection()
    cursor = conn.cursor()
    
    print("\n📊 Database Status:")
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = cursor.fetchall()
    
    for table in tables:
        cursor.execute(f"SELECT COUNT(*) FROM {table[0]}")
        count = cursor.fetchone()[0]
        print(f"  ✓ {table[0]}: {count} records")
    
    conn.close()
    print("\n✅ Database migration complete!")

if __name__ == "__main__":
    migrate_database()