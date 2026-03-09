import inspect
from typing import Any
from uuid import UUID

from fastapi import APIRouter, HTTPException, Request

from indigoapi.analyses.registry import get_analysis, list_analyses
from indigoapi.models import AnalysisRequest, AnalysisResult

ROUTER = APIRouter()


@ROUTER.get("/get_analyses")
async def available_analyses() -> list[dict[str, Any]]:
    analyses_info = []
    for name in list_analyses():
        func = get_analysis(name)
        sig = inspect.signature(func)
        params = []
        for p in sig.parameters.values():
            params.append(
                {
                    "name": p.name,
                    "default": p.default
                    if p.default != inspect.Parameter.empty
                    else None,
                    "annotation": str(p.annotation)
                    if p.annotation != inspect.Parameter.empty
                    else "Any",
                }
            )
        analyses_info.append({"name": name, "parameters": params})
    return analyses_info


@ROUTER.post("/analyse")
async def analyse(request: Request, job: AnalysisRequest):
    queue = request.app.state.queue_manager
    await queue.enqueue(job)
    return {"request_id": job.request_id}


@ROUTER.get("/result/{request_id}", response_model=AnalysisResult)
async def result(request: Request, request_id: UUID):
    queue = request.app.state.queue_manager
    if request_id not in queue.results:
        raise HTTPException(404, "Result not found")
    result, _ = queue.results[request_id]
    return result
