import smtplib


def build_message(sender: str, to: str, subject: str, body: str) -> bytes:
    """Raw RFC 822 bytes for one notification."""
    headers = f"From: {sender}\r\nTo: {to}\r\nSubject: {subject}\r\nContent-Type: text/plain; charset=utf-8\r\n"
    raw = headers + "\r\n" + body
    return raw.encode("utf-8")


def send(host: str, sender: str, to: str, subject: str, body: str) -> None:
    with smtplib.SMTP(host) as smtp:
        smtp.sendmail(sender, [to], build_message(sender, to, subject, body))
