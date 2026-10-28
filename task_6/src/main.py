import uuid
from pathlib import Path
from time import perf_counter
from typing import List, Literal, Union
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
from src.core.database_init import initialize_database
from src.domain.schemas import (
    UserProfile,
    BenchmarkResult
)
from src.core.logger import logger
from src.core.constants import (
    INT32_MIN,
    INT32_MAX,
    MIN_BENCHMARK_USERS,
    MAX_BENCHMARK_USERS
)


@asynccontextmanager
async def lifecycle(app: FastAPI):
    try:
        await initialize_database()
        yield
    finally:
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


@app.get("/api", response_model=Union[List[UserProfile], BenchmarkResult])
async def api(
    mode: Literal["generate", "benchmark"] = Query(
        "generate",
        description="Generate one batch or benchmark generation speed",
    ),
    locale: str = Query(
        ..., 
        min_length=3, 
        max_length=3, 
        description="ISO Code: ENG or DEU"
        ),
    seed: int = Query(
        ...,
            ge=INT32_MIN,
            le=INT32_MAX,
            description="Deterministic signed 32-bit integer"
        ),
    users: int = Query(
            MIN_BENCHMARK_USERS,
            ge=1,
            le=MAX_BENCHMARK_USERS,
            description=f"Users to generate in benchmark mode (maximum {MAX_BENCHMARK_USERS})",
    ),
    batch_index: int = Query(
            0,
            ge=0,
        description="Tracks user paging requests"
        ),
    db: AsyncSession = Depends(get_db_session)
):
    is_benchmark = mode == "benchmark"
    if is_benchmark and users < MIN_BENCHMARK_USERS:
        raise HTTPException(
            status_code=422,
            detail=f"Benchmark users must be between {MIN_BENCHMARK_USERS} and {MAX_BENCHMARK_USERS}.",
        )

    batch_size = users if is_benchmark else 10
    batch_offset = 0 if is_benchmark else batch_index * batch_size
    cursor_name = f"cur_{uuid.uuid4().hex}"

    try:
        started_at = perf_counter() if is_benchmark else 0.0
        async with db.begin():
            await db.execute(
                text("CALL faker.proc_generate_user_batch(:seed, :locale, :size, :offset, :cursor)"),
                {
                    "seed": seed,
                    "locale": locale,
                    "size": batch_size,
                    "offset": batch_offset,
                    "cursor": cursor_name
                }
            )
            raw_conn = await db.connection()
            if is_benchmark:
                driver_connection = await raw_conn.get_raw_connection()
                move_status = await driver_connection.driver_connection.execute(
                    f"MOVE FORWARD ALL IN {cursor_name}"
                )
                generated_count = int(move_status.split()[-1])
            else:
                result = await raw_conn.execute(text(f"FETCH ALL IN {cursor_name}"))
                records = result.fetchall()
                generated_users = [UserProfile(**row._asdict()) for row in records]

        if is_benchmark:
            elapsed_seconds = perf_counter() - started_at
            return BenchmarkResult(
                users_generated=generated_count,
                elapsed_seconds=elapsed_seconds,
                users_per_second=generated_count / elapsed_seconds,
            )

        return generated_users
    except Exception as e:
        logger.warning("Could not process API request")
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
