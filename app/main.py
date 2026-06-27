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
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
import jwt
from app.repositories import UserRepository
from app.mcp_server import mcp, mcp_user_var

MultiPartParser.max_part_size = setting.MAX_FILE_MEMORY_SIZE


class MCPAuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if request.url.path.startswith("/mcp"):
            token = None
            auth_header = request.headers.get("Authorization")
            if auth_header and auth_header.startswith("Bearer "):
                token = auth_header.split(" ")[1]
            else:
                token = request.query_params.get("token")

            email = request.query_params.get("email") or request.headers.get("X-User-Email")

            user = None
            if token:
                try:
                    payload = jwt.decode(token, setting.SECRET_KEY, algorithms=[setting.ALGORITHM])
                    user_id = payload.get("user_id")
                    if user_id:
                        user = await UserRepository.get_user_by_id(user_id)
                except Exception:
                    pass
            elif email:
                user = await UserRepository.get_user_by_email(email)

            if user:
                token_ref = mcp_user_var.set(user)
                try:
                    return await call_next(request)
                finally:
                    mcp_user_var.reset(token_ref)

        return await call_next(request)


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
app.add_middleware(MCPAuthMiddleware)

app.add_exception_handler(CustomException, exception_handler.custom_exception_handler)
app.add_exception_handler(RequestValidationError, exception_handler.custom_validation_error_handler)
app.add_exception_handler(HTTPException, exception_handler.http_exception_handler)
app.add_exception_handler(Exception, exception_handler.unhandled_exception_handler)

@app.get("/")
async def read_root():
 
    return {"Hello": "World"}


app.include_router(v1_router, prefix="/api/v1")

# Mount the MCP server as an SSE application under /mcp
app.mount("/mcp", mcp.sse_app())

