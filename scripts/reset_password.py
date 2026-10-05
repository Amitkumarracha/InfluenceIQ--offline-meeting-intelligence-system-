"""Local recovery only: requires access to the laptop's project and database."""
import getpass
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from api import SessionLocal, User, UserCreate
import bcrypt

if __name__ == '__main__':
    email = input('Account email: ').strip().lower()
    password = getpass.getpass('New password: ')
    UserCreate(email=email, password=password)
    with SessionLocal() as db:
        user = db.query(User).filter_by(email=email).first()
        if user is None:
            raise SystemExit('Account not found')
        user.password_hash = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
        user.reset_token = None
        db.commit()
    print('Password updated.')
