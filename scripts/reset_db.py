import os
import shutil

def reset_database():
    print("=" * 50)
    print("RESETTING DATABASE")
    print("=" * 50)
    
    # List of possible database files
    db_files = [
        'submita.db',
        'instance/submita.db',
        'test.db',
        'app.db',
        'database.db'
    ]
    
    # Delete database files
    for db_file in db_files:
        if os.path.exists(db_file):
            os.remove(db_file)
            print(f"✅ Deleted: {db_file}")
    
    # Delete instance folder
    if os.path.exists('instance'):
        shutil.rmtree('instance')
        print("✅ Deleted: instance folder")
    
    # Recreate instance folder
    os.makedirs('instance', exist_ok=True)
    print("✅ Created: instance folder")
    
    # Delete all __pycache__ folders
    for root, dirs, files in os.walk('.'):
        if '__pycache__' in dirs:
            pycache_path = os.path.join(root, '__pycache__')
            shutil.rmtree(pycache_path)
            print(f"✅ Deleted: {pycache_path}")
    
    print("\n" + "=" * 50)
    print("✅ Database reset complete!")
    print("=" * 50)
    print("\nNow run: python app.py")
    print("=" * 50)

if __name__ == "__main__":
    confirm = input("⚠️  This will DELETE ALL DATA! Are you sure? (yes/no): ")
    if confirm.lower() == 'yes':
        reset_database()
    else:
        print("Operation cancelled.")