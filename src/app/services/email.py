from email.mime.text import MIMEText
from dotenv import load_dotenv
import os
import aiosmtplib

load_dotenv()


async def send_confirmation_email(email: str, token: str):
    message = MIMEText(
        f"Подтвердите email: {os.getenv('API_URL')}/confirm-email?token={token}"
    )
    message["Subject"] = "Подтверждение регистрации"
    message["From"] = os.getenv("SMTP_USER")
    message["To"] = email

    await aiosmtplib.send(
        message,
        hostname=os.getenv("SMTP_HOST"),
        port=os.getenv("SMTP_PORT"),
        username=os.getenv("SMTP_USER"),
        password=os.getenv("SMTP_PASSWORD"),
        use_tls=True,
    )
