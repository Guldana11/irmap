from fastapi import Request, Response
from fastapi.responses import RedirectResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.datastructures import MutableHeaders
from starlette.middleware.sessions import SessionMiddleware
from sqlalchemy.orm import Session as DBSession
from models.user import User
from database import SessionLocal

class InjectUserMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        path = request.url.path
        public_paths = ["/login", "/register", "/static", "/"]

        user = None
        if "session" in request.scope:
            user_val = request.session.get("user")
            print("SESSION USER:", user_val) 
            if isinstance(user_val, str):
                user = {"username": user_val}
            elif isinstance(user_val, dict):
                user = user_val

        from main import templates
        templates.env.globals["user"] = user

        if not user and not any(path.startswith(p) for p in public_paths):
            return RedirectResponse("/login", status_code=303)

        return await call_next(request)
