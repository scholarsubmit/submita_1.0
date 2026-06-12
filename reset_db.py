# FILE: reset_db.py
# PURPOSE: Quick database reset
# USAGE: python reset_db.py

import os
import sys

def reset_database():
    db_file = 'submita.db'

    if os.path.exists(db_file):
        print(f"🗑️  Removing {db_file}...")
        os.remove(db_file)
        print(f"   ✅ {db_file} deleted")
    else:
        print(f"ℹ️  {db_file} not found (already clean)")

    print("
📋 Next steps:")
    print("   1. Run: python app.py")
    print("   2. Stop the server (Ctrl+C)")
    print("   3. Run: python seed_data.py")
    print("
✅ Database reset complete!")

if __name__ == '__main__':
    print("=" * 50)
    print("🔄 SUBMITA DATABASE RESET")
    print("=" * 50)

    confirm = input("
⚠️  This will delete submita.db. Continue? (y/n): ").lower()
    if confirm == 'y':
        reset_database()
    else:
        print("   Cancelled.")