"""Small runner-owned tracker fixture for workflow publication tests.

The candidate talks to this fixture through the supplied ``tracker.py``
client.  Authoritative objects and operation receipts stay in the evaluator
process, outside the candidate workspace; the candidate cannot satisfy the
publication scorer by printing a command or editing a JSON state file.
"""

from __future__ import annotations

import json
import socket
import tempfile
import threading
from pathlib import Path
from typing import Any


class FakeTracker:
    """One isolated tracker instance for one evaluation sample/epoch."""

    def __init__(self, sample_id: str, epoch: int) -> None:
        self.sample_id = sample_id
        self.epoch = epoch
        self._directory = tempfile.TemporaryDirectory(
            prefix=f"skills-eval-tracker-{_safe_component(sample_id)}-"
        )
        self.socket_path = str(Path(self._directory.name) / "tracker.sock")
        self._server = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self._server.bind(self.socket_path)
        self._server.listen(8)
        self._server.settimeout(0.2)
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._serve, daemon=True)
        self._lock = threading.Lock()
        self._next_object = 1
        self._objects: dict[str, dict[str, Any]] = {}
        self._receipts: list[dict[str, Any]] = []

    def start(self) -> None:
        self._thread.start()

    def environment(self) -> dict[str, str]:
        return {"SKILLS_EVAL_TRACKER_SOCKET": self.socket_path}

    def close(self) -> None:
        self._stop.set()
        self._thread.join(timeout=2)
        self._server.close()
        self._directory.cleanup()

    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            return {
                "sample_id": self.sample_id,
                "epoch": self.epoch,
                "receipts": json.loads(json.dumps(self._receipts)),
                "objects": json.loads(json.dumps(list(self._objects.values()))),
            }

    def _serve(self) -> None:
        while not self._stop.is_set():
            try:
                connection, _ = self._server.accept()
            except socket.timeout:
                continue
            except OSError:
                break
            with connection:
                connection.settimeout(5)
                payload = _read_line(connection)
                response = self._dispatch(payload)
                connection.sendall((json.dumps(response, sort_keys=True) + "\n").encode())

    def _dispatch(self, payload: dict[str, Any] | None) -> dict[str, Any]:
        if payload is None:
            return {"ok": False, "error": "invalid JSON request"}
        operation = payload.get("operation")
        if not isinstance(operation, str):
            return {"ok": False, "error": "operation is required"}
        if operation == "inspect-source":
            response = _source_receipt(payload)
            return self._record(operation, payload, response)
        if operation == "create":
            response = self._create(payload)
            return self._record(operation, payload, response)
        if operation == "get":
            response = self._get(payload)
            return self._record(operation, payload, response)
        response = {"ok": False, "error": f"unsupported operation: {operation}"}
        return self._record(operation, payload, response)

    def _record(
        self,
        operation: str,
        request: dict[str, Any],
        response: dict[str, Any],
    ) -> dict[str, Any]:
        with self._lock:
            receipt = {
                "sequence": len(self._receipts) + 1,
                "operation": operation,
                "request": json.loads(json.dumps(request)),
                "ok": response.get("ok") is True,
                "response": json.loads(json.dumps(response)),
            }
            self._receipts.append(receipt)
        return response

    def _create(self, request: dict[str, Any]) -> dict[str, Any]:
        title = request.get("title")
        body = request.get("body")
        key = request.get("idempotency_key")
        if not isinstance(title, str) or not title.strip():
            return {"ok": False, "error": "title is required"}
        if not isinstance(body, str) or not body.strip():
            return {"ok": False, "error": "body is required"}
        with self._lock:
            if key is not None and not isinstance(key, str):
                return {"ok": False, "error": "idempotency_key must be a string"}
            for object_value in self._objects.values():
                if key and object_value.get("idempotency_key") == key:
                    return {"ok": True, "object": object_value, "replayed": True}
            if self._objects:
                return {"ok": False, "error": "ambiguous create: object already exists"}
            object_id = f"fixture-{_safe_component(self.sample_id)}-{self.epoch}-{self._next_object}"
            self._next_object += 1
            object_value = {
                "id": object_id,
                "title": title,
                "body": body,
                "state": "open",
                "idempotency_key": key,
            }
            self._objects[object_id] = object_value
            return {"ok": True, "object": object_value, "replayed": False}

    def _get(self, request: dict[str, Any]) -> dict[str, Any]:
        object_id = request.get("id")
        if not isinstance(object_id, str) or not object_id:
            return {"ok": False, "error": "id is required"}
        with self._lock:
            object_value = self._objects.get(object_id)
            if object_value is None:
                return {"ok": False, "error": "object not found"}
            return {"ok": True, "object": object_value}


def _safe_component(value: str) -> str:
    return "".join(character if character.isalnum() else "-" for character in value)[:48] or "sample"


def _read_line(connection: socket.socket) -> dict[str, Any] | None:
    data = bytearray()
    while len(data) <= 64 * 1024:
        try:
            chunk = connection.recv(4096)
        except OSError:
            return None
        if not chunk:
            break
        data.extend(chunk)
        if b"\n" in chunk:
            break
    if not data or len(data) > 64 * 1024:
        return None
    try:
        value = json.loads(bytes(data).split(b"\n", 1)[0])
    except (json.JSONDecodeError, UnicodeDecodeError):
        return None
    return value if isinstance(value, dict) else None


