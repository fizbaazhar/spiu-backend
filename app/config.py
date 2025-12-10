import os


class Config:
    SQL_SERVER = os.getenv('SQL_SERVER', 'SERVER_IP')
    SQL_DATABASE = os.getenv('SQL_DATABASE', 'spiu_replica')
    SQL_USERNAME = os.getenv('SQL_USERNAME', 'enviro_api')
    SQL_PASSWORD = os.getenv('SQL_PASSWORD', 'Enviropak123-')

    # SMTP / Email settings
    SMTP_HOST = os.getenv('SMTP_HOST', 'smtp.hostinger.com')
    SMTP_PORT = int(os.getenv('SMTP_PORT', '465'))
    SMTP_USERNAME = os.getenv('SMTP_USERNAME', 'no-reply@epd-aqms-pk.com')
    SMTP_PASSWORD = os.getenv('SMTP_PASSWORD', '123XYZabc!')
    # For SSL on port 465, leave TLS disabled (set to false)
    SMTP_USE_TLS = os.getenv(
        'SMTP_USE_TLS', 'false').lower() in ('1', 'true', 'yes')
    ALERT_EMAIL_FROM = os.getenv(
        'ALERT_EMAIL_FROM', 'no-reply@epd-aqms-pk.com')
    ALERT_EMAIL_TO = os.getenv(
        'ALERT_EMAIL_TO', 'deputydirectorepe@gmail.com, alshanconstruc786@gmail.com, aqms.maintenance@gmail.com')  # comma-separated list
