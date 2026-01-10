from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import auth, webhook, chat, context, goals, notes, activity, settings, memory, meetings, projects, coding_sessions, drafts, subscription


app = FastAPI(
    title="BumbleBee API",
    description="AI Assistant Backend",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health_check():
    return {"status": "healthy"}


app.include_router(auth.router)
app.include_router(webhook.router)
app.include_router(chat.router)
app.include_router(context.router)
app.include_router(goals.router)
app.include_router(notes.router)
app.include_router(activity.router)
app.include_router(settings.router)
app.include_router(memory.router)
app.include_router(meetings.router)
app.include_router(projects.router)
app.include_router(coding_sessions.router)
app.include_router(drafts.router)
app.include_router(subscription.router)
