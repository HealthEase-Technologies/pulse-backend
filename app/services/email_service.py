import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from app.config.settings import settings
from typing import Optional, List, Dict
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
        try:
            msg = MIMEMultipart("alternative")
            msg["Subject"] = subject
            msg["From"] = settings.email_sender
            msg["To"] = to_email

            msg.attach(MIMEText(body_text, "plain"))

            if body_html:
                msg.attach(MIMEText(body_html, "html"))

            with smtplib.SMTP(settings.smtp_server, settings.smtp_port) as server:
                server.starttls()
                server.login(settings.email_sender, settings.email_password)
                server.sendmail(
                    settings.email_sender,
                    to_email,
                    msg.as_string()
                )

            logger.info(f"Email sent successfully to {to_email}")
            return True

        except Exception as e:
            logger.error(f"Failed to send email to {to_email}: {e}")
            return False

    # --------------------------------------------------
    # Connection notifications
    # --------------------------------------------------

    @staticmethod
    def send_connection_request_notification(
        provider_email: str,
        provider_name: str,
        patient_name: str
    ):
        subject = "New Connection Request - Pulse"

        body_text = f"""
Hello Dr. {provider_name},

You have received a new connection request from {patient_name}.

Please log in to your Pulse dashboard to review and respond.

Best regards,
The Pulse Team
"""

        body_html = f"""
<html>
  <body>
    <h2>New Connection Request</h2>
    <p>Hello Dr. {provider_name},</p>
    <p>You have received a new connection request from <strong>{patient_name}</strong>.</p>
    <p>Please log in to your Pulse dashboard to review and respond.</p>
    <br>
    <p>Best regards,<br>The Pulse Team</p>
  </body>
</html>
"""

        return EmailService.send_email(
            provider_email, subject, body_text, body_html
        )

    @staticmethod
    def send_connection_accepted_notification(
        patient_email: str,
        patient_name: str,
        provider_name: str
    ):
        subject = "Connection Request Accepted - Pulse"

        body_text = f"""
Hello {patient_name},

Great news! Dr. {provider_name} has accepted your connection request.

You can now access personalized care and track your health goals.

Log in to your Pulse dashboard to get started.

Best regards,
The Pulse Team
"""

        body_html = f"""
<html>
  <body>
    <h2>Connection Accepted</h2>
    <p>Hello {patient_name},</p>
    <p><strong>Dr. {provider_name}</strong> has accepted your connection request.</p>
    <p>You can now access personalized care and track your health goals.</p>
    <br>
    <p>Best regards,<br>The Pulse Team</p>
  </body>
</html>
"""

        return EmailService.send_email(
            patient_email, subject, body_text, body_html
        )

    @staticmethod
    def send_connection_rejected_notification(
        patient_email: str,
        patient_name: str,
        provider_name: str
    ):
        subject = "Connection Request Update - Pulse"

        body_text = f"""
Hello {patient_name},

Dr. {provider_name} is currently unable to accept new patients.

Please explore other providers in the Pulse directory.

Best regards,
The Pulse Team
"""

        body_html = f"""
<html>
  <body>
    <h2>Connection Update</h2>
    <p>Hello {patient_name},</p>
    <p><strong>Dr. {provider_name}</strong> is currently unable to accept new patients.</p>
    <p>Please explore other providers in the Pulse directory.</p>
    <br>
    <p>Best regards,<br>The Pulse Team</p>
  </body>
</html>
"""

        return EmailService.send_email(
            patient_email, subject, body_text, body_html
        )

    @staticmethod
    def send_disconnection_notification(
        provider_email: str,
        provider_name: str,
        patient_name: str
    ):
        subject = "Patient Disconnected - Pulse"

        body_text = f"""
Hello Dr. {provider_name},

{patient_name} has disconnected from your care.

You will no longer have access to their health information.

Best regards,
The Pulse Team
"""

        body_html = f"""
<html>
  <body>
    <h2>Patient Disconnected</h2>
    <p>Hello Dr. {provider_name},</p>
    <p><strong>{patient_name}</strong> has disconnected from your care.</p>
    <p>You will no longer have access to their health information.</p>
    <br>
    <p>Best regards,<br>The Pulse Team</p>
  </body>
</html>
"""

        return EmailService.send_email(
            provider_email, subject, body_text, body_html
        )

    # --------------------------------------------------
    # Morning health briefing
    # --------------------------------------------------

    @staticmethod
    def _format_metric_value(metric_name: str, metric_data: dict) -> str:
        """Helper to format metric value based on metric type"""
        if metric_name == "steps":
            return f"{metric_data.get('total', 'N/A')} steps (Goal: {metric_data.get('goal', 10000)})"
        elif metric_name == "sleep":
            avg = metric_data.get('avg', metric_data.get('hours', 'N/A'))
            return f"{avg} hours"
        elif metric_name == "blood_pressure":
            systolic = metric_data.get('systolic_avg', 'N/A')
            diastolic = metric_data.get('diastolic_avg', 'N/A')
            return f"{systolic}/{diastolic} mmHg"
        else:
            # For heart_rate, glucose, etc. - use avg
            avg = metric_data.get('avg', 'N/A')
            unit = "bpm" if metric_name == "heart_rate" else "mg/dL" if metric_name == "glucose" else ""
            return f"{avg} {unit}"

    @staticmethod
    def _format_recommendation_text(recommendations: List[Dict]) -> str:
        """Helper to format recommendations for plain text email"""
        if not recommendations:
            return "No recommendations at this time."

        lines = []
        for rec in recommendations:
            priority_indicator = "[!]" if rec.get("priority") == "high" else ""
            category = rec.get("category", "").replace("_", " ").title()
            title = rec.get("title", "")
            description = rec.get("description", "")
            lines.append(f"{priority_indicator} [{category}] {title}")
            lines.append(f"   {description}")
            lines.append("")
        return "\n".join(lines)

    @staticmethod
    def _format_recommendation_html(recommendations: List[Dict]) -> str:
        """Helper to format recommendations for HTML email"""
        if not recommendations:
            return "<p>No recommendations at this time.</p>"

        priority_colors = {
            "high": "#dc3545",
            "medium": "#ffc107",
            "low": "#28a745"
        }

        category_icons = {
            "nutrition": "🥗",
            "exercise": "🏃",
            "sleep": "😴",
            "lifestyle": "🌟",
            "medical": "⚕️"
        }

        html_parts = []
        for rec in recommendations:
            priority = rec.get("priority", "medium")
            category = rec.get("category", "lifestyle")
            icon = category_icons.get(category, "💡")
            color = priority_colors.get(priority, "#ffc107")
            title = rec.get("title", "")
            description = rec.get("description", "")

            html_parts.append(f"""
            <div style="border-left: 4px solid {color}; padding: 10px 15px; margin: 10px 0; background-color: #f8f9fa;">
                <p style="margin: 0; font-weight: bold;">{icon} {title}</p>
                <p style="margin: 5px 0 0 0; color: #666; font-size: 14px;">{description}</p>
                <p style="margin: 5px 0 0 0; font-size: 12px; color: #888;">
                    <span style="text-transform: capitalize;">{category.replace('_', ' ')}</span> |
                    <span style="color: {color}; text-transform: uppercase;">{priority} priority</span>
                </p>
            </div>
            """)

        return "".join(html_parts)

    @staticmethod
    def send_morning_briefing(
        patient_email: str,
        patient_name: str,
        summary_data: dict,
        recommendations: Optional[List[Dict]] = None
    ):
        subject = f"Your Daily Health Briefing - {summary_data.get('date', 'Yesterday')}"

        metrics = summary_data.get("metrics", {})
        insights = summary_data.get("insights", [])
        alerts = summary_data.get("alerts", [])
        recommendations = recommendations or []

        metric_text = "\n".join(
            f"- {k.replace('_', ' ').title()}: {EmailService._format_metric_value(k, v)}"
            for k, v in metrics.items()
        )

        recommendations_text = EmailService._format_recommendation_text(recommendations)

        body_text = f"""
Good morning {patient_name},

Here is your health summary for yesterday.

Metrics:
{metric_text or 'No metrics available'}

Insights:
{chr(10).join(insights) if insights else 'No insights'}

Alerts:
{chr(10).join(alerts) if alerts else 'No alerts'}

AI Recommendations:
{recommendations_text}

View your dashboard:
https://pulse-so.vercel.app/dashboard

Best regards,
The Pulse Team
"""

        recommendations_html = EmailService._format_recommendation_html(recommendations)

        body_html = f"""
<html>
  <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
    <h2>🌅 Good Morning, {patient_name}</h2>
    <p><strong>Date:</strong> {summary_data.get('date', 'Yesterday')}</p>

    <h3>📊 Metrics</h3>
    {''.join(
        f"<p><strong>{k.replace('_',' ').title()}:</strong> {EmailService._format_metric_value(k, v)}</p>"
        for k, v in metrics.items()
    )}

    <h3>✨ Insights</h3>
    {''.join(f"<p>{i}</p>" for i in insights) or "<p>No insights</p>"}

    <h3>⚠️ Alerts</h3>
    {''.join(f"<p>{a}</p>" for a in alerts) or "<p>No alerts</p>"}

    <h3>🤖 AI Recommendations</h3>
    {recommendations_html}

    <br>
    <a href="https://pulse-so.vercel.app/dashboard" style="display: inline-block; padding: 10px 20px; background-color: #007bff; color: white; text-decoration: none; border-radius: 5px;">
      View Full Dashboard
    </a>

    <p><br>Best regards,<br>The Pulse Team</p>
  </body>
</html>
"""

        return EmailService.send_email(
            patient_email, subject, body_text, body_html
        )


# Singleton instance
email_service = EmailService()
#for commiting