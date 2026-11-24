import logging
from pathlib import Path
from uuid import uuid4
from fastapi import FastAPI, Request, Depends
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from starlette.exceptions import HTTPException as StarletteHTTPException
from app.database import get_db
from app.routes.api import router

app=FastAPI(title='Access Ledger API',version='2.0.0',docs_url=None,openapi_url='/api/openapi.json',redoc_url=None)
app.include_router(router)
logger=logging.getLogger('dac')
DIST=Path(__file__).resolve().parents[2]/'frontend'/'dist'
if (DIST/'assets').is_dir(): app.mount('/assets',StaticFiles(directory=DIST/'assets'),name='assets')


@app.middleware('http')
async def security_headers(request: Request,call_next):
    request.state.request_id=uuid4()
    try: response=await call_next(request)
    except Exception as exc:
        logger.error('Request failed: %s',type(exc).__name__)
        response=JSONResponse({'message':'This request could not be completed. Please try again.'},status_code=500)
    response.headers.update({
        'X-Content-Type-Options':'nosniff','X-Frame-Options':'DENY','Referrer-Policy':'same-origin',
        # Radix's scroll lock uses style elements. Scripts remain self-only.
        'Content-Security-Policy':"default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; font-src 'self'; frame-ancestors 'none'; form-action 'self'; base-uri 'self'",
        'Cache-Control':'no-store','X-Request-ID':str(request.state.request_id)})
    return response


@app.exception_handler(StarletteHTTPException)
async def http_error(request,exc):
    return JSONResponse({'message':exc.detail},status_code=exc.status_code)


@app.exception_handler(RequestValidationError)
async def validation_error(request,exc):
    return JSONResponse({'message':'Check the submitted fields and try again.',
        'errors':[{'field':str(e['loc'][-1]),'message':e['msg']} for e in exc.errors()]},status_code=422)


@app.exception_handler(SQLAlchemyError)
async def database_error(request,exc):
    logger.error('Database operation failed: %s',type(exc).__name__)
    return JSONResponse({'message':'The operation could not be recorded safely. No access is granted. Please try again shortly.'},status_code=503)


@app.get('/health',include_in_schema=False)
def health(db=Depends(get_db)):
    db.execute(text('SELECT 1'));return {'status':'ok'}


@app.get('/{path:path}',include_in_schema=False)
def frontend(path: str):
    if path.startswith('api/') or path=='api':
        return JSONResponse({'message':'This API endpoint does not exist.'},status_code=404)
    if path=='favicon.svg' and (DIST/'favicon.svg').exists(): return FileResponse(DIST/'favicon.svg')
    if not (DIST/'index.html').exists():
        return JSONResponse({'message':'Frontend build missing. Run npm run build in frontend, or start the Vite development server.'},status_code=503)
    return FileResponse(DIST/'index.html')
