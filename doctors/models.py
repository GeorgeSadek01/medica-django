from django.db import models
from django.conf import settings
from django.db.models import Avg, Count
from django.core.validators import MinValueValidator, MaxValueValidator


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
    session_duration = models.IntegerField(default=30)
    average_rating = models.FloatField(default=0.0)
    review_count = models.IntegerField(default=0)

    def update_rating(self):
        result = DoctorReview.objects.filter(doctor=self).aggregate(
            avg=Avg('rating'), count=Count('id')
        )
        self.average_rating = result['avg'] or 0.0
        self.review_count = result['count'] or 0
        self.save(update_fields=['average_rating', 'review_count'])

    def __str__(self):
        return f'{self.first_name} {self.last_name}'


class DoctorReview(models.Model):
    doctor = models.ForeignKey(
        DoctorProfile,
        on_delete=models.CASCADE,
        related_name='reviews',
    )
    patient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='reviews',
    )
    appointment = models.OneToOneField(
        'appointments.Appointment',
        on_delete=models.CASCADE,
        related_name='review',
    )
    rating = models.IntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)])
    comment = models.TextField(default='', blank=True, max_length=1000)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        constraints = [
            models.UniqueConstraint(
                fields=['doctor', 'patient', 'appointment'],
                name='unique_review_per_appointment',
            )
        ]

    def __str__(self):
        return f'{self.patient} -> {self.doctor} ({self.rating}/5)'


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
