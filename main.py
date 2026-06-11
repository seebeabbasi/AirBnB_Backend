from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
import os
from core.database import engine, Base
from routes.booking import router as booking_router
import models 
from  routes.auth import router as auth_router 
from routes.review import router as reviews_router
from routes.family import router as family_router
from routes.property import router as property_router
from routes.wishlist import router as wishlist_router 
from routes.message import router as message_router
from routes.admin import router as admin_router
from routes.notification import router as notification_router
app = FastAPI()


@app.middleware("http")
async def log_requests(request: Request, call_next):
    origin = request.headers.get("origin")
    method = request.method
    path = request.url.path
    print(f"CORS Check: Origin={origin}, Method={method}, Path={path}")
    response = await call_next(request)
    return response


origins = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://[::1]:3000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_DIR = os.path.join(BASE_DIR, "uploads")

if not os.path.exists(UPLOAD_DIR):
    os.makedirs(UPLOAD_DIR)

app.mount("/uploads", StaticFiles(directory=UPLOAD_DIR), name="uploads")



@app.on_event("startup")
async def create_tables():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


app.include_router(auth_router)
app.include_router(family_router)
app.include_router(property_router)
app.include_router(booking_router)
app.include_router(reviews_router)
app.include_router(wishlist_router)
app.include_router(message_router)
app.include_router(admin_router)
app.include_router(notification_router)