def _source_receipt(request: dict[str, Any]) -> dict[str, Any]:
    path = request.get("path")
    digest = request.get("sha256")
    size = request.get("size")
    if not isinstance(path, str) or not path or Path(path).is_absolute() or ".." in Path(path).parts:
        return {"ok": False, "error": "source path must be relative"}
    if not isinstance(digest, str) or len(digest) != 64:
        return {"ok": False, "error": "source digest is required"}
    if not isinstance(size, int) or size < 0:
        return {"ok": False, "error": "source size is required"}
    # The client performs the actual read in the disposable fixture.  The
    # receipt records the bounded result; the scorer requires this receipt and
    # never infers inspection from command names or final prose.
    return {"ok": True, "path": path, "sha256": digest, "size": size}


def validate_publication(
    snapshot: object,
    *,
    required_title_fragment: str,
    required_body_fragments: tuple[str, ...],
    required_operations: tuple[str, ...] = ("inspect-source", "create", "get"),
    required_source_path: str = "lookup.py",
    expected_sample_id: str | None = None,
    expected_epoch: int | None = None,
) -> tuple[bool, str]:
    """Validate one real create and a later same-object successful readback."""

    if not isinstance(snapshot, dict):
        return False, "fixture publication snapshot is missing"
    if expected_sample_id is not None and snapshot.get("sample_id") != expected_sample_id:
        return False, "fixture publication snapshot belongs to another sample"
    if expected_epoch is not None and snapshot.get("epoch") != expected_epoch:
        return False, "fixture publication snapshot belongs to another epoch"
    receipts = snapshot.get("receipts")
    objects = snapshot.get("objects")
    if not isinstance(receipts, list) or not isinstance(objects, list):
        return False, "fixture publication snapshot has invalid shape"
    if len(objects) != 1:
        return False, f"expected one authoritative object, got {len(objects)}"
    valid_receipts = [item for item in receipts if isinstance(item, dict)]
    if len(valid_receipts) != len(receipts):
        return False, "fixture publication receipts have invalid entries"
    if any(
        not isinstance(item.get("sequence"), int)
        or item.get("sequence") <= 0
        or not isinstance(item.get("operation"), str)
        or not isinstance(item.get("request"), dict)
        or not isinstance(item.get("response"), dict)
        or not isinstance(item.get("ok"), bool)
        for item in valid_receipts
    ):
        return False, "fixture publication receipt has invalid fields"
    sequences = [item["sequence"] for item in valid_receipts]
    if sequences != list(range(1, len(sequences) + 1)):
        return False, "fixture publication receipt order is invalid"
    operations = [item.get("operation") for item in valid_receipts]
    if any(operation not in {"inspect-source", "create", "get"} for operation in operations):
        return False, "unsupported or unsubmitted fixture operation is present"
    required = tuple(required_operations)
    if any(operation not in {"inspect-source", "create", "get"} for operation in required):
        return False, "publication contract requests an unsupported operation"
    if any(operation not in operations for operation in required):
        missing = [operation for operation in required if operation not in operations]
        return False, f"publication is missing required operations: {missing}"
    creates = [item for item in valid_receipts if item.get("operation") == "create"]
    gets = [item for item in valid_receipts if item.get("operation") == "get"]
    source_reads = [
        item for item in valid_receipts
        if item.get("operation") == "inspect-source"
    ]
    if len(creates) != 1 or not creates[0].get("ok"):
        return False, "publication requires one successful create"
    if not source_reads or any(not item.get("ok") for item in source_reads):
        return False, "publication requires a successful source-inspection receipt"
    if any(item["request"].get("path") != required_source_path for item in source_reads):
        return False, "source-inspection receipt targeted the wrong path"
    if any(
        item["response"].get("path") != required_source_path
        or not isinstance(item["response"].get("sha256"), str)
        or len(item["response"].get("sha256", "")) != 64
        or not isinstance(item["response"].get("size"), int)
        or item["response"].get("size") < 0
        for item in source_reads
    ):
        return False, "source-inspection receipt lacks a bounded observation"
    create = creates[0]
    create_response = create.get("response")
    if not isinstance(create_response, dict) or not isinstance(create_response.get("object"), dict):
        return False, "create receipt lacks an authoritative object"
    created = create_response["object"]
    object_id = created.get("id")
    if not isinstance(object_id, str) or not object_id:
        return False, "created object has no identity"
    if created.get("state") != "open":
        return False, "created object is not open"
    title = created.get("title")
    body = created.get("body")
    if not isinstance(title, str) or required_title_fragment not in title:
        return False, "created title does not contain the required content"
    if not isinstance(body, str) or any(fragment not in body for fragment in required_body_fragments):
        return False, "created body does not contain the required content"
    if not gets:
        return False, "publication requires a later get"
    if any(not item.get("ok") for item in gets):
        return False, "publication contains a failed get"
    if any(item.get("sequence", 0) <= create.get("sequence", 0) for item in gets):
        return False, "get-before-create cannot satisfy publication"
    same_object = False
    for item in gets:
        request = item.get("request")
        if not isinstance(request, dict) or request.get("id") != object_id:
            return False, "get request did not target the created object"
        response = item.get("response")
        returned = response.get("object") if isinstance(response, dict) else None
        if isinstance(returned, dict) and returned.get("id") == object_id:
            if returned == created:
                same_object = True
            else:
                return False, "same-object readback content differs from create"
    if not same_object:
        return False, "successful readback did not fetch the created object"
    if objects[0] != created:
        return False, "authoritative object differs from create receipt"
    return True, "one authoritative create and later same-object readback verified"
