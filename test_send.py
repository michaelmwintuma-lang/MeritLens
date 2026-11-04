"""
Example script demonstrating how to import and use the email sender.

Usage:
    # Send to the default account (meritlens29@gmail.com):
    python test_send.py

    # Or specify any recipient address:
    python test_send.py recipient@example.com
"""
import sys
from scripts.send_email import send_email

# Pick recipient from command-line argument or default to the platform email
recipient = sys.argv[1] if len(sys.argv) > 1 else "meritlens29@gmail.com"

print(f"Preparing to send test email to: {recipient}...")

subject = "Test Email from MeritLens Standalone Script"
body_text = (
    f"Hello,\n\n"
    f"This is a test email sent using Python standard library smtplib and Gmail SMTP.\n"
    f"Recipient: {recipient}\n"
    f"Status: Operational\n"
)

body_html = f"""
<!DOCTYPE html>
<html>
<body style="font-family: Arial, sans-serif; background-color: #f8fafc; padding: 20px; color: #1e293b;">
  <div style="max-width: 500px; margin: 0 auto; background: #ffffff; border: 1px solid #e2e8f0; border-radius: 10px; padding: 24px; box-shadow: 0 2px 4px rgba(0,0,0,0.05);">
    <h2 style="color: #0F2A44; margin-top: 0;">MeritLens SMTP Test</h2>
    <p>This email was successfully sent from your standalone Python script using <strong>Gmail SMTP</strong> with <strong>STARTTLS</strong>.</p>
    <div style="background: #f1f5f9; padding: 12px 16px; border-radius: 6px; font-size: 14px; margin: 16px 0;">
      <div><strong>To:</strong> {recipient}</div>
      <div><strong>Status:</strong> Success</div>
    </div>
    <p style="color: #64748b; font-size: 12px; margin-bottom: 0;">Sent via smtplib on port 587.</p>
  </div>
</body>
</html>
"""

# Send the email
result = send_email(
    to=recipient,
    subject=subject,
    body_text=body_text,
    body_html=body_html,
)

# Output result
if result.get("success"):
    print("[SUCCESS]", result.get("message"))
else:
    print("[ERROR]", result.get("message"))

