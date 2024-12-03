# email_operations.py
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import smtplib
import logging
from django.conf import settings

# Configuración de logging para ver los mensajes de depuración
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class EmailOperations:
    def __init__(self):
        self.username = settings.EMAIL_HOST_USER
        self.password = settings.EMAIL_HOST_PASSWORD
        self.smtp_server = 'smtp.gmail.com'
        self.smtp_port = 587
        self.msg = MIMEMultipart()

    def send_email(self, receivers_email, subject, message):
        self.msg['From'] = self.username
        self.msg['To'] = ', '.join(receivers_email)
        self.msg['Subject'] = subject
        self.msg.attach(MIMEText(message, 'plain'))

        try:
            logger.info('Iniciando conexión con el servidor SMTP')
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()  # Inicia TLS
                server.login(self.username, self.password)  # Iniciar sesión

                logger.info(f'Enviando correo a: {receivers_email}')
                server.sendmail(self.msg['From'], receivers_email, self.msg.as_string())
            logger.info('Correo enviado exitosamente!')

        except Exception as e:
            logger.error(f'Error al enviar el correo: {e}')
