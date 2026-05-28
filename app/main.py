from contextlib import asynccontextmanager

from dotenv import load_dotenv

load_dotenv()

from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from jose import jwt, JWTError
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request as StarletteRequest
from starlette.responses import RedirectResponse as StarletteRedirectResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.config.auth import SECRET_KEY, ALGORITHM
from app.config.database import engine, Base, SessionLocal
from app.models import User
from app.routes import home, auth_routes, user_routes


class AuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: StarletteRequest, call_next):
        path = request.url.path

        if not path.startswith("/home") and not path.startswith("/admin"):
            return await call_next(request)

        token = request.cookies.get("licitai_token")
        if not token:
            return StarletteRedirectResponse(url="/")

        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            user_id = payload.get("sub")
            if user_id is None:
                return StarletteRedirectResponse(url="/")
        except JWTError:
            return StarletteRedirectResponse(url="/")

        db = SessionLocal()
        try:
            user = db.query(User).filter(User.id == int(user_id)).first()
        finally:
            db.close()

        if user is None:
            return StarletteRedirectResponse(url="/")

        if path.startswith("/admin") and user.user_type != "admin":
            return StarletteRedirectResponse(url="/home")

        request.state.current_user = user
        return await call_next(request)


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(title="LicitAI", lifespan=lifespan)

templates = Jinja2Templates(directory="app/templates")

@app.exception_handler(StarletteHTTPException)
async def not_found_handler(request: Request, exc: StarletteHTTPException):
    if exc.status_code == 404:
        return templates.TemplateResponse(request, "404.html", {"request": request}, status_code=404)
    return templates.TemplateResponse(request, "404.html", {"request": request}, status_code=exc.status_code)

app.mount("/static", StaticFiles(directory="app/static"), name="static")

app.add_middleware(AuthMiddleware)

app.include_router(home.router)
app.include_router(auth_routes.router)
app.include_router(user_routes.router)
