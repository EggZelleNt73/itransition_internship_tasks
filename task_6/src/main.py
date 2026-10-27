import uuid
from pathlib import Path
from typing import List
from contextlib import asynccontextmanager
from fastapi import (
    FastAPI,
    Query,
    HTTPException,
    Request,
    Depends
)
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from src.core.config import settings
from src.core.database import (
    async_engine,
    get_db_session
)
from src.domain.schemas import UserProfile
from src.core.logger import logger


@asynccontextmanager
async def lifecycle(app: FastAPI):
    yield
    await async_engine.dispose()


app = FastAPI(
    title="SQL Faker Engine API",
    lifespan=lifecycle     
    )
templates = Jinja2Templates(directory=settings.templates_path)
app.mount(
    "/static",
    StaticFiles(directory=Path(__file__).resolve().parent.parent / "static"),
    name="static",
)


@app.get(
    "/api/users", 
    response_model=List[UserProfile]
    )
async def get_user_batch(
    locale: str = Query(
        ..., 
        min_length=3, 
        max_length=3, 
        description="ISO Code: ENG or DEU"
        ),
    seed: int = Query(
        ...,
        description="Deterministic base integer"
        ),
    batch_index: int = Query(
        0,
        ge=0,
        description="Tracks user paging requests"
        ),
    db: AsyncSession = Depends(get_db_session)
):
    batch_size = 10
    batch_offset = batch_index * batch_size
    cursor_name = f"cur_{uuid.uuid4().hex}"

    try:
        async with db.begin():
            await db.execute(text("CALL faker.proc_generate_user_batch(:seed, :locale, :size, :offset, :cursor)"),
                {
                    "seed": seed,
                    "locale": locale,
                    "size": batch_size,
                    "offset": batch_offset,
                    "cursor": cursor_name
                }
            )
            raw_conn = await db.connection()
            result = await raw_conn.execute(text(f"FETCH ALL IN {cursor_name}"))
            records = result.fetchall()
            return [UserProfile(**row._asdict()) for row in records]
    except Exception as e:
        logger.warning("Could not fetch data from DB")
        raise HTTPException(
            status_code=500,
            detail=f"Database execution error: {str(e)}"
            )


@app.get(
    "/", 
    response_class=HTMLResponse
    )
async def serve_index(request: Request):
    return templates.TemplateResponse(request=request, name="index.html")
