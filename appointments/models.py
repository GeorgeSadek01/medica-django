from django.db import models
from django.conf import settings


class Appointment(models.Model):
    class Status(models.TextChoices):
        PENDING = 'pending'
        CONFIRMED = 'confirmed'
        COMPLETED = 'completed'
        CANCELLED = 'cancelled'

    doctor = models.ForeignKey(
        'doctors.DoctorProfile',
        on_delete=models.CASCADE,
        related_name='appointments',
    )
    doctor_name = models.CharField(max_length=511)
    specialty = models.CharField(max_length=255)
    patient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='appointments',
    )
    patient_name = models.CharField(max_length=511)
    date = models.DateField()
    time_slot = models.IntegerField()
    time = models.TimeField()
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.PENDING)
    notes = models.TextField(default='', blank=True, max_length=500)
    doctor_notes = models.TextField(default='', blank=True)
    paid = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f'{self.patient_name} - {self.doctor_name} - {self.date}'
