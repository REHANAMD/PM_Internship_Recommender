"""
Database Cleanup Script - Remove duplicates and show stats
"""
from database import Database

def cleanup_database():
    """Clean up database duplicates and show statistics"""
    print("🧹 Database Cleanup Tool")
    print("-" * 40)
    
    db = Database()
    
    # Get stats before cleanup
    print("\n📊 Current Database Status:")
    stats = db.get_internship_stats()
    print(f"  Total internships: {stats['total']}")
    print(f"  Duplicate groups: {stats['duplicate_groups']}")
    
    if stats['duplicate_groups'] > 0:
        print("\n🔄 Removing duplicates...")
        removed = db.remove_duplicate_internships()
        print(f"  ✅ Removed {removed} duplicate entries")
        
        # Get stats after cleanup
        print("\n📊 Database After Cleanup:")
        stats = db.get_internship_stats()
        print(f"  Total internships: {stats['total']}")
        print(f"  Duplicate groups: {stats['duplicate_groups']}")
    else:
        print("\n✅ No duplicates found - database is clean!")
    
    print("\n📍 Internships by Location:")
    for location, count in stats['by_location'].items():
        print(f"  {location}: {count}")
    
    print("\n🏢 Internships by Company:")
    for company, count in stats['by_company'].items():
        print(f"  {company}: {count}")
    
    print("\n✅ Cleanup complete!")

if __name__ == "__main__":
    cleanup_database()