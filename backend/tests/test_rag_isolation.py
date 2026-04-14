import asyncio
from sqlalchemy import text
import pytest
from app.core.common.db import engine
from app.services.rag import RagService
from app.models.rag import RagInstanceModel


def _can_connect() -> bool:
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except Exception:
        return False


def _has_rag_instances_table() -> bool:
    try:
        with engine.connect() as conn:
            res = conn.execute(
                text(
                    """
                    SELECT 1
                    FROM information_schema.tables
                    WHERE table_name = 'rag_instances'
                    LIMIT 1
                    """
                )
            ).fetchone()
            return bool(res)
    except Exception:
        return False


pytestmark = pytest.mark.skipif(
    (not _can_connect()) or (not _has_rag_instances_table()),
    reason="postgres_not_available_or_migrations_not_applied",
)


async def _test_rag_workspace_isolation():
    rag_service = RagService()

    ws1_id = 101
    ws1_instance = await rag_service.create_instance(
        workspace_id=ws1_id,
        name="WS1 KB",
        embedding_model_id=1,
        dimension=1536,
    )

    ws2_id = 102
    ws2_instance = await rag_service.create_instance(
        workspace_id=ws2_id,
        name="WS2 KB",
        embedding_model_id=1,
        dimension=1536,
    )

    try:
        ws1_list = await rag_service.list_instances(ws1_id)
        ws2_list = await rag_service.list_instances(ws2_id)

        assert len(ws1_list) == 1
        assert ws1_list[0].id == ws1_instance.id
        assert len(ws2_list) == 1
        assert ws2_list[0].id == ws2_instance.id

        assert await rag_service.get_instance(ws1_id, ws2_instance.id) is None
        assert await rag_service.get_instance(ws2_id, ws1_instance.id) is None

        assert await rag_service.delete_instance(ws1_id, ws2_instance.id) is False

        assert await rag_service.delete_instance(ws1_id, ws1_instance.id) is True
        assert await rag_service.delete_instance(ws2_id, ws2_instance.id) is True

    finally:
        await rag_service.delete_instance(ws1_id, ws1_instance.id)
        await rag_service.delete_instance(ws2_id, ws2_instance.id)


def test_rag_workspace_isolation():
    asyncio.run(_test_rag_workspace_isolation())


async def _test_rag_concurrent_creation():
    rag_service = RagService()

    async def create_one(i):
        return await rag_service.create_instance(
            workspace_id=i,
            name=f"Concurrent KB {i}",
            embedding_model_id=1,
            dimension=1536,
        )

    instances = await asyncio.gather(*[create_one(i) for i in range(200, 210)])

    try:
        assert len(instances) == 10
        collections = [ins.collection_name for ins in instances]
        assert len(set(collections)) == 10
    finally:
        for ins in instances:
            await rag_service.delete_instance(ins.workspace_id, ins.id)


def test_rag_concurrent_creation():
    asyncio.run(_test_rag_concurrent_creation())
