import email
import unittest

from notify.digest import daily_digest
from notify.sender import build_message


class SenderTests(unittest.TestCase):
    def test_ascii_subject(self):
        msg = email.message_from_bytes(build_message("a@x.com", "b@x.com", "Hello", "Body"))
        self.assertEqual(msg["Subject"], "Hello")
        self.assertEqual(msg.get_payload(decode=True).decode().strip(), "Body")

    def test_digest(self):
        msg = email.message_from_bytes(daily_digest("b@x.com", ["one", "two"]))
        self.assertEqual(msg["Subject"], "Your digest (2 items)")


if __name__ == "__main__":
    unittest.main()
