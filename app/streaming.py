"""Live investigation progress over newline-delimited JSON."""
import json
from agents.llm import provider
from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

router = APIRouter()

class StreamRequest(BaseModel):
    incident_id: str

def install_streaming(graph, config_factory, evidence_factory, retriever_factory, response_factory):
    @router.post("/api/v1/investigations/stream")
    def stream_investigation(request: StreamRequest):
        def encode(value):
            return json.dumps(value, default=str) + "\n"

        def events():
            try:
                evidence = evidence_factory(request.incident_id)
                config = config_factory(request.incident_id)
                saved = graph.get_state(config)
                if saved.values:
                    yield encode({"type":"status","message":"Loading saved investigation"})
                    yield encode({"type":"result","data":response_factory(saved.values).model_dump(mode="json")})
                    return
                yield encode({"type":"status","message":"Preparing retrieval and evidence"})
                retriever = retriever_factory()
                yield encode({"type":"status","message":"Running investigation agents"})
                initial = {"incident_id":evidence.incident.incident_id,
                           "incident_summary":evidence.incident.description,
                           "evidence":evidence}
                for update in graph.stream(initial,
                        config=config_factory(request.incident_id, knowledge_retriever=retriever),
                        stream_mode="updates"):
                    for node, delta in update.items():
                        if node == "__interrupt__":
                            yield encode({"type":"status","message":"Awaiting human approval"})
                        else:
                            yield encode({"type":"node","node":node,
                                          "message":node.replace("_"," ").title()+" completed"})
                            if node == "supervisor" and isinstance(delta, dict):
                                next_agent = delta.get("next_agent")
                                if next_agent and next_agent != "complete":
                                    yield encode({"type":"status",
                                                  "message":"Running "+next_agent.replace("_"," ").title()
                                                  + (" (waiting for "+provider().title()+" LLM response)" if next_agent in ("root_cause","critic") else "")})
                            if isinstance(delta, dict):
                                for finding in delta.get("findings", []):
                                    if getattr(finding,"agent","") in ("root_cause_llm","critic_llm"):
                                        yield encode({"type":"llm","agent":finding.agent,
                                                      "text":finding.summary})
                final = graph.get_state(config)
                if not final.values:
                    raise RuntimeError("No saved investigation result")
                yield encode({"type":"result","data":response_factory(final.values).model_dump(mode="json")})
            except Exception as exc:
                yield encode({"type":"error","message":str(exc)})
        return StreamingResponse(events(),media_type="application/x-ndjson",
                                 headers={"Cache-Control":"no-cache"})
