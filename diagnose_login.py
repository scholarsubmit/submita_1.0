#!/usr/bin/env python3
"""
Submita Login Diagnostic Tool
=============================
Run this in your project directory to find the exact bottleneck.

Usage:
    python diagnose_login.py
"""

import time
import sys
import os

print("=" * 70)
print("SUBMITA LOGIN DIAGNOSTIC")
print("=" * 70)

# Check 1: Database connection speed
print("\n[1] DATABASE CONNECTION TEST")
print("-" * 40)
try:
    from app import app, db
    from models import User  # adjust import as needed

    start = time.perf_counter()
    with app.app_context():
        # Test connection
        db.session.execute(db.text("SELECT 1"))
        conn_time = (time.perf_counter() - start) * 1000
        print(f"   ✅ Database connection: {conn_time:.2f}ms")

        # Test user lookup speed
        start = time.perf_counter()
        user = User.query.first()
        lookup_time = (time.perf_counter() - start) * 1000
        print(f"   ✅ First user lookup: {lookup_time:.2f}ms")

        # Check indexes
        from sqlalchemy import inspect
        inspector = inspect(db.engine)
        indexes = inspector.get_indexes('users')
        index_cols = []
        for idx in indexes:
            index_cols.extend(idx.get('column_names', []))

        required = ['email', 'matric_number', 'staff_id']
        missing = [col for col in required if col not in index_cols]

        if missing:
            print(f"   ⚠️  MISSING INDEXES: {missing}")
            print(f"   💡 Run: python add_indexes.py")
        else:
            print(f"   ✅ All required indexes present")

except Exception as e:
    print(f"   ❌ Error: {e}")
    print(f"   💡 Make sure you're running this from your project directory")

# Check 2: Bcrypt configuration
print("\n[2] PASSWORD HASHING CONFIGURATION")
print("-" * 40)
try:
    from app import bcrypt
    rounds = getattr(bcrypt, '_log_rounds', 12)

    print(f"   Current bcrypt rounds: {rounds}")

    if rounds > 13:
        print(f"   ⚠️  TOO HIGH! Each login takes {rounds-12}x longer than necessary")
        print(f"   💡 Fix: Set BCRYPT_LOG_ROUNDS=12 in config")
    elif rounds == 12:
        print(f"   ✅ Optimal (12 rounds)")
    else:
        print(f"   ⚠️  Low rounds ({rounds}) - faster but less secure")

    # Test actual hash speed
    import bcrypt as bcrypt_lib
    test_password = b"test_password_123"
    test_hash = bcrypt_lib.hashpw(test_password, bcrypt_lib.gensalt(rounds=rounds))

    start = time.perf_counter()
    bcrypt_lib.checkpw(test_password, test_hash)
    verify_time = (time.perf_counter() - start) * 1000

    print(f"   Single hash verify time: {verify_time:.2f}ms")

    if verify_time > 300:
        print(f"   🔴 SLOW: This is why login feels sluggish!")
    elif verify_time > 150:
        print(f"   🟡 Acceptable but could be faster")
    else:
        print(f"   🟢 Fast")

except Exception as e:
    print(f"   ❌ Error: {e}")

# Check 3: Session configuration
print("\n[3] SESSION CONFIGURATION")
print("-" * 40)
try:
    from app import app

    session_type = app.config.get('SESSION_TYPE', 'filesystem')
    print(f"   Session type: {session_type}")

    if session_type == 'filesystem':
        print(f"   ⚠️  Using filesystem sessions - slow under load")
        print(f"   💡 Fix: Use Redis for production")
    else:
        print(f"   ✅ Using {session_type} sessions")

    # Check cookie settings
    httponly = app.config.get('SESSION_COOKIE_HTTPONLY', False)
    secure = app.config.get('SESSION_COOKIE_SECURE', False)
    samesite = app.config.get('SESSION_COOKIE_SAMESITE', None)

    print(f"   HttpOnly: {'✅' if httponly else '❌'}")
    print(f"   Secure: {'✅' if secure else '❌ (set to True in production)'}")
    print(f"   SameSite: {samesite or '❌ Not set'}")

except Exception as e:
    print(f"   ❌ Error: {e}")

# Check 4: Full login simulation
print("\n[4] FULL LOGIN SIMULATION")
print("-" * 40)
try:
    from app import app, db
    from models import User

    with app.app_context():
        # Find a test user or create one
        test_user = User.query.filter_by(email="test@diagnostic.com").first()

        if not test_user:
            print(f"   ℹ️  No test user found. Creating one...")
            test_user = User(
                email="test@diagnostic.com",
                matric_number="TEST001",
                role="student"
            )
            test_user.set_password("testpass123")
            db.session.add(test_user)
            db.session.commit()
            print(f"   ✅ Created test user (test@diagnostic.com / testpass123)")

        # Simulate full login flow
        print(f"   Running full login simulation...")

        # Step 1: User lookup
        start = time.perf_counter()
        user = User.query.filter_by(email="test@diagnostic.com").first()
        t_lookup = (time.perf_counter() - start) * 1000

        # Step 2: Password verify
        start = time.perf_counter()
        valid = user.check_password("testpass123") if user else False
        t_verify = (time.perf_counter() - start) * 1000

        # Step 3: Session operations (simulated)
        start = time.perf_counter()
        # Simulate session dict operations
        sess_data = {'user_id': user.id, 'role': user.role}
        t_session = (time.perf_counter() - start) * 1000

        total = t_lookup + t_verify + t_session

        print(f"\n   Results:")
        print(f"   {'User lookup':<20} {t_lookup:>8.2f}ms")
        print(f"   {'Password verify':<20} {t_verify:>8.2f}ms")
        print(f"   {'Session create':<20} {t_session:>8.2f}ms")
        print(f"   {'-'*30}")
        print(f"   {'TOTAL':<20} {total:>8.2f}ms")

        if total > 500:
            print(f"\n   🔴 SLOW LOGIN: {total:.0f}ms")
            print(f"   The bottleneck is: {'password verify' if t_verify > t_lookup else 'user lookup'}")
        elif total > 200:
            print(f"\n   🟡 Acceptable but improvable")
        else:
            print(f"\n   🟢 Fast login")

        # Cleanup
        if user and user.email == "test@diagnostic.com":
            db.session.delete(user)
            db.session.commit()
            print(f"\n   🧹 Cleaned up test user")

except Exception as e:
    print(f"   ❌ Error: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 70)
print("DIAGNOSTIC COMPLETE")
print("=" * 70)
print("\nNext steps:")
print("  1. If password_verify is >300ms → Reduce bcrypt rounds to 12")
print("  2. If user_lookup is >50ms → Run: python add_indexes.py")
print("  3. If using filesystem sessions → Switch to Redis")
print("  4. Replace your login route with optimized_login_route.py")