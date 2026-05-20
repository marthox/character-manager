# src/main.py
from contextlib import asynccontextmanager
from fastapi import FastAPI

from adapters.inbound.routers.modules import router as modules_router
from adapters.inbound.routers.templates import router as templates_router
from adapters.inbound.routers.characters import router as characters_router
from adapters.outbound.db.models import Base
from adapters.outbound.db.session import engine, SessionLocal
from adapters.outbound.db.module_definition_repo import SQLModuleDefinitionRepository
from adapters.outbound.db.sheet_template_repo import SQLSheetTemplateRepository
from domain.seeder import seed_dnd5e


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    with SessionLocal() as session:
        seed_dnd5e(
            SQLModuleDefinitionRepository(session),
            SQLSheetTemplateRepository(session),
        )
    yield


app = FastAPI(title="Character Manager", lifespan=lifespan)

app.include_router(modules_router)
app.include_router(templates_router)
app.include_router(characters_router)
