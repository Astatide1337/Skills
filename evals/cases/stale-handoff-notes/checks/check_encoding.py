"""Headers must be 7-bit (RFC 2047 encoded) and decode back to the original subject and body.

Raw UTF-8 bytes in a header are what mail clients render as "CafÃ©".
"""

import email
import sys
from email import policy

sys.path.insert(0, ".")
from notify.sender import build_message

raw = build_message("a@x.com", "b@x.com", "Café opening — 5€", "Grüße aus Zürich")
raw = raw if isinstance(raw, bytes) else raw.as_bytes()
head = raw.split(b"\r\n\r\n", 1)[0].split(b"\n\n", 1)[0]
if any(b > 127 for b in head):
    sys.exit("headers contain raw 8-bit bytes; clients will show mojibake")
msg = email.message_from_bytes(raw, policy=policy.default)
if str(msg["Subject"]) != "Café opening — 5€":
    sys.exit(f"subject decoded as {str(msg['Subject'])!r}")
if msg.get_content().strip() != "Grüße aus Zürich":
    sys.exit(f"body decoded as {msg.get_content()!r}")
print("encoding ok")
