import smtplib
import os
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders

# --- Config ---
GMAIL_ADDRESS = "dylanmartinez6@gmail.com"
APP_PASSWORD   = "krebtgxggwuylwlm"
TO_ADDRESS     = "dylanmartinez6@gmail.com"
DRAFT_BOARD    = "output/draft_board.html"

def send_draft_board():
    if not os.path.exists(DRAFT_BOARD):
        print(f"ERROR: {DRAFT_BOARD} not found. Run 'python main.py' first.")
        return

    msg = MIMEMultipart()
    msg["From"]    = GMAIL_ADDRESS
    msg["To"]      = TO_ADDRESS
    msg["Subject"] = "🏆 Fantasy Draft Board — Tonight 8PM"

    body = """\
Your draft board is attached. Open the HTML file in your phone's browser for the full interactive board with filters and search.

Good luck tonight! 🎯
"""
    msg.attach(MIMEText(body, "plain"))

    # Attach the HTML file
    with open(DRAFT_BOARD, "rb") as f:
        part = MIMEBase("application", "octet-stream")
        part.set_payload(f.read())
    encoders.encode_base64(part)
    part.add_header("Content-Disposition", f'attachment; filename="draft_board.html"')
    msg.attach(part)

    # Send
    print("Connecting to Gmail...")
    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(GMAIL_ADDRESS, APP_PASSWORD)
        server.sendmail(GMAIL_ADDRESS, TO_ADDRESS, msg.as_string())

    print(f"✅ Draft board sent to {TO_ADDRESS}!")

if __name__ == "__main__":
    send_draft_board()
