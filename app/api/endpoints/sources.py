from fastapi import APIRouter
from starlette import status

from app.api.dependencies import sessionDepends, roleDepends
from app.api.schemas import SourceInputSchema, SourceOutputSchema
from app.database.models import Source
from app.database.repositories.imports import create_source, list_sources

sources_router = APIRouter(prefix="/sources",
    tags=["Загрузка, взаимодействие с источниками"],
    dependencies=[roleDepends])

@sources_router.post("/", summary="Загрузить источник", status_code=status.HTTP_201_CREATED,
                     response_model=SourceOutputSchema)
async def create_new_source(session: sessionDepends, input_source: SourceInputSchema):
    source = Source(name=input_source.name, description=input_source.description)
    await create_source(session, source)
    await session.commit()
    return source

@sources_router.get("/", response_model=list[SourceOutputSchema],
                    summary="Вывести все источники", status_code=status.HTTP_200_OK)
async def get_sources(session: sessionDepends):
    return await list_sources(session)
