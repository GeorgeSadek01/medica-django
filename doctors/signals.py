from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver


@receiver([post_save, post_delete], sender='doctors.DoctorReview')
def update_doctor_rating(sender, instance, **kwargs):
    instance.doctor.update_rating()
