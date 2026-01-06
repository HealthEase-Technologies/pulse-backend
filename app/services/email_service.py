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

    @staticmethod
    def send_morning_briefing(
        patient_email: str,
        patient_name: str,
        summary_data: dict
    ):
        """
        Send morning health briefing to patient

        This email contains yesterday's health summary with insights and alerts.

        Args:
            patient_email: Patient's email address
            patient_name: Patient's full name
            summary_data: Health summary data (from daily_health_summaries.summary_data JSONB)

        Template includes:
        - Date of summary
        - Overall health status
        - Key metrics (heart rate, BP, glucose, steps, sleep) with status indicators
        - Insights (positive health observations)
        - Alerts (concerning values that need attention)
        - Link to view full summary in app

        TODO: Implement this function
        - Extract metrics from summary_data
        - Format metrics for email display (with emojis/colors for status)
        - Build HTML email template with proper styling
        - Call send_email() with formatted subject and body
        - Return True/False based on send success
        """
        subject = f"Your Daily Health Briefing - {summary_data.get('date', 'Today')}"

        # TODO: Extract and format metrics from summary_data
        # Example structure:
        # metrics = summary_data.get('metrics', {})
        # heart_rate = metrics.get('heart_rate', {})
        # insights = summary_data.get('insights', [])
        # alerts = summary_data.get('alerts', [])

        body_text = f"""
Good morning {patient_name},

Here's your health summary for yesterday.

[TODO: Format metrics, insights, and alerts in plain text]

View your full health dashboard at: https://pulse-so.vercel.app/dashboard

Best regards,
The Pulse Team
"""

        body_html = f"""
<html>
  <head>
    <style>
      body {{
        font-family: Arial, sans-serif;
        line-height: 1.6;
        color: #333;
      }}
      .container {{
        max-width: 600px;
        margin: 0 auto;
        padding: 20px;
      }}
      .header {{
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        padding: 30px;
        text-align: center;
        border-radius: 10px 10px 0 0;
      }}
      .content {{
        background: #ffffff;
        padding: 30px;
        border: 1px solid #e0e0e0;
      }}
      .metric-card {{
        background: #f9f9f9;
        padding: 15px;
        margin: 10px 0;
        border-radius: 8px;
        border-left: 4px solid #667eea;
      }}
      .status-good {{
        color: #28a745;
        font-weight: bold;
      }}
      .status-alert {{
        color: #dc3545;
        font-weight: bold;
      }}
      .insight {{
        background: #e8f4f8;
        padding: 10px;
        margin: 5px 0;
        border-radius: 5px;
      }}
      .alert-box {{
        background: #fff3cd;
        border: 1px solid #ffc107;
        padding: 15px;
        margin: 15px 0;
        border-radius: 5px;
      }}
      .cta-button {{
        display: inline-block;
        background: #667eea;
        color: white;
        padding: 12px 24px;
        text-decoration: none;
        border-radius: 5px;
        margin: 20px 0;
      }}
    </style>
  </head>
  <body>
    <div class="container">
      <div class="header">
        <h1>🌅 Good Morning, {patient_name}!</h1>
        <p>Your Daily Health Briefing</p>
      </div>
      <div class="content">
        <p><strong>Summary for:</strong> {summary_data.get('date', 'Yesterday')}</p>

        <!-- TODO: Add formatted metrics cards here -->
        <!-- Example:
        <div class="metric-card">
          <h3>❤️ Heart Rate</h3>
          <p>Average: <span class="status-good">72 bpm</span></p>
          <p>Status: Optimal Range</p>
        </div>
        -->

        <!-- TODO: Add insights section -->
        <!-- Example:
        <h3>✨ Insights</h3>
        <div class="insight">
          Your heart rate was in optimal range throughout the day
        </div>
        -->

        <!-- TODO: Add alerts section if any -->
        <!-- Example:
        <div class="alert-box">
          <h3>⚠️ Attention Needed</h3>
          <p>Your blood glucose was elevated in the evening</p>
        </div>
        -->

        <a href="https://pulse-so.vercel.app/dashboard" class="cta-button">
          View Full Dashboard
        </a>

        <p style="margin-top: 30px; color: #666; font-size: 14px;">
          Best regards,<br>
          The Pulse Team
        </p>
      </div>
    </div>
  </body>
</html>
"""

        return EmailService.send_email(patient_email, subject, body_text, body_html)


# Create singleton instance
email_service = EmailService()
