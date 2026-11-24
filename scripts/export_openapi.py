"""Run with PYTHONPATH=backend to refresh the canonical frontend API schema."""
import json
from pathlib import Path
from app.main import app
Path('docs/openapi.json').write_text(json.dumps(app.openapi(),indent=2)+'\n')
print('Exported docs/openapi.json')
