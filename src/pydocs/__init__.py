from fastapi import FastAPI
from contextlib import asynccontextmanager
from fastapi.middleware.cors import CORSMiddleware
from broadcaster import Broadcast
from sse_starlette.sse import EventSourceResponse
from sse_starlette import ServerSentEvent
import asyncio
import random

from pydocs.config import settings
from pydocs.database import (
    sessionmanager,
)


def create_app(init=True) -> FastAPI:
    lifespan = None

    if init:
        sessionmanager.init(settings.DATABASE_URL)
        broadcast = Broadcast("redis://redis:6379")

        async def generate_random_numbers():
            while True:
                number = random.randint(1, 100)
                await broadcast.publish(channel="random", message=number)
                await asyncio.sleep(1)  # Broadcast every second

        @asynccontextmanager
        async def lifespan(app: FastAPI):
            await broadcast.connect()
            asyncio.create_task(generate_random_numbers())
            yield
            await broadcast.disconnect()
            if sessionmanager._engine is not None:
                await sessionmanager.close()

    app = FastAPI(title="my great app", lifespan=lifespan, root_path="/api")

    # from fastapi_rq.views.user import router as user_router
    from pydocs.schema.user import router as user_router
    from pydocs.schema.user import current_active_user
    from pydocs.schema.file import router as file_router

    # app.include_router(user_router, prefix="/api", tags=["user"])
    app.include_router(user_router)
    app.include_router(file_router)

    # only needed for dev
    if settings.CORS_MIDDLEWARE:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

    # @app.get("/broadcaster/publish")
    # async def publish():
    #     await broadcast.publish(channel="msg", message="Hello world!")
    #     return "OK"

    @app.get("/broadcaster/subscribe")
    async def subscribe():
        async def event_generator():
            async with broadcast.subscribe(channel="random") as subscriber:
                async for msg in subscriber:
                    yield ServerSentEvent(data=str(msg))

        return EventSourceResponse(event_generator())

    # @app.get("/authenticated-route")
    # async def authenticated_route(user: User = Depends(current_active_user)):
    #     return {"message": f"Hello {user.email}!"}

    # @app.get("/")
    # async def root():
    #     return {"message": "Hello World"}

    # @app.get("/test_insert")
    # async def test_insert(
    #     db=Depends(get_db),
    #     user_manager=Depends(get_user_manager),
    # ):
    #     try:
    #         user = await user_manager.create(
    #             UserCreate(
    #                 email="jonatron@gmail.com",
    #                 password="string",
    #                 username="jonatron",
    #                 is_superuser=True,
    #             )
    #         )
    #         task = Task(
    #             userid=user.id,
    #         )
    #         db.add(task)
    #         await db.flush()
    #         taskpayload = TaskPayload(taskid=task.id, payload={"hello": "world"})
    #         db.add(taskpayload)
    #         await db.commit()

    #         print(f"User created {user}")
    #         return {"done"}
    #     except UserAlreadyExists:
    #         print("User jonatron@gmail.com already exists")

    return app
