import logging

from django.core.management.base import BaseCommand
from django.utils import timezone

from appointments.models import Appointment
from accounts.email_service import EmailService

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Sends appointment reminder emails for appointments scheduled tomorrow'

    def handle(self, *args, **options):
        tomorrow = timezone.now().date() + timezone.timedelta(days=1)
        appointments = Appointment.objects.filter(
            date=tomorrow,
            status__in=[Appointment.Status.PENDING, Appointment.Status.CONFIRMED],
        ).select_related('patient', 'doctor__user')

        sent = 0
        for appointment in appointments:
            try:
                if appointment.patient.email:
                    EmailService.send_appointment_reminder(appointment)
                    sent += 1
            except Exception:
                logger.exception(
                    "Failed to send reminder for appointment %s", appointment.id
                )

        self.stdout.write(self.style.SUCCESS(
            f"Sent {sent} reminder(s) for {tomorrow}"
        ))
