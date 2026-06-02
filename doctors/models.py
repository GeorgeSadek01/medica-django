from django.db import models
from django.conf import settings


class DoctorProfile(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='doctor_profile',
        primary_key=True,
    )
    first_name = models.CharField(max_length=255)
    last_name = models.CharField(max_length=255)
    specialty = models.CharField(max_length=255, db_index=True)
    bio = models.TextField(default='', blank=True, max_length=1000)
    contact = models.CharField(max_length=255, default='', blank=True)
    session_price = models.IntegerField(default=0)

    def __str__(self):
        return f'{self.first_name} {self.last_name}'


class DoctorDocument(models.Model):
    class Status(models.TextChoices):
        PENDING = 'pending'
        APPROVED = 'approved'
        REJECTED = 'rejected'

    doctor = models.OneToOneField(
        DoctorProfile,
        on_delete=models.CASCADE,
        related_name='documents',
    )
    identity_document = models.FileField(upload_to='doctor_documents/')
    medical_certificate = models.FileField(upload_to='doctor_documents/')
    uploaded_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
    )
    rejection_reason = models.TextField(default='', blank=True)

    def __str__(self):
        return f'Documents for {self.doctor.first_name} {self.doctor.last_name} ({self.status})'


class AvailabilityBlock(models.Model):
    DAYS_OF_WEEK = [
        ('Monday', 'Monday'),
        ('Tuesday', 'Tuesday'),
        ('Wednesday', 'Wednesday'),
        ('Thursday', 'Thursday'),
        ('Friday', 'Friday'),
        ('Saturday', 'Saturday'),
        ('Sunday', 'Sunday'),
    ]

    doctor = models.ForeignKey(
        DoctorProfile,
        on_delete=models.CASCADE,
        related_name='availability',
    )
    day = models.CharField(max_length=15, choices=DAYS_OF_WEEK)
    start_time = models.TimeField()
    end_time = models.TimeField()

    def __str__(self):
        return f'{self.doctor} - {self.day} {self.start_time}-{self.end_time}'
