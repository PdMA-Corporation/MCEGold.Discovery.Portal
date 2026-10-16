from contextlib import asynccontextmanager
import logging
from pathlib import Path

from fastapi import FastAPI
from starlette.middleware.sessions import SessionMiddleware
from fastapi.staticfiles import StaticFiles

from app.api.routes import router
from app.core.config import settings
from app.services.reference_data_service import ReferenceDataService
from app.storage.database import initialize_database
from app.storage.application_settings import ApplicationSettingsRepository
from app.storage.reference_data_seed import ReferenceDataSeedResult, ReferenceDataSeeder


logger = logging.getLogger("mcegold.discovery.portal")


def import_reference_data_if_needed(
    db_path: str,
    reference_data: ReferenceDataService,
) -> ReferenceDataSeedResult:
    return ReferenceDataSeeder(db_path, reference_data).seed()


@asynccontextmanager
async def lifespan(app: FastAPI):
    database_path = settings.discovery_database_path
    app.state.database_existed_before_initialization = Path(database_path).exists()
    app.state.database = initialize_database(database_path)
    session_id, started_at = ApplicationSettingsRepository(database_path).get_request_session()
    # This restores local state only; normal discovery calls validate the remote ID.
    app.state.discovery_session_id = session_id
    app.state.discovery_started_at = started_at
    reference_data = ReferenceDataService(
        settings.reference_data_path,
        settings.reference_data_sheet,
    )
    app.state.reference_data_seed = import_reference_data_if_needed(
        database_path,
        reference_data,
    )
    app.state.reference_data = reference_data
    yield


app = FastAPI(title=settings.app_name, lifespan=lifespan)
app.add_middleware(SessionMiddleware, secret_key=settings.session_secret_key)
app.mount("/static", StaticFiles(directory="app/static"), name="static")
app.include_router(router)
