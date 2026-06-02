# specialties/models.py
from django.db import models
class Specialty(models.Model):
    name = models.CharField(max_length=255, unique=True)

    class Meta:
        verbose_name_plural = 'Specialties'  # ← ضيفي ده

    def __str__(self):
        return self.name