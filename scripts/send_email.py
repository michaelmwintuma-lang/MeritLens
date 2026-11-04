"""
Standalone Gmail SMTP Email Sender

Can be run directly from the command line:
    python scripts/send_email.py recipient@example.com "Test Subject" "Hello from MeritLens!"

Or imported as a module in any Python project:
    from send_email import send_email
    send_email(to="recipient@example.com", subject="Hello", body_text="Test message")
"""
import argparse
import os
import smtplib
import sys
from email.message import EmailMessage
from email.utils import formataddr
from pathlib import Path


# Default configuration (can be overridden via environment variables or .env)
DEFAULT_SMTP_HOST = "smtp.gmail.com"
DEFAULT_SMTP_PORT = 587
DEFAULT_SMTP_USER = "meritlens29@gmail.com"
DEFAULT_SMTP_PASSWORD = "zuxx bbgf rfmz atzb"  # 16-character Google App Password
DEFAULT_SENDER_NAME = "MeritLens"


def load_env_file(env_path: Path | None = None) -> None:
    """Reads simple KEY=VALUE pairs from a .env file if present."""
    if env_path is None:
        # Check current directory and backend/
        candidates = [Path(".env"), Path("backend/.env"), Path("../backend/.env")]
        for p in candidates:
            if p.exists():
                env_path = p
                break

    if env_path and env_path.exists():
        for line in env_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, val = line.split("=", 1)
            os.environ.setdefault(key.strip(), val.strip().strip('"').strip("'"))


def build_message(
    to: str,
    subject: str,
    body_text: str,
    body_html: str | None = None,
    sender_name: str | None = None,
    sender_email: str | None = None,
) -> EmailMessage:
    """Constructs a standard multipart EmailMessage (plain text + optional HTML)."""
    message = EmailMessage()
    message["Subject"] = subject
    from_name = sender_name or os.getenv("SMTP_SENDER_NAME", DEFAULT_SENDER_NAME)
    from_email = sender_email or os.getenv("SMTP_USER", DEFAULT_SMTP_USER)
    message["From"] = formataddr((from_name, from_email))
    message["To"] = to

    # Base plain-text version
    message.set_content(body_text)

    # Optional HTML alternative
    if body_html:
        message.add_alternative(body_html, subtype="html")

    return message


def send_email(
    to: str,
    subject: str,
    body_text: str,
    body_html: str | None = None,
    smtp_host: str | None = None,
    smtp_port: int | None = None,
    smtp_user: str | None = None,
    smtp_password: str | None = None,
    sender_name: str | None = None,
    timeout: int = 15,
) -> dict:
    """
    Sends an email via Gmail SMTP using STARTTLS (port 587).
    Returns a status dict: {"success": True/False, "message": "..."}
    """
    load_env_file()

    host = smtp_host or os.getenv("SMTP_HOST", DEFAULT_SMTP_HOST)
    port = smtp_port or int(os.getenv("SMTP_PORT", str(DEFAULT_SMTP_PORT)))
    user = smtp_user or os.getenv("SMTP_USER", DEFAULT_SMTP_USER)
    raw_pass = smtp_password or os.getenv("SMTP_PASSWORD", DEFAULT_SMTP_PASSWORD)
    password = raw_pass.replace(" ", "")  # Google shows app passwords with spaces

    message = build_message(
        to=to,
        subject=subject,
        body_text=body_text,
        body_html=body_html,
        sender_name=sender_name,
        sender_email=user,
    )

    try:
        # Step 1: Connect to SMTP server
        with smtplib.SMTP(host, port, timeout=timeout) as server:
            # Step 2: Identify and upgrade connection to TLS
            server.ehlo()
            server.starttls()
            server.ehlo()

            # Step 3: Authenticate with App Password
            server.login(user, password)

            # Step 4: Transmit the message
            server.send_message(message)

        return {"success": True, "message": f"Email successfully sent to {to}"}

    except smtplib.SMTPAuthenticationError as err:
        return {
            "success": False,
            "error": "Authentication failed",
            "message": f"Gmail refused credentials ({err.smtp_code}: {err.smtp_error.decode() if isinstance(err.smtp_error, bytes) else err.smtp_error}). Ensure 2-Step Verification is enabled and a valid 16-character App Password is used.",
        }
    except smtplib.SMTPException as err:
        return {"success": False, "error": "SMTPException", "message": str(err)}
    except OSError as err:
        return {"success": False, "error": "NetworkError", "message": f"Could not connect to {host}:{port}: {err}"}


def main():
    parser = argparse.ArgumentParser(description="Standalone Gmail SMTP Emailer")
    parser.add_argument("to", help="Recipient email address")
    parser.add_argument("subject", nargs="?", default="Test Email from MeritLens", help="Email subject")
    parser.add_argument("body", nargs="?", default="This is a test email sent via Gmail SMTP.", help="Email body text")
    parser.add_argument("--html", help="Optional HTML body", default=None)
    parser.add_argument("--check-only", action="store_true", help="Only verify SMTP credentials without sending")

    args = parser.parse_args()

    if args.check_only:
        load_env_file()
        host = os.getenv("SMTP_HOST", DEFAULT_SMTP_HOST)
        port = int(os.getenv("SMTP_PORT", str(DEFAULT_SMTP_PORT)))
        user = os.getenv("SMTP_USER", DEFAULT_SMTP_USER)
        pwd = os.getenv("SMTP_PASSWORD", DEFAULT_SMTP_PASSWORD).replace(" ", "")

        print(f"Testing SMTP handshake to {host}:{port} as {user}...")
        try:
            with smtplib.SMTP(host, port, timeout=10) as s:
                s.starttls()
                s.login(user, pwd)
                print("[SUCCESS] SMTP Login Successful!")
                sys.exit(0)
        except Exception as e:
            print(f"[ERROR] SMTP connection failed: {e}")
            sys.exit(1)

    result = send_email(
        to=args.to,
        subject=args.subject,
        body_text=args.body,
        body_html=args.html,
    )

    if result["success"]:
        print(f"[SUCCESS] {result['message']}")
    else:
        print(f"[ERROR] Failed: {result['message']}")
        sys.exit(1)


if __name__ == "__main__":
    main()
