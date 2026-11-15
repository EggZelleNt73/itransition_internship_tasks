from pathlib import Path

from src.core.database import async_engine
from src.core.logger import logger


SQL_DIRECTORY = Path(__file__).resolve().parents[2] / "sql"
SQL_EXECUTION_ORDER = (
    "table_creation_index.sql",
    "base_population_seed.sql",
    "float_number_generation.sql",
    "generate_longtitue_latitude.sql",
    "mask_evaluator.sql",
    "generate_phone_number.sql",
    "generate_user_batch.sql",
)


async def initialize_database() -> None:
    sql_files = {path.name: path for path in SQL_DIRECTORY.glob("*.sql")}
    if not sql_files:
        raise FileNotFoundError(f"No SQL scripts found in {SQL_DIRECTORY}")

    missing_files = set(SQL_EXECUTION_ORDER) - sql_files.keys()
    if missing_files:
        missing_names = ", ".join(sorted(missing_files))
        raise FileNotFoundError(
            f"Required database initialization scripts are missing: {missing_names}"
        )

    ordered_names = [
        name for name in SQL_EXECUTION_ORDER if name in sql_files
    ]
    ordered_names.extend(sorted(sql_files.keys() - set(ordered_names)))

    async with async_engine.connect() as connection:
        raw_connection = await connection.get_raw_connection()
        driver_connection = raw_connection.driver_connection

        async with driver_connection.transaction():
            await driver_connection.execute("SELECT pg_advisory_xact_lock(614726391)")

            for name in ordered_names:
                if name == "base_population_seed.sql":
                    already_applied = await driver_connection.fetchval(
                        "SELECT EXISTS ("
                        "SELECT 1 FROM faker.initialization_scripts "
                        "WHERE script_name = $1"
                        ")",
                        name,
                    )
                    if already_applied:
                        logger.info("Skipping previously applied database seed: %s", name)
                        continue

                    lookup_data_exists = await driver_connection.fetchval(
                        "SELECT EXISTS (SELECT 1 FROM faker.lookup_first_names) "
                        "OR EXISTS (SELECT 1 FROM faker.lookup_last_names) "
                        "OR EXISTS (SELECT 1 FROM faker.lookup_streets) "
                        "OR EXISTS (SELECT 1 FROM faker.lookup_cities)"
                    )
                    if lookup_data_exists:
                        logger.info(
                            "Skipping database seed because lookup tables already contain data"
                        )
                    else:
                        logger.info("Running database initialization script: %s", name)
                        try:
                            await driver_connection.execute(
                                sql_files[name].read_text(encoding="utf-8")
                            )
                        except Exception as exc:
                            raise RuntimeError(
                                f"Database initialization failed while running {name}"
                            ) from exc

                    await driver_connection.execute(
                        "INSERT INTO faker.initialization_scripts (script_name) "
                        "VALUES ($1)",
                        name,
                    )
                    continue

                logger.info("Running database initialization script: %s", name)
                try:
                    await driver_connection.execute(sql_files[name].read_text(encoding="utf-8"))
                except Exception as exc:
                    raise RuntimeError(
                        f"Database initialization failed while running {name}"
                    ) from exc
