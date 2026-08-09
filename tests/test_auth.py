import asyncio
import os
import unittest

from starlette.testclient import TestClient


TEST_TOKEN = "test-token-" + "a" * 53
os.environ["SKILLS_GATEWAY_AUTH_TOKEN"] = TEST_TOKEN

from server import GatewayTokenVerifier, gateway_auth_token, mcp


class GatewayTokenVerifierTests(unittest.TestCase):
    def test_accepts_configured_token(self):
        verifier = GatewayTokenVerifier("a" * 64)
        access = asyncio.run(verifier.verify_token("a" * 64))

        self.assertIsNotNone(access)
        self.assertEqual(access.client_id, "skills-gateway-client")
        self.assertEqual(access.scopes, ["skills:read"])

    def test_rejects_incorrect_token(self):
        verifier = GatewayTokenVerifier("a" * 64)

        self.assertIsNone(asyncio.run(verifier.verify_token("b" * 64)))

    def test_requires_a_strong_environment_token(self):
        previous = os.environ.get("SKILLS_GATEWAY_AUTH_TOKEN")
        try:
            os.environ["SKILLS_GATEWAY_AUTH_TOKEN"] = "too-short"
            with self.assertRaisesRegex(RuntimeError, "at least 32 characters"):
                gateway_auth_token()
        finally:
            if previous is None:
                os.environ.pop("SKILLS_GATEWAY_AUTH_TOKEN", None)
            else:
                os.environ["SKILLS_GATEWAY_AUTH_TOKEN"] = previous

    def test_rejects_whitespace(self):
        previous = os.environ.get("SKILLS_GATEWAY_AUTH_TOKEN")
        try:
            os.environ["SKILLS_GATEWAY_AUTH_TOKEN"] = "a" * 63 + " "
            with self.assertRaisesRegex(RuntimeError, "must not contain whitespace"):
                gateway_auth_token()
        finally:
            if previous is None:
                os.environ.pop("SKILLS_GATEWAY_AUTH_TOKEN", None)
            else:
                os.environ["SKILLS_GATEWAY_AUTH_TOKEN"] = previous


class GatewayHTTPAuthTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client_context = TestClient(mcp.http_app())
        cls.client = cls.client_context.__enter__()

    @classmethod
    def tearDownClass(cls):
        cls.client_context.__exit__(None, None, None)

    @staticmethod
    def initialize_body() -> dict:
        return {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2025-03-26",
                "capabilities": {},
                "clientInfo": {"name": "auth-test", "version": "1"},
            },
        }

    def test_health_and_version_routes_are_public(self):
        health = self.client.get("/health")
        version = self.client.get("/version")

        self.assertEqual(health.status_code, 200)
        self.assertEqual(health.json()["status"], "ok")
        self.assertEqual(version.status_code, 200)
        self.assertEqual(version.json()["version"], "0.3.0")

    def test_mcp_rejects_missing_and_incorrect_bearer_tokens(self):
        headers = {"Accept": "application/json, text/event-stream"}
        anonymous = self.client.post("/mcp", json=self.initialize_body(), headers=headers)
        incorrect = self.client.post(
            "/mcp",
            json=self.initialize_body(),
            headers={**headers, "Authorization": "Bearer incorrect-token"},
        )

        self.assertEqual(anonymous.status_code, 401)
        self.assertEqual(incorrect.status_code, 401)

    def test_mcp_accepts_the_configured_bearer_token(self):
        response = self.client.post(
            "/mcp",
            json=self.initialize_body(),
            headers={
                "Accept": "application/json, text/event-stream",
                "Authorization": f"Bearer {TEST_TOKEN}",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn('"result"', response.text)


if __name__ == "__main__":
    unittest.main()
