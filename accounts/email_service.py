import logging

from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.utils.http import urlsafe_base64_encode
from django.utils.encoding import force_bytes
from django.contrib.auth.tokens import PasswordResetTokenGenerator

logger = logging.getLogger(__name__)
token_generator = PasswordResetTokenGenerator()


class EmailService:

    @staticmethod
    def _send(subject, template_name, context, to_email):
        html = render_to_string(template_name, context)
        text = strip_tags(html)
        msg = EmailMultiAlternatives(subject, text, settings.DEFAULT_FROM_EMAIL, [to_email])
        msg.attach_alternative(html, 'text/html')
        msg.send()

    # ---- Auth Emails ----

    @staticmethod
    def send_verification_email(user):
        uidb64 = urlsafe_base64_encode(force_bytes(user.pk))
        token = token_generator.make_token(user)
        verification_url = f"{settings.FRONTEND_URL}/verify-email?uidb64={uidb64}&token={token}"
        logger.info("Verification URL for %s: %s", user.email, verification_url)
        EmailService._send(
            subject='Verify your Medica email address',
            template_name='accounts/email_verification_email.html',
            context={'user': user, 'verification_url': verification_url},
            to_email=user.email,
        )

    @staticmethod
    def send_password_reset_email(user):
        uidb64 = urlsafe_base64_encode(force_bytes(user.pk))
        token = token_generator.make_token(user)
        reset_url = f"{settings.FRONTEND_URL}/reset-password?uidb64={uidb64}&token={token}"
        EmailService._send(
            subject='Reset your Medica password',
            template_name='accounts/password_reset_email.html',
            context={'user': user, 'reset_url': reset_url},
            to_email=user.email,
        )

    # ---- Appointment Emails ----

    @staticmethod
    def send_appointment_confirmed(appointment):
        patient = appointment.patient
        EmailService._send(
            subject='Appointment Confirmed – Medica',
            template_name='accounts/appointment_confirmed_email.html',
            context={
                'user': patient,
                'appointment': appointment,
                'doctor_name': appointment.doctor_name,
                'specialty': appointment.specialty,
                'date': appointment.date,
                'time': appointment.time,
            },
            to_email=patient.email,
        )

    @staticmethod
    def send_appointment_cancelled(appointment, cancelled_by_role):
        if cancelled_by_role == 'doctor':
            recipient = appointment.patient
            template = 'accounts/appointment_cancelled_for_patient_email.html'
            subject = 'Appointment Cancelled – Medica'
        else:
            try:
                recipient = appointment.doctor.user
            except AttributeError:
                logger.warning("Cannot send cancellation email to doctor: no user associated")
                return
            template = 'accounts/appointment_cancelled_for_doctor_email.html'
            subject = 'Appointment Cancelled by Patient – Medica'

        EmailService._send(
            subject=subject,
            template_name=template,
            context={
                'user': recipient,
                'appointment': appointment,
                'patient_name': appointment.patient_name,
                'doctor_name': appointment.doctor_name,
                'specialty': appointment.specialty,
                'date': appointment.date,
                'time': appointment.time,
            },
            to_email=recipient.email,
        )

    @staticmethod
    def send_appointment_completed(appointment):
        patient = appointment.patient
        review_url = f"{settings.FRONTEND_URL}/doctors/{appointment.doctor_id}/review?appointment={appointment.id}"
        EmailService._send(
            subject='Appointment Completed – Leave a Review',
            template_name='accounts/appointment_completed_email.html',
            context={
                'user': patient,
                'appointment': appointment,
                'doctor_name': appointment.doctor_name,
                'specialty': appointment.specialty,
                'date': appointment.date,
                'time': appointment.time,
                'review_url': review_url,
            },
            to_email=patient.email,
        )

    @staticmethod
    def send_payment_confirmation(appointment):
        patient = appointment.patient
        EmailService._send(
            subject='Payment Confirmed – Medica',
            template_name='accounts/payment_confirmation_email.html',
            context={
                'user': patient,
                'appointment': appointment,
                'doctor_name': appointment.doctor_name,
                'specialty': appointment.specialty,
                'date': appointment.date,
                'time': appointment.time,
                'amount': appointment.doctor.session_price if appointment.doctor else 0,
            },
            to_email=patient.email,
        )

    @staticmethod
    def send_appointment_reminder(appointment):
        patient = appointment.patient
        doctor = appointment.doctor
        doctor_detail_url = f"{settings.FRONTEND_URL}/doctors/{doctor.pk}" if doctor else settings.FRONTEND_URL
        EmailService._send(
            subject='Reminder: Upcoming Appointment Tomorrow – Medica',
            template_name='accounts/appointment_reminder_email.html',
            context={
                'user': patient,
                'appointment': appointment,
                'doctor_name': appointment.doctor_name,
                'specialty': appointment.specialty,
                'date': appointment.date,
                'time': appointment.time,
                'doctor_detail_url': doctor_detail_url,
            },
            to_email=patient.email,
        )

    # ---- Doctor Verification Emails ----

    @staticmethod
    def send_doctor_approved(doctor_profile):
        user = doctor_profile.user
        dashboard_url = f"{settings.FRONTEND_URL}/doctor/dashboard"
        EmailService._send(
            subject='Documents Approved – Medica',
            template_name='accounts/doctor_approved_email.html',
            context={
                'user': user,
                'doctor': doctor_profile,
                'dashboard_url': dashboard_url,
            },
            to_email=user.email,
        )

    @staticmethod
    def send_doctor_rejected(doctor_profile, reason=''):
        user = doctor_profile.user
        resubmit_url = f"{settings.FRONTEND_URL}/doctor/documents"
        EmailService._send(
            subject='Documents Update Needed – Medica',
            template_name='accounts/doctor_rejected_email.html',
            context={
                'user': user,
                'doctor': doctor_profile,
                'reason': reason,
                'resubmit_url': resubmit_url,
            },
            to_email=user.email,
        )
