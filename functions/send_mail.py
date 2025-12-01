from config import settings  # optional
import boto3
import secrets
from datetime import datetime, timedelta, timezone

def send_welcome_email(first_name:str, email: str, password: str):
    """
    Sends a welcome email with credentials using AWS SES.
    Includes both HTML and Plain Text versions.
    """
    
    # Initialize SES Client
    ses = boto3.client(
        "ses",
        region_name=settings.AWS_SES_REGION,
        aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
        aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
    )

    # Translated Subject
    subject = "Dobrodošli u Chosen International - Vaši pristupni podaci"

    # 1. Plain Text Version (Fallback)
    text_body = f"""
Pozdrav {first_name},

Dobrodošli u Chosen International. Vaš korisnički račun je uspješno kreiran.

Ovo su Vaši podaci za prijavu:
----------------------------
E-mail: {email}
Lozinka: {password}
----------------------------

Radi Vaše sigurnosti, molimo Vas da odmah promijenite lozinku u mobilnoj aplikaciji.

Lijep pozdrav,
Chosen International Tim
"""

    # 2. HTML Version (Design)
    # We inject the {email} and {password} variables into the template using f-string
    html_body = f"""
<!DOCTYPE html>
<html>
<head>
<style>
    body, td {{ font-family: 'Avenir', 'Segoe UI', 'Roboto', Helvetica, Arial, sans-serif; }}
</style>
</head>
<body style="background-color: #f4f4f4; margin: 0; padding: 20px;">
    <table border="0" cellpadding="0" cellspacing="0" width="100%">
        <tr>
            <td align="center">
                <table border="0" cellpadding="0" cellspacing="0" width="600" style="background-color: #ffffff; max-width: 600px; width: 100%; box-shadow: 0 2px 8px rgba(0,0,0,0.05);">
                    <tr>
                        <td align="center" style="background-color: #000000; padding: 30px 20px;">
                            <h1 style="color: #ffffff; margin: 0; font-size: 24px; letter-spacing: 2px; text-transform: uppercase; font-weight: 500;">
                                CHOSEN INTERNATIONAL
                            </h1>
                        </td>
                    </tr>
                    <tr>
                        <td style="padding: 40px;">
                            <h2 style="margin-top: 0; color: #000000;">Dobrodošli {first_name}</h2>
                            <p style="color: #555555; line-height: 1.5;">Vaš korisnički račun je kreiran. Drago nam je što ste nam se pridružili.</p>
                            
                            <table width="100%" style="background-color: #f9f9f9; border-left: 4px solid #000000; margin: 20px 0; padding: 20px;">
                                <tr>
                                    <td>
                                        <p style="margin: 0 0 5px 0; font-size: 12px; text-transform: uppercase; color: #888888;">E-mail</p>
                                        <p style="margin: 0 0 15px 0; font-size: 16px; font-weight: bold; color: #000000;">{email}</p>
                                        
                                        <p style="margin: 0 0 5px 0; font-size: 12px; text-transform: uppercase; color: #888888;">Lozinka</p>
                                        <p style="margin: 0; font-size: 16px; font-weight: bold; color: #000000;">{password}</p>
                                    </td>
                                </tr>
                            </table>

                            <p style="color: #666666; font-size: 14px;">Svoju lozinku možete promijeniti u mobilnoj aplikaciji.</p>
                            
                            <p style="margin-top: 30px; font-weight: bold;">Lijep pozdrav,<br>Chosen International Tim</p>
                        </td>
                    </tr>
                    <tr>
                        <td style="background-color: #f9f9f9; padding: 20px; text-align: center; font-size: 12px; color: #999999;">
                            &copy; Chosen International. Sva prava pridržana.
                        </td>
                    </tr>
                </table>
            </td>
        </tr>
    </table>
</body>
</html>
"""

    # Send Logic
    try:
        response = ses.send_email(
            Source=settings.SES_FROM_EMAIL,
            Destination={"ToAddresses": [email]},
            Message={
                "Subject": {"Data": subject},
                "Body": {
                    # SES sends Multipart: Clients that support HTML show HTML, others show Text.
                    # Charset UTF-8 is crucial for Croatian characters (č, ć, ž, š, đ)
                    "Text": {"Data": text_body, "Charset": "UTF-8"},
                    "Html": {"Data": html_body, "Charset": "UTF-8"},
                },
            },
        )
        return response
    except Exception as e:
        print(f"Error sending email: {e}")
        return None


def generate_reset_token():
    """Generate a secure random token for password reset."""
    return secrets.token_urlsafe(32)


