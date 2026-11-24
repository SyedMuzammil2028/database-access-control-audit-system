"""Create local development secrets once. Never overwrite an existing .env."""
import secrets
from pathlib import Path

path = Path('.env')
if path.exists():
    print('.env already exists; left unchanged.')
else:
    owner = secrets.token_hex(24); app = secrets.token_hex(24)
    path.write_text(f'''POSTGRES_PASSWORD={owner}
APP_DB_PASSWORD={app}
SECRET_KEY={secrets.token_hex(32)}
DATABASE_URL=postgresql+psycopg://dac_app:{app}@localhost:5434/dac
COOKIE_SECURE=false
ENVIRONMENT=development
''')
    path.chmod(0o600)
    print('Created .env with random local secrets.')
