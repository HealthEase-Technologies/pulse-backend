import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from app.config.settings import settings
from typing import Optional
import logging

logger = logging.getLogger(__name__)


class EmailService:
    """Service for sending email notifications"""

    @staticmethod
    def send_email(
        to_email: str,
        subject: str,
        body_text: str,
        body_html: Optional[str] = None
    ) -> bool:
        """
        Send an email using SMTP

        Args:
            to_email: Recipient email address
            subject: Email subject
            body_text: Plain text email body
            body_html: Optional HTML email body

        Returns:
            True if email sent successfully, False otherwise
        """
        try:
            # Create message
            msg = MIMEMultipart('alternative')
            msg['Subject'] = subject
            msg['From'] = settings.email_sender
            msg['To'] = to_email

            # Attach plain text version
            part1 = MIMEText(body_text, 'plain')
            msg.attach(part1)

            # Attach HTML version if provided
            if body_html:
                part2 = MIMEText(body_html, 'html')
                msg.attach(part2)

            # Send email
            with smtplib.SMTP(settings.smtp_server, settings.smtp_port) as server:
                server.starttls()
                server.login(settings.email_sender, settings.email_password)
                server.sendmail(settings.email_sender, to_email, msg.as_string())

            logger.info(f"Email sent successfully to {to_email}")
            return True

        except Exception as e:
            logger.error(f"Failed to send email to {to_email}: {str(e)}")
            return False

    @staticmethod
    def send_connection_request_notification(
        provider_email: str,
        provider_name: str,
        patient_name: str
    ):
        """
        Notify provider when patient sends connection request

        Args:
            provider_email: Provider's email address
            provider_name: Provider's full name
            patient_name: Patient's full name
        """
        subject = "New Connection Request - Pulse"

        body_text = f"""
Hello Dr. {provider_name},

You have received a new connection request from {patient_name}.

Please log in to your Pulse dashboard to review and respond to this request.

Best regards,
The Pulse Team
"""

        body_html = f"""
<html>
  <body>
    <h2>New Connection Request</h2>
    <p>Hello Dr. {provider_name},</p>
    <p>You have received a new connection request from <strong>{patient_name}</strong>.</p>
    <p>Please log in to your Pulse dashboard to review and respond to this request.</p>
    <br>
    <p>Best regards,<br>The Pulse Team</p>
  </body>
</html>
"""

        return EmailService.send_email(provider_email, subject, body_text, body_html)

    @staticmethod
    def send_connection_accepted_notification(
        patient_email: str,
        patient_name: str,
        provider_name: str
    ):
        """
        Notify patient when provider accepts connection request

        Args:
            patient_email: Patient's email address
            patient_name: Patient's full name
            provider_name: Provider's full name
        """
        subject = "Connection Request Accepted - Pulse"

        body_text = f"""
Hello {patient_name},

Great news! Dr. {provider_name} has accepted your connection request.

You can now access personalized care and track your health goals with your healthcare provider.

Log in to your Pulse dashboard to get started.

Best regards,
The Pulse Team
"""

        body_html = f"""
<html>
  <body>
    <h2>Connection Request Accepted</h2>
    <p>Hello {patient_name},</p>
    <p>Great news! <strong>Dr. {provider_name}</strong> has accepted your connection request.</p>
    <p>You can now access personalized care and track your health goals with your healthcare provider.</p>
    <p>Log in to your Pulse dashboard to get started.</p>
    <br>
    <p>Best regards,<br>The Pulse Team</p>
  </body>
</html>
"""

        return EmailService.send_email(patient_email, subject, body_text, body_html)

    @staticmethod
    def send_connection_rejected_notification(
        patient_email: str,
        patient_name: str,
        provider_name: str
    ):
        """
        Notify patient when provider rejects connection request

        Args:
            patient_email: Patient's email address
            patient_name: Patient's full name
            provider_name: Provider's full name
        """
        subject = "Connection Request Update - Pulse"

        body_text = f"""
Hello {patient_name},

We're writing to inform you that Dr. {provider_name} is currently unable to accept new patients.

We encourage you to explore other healthcare providers in our directory who may be available to help you with your health journey.

Log in to your Pulse dashboard to browse available providers.

Best regards,
The Pulse Team
"""

        body_html = f"""
<html>
  <body>
    <h2>Connection Request Update</h2>
    <p>Hello {patient_name},</p>
    <p>We're writing to inform you that <strong>Dr. {provider_name}</strong> is currently unable to accept new patients.</p>
    <p>We encourage you to explore other healthcare providers in our directory who may be available to help you with your health journey.</p>
    <p>Log in to your Pulse dashboard to browse available providers.</p>
    <br>
    <p>Best regards,<br>The Pulse Team</p>
  </body>
</html>
"""

        return EmailService.send_email(patient_email, subject, body_text, body_html)

    @staticmethod
    def send_disconnection_notification(
        provider_email: str,
        provider_name: str,
        patient_name: str
    ):
        """
        Notify provider when patient disconnects

        Args:
            provider_email: Provider's email address
            provider_name: Provider's full name
            patient_name: Patient's full name
        """
        subject = "Patient Disconnected - Pulse"

        body_text = f"""
Hello Dr. {provider_name},

{patient_name} has disconnected from your care.

You will no longer have access to their health information in your dashboard.

Best regards,
The Pulse Team
"""

        body_html = f"""
<html>
  <body>
    <h2>Patient Disconnected</h2>
    <p>Hello Dr. {provider_name},</p>
    <p><strong>{patient_name}</strong> has disconnected from your care.</p>
    <p>You will no longer have access to their health information in your dashboard.</p>
    <br>
    <p>Best regards,<br>The Pulse Team</p>
  </body>
</html>
"""

        return EmailService.send_email(provider_email, subject, body_text, body_html)


# Create singleton instance
email_service = EmailService()
