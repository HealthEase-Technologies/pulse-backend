import time
from app.config.database import supabase_admin
from app.config.settings import settings
from app.services.email_service import email_service
from typing import Dict, Optional, List
import logging

logger = logging.getLogger(__name__)


class NotificationService:
    """Service for sending alert notifications (email + WhatsApp)"""

    def __init__(self):
        self._twilio_client = None

    @property
    def twilio_client(self):
        """Lazy-initialize Twilio client"""
        if self._twilio_client is None and settings.whatsapp_enabled:
            try:
                from twilio.rest import Client
                self._twilio_client = Client(
                    settings.twilio_account_sid,
                    settings.twilio_auth_token,
                )
                logger.info("Twilio client initialized successfully")
            except Exception as e:
                logger.error(f"Failed to initialize Twilio client: {e}")
        return self._twilio_client

    # =========================================================================
    # PUBLIC METHODS
    # =========================================================================

    async def send_warning_notification(
        self,
        patient_user_id: str,
        biomarker_type: str,
        value: float,
        unit: str,
        threshold_value: float,
        direction: str,
        alert_id: str,
    ) -> List[Dict]:
        """Send warning notification to the patient via email."""
        results = []

        # Get patient info
        patient = await self._get_patient_info(patient_user_id)
        if not patient:
            logger.error(f"Patient not found for warning notification: {patient_user_id}")
            return results

        patient_name = patient.get("full_name", "").strip() or "Patient"
        patient_email = patient.get("email")

        if patient_email:
            subject, body_text, body_html = self._build_warning_email_html(
                patient_name, biomarker_type, value, unit, threshold_value, direction
            )
            result = await self._send_with_retry(
                self._send_email, max_retries=3,
                to_email=patient_email, subject=subject,
                body_text=body_text, body_html=body_html
            )
            result["channel"] = "email"
            result["recipient"] = patient_email
            results.append(result)

        return results

    async def send_critical_alert(
        self,
        patient_user_id: str,
        biomarker_type: str,
        value: float,
        unit: str,
        threshold_value: float,
        direction: str,
        alert_id: str,
    ) -> List[Dict]:
        """
        Send critical alert with retry logic.
        Recipients: patient + emergency contacts (email + SMS) + connected providers
        """
        results = []

        # Get patient info
        patient = await self._get_patient_info(patient_user_id)
        if not patient:
            logger.error(f"Patient not found for critical alert: {patient_user_id}")
            return results
        logger.info(f"Sending critical alert for patient {patient_user_id}, email={patient.get('email')}")

        patient_name = patient.get("full_name", "").strip() or "Patient"
        patient_email = patient.get("email")

        # 1. Email to patient
        if patient_email:
            subject, body_text, body_html = self._build_critical_email_html(
                patient_name, biomarker_type, value, unit, threshold_value, direction
            )
            result = await self._send_with_retry(
                self._send_email, max_retries=3,
                to_email=patient_email, subject=subject,
                body_text=body_text, body_html=body_html
            )
            result["channel"] = "email"
            result["recipient"] = patient_email
            results.append(result)

        # 2. Emergency contacts (up to 3)
        emergency_contacts = await self._get_emergency_contacts(patient_user_id)
        logger.info(f"Emergency contacts found: {len(emergency_contacts)}, contacts: {emergency_contacts}")
        logger.info(f"WhatsApp enabled: {settings.whatsapp_enabled}, Twilio SID set: {bool(settings.twilio_account_sid)}")
        for contact in emergency_contacts[:3]:
            contact_name = contact.get("name", "Emergency Contact")
            contact_email = contact.get("email")
            contact_phone = contact.get("phone")
            logger.info(f"Processing contact: name={contact_name}, email={contact_email}, phone={contact_phone}")

            # Email to emergency contact
            if contact_email:
                subject, body_text, body_html = self._build_emergency_contact_email_html(
                    contact_name, patient_name, biomarker_type, value, unit
                )
                result = await self._send_with_retry(
                    self._send_email, max_retries=3,
                    to_email=contact_email, subject=subject,
                    body_text=body_text, body_html=body_html
                )
                result["channel"] = "email"
                result["recipient"] = contact_email
                results.append(result)

            # WhatsApp to emergency contact
            if contact_phone and settings.whatsapp_enabled:
                biomarker_label = biomarker_type.replace("_", " ").title()
                wa_message = (
                    f"🚨 *PULSE CRITICAL ALERT*\n\n"
                    f"{patient_name}'s {biomarker_label} reading is "
                    f"*{value} {unit}* ({direction}).\n\n"
                    f"Please check on them immediately."
                )
                result = await self._send_with_retry(
                    self._send_whatsapp, max_retries=3,
                    phone_number=contact_phone, message=wa_message
                )
                result["channel"] = "whatsapp"
                result["recipient"] = contact_phone
                results.append(result)

        # 3. Connected providers
        provider_emails = await self._get_connected_provider_emails(patient_user_id)
        for provider_email in provider_emails:
            subject, body_text, body_html = self._build_provider_alert_email_html(
                patient_name, biomarker_type, value, unit, threshold_value, direction
            )
            result = await self._send_with_retry(
                self._send_email, max_retries=3,
                to_email=provider_email, subject=subject,
                body_text=body_text, body_html=body_html
            )
            result["channel"] = "email"
            result["recipient"] = provider_email
            results.append(result)

        return results

    # =========================================================================
    # RETRY LOGIC
    # =========================================================================

    async def _send_with_retry(self, send_fn, max_retries: int = 3, **kwargs) -> Dict:
        """Retry wrapper. Returns result dict with attempt details."""
        last_error = None
        for attempt in range(1, max_retries + 1):
            try:
                success = send_fn(**kwargs)
                if success:
                    return {
                        "success": True,
                        "attempts": attempt,
                        "error": None,
                        "timestamp": time.time()
                    }
                last_error = "Send returned False"
            except Exception as e:
                last_error = str(e)
                logger.warning(f"Notification attempt {attempt}/{max_retries} failed: {e}")
            if attempt < max_retries:
                time.sleep(1)  # brief delay between retries

        return {
            "success": False,
            "attempts": max_retries,
            "error": last_error,
            "timestamp": time.time()
        }

    # =========================================================================
    # SEND METHODS
    # =========================================================================

    def _send_email(self, to_email: str, subject: str, body_text: str, body_html: str = None) -> bool:
        """Send email using existing email service."""
        return email_service.send_email(to_email, subject, body_text, body_html)

    def _send_whatsapp(self, phone_number: str, message: str) -> bool:
        """Send WhatsApp message via Twilio."""
        if not self.twilio_client:
            logger.warning(f"WhatsApp not enabled. Would send to {phone_number}: {message}")
            return False
        try:
            # Ensure phone number has whatsapp: prefix
            to_number = phone_number if phone_number.startswith("whatsapp:") else f"whatsapp:{phone_number}"
            msg = self.twilio_client.messages.create(
                from_=settings.twilio_whatsapp_from,
                body=message,
                to=to_number,
            )
            logger.info(f"WhatsApp sent to {phone_number}, SID: {msg.sid}")
            return True
        except Exception as e:
            logger.error(f"Failed to send WhatsApp to {phone_number}: {e}")
            raise

    # =========================================================================
    # DATA FETCHING HELPERS
    # =========================================================================

    async def _get_patient_info(self, patient_user_id: str) -> Optional[Dict]:
        """Get patient's user info (name, email) by joining users + patients tables."""
        try:
            # Get email from users table
            user_response = (
                supabase_admin.table("users")
                .select("id, email")
                .eq("id", patient_user_id)
                .execute()
            )
            if not user_response.data:
                return None

            user = user_response.data[0]

            # Get full_name from patients table
            patient_response = (
                supabase_admin.table("patients")
                .select("full_name")
                .eq("user_id", patient_user_id)
                .execute()
            )
            full_name = ""
            if patient_response.data:
                full_name = patient_response.data[0].get("full_name", "")

            user["full_name"] = full_name
            return user
        except Exception as e:
            logger.error(f"Error fetching patient info: {e}")
            return None

    async def _get_emergency_contacts(self, patient_user_id: str) -> List[Dict]:
        """Get patient's emergency contacts from patient profile."""
        try:
            response = (
                supabase_admin.table("patients")
                .select("emergency_contacts")
                .eq("user_id", patient_user_id)
                .execute()
            )
            if response.data and response.data[0].get("emergency_contacts"):
                return response.data[0]["emergency_contacts"]
            return []
        except Exception as e:
            logger.error(f"Error fetching emergency contacts: {e}")
            return []

    async def _get_connected_provider_emails(self, patient_user_id: str) -> List[str]:
        """Get emails of providers connected to this patient."""
        try:
            # Get patient profile id
            patient = (
                supabase_admin.table("patients")
                .select("id")
                .eq("user_id", patient_user_id)
                .execute()
            )
            if not patient.data:
                return []

            # Get accepted connections
            connections = (
                supabase_admin.table("patient_provider_connections")
                .select("provider_id")
                .eq("patient_id", patient.data[0]["id"])
                .eq("status", "accepted")
                .execute()
            )
            if not connections.data:
                return []

            provider_ids = [c["provider_id"] for c in connections.data]

            # Get provider user_ids
            emails = []
            for pid in provider_ids:
                provider = (
                    supabase_admin.table("providers")
                    .select("user_id")
                    .eq("id", pid)
                    .execute()
                )
                if provider.data:
                    user = (
                        supabase_admin.table("users")
                        .select("email")
                        .eq("id", provider.data[0]["user_id"])
                        .execute()
                    )
                    if user.data and user.data[0].get("email"):
                        emails.append(user.data[0]["email"])

            return emails
        except Exception as e:
            logger.error(f"Error fetching provider emails: {e}")
            return []

    # =========================================================================
    # EMAIL TEMPLATES
    # =========================================================================

    def _build_warning_email_html(self, patient_name, biomarker_type, value, unit, threshold_value, direction):
        biomarker_label = biomarker_type.replace("_", " ").title()
        direction_text = "above" if direction == "high" else "below"

        subject = f"⚠️ Health Warning: {biomarker_label} {direction_text} safe range - Pulse"

        body_text = (
            f"Hello {patient_name},\n\n"
            f"Your {biomarker_label} reading of {value} {unit} is {direction_text} "
            f"your warning threshold of {threshold_value} {unit}.\n\n"
            f"This is a warning — please monitor this closely and consult your "
            f"healthcare provider if it persists.\n\n"
            f"Best regards,\nThe Pulse Team"
        )

        body_html = f"""
<html>
  <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
    <div style="background: linear-gradient(135deg, #FEF3C7, #FDE68A); padding: 20px; border-radius: 12px; border: 1px solid #F59E0B;">
      <h2 style="color: #92400E; margin: 0;">⚠️ Health Warning</h2>
    </div>
    <div style="padding: 20px;">
      <p>Hello <strong>{patient_name}</strong>,</p>
      <div style="background: #FFFBEB; border: 1px solid #F59E0B; border-radius: 8px; padding: 16px; margin: 16px 0;">
        <p style="margin: 0; font-size: 18px; color: #92400E;">
          <strong>{biomarker_label}:</strong> {value} {unit}
        </p>
        <p style="margin: 4px 0 0; color: #B45309;">
          Warning threshold: {threshold_value} {unit} ({direction_text})
        </p>
      </div>
      <p>Your reading is <strong>{direction_text}</strong> your safe range. Please monitor this closely.</p>
      <p>If this continues, we recommend consulting your healthcare provider.</p>
      <br>
      <p style="color: #6B7280;">Best regards,<br>The Pulse Team</p>
    </div>
  </body>
</html>"""

        return subject, body_text, body_html

    def _build_critical_email_html(self, patient_name, biomarker_type, value, unit, threshold_value, direction):
        biomarker_label = biomarker_type.replace("_", " ").title()
        direction_text = "above" if direction == "high" else "below"

        subject = f"🚨 CRITICAL ALERT: {biomarker_label} - Immediate Attention Required - Pulse"

        body_text = (
            f"CRITICAL HEALTH ALERT\n\n"
            f"Hello {patient_name},\n\n"
            f"Your {biomarker_label} reading of {value} {unit} is {direction_text} "
            f"your CRITICAL threshold of {threshold_value} {unit}.\n\n"
            f"This requires immediate attention. Your emergency contacts and healthcare "
            f"provider have been notified.\n\n"
            f"If you feel unwell, please seek medical attention immediately.\n\n"
            f"The Pulse Team"
        )

        body_html = f"""
<html>
  <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
    <div style="background: linear-gradient(135deg, #FEE2E2, #FECACA); padding: 20px; border-radius: 12px; border: 2px solid #EF4444;">
      <h2 style="color: #991B1B; margin: 0;">🚨 CRITICAL HEALTH ALERT</h2>
    </div>
    <div style="padding: 20px;">
      <p>Hello <strong>{patient_name}</strong>,</p>
      <div style="background: #FEF2F2; border: 2px solid #EF4444; border-radius: 8px; padding: 16px; margin: 16px 0;">
        <p style="margin: 0; font-size: 22px; color: #991B1B; font-weight: bold;">
          {biomarker_label}: {value} {unit}
        </p>
        <p style="margin: 4px 0 0; color: #DC2626;">
          Critical threshold: {threshold_value} {unit} ({direction_text})
        </p>
      </div>
      <div style="background: #FEF2F2; border-left: 4px solid #EF4444; padding: 12px; margin: 16px 0;">
        <p style="margin: 0; color: #991B1B; font-weight: bold;">
          ⚠️ This requires immediate attention.
        </p>
        <p style="margin: 8px 0 0; color: #DC2626;">
          Your emergency contacts and healthcare provider have been notified.
        </p>
      </div>
      <p><strong>If you feel unwell, please seek medical attention immediately.</strong></p>
      <br>
      <p style="color: #6B7280;">The Pulse Team</p>
    </div>
  </body>
</html>"""

        return subject, body_text, body_html

    def _build_emergency_contact_email_html(self, contact_name, patient_name, biomarker_type, value, unit):
        biomarker_label = biomarker_type.replace("_", " ").title()

        subject = f"🚨 EMERGENCY: {patient_name} Critical Health Alert - Pulse"

        body_text = (
            f"Hello {contact_name},\n\n"
            f"You are receiving this alert because you are listed as an emergency "
            f"contact for {patient_name} on Pulse.\n\n"
            f"A CRITICAL health reading has been detected:\n"
            f"  {biomarker_label}: {value} {unit}\n\n"
            f"Please check on {patient_name} as soon as possible.\n\n"
            f"The Pulse Team"
        )

        body_html = f"""
<html>
  <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
    <div style="background: linear-gradient(135deg, #FEE2E2, #FECACA); padding: 20px; border-radius: 12px; border: 2px solid #EF4444;">
      <h2 style="color: #991B1B; margin: 0;">🚨 EMERGENCY ALERT</h2>
    </div>
    <div style="padding: 20px;">
      <p>Hello <strong>{contact_name}</strong>,</p>
      <p>You are receiving this because you are listed as an <strong>emergency contact</strong> for <strong>{patient_name}</strong> on Pulse.</p>
      <div style="background: #FEF2F2; border: 2px solid #EF4444; border-radius: 8px; padding: 16px; margin: 16px 0;">
        <p style="margin: 0; font-size: 18px; color: #991B1B; font-weight: bold;">
          Critical Reading Detected
        </p>
        <p style="margin: 8px 0 0; font-size: 20px; color: #DC2626;">
          {biomarker_label}: {value} {unit}
        </p>
      </div>
      <p><strong>Please check on {patient_name} as soon as possible.</strong></p>
      <br>
      <p style="color: #6B7280;">The Pulse Team</p>
    </div>
  </body>
</html>"""

        return subject, body_text, body_html

    def _build_provider_alert_email_html(self, patient_name, biomarker_type, value, unit, threshold_value, direction):
        biomarker_label = biomarker_type.replace("_", " ").title()
        direction_text = "above" if direction == "high" else "below"

        subject = f"🚨 Patient Critical Alert: {patient_name} - {biomarker_label} - Pulse"

        body_text = (
            f"PATIENT CRITICAL ALERT\n\n"
            f"Your patient {patient_name} has a critical health reading:\n"
            f"  {biomarker_label}: {value} {unit}\n"
            f"  Critical threshold: {threshold_value} {unit} ({direction_text})\n\n"
            f"Please review the patient's data on your Pulse dashboard.\n\n"
            f"The Pulse Team"
        )

        body_html = f"""
<html>
  <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
    <div style="background: linear-gradient(135deg, #EEF2FF, #E0E7FF); padding: 20px; border-radius: 12px; border: 2px solid #EF4444;">
      <h2 style="color: #991B1B; margin: 0;">🚨 Patient Critical Alert</h2>
    </div>
    <div style="padding: 20px;">
      <p>Your patient <strong>{patient_name}</strong> has a critical health reading:</p>
      <div style="background: #FEF2F2; border: 2px solid #EF4444; border-radius: 8px; padding: 16px; margin: 16px 0;">
        <p style="margin: 0; font-size: 20px; color: #991B1B; font-weight: bold;">
          {biomarker_label}: {value} {unit}
        </p>
        <p style="margin: 4px 0 0; color: #DC2626;">
          Critical threshold: {threshold_value} {unit} ({direction_text})
        </p>
      </div>
      <p>Please review the patient's data on your <a href="https://pulse-so.vercel.app/dashboard/provider" style="color: #4F46E5;">Pulse dashboard</a>.</p>
      <br>
      <p style="color: #6B7280;">The Pulse Team</p>
    </div>
  </body>
</html>"""

        return subject, body_text, body_html


# Singleton instance
notification_service = NotificationService()
