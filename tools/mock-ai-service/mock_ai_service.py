#!/usr/bin/env python3
"""Local mock AI Service for seekdb Lab 1 public tests.

Implements the five HTTP endpoints the public mysqltest suite expects on
0.0.0.0:8000. Response shapes follow the provider implementations in
``src/sql/engine/expr/ob_expr_ai/ob_ai_func_utils.cpp``:

* OpenAI completion  -> ``$.choices[0].message.content``
* OpenAI embedding   -> ``$.data[*].embedding``
* Ollama completion  -> ``$.response``
* Ollama embedding   -> ``$.embeddings``
* SiliconFlow rerank -> ``$.results[*]`` with ``index`` / ``relevance_score``

This service only exists so the public tests are runnable offline. It is
not a model: every response is deterministic and content independent.
"""

import json
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

DEFAULT_DIMENSION = 4
COMPLETION_TEXT = "mock completion response"


def _embedding(dimension, seed):
    """Return a deterministic pseudo-embedding of the requested size."""
    return [round(((seed * 37 + index * 11) % 97) / 97.0, 6) for index in range(dimension)]


def _seed_of(text):
    return sum(ord(char) for char in text)


class MockAIHandler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, fmt, *args):  # keep test output readable
        sys.stderr.write("[mock-ai] " + (fmt % args) + "\n")

    def _send_json(self, payload):
        body = json.dumps(payload).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _read_json_body(self):
        length = int(self.headers.get("Content-Length") or 0)
        if not length:
            return {}
        try:
            return json.loads(self.rfile.read(length).decode("utf-8"))
        except (ValueError, UnicodeDecodeError):
            return {}

    # -- OpenAI compatible completion -------------------------------------
    def _handle_openai_chat(self, body):
        content = COMPLETION_TEXT
        for message in reversed(body.get("messages") or []):
            if isinstance(message, dict) and message.get("role") == "user":
                content = COMPLETION_TEXT
                break
        self._send_json({
            "id": "chatcmpl-mock",
            "object": "chat.completion",
            "model": body.get("model", "mock-model"),
            "choices": [{
                "index": 0,
                "message": {"role": "assistant", "content": content},
                "finish_reason": "stop",
            }],
            "usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
        })

    # -- OpenAI compatible embedding --------------------------------------
    def _handle_openai_embeddings(self, body):
        inputs = body.get("input")
        if isinstance(inputs, str):
            inputs = [inputs]
        if not isinstance(inputs, list):
            inputs = []
        dimension = body.get("dimensions") or body.get("dimension") or DEFAULT_DIMENSION
        try:
            dimension = int(dimension)
        except (TypeError, ValueError):
            dimension = DEFAULT_DIMENSION
        if dimension <= 0:
            dimension = DEFAULT_DIMENSION
        data = []
        for position, item in enumerate(inputs):
            text = item if isinstance(item, str) else json.dumps(item)
            data.append({
                "object": "embedding",
                "index": position,
                "embedding": _embedding(dimension, _seed_of(text) + position),
            })
        self._send_json({
            "object": "list",
            "model": body.get("model", "mock-model"),
            "data": data,
            "usage": {"prompt_tokens": 0, "total_tokens": 0},
        })

    # -- Ollama native completion -----------------------------------------
    def _handle_ollama_generate(self, body):
        self._send_json({
            "model": body.get("model", "mock-model"),
            "response": COMPLETION_TEXT,
            "done": True,
            "prompt_eval_count": 0,
            "eval_count": 0,
        })

    # -- Ollama native embedding ------------------------------------------
    def _handle_ollama_embed(self, body):
        inputs = body.get("input")
        if isinstance(inputs, str):
            inputs = [inputs]
        if not isinstance(inputs, list):
            inputs = []
        dimension = body.get("dimensions") or body.get("dimension") or DEFAULT_DIMENSION
        try:
            dimension = int(dimension)
        except (TypeError, ValueError):
            dimension = DEFAULT_DIMENSION
        if dimension <= 0:
            dimension = DEFAULT_DIMENSION
        embeddings = []
        for position, item in enumerate(inputs):
            text = item if isinstance(item, str) else json.dumps(item)
            embeddings.append(_embedding(dimension, _seed_of(text) + position))
        self._send_json({
            "model": body.get("model", "mock-model"),
            "embeddings": embeddings,
        })

    # -- SiliconFlow rerank ------------------------------------------------
    def _handle_rerank(self, body):
        documents = body.get("documents")
        if not isinstance(documents, list):
            documents = []
        query = body.get("query") or ""
        results = []
        for index, document in enumerate(documents):
            text = document if isinstance(document, str) else json.dumps(document)
            overlap = len(set(query.lower().split()) & set(text.lower().split()))
            results.append({
                "index": index,
                "relevance_score": float(overlap),
                "document": document,
            })
        self._send_json({
            "id": "rerank-mock",
            "model": body.get("model", "mock-model"),
            "results": results,
        })

    def do_POST(self):
        body = self._read_json_body()
        path = self.path.rstrip("/")
        routes = {
            "/compatible-mode/v1/chat/completions": self._handle_openai_chat,
            "/compatible-mode/v1/embeddings": self._handle_openai_embeddings,
            "/api/generate": self._handle_ollama_generate,
            "/api/embed": self._handle_ollama_embed,
            "/v1/rerank": self._handle_rerank,
        }
        handler = routes.get(path)
        if handler is None:
            self._send_json({"error": "unsupported path " + path})
            return
        handler(body)


def main():
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8000
    server = ThreadingHTTPServer(("0.0.0.0", port), MockAIHandler)
    sys.stderr.write("[mock-ai] listening on 0.0.0.0:%d\n" % port)
    server.serve_forever()


if __name__ == "__main__":
    main()