def get_reset_token_expiry(hours: int = 24):
    """Get the expiry datetime for a reset token."""
    return datetime.now(timezone.utc) + timedelta(hours=hours)


def send_password_reset_email(first_name: str, email: str, reset_token: str, reset_url: str = None):
    """
    Sends a password reset email using AWS SES with a clickable link.
    Includes both HTML and Plain Text versions.
    """

    # Initialize SES Client
    ses = boto3.client(
        "ses",
        region_name=settings.AWS_SES_REGION,
        aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
        aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
    )

    # Default reset URL if not provided
    if not reset_url:
        reset_url = f"https://admin.chosen-international.com/reset-password?token={reset_token}"

    subject = "Chosen International - Zahtjev za resetiranje lozinke"

    # Plain Text Version
    text_body = f"""
Pozdrav {first_name},

Primili smo zahtjev za resetiranje Vaše lozinke.

Kliknite na sljedeći link za resetiranje lozinke:
{reset_url}

Ako link ne radi, kopirajte ga i zalijepite u svoj preglednik.

Ovaj link vrijedi 24 sata.

Ako niste zatražili resetiranje lozinke, molimo ignorirajte ovaj e-mail.

Lijep pozdrav,
Chosen International Tim
"""

    # HTML Version with clickable button
    html_body = f"""
<!DOCTYPE html>
<html>
<head>
<style>
    body, td {{ font-family: 'Avenir', 'Segoe UI', 'Roboto', Helvetica, Arial, sans-serif; }}
</style>
</head>
<body style="background-color: #f4f4f4; margin: 0; padding: 20px;">
    <table border="0" cellpadding="0" cellspacing="0" width="100%">
        <tr>
            <td align="center">
                <table border="0" cellpadding="0" cellspacing="0" width="600" style="background-color: #ffffff; max-width: 600px; width: 100%; box-shadow: 0 2px 8px rgba(0,0,0,0.05);">
                    <tr>
                        <td align="center" style="background-color: #000000; padding: 30px 20px;">
                            <h1 style="color: #ffffff; margin: 0; font-size: 24px; letter-spacing: 2px; text-transform: uppercase; font-weight: 500;">
                                CHOSEN INTERNATIONAL
                            </h1>
                        </td>
                    </tr>
                    <tr>
                        <td style="padding: 40px;">
                            <h2 style="margin-top: 0; color: #000000;">Resetiranje lozinke</h2>
                            <p style="color: #555555; line-height: 1.5;">Pozdrav {first_name},</p>
                            <p style="color: #555555; line-height: 1.5;">Primili smo zahtjev za resetiranje Vaše lozinke.</p>

                            <div style="text-align: center; margin: 30px 0;">
                                <a href="{reset_url}"
                                   style="display: inline-block;
                                          padding: 16px 36px;
                                          background-color: #000000;
                                          color: #ffffff;
                                          text-decoration: none;
                                          border-radius: 8px;
                                          font-weight: bold;
                                          font-size: 16px;
                                          letter-spacing: 1px;">
                                    RESETIRAJ LOZINKU
                                </a>
                            </div>

                            <p style="color: #666666; font-size: 14px; text-align: center; margin-top: 20px;">
                                Ili kopirajte ovaj link u svoj preglednik:
                            </p>
                            <p style="color: #888888; font-size: 12px; word-break: break-all; background-color: #f9f9f9; padding: 12px; border-radius: 4px; text-align: center;">
                                {reset_url}
                            </p>

                            <p style="color: #666666; font-size: 14px; margin-top: 30px;">Ovaj link vrijedi 24 sata.</p>
                            <p style="color: #666666; font-size: 14px;">Ako niste zatražili resetiranje lozinke, molimo ignorirajte ovaj e-mail.</p>

                            <p style="margin-top: 30px; font-weight: bold;">Lijep pozdrav,<br>Chosen International Tim</p>
                        </td>
                    </tr>
                    <tr>
                        <td style="background-color: #f9f9f9; padding: 20px; text-align: center; font-size: 12px; color: #999999;">
                            &copy; Chosen International. Sva prava pridržana.
                        </td>
                    </tr>
                </table>
            </td>
        </tr>
    </table>
</body>
</html>
"""

    try:
        response = ses.send_email(
            Source=settings.SES_FROM_EMAIL,
            Destination={"ToAddresses": [email]},
            Message={
                "Subject": {"Data": subject},
                "Body": {
                    "Text": {"Data": text_body, "Charset": "UTF-8"},
                    "Html": {"Data": html_body, "Charset": "UTF-8"},
                },
            },
        )
        return response
    except Exception as e:
        print(f"Error sending password reset email: {e}")
        return None