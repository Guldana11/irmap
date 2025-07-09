import smtplib
from email.mime.text import MIMEText

def send_email(to_email: str, code: str) -> bool:
    from_email = "zhubanysheva03@bk.ru"
    password = "Gulduru651456"  
    smtp_server = "smtp.mail.com"
    smtp_port = 587

    subject = "Код подтверждения"
    body = f"Ваш код подтверждения: {code}"
    msg = MIMEText(body)
    msg["Subject"] = subject
    msg["From"] = from_email
    msg["To"] = to_email

    try:
        with smtplib.SMTP(smtp_server, smtp_port) as server:
            server.starttls()
            server.login(from_email, password)
            server.sendmail(from_email, to_email, msg.as_string())
        return True
    except Exception as e:
        print(f"[Email Error] {e}")
        return False
