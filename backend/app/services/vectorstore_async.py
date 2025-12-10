import asyncio
from app.services.vectorstore import query as sync_query, ingest_document as sync_ingest


async def ingest_document_async(*args, **kwargs):
    return await asyncio.to_thread(sync_ingest, *args, **kwargs)


async def query_async(*args, **kwargs):
    return await asyncio.to_thread(sync_query, *args, **kwargs)
