"""
SSE (Server-Sent Events) log endpoint for real-time consolidation progress.

Architecture
------------
A global ``job_log_store`` dict maps a short job ID to a list of
``MergerLogEvent`` objects.  The consolidation pipeline (merger.py endpoint)
populates this store during processing.  The frontend connects to the
``GET /api/merger/logs/{job_id}`` SSE stream *before* or *during* the POST
request and receives events as they are appended.

Because FastAPI uses an async event loop the store is safely accessed from
within a single process without locks (single-writer / single-reader per job).
"""

import asyncio
import json
from typing import AsyncGenerator

from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from src.models.merger import MergerLogEvent

router = APIRouter()

# In-memory store: job_id -> list[MergerLogEvent]
# Populated by the consolidation endpoint; consumed (and eventually cleaned up)
# by the SSE stream below.
job_log_store: dict[str, list[MergerLogEvent]] = {}

# Sentinel value appended to the list when a job is fully complete/errored.
_DONE_SENTINEL = "__DONE__"


def register_job(job_id: str) -> None:
    """Create an empty log queue for *job_id*. Call before starting processing."""
    job_log_store[job_id] = []


def emit(job_id: str, event: MergerLogEvent) -> None:
    """Append a log event to the job's queue (called from the processing pipeline)."""
    if job_id in job_log_store:
        job_log_store[job_id].append(event)


def close_job(job_id: str) -> None:
    """Signal that the job is done by appending the sentinel."""
    if job_id in job_log_store:
        job_log_store[job_id].append(_DONE_SENTINEL)  # type: ignore[arg-type]


async def _event_generator(job_id: str) -> AsyncGenerator[str, None]:
    """
    Async generator that yields SSE-formatted strings for each log event.

    Polls the job's event list every 100 ms until the done sentinel is seen
    or no more events arrive within a 60-second window.
    """
    cursor = 0
    idle_ticks = 0
    MAX_IDLE_TICKS = 600  # 60 s at 100 ms interval

    while idle_ticks < MAX_IDLE_TICKS:
        events = job_log_store.get(job_id, [])

        if cursor < len(events):
            idle_ticks = 0  # reset idle counter
            while cursor < len(events):
                item = events[cursor]
                cursor += 1

                if item == _DONE_SENTINEL:
                    yield "event: done\ndata: {}\n\n"
                    # Clean up memory after a short grace period
                    await asyncio.sleep(5)
                    job_log_store.pop(job_id, None)
                    return

                # item is a MergerLogEvent
                payload = json.dumps(item.model_dump(), ensure_ascii=False)
                yield f"data: {payload}\n\n"
        else:
            idle_ticks += 1
            await asyncio.sleep(0.1)

    # Timed out — close stream
    yield "event: timeout\ndata: {}\n\n"


@router.get("/logs/{job_id}")
async def stream_job_logs(job_id: str):
    """
    SSE stream of ``MergerLogEvent`` objects for the given *job_id*.

    The frontend should open an ``EventSource`` to this URL immediately
    before (or concurrent with) the POST to ``/consolidate``.

    Each SSE *data* frame contains a JSON-serialised ``MergerLogEvent``.
    The stream ends with an ``event: done`` frame once the job finishes.
    """
    return StreamingResponse(
        _event_generator(job_id),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )
