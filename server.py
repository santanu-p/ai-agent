from __future__ import annotations

import json
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any, Dict
from urllib.parse import parse_qs, urlparse

from aegisworld_service import AegisWorldService


service = AegisWorldService()


def read_json(handler: BaseHTTPRequestHandler) -> Dict[str, Any]:
    length = int(handler.headers.get("Content-Length", "0"))
    if length == 0:
        return {}
    body = handler.rfile.read(length)
    return json.loads(body.decode("utf-8"))


class AegisWorldHandler(BaseHTTPRequestHandler):
    def _send(self, status: HTTPStatus, payload: Dict[str, Any]) -> None:
        encoded = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)

    def do_POST(self) -> None:  # noqa: N802
        try:
            payload = read_json(self)
            parsed = urlparse(self.path)
            path = parsed.path

            if path == "/v1/goals":
                self._send(HTTPStatus.CREATED, service.create_goal(payload))
                return
            if path == "/v1/agents":
                self._send(HTTPStatus.CREATED, service.create_agent(payload))
                return
            if path.startswith("/v1/agents/") and path.endswith("/execute"):
                agent_id = path.split("/")[3]
                goal_id = payload["goal_id"]
                self._send(HTTPStatus.OK, service.execute(agent_id=agent_id, goal_id=goal_id))
                return
            if path.startswith("/v1/agents/") and path.endswith("/policy"):
                agent_id = path.split("/")[3]
                self._send(HTTPStatus.OK, service.update_agent_policy(agent_id, payload))
                return
            if path == "/v1/domain/social/projects":
                self._send(HTTPStatus.CREATED, service.create_domain_project("social", payload))
                return
            if path == "/v1/domain/dev/pipelines":
                self._send(HTTPStatus.CREATED, service.create_domain_project("dev", payload))
                return
            if path == "/v1/domain/games/projects":
                self._send(HTTPStatus.CREATED, service.create_domain_project("games", payload))
                return
            if path == "/v1/policies/simulate":
                self._send(HTTPStatus.OK, service.simulate_policy(payload))
                return
            if path == "/v1/scheduler/assign":
                self._send(HTTPStatus.OK, service.assign_goal(payload))
                return
            if path == "/v1/scheduler/run":
                max_runs = int(payload.get("max_runs", 10))
                self._send(HTTPStatus.OK, service.run_scheduler(max_runs=max_runs))
                return
            if path == "/v1/learning/compact":
                params = parse_qs(parsed.query)
                agent_id = payload.get("agent_id") or params.get("agent_id", [None])[0]
                if not agent_id:
                    self._send(HTTPStatus.BAD_REQUEST, {"error": "missing agent_id"})
                    return
                max_items = int(payload.get("max_items", params.get("max_items", [100])[0]))
                self._send(HTTPStatus.OK, service.compact_memory(agent_id=agent_id, max_items=max_items))
                return
        except json.JSONDecodeError:
            self._send(HTTPStatus.BAD_REQUEST, {"error": "malformed JSON payload"})
            return
        except KeyError as exc:
            self._send(HTTPStatus.BAD_REQUEST, {"error": f"missing field: {exc}"})
            return
        except Exception as exc:  # pragma: no cover
            self._send(HTTPStatus.INTERNAL_SERVER_ERROR, {"error": str(exc)})
            return

        self._send(HTTPStatus.NOT_FOUND, {"error": "not found"})

    def do_GET(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        path = parsed.path

        if path == "/healthz":
            self._send(HTTPStatus.OK, {"status": "ok"})
            return

        if path.startswith("/v1/goals/"):
            goal_id = path.split("/")[3]
            goal = service.get_goal(goal_id)
            if goal is None:
                self._send(HTTPStatus.NOT_FOUND, {"error": "goal not found"})
            else:
                self._send(HTTPStatus.OK, goal)
            return

        if path.startswith("/v1/agents/") and path.endswith("/memory"):
            agent_id = path.split("/")[3]
            if agent_id not in service.agents:
                self._send(HTTPStatus.NOT_FOUND, {"error": "agent not found"})
                return
            self._send(HTTPStatus.OK, service.get_memory(agent_id))
            return

        if path.startswith("/v1/agents/") and len(path.split("/")) == 4:
            agent_id = path.split("/")[3]
            agent = service.get_agent(agent_id)
            if agent is None:
                self._send(HTTPStatus.NOT_FOUND, {"error": "agent not found"})
            else:
                self._send(HTTPStatus.OK, agent)
            return

        if path == "/v1/incidents":
            self._send(HTTPStatus.OK, {"incidents": service.list_incidents()})
            return

        if path == "/v1/traces":
            self._send(HTTPStatus.OK, {"traces": service.list_traces()})
            return

        if path == "/v1/reflections":
            self._send(HTTPStatus.OK, {"reflections": service.list_reflections()})
            return

        if path == "/v1/changes":
            self._send(HTTPStatus.OK, {"changes": service.list_changes()})
            return

        if path == "/v1/scheduler/queue":
            self._send(HTTPStatus.OK, {"queue": service.get_queue()})
            return

        if path == "/v1/learning/summary":
            self._send(HTTPStatus.OK, service.learning_summary())
            return

        if path == "/v1/stats":
            self._send(HTTPStatus.OK, service.stats())
            return

        self._send(HTTPStatus.NOT_FOUND, {"error": "not found"})


def run_server(host: str = "0.0.0.0", port: int = 8080) -> None:
    httpd = ThreadingHTTPServer((host, port), AegisWorldHandler)
    print(f"AegisWorld API listening on http://{host}:{port}")
    httpd.serve_forever()


if __name__ == "__main__":
    run_server()
