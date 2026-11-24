"""Package source and docs without secrets, local dependencies or runtime data."""
import os
from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED

root = Path(__file__).resolve().parents[1]
out = root / 'artifacts' / 'Database-Access-Control-Audit-System.zip'
out.parent.mkdir(exist_ok=True)
excluded = {'.git','.venv','__pycache__','.pytest_cache','artifacts','node_modules','dist','test-results','playwright-report'}
with ZipFile(out,'w',ZIP_DEFLATED) as archive:
    for directory, dirs, files in os.walk(root):
        dirs[:] = sorted(d for d in dirs if d not in excluded)
        for name in sorted(files):
            path=Path(directory)/name
            if name=='.env' or name.endswith(('.pyc','.zip','.dump','.tsbuildinfo')): continue
            archive.write(path, Path('DataBase-project')/path.relative_to(root))
with ZipFile(out) as archive:
    assert all(Path(n).name!='.env' for n in archive.namelist())
    assert archive.testzip() is None
print(out)
