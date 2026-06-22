from contextlib import asynccontextmanager
from fastapi import FastAPI
from app.utils.common import CustomException
from app.middlewares import exception_handler
from app.routes.v1 import router as v1_router
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException
from fastapi.middleware.cors import CORSMiddleware
from app.core.settings import setting
from app.core.db_config import init_db
from starlette.formparsers import MultiPartParser

MultiPartParser.max_part_size = setting.MAX_FILE_MEMORY_SIZE


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield


app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=setting.CSRF_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_exception_handler(CustomException, exception_handler.custom_exception_handler)
app.add_exception_handler(RequestValidationError, exception_handler.custom_validation_error_handler)
app.add_exception_handler(HTTPException, exception_handler.http_exception_handler)
app.add_exception_handler(Exception, exception_handler.unhandled_exception_handler)

@app.get("/")
async def read_root():
 
    return {"Hello": "World"}


app.include_router(v1_router, prefix="/api/v1")
