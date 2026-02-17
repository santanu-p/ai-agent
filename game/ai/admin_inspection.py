from __future__ import annotations

import argparse
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

from game.ai.policy_guard import audit_summary, read_recent_audit_entries


class AuditInspectionHandler(BaseHTTPRequestHandler):
    def _json(self, code: int, payload: dict) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        if parsed.path == "/changes":
            params = parse_qs(parsed.query)
            limit = int(params.get("limit", [20])[0])
            self._json(200, {"entries": read_recent_audit_entries(limit=limit)})
            return
        if parsed.path == "/stats":
            self._json(200, {"summary": audit_summary()})
            return
        self._json(404, {"error": "not_found"})


def _run_server(host: str, port: int) -> None:
    server = ThreadingHTTPServer((host, port), AuditInspectionHandler)
    print(f"Serving admin inspection API on http://{host}:{port}")
    server.serve_forever()


def main() -> None:
    parser = argparse.ArgumentParser(description="Inspect autonomous deployment activity")
    sub = parser.add_subparsers(dest="command", required=True)

    p_recent = sub.add_parser("recent", help="Show recent autonomy audit entries")
    p_recent.add_argument("--limit", type=int, default=20)

    sub.add_parser("stats", help="Show aggregate counts of proposed/applied/reverted")

    p_serve = sub.add_parser("serve", help="Serve a local HTTP inspection API")
    p_serve.add_argument("--host", default="127.0.0.1")
    p_serve.add_argument("--port", default=8089, type=int)

    args = parser.parse_args()
    if args.command == "recent":
        print(json.dumps(read_recent_audit_entries(limit=args.limit), indent=2))
    elif args.command == "stats":
        print(json.dumps(audit_summary(), indent=2))
    elif args.command == "serve":
        _run_server(args.host, args.port)


if __name__ == "__main__":
    main()
