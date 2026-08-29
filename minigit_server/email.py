import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from .config import EMAIL_USER, EMAIL_PASS, EMAIL_FROM


def send_otp_email(to_email: str, otp_code: str) -> bool:
    """
    Send OTP code to user's email address using Gmail's SSL server.
    """
    if not EMAIL_USER or not EMAIL_PASS:
        print("Warning: Cannot send OTP email. EMAIL_USER and EMAIL_PASS not configured.")
        return False

    subject = "MiniGit Registration Verification"
    body = f"""
    Your MiniGit registration verification code is: {otp_code}

    This code will expire in 5 minutes.
    If you didn't register for a MiniGit account, please ignore this email.
    """

    msg = MIMEMultipart()
    msg['From'] = EMAIL_FROM
    msg['To'] = to_email
    msg['Subject'] = subject

    msg.attach(MIMEText(body, 'plain'))

    try:
        # Try SSL on port 465 with 10s timeout
        try:
            with smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=10) as smtp_server:
                smtp_server.login(EMAIL_USER, EMAIL_PASS)
                smtp_server.send_message(msg)
            return True
        except Exception as ssl_err:
            # Fallback to STARTTLS on port 587
            print(f"[Email] SSL (465) failed ({ssl_err}), trying STARTTLS (587)...")
            with smtplib.SMTP("smtp.gmail.com", 587, timeout=10) as smtp_server:
                smtp_server.ehlo()
                smtp_server.starttls()
                smtp_server.ehlo()
                smtp_server.login(EMAIL_USER, EMAIL_PASS)
                smtp_server.send_message(msg)
            return True
    except Exception as e:
        print(f"[Email Error] Failed to send OTP to {to_email}: {e}")
        return False