"""
create_admin.py — run once to create the first admin account, since
admins can't self-register (by design — only an existing admin can
create another admin, this script fills that gap for account #1).

Usage: python create_admin.py
"""
import getpass

from app import create_app
from app.extensions import db
from app.models import User, UserRole
from app.utils.security import validate_password_strength, valid_email_format

app = create_app()

with app.app_context():
    print('=' * 50)
    print('CREATE FIRST ADMIN ACCOUNT')
    print('=' * 50)

    name = input('Full name: ').strip()
    email = input('Email: ').strip().lower()
    staff_id = input('Staff ID (e.g. ADMIN001): ').strip().upper()

    if not valid_email_format(email):
        print('❌ Invalid email format.')
        raise SystemExit(1)
    if User.query.filter_by(email=email).first():
        print('❌ An account with this email already exists.')
        raise SystemExit(1)
    if User.query.filter_by(staff_id=staff_id).first():
        print('❌ This staff ID is already in use.')
        raise SystemExit(1)

    while True:
        password = getpass.getpass('Password: ')
        confirm = getpass.getpass('Confirm password: ')
        if password != confirm:
            print('❌ Passwords do not match. Try again.')
            continue
        ok, errors = validate_password_strength(password)
        if not ok:
            for e in errors:
                print(f'❌ {e}')
            continue
        break

    admin = User(
        role=UserRole.ADMIN, name=name, email=email, staff_id=staff_id,
        is_email_verified=True,  # admin accounts are created out-of-band, already trusted
    )
    admin.set_password(password)
    db.session.add(admin)
    db.session.commit()

    print(f'\n✅ Admin account created: {email} / staff ID {staff_id}')
