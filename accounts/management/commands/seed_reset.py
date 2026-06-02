from django.core.management.base import BaseCommand
from datetime import date, timedelta
from accounts.models import User
from doctors.models import DoctorProfile, AvailabilityBlock
from appointments.models import Appointment


class Command(BaseCommand):
    help = 'Reset and seed fresh appointments for testing'

    def handle(self, *args, **options):
        try:
            patient = User.objects.get(email='patient@test.com')
            doctor = DoctorProfile.objects.first()
            if not doctor:
                raise DoctorProfile.DoesNotExist
        except (User.DoesNotExist, DoctorProfile.DoesNotExist):
            self.stdout.write(self.style.ERROR('Run `python manage.py seed` first'))
            return

        deleted, _ = Appointment.objects.filter(patient=patient).delete()
        self.stdout.write(f'Cleared {deleted} existing appointments')

        today = date.today()

        def next_weekday(d, wday):
            days_ahead = wday - d.weekday()
            if days_ahead <= 0:
                days_ahead += 7
            return d + timedelta(days=days_ahead)

        mon = next_weekday(today, 0)
        wed = next_weekday(today, 2)

        appointments_data = [
            {'date': mon, 'time_slot': 1, 'time': '09:00', 'status': 'pending', 'paid': False, 'notes': 'Test payment'},
            {'date': mon, 'time_slot': 2, 'time': '10:00', 'status': 'confirmed', 'paid': True, 'notes': ''},
            {'date': wed, 'time_slot': 3, 'time': '14:00', 'status': 'confirmed', 'paid': True, 'notes': ''},
        ]

        created = []
        for data in appointments_data:
            obj = Appointment.objects.create(
                doctor=doctor,
                patient=patient,
                doctor_name=f'{doctor.first_name} {doctor.last_name}',
                specialty=doctor.specialty,
                patient_name=f'{patient.first_name} {patient.last_name}',
                date=data['date'],
                time_slot=data['time_slot'],
                time=data['time'],
                status=data['status'],
                paid=data['paid'],
                notes=data.get('notes', ''),
            )
            created.append(obj)

        self.stdout.write(self.style.SUCCESS('Appointments seeded:'))
        for a in created:
            self.stdout.write(f'  ID={a.id} | {a.date} {a.time} | {a.status} | paid={a.paid}')
        self.stdout.write(f'\n  Doctor Profile ID to use: {doctor.pk}')
        self.stdout.write('\n  To test payment on the pending one:')
        self.stdout.write(f'    POST /api/appointments/{created[0].id}/payment/')
