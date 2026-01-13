import os
import smtplib

EMAIL = os.getenv("EMAIL_FROM")
PASSWORD = os.getenv("EMAIL_PASSWORD")

print("EMAIL:", EMAIL)
print("PASSWORD OK:", bool(PASSWORD))

try:
    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(EMAIL, PASSWORD)
        print("LOGIN SMTP OK")
except Exception as e:
    print("ERRO SMTP:")
    print(e)
