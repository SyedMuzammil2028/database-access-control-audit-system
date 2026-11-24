"""Build a submission ZIP from an explicit list of project deliverables.

Local notes, original proposal material, editable document duplicates and
runtime files stay in the workspace and are not part of this distribution.
"""
from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED

ROOT = Path(__file__).resolve().parents[1]
ARCHIVE_ROOT = Path('DataBase-project')
OUTPUT = ROOT / 'artifacts' / 'Database-Access-Control-Audit-System.zip'
ROOT_FILES = (
    '.dockerignore', '.env.example', '.gitattributes', '.gitignore',
    'Dockerfile', 'README.md', 'alembic.ini', 'docker-compose.yml',
    'pytest.ini', 'requirements.txt', 'requirements.lock',
)
SOURCE_TREES = ('backend', 'frontend', 'alembic', 'sql', 'tests')
DOC_FILES = (
    'DATABASE_DESIGN.md', 'DEMO_GUIDE.md', 'DESIGN_REFERENCE.md',
    'ERD.md', 'INSTALLATION.md', 'REQUIREMENTS.md', 'SECURITY.md',
    'SOURCES.md', 'SQL_DEMONSTRATION.md', 'TEST_RESULTS.md',
    'backend-test-output.txt', 'browser-test-output.txt',
    'frontend-test-output.txt', 'openapi.json',
)
SCRIPT_FILES = (
    '__init__.py', 'build_archive.py', 'configure.py', 'export_openapi.py',
    'generate_sql.py', 'init-db.sh', 'seed.py', 'setup.py', 'smoke.py',
)
SUBMISSION_FILES = ('Project_Report.pdf', 'ER_Diagram.pdf')
EXCLUDED_DIRS = {
    '.git', '.venv', '__pycache__', '.pytest_cache', 'node_modules',
    'dist', 'test-results', 'playwright-report', '.vite', '.cache',
}
EXCLUDED_SUFFIXES = ('.pyc', '.pyo', '.tsbuildinfo', '.log', '.zip', '.dump')


def submission_files():
    """Return only source, setup, test and submission deliverables."""
    selected = {ROOT / name for name in ROOT_FILES}
    selected.update(ROOT / 'scripts' / name for name in SCRIPT_FILES)
    selected.update(ROOT / 'docs' / name for name in DOC_FILES)
    selected.update(ROOT / 'docs' / 'submission' / name for name in SUBMISSION_FILES)
    for tree in (*SOURCE_TREES, 'docs/screenshots', 'docs/third-party'):
        for path in (ROOT / tree).rglob('*'):
            relative = path.relative_to(ROOT)
            if any(part in EXCLUDED_DIRS for part in relative.parts):
                continue
            if path.name == '.env' or path.name.endswith(EXCLUDED_SUFFIXES):
                continue
            if path.is_file():
                selected.add(path)
    for path in selected:
        if not path.is_file() or path.is_symlink():
            raise RuntimeError(f'Missing or unexpected submission file: {path.relative_to(ROOT)}')
    return sorted(selected)


def build_archive():
    files = submission_files()
    OUTPUT.parent.mkdir(exist_ok=True)
    temporary = OUTPUT.with_suffix('.zip.tmp')
    try:
        with ZipFile(temporary, 'w', ZIP_DEFLATED) as archive:
            for path in files:
                archive.write(path, ARCHIVE_ROOT / path.relative_to(ROOT))
        with ZipFile(temporary) as archive:
            names = archive.namelist()
            if archive.testzip() is not None:
                raise RuntimeError('Submission archive integrity check failed.')
            if len(names) != len(set(names)):
                raise RuntimeError('Submission archive contains duplicate paths.')
            if any(Path(name).suffix.lower() == '.docx' for name in names):
                raise RuntimeError('Editable Word duplicates must not be packaged.')
            if any(Path(name).name == '.env' for name in names):
                raise RuntimeError('Local secrets must not be packaged.')
        temporary.replace(OUTPUT)
    finally:
        temporary.unlink(missing_ok=True)
    return OUTPUT, len(files)


if __name__ == '__main__':
    path, count = build_archive()
    print(f'{path}\n{count} project files; source, setup, tests, report and ER diagram.')
