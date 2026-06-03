from django.core.management.base import BaseCommand
from datetime import date, timedelta
from accounts.models import User
from doctors.models import DoctorProfile, AvailabilityBlock
from appointments.models import Appointment


class Command(BaseCommand):
    help = 'Seed sample appointments for testing payment flow'

    def handle(self, *args, **options):
        try:
            patient = User.objects.get(email='patient@test.com')
            doctor = DoctorProfile.objects.first()
            if not doctor:
                raise DoctorProfile.DoesNotExist
        except (User.DoesNotExist, DoctorProfile.DoesNotExist):
            self.stdout.write(self.style.ERROR('Run `python manage.py seed` first'))
            return

        today = date.today()

        def next_weekday(d, wday):
            days_ahead = wday - d.weekday()
            if days_ahead <= 0:
                days_ahead += 7
            return d + timedelta(days=days_ahead)

        mon = next_weekday(today, 0)
        wed = next_weekday(today, 2)

        appointments_data = [
            {'date': mon, 'time_slot': 1, 'time': '09:00', 'status': 'pending', 'paid': False, 'notes': 'First visit — routine checkup'},
            {'date': mon, 'time_slot': 2, 'time': '09:45', 'status': 'confirmed', 'paid': True, 'notes': 'Follow up — lab results review'},
            {'date': wed, 'time_slot': 3, 'time': '09:00', 'status': 'completed', 'paid': True, 'notes': 'Annual cardiac assessment'},
            {'date': wed, 'time_slot': 4, 'time': '09:45', 'status': 'cancelled', 'paid': False, 'notes': 'Patient cancelled — rescheduled'},
        ]

        created = []
        for data in appointments_data:
            obj, was = Appointment.objects.get_or_create(
                doctor=doctor,
                patient=patient,
                date=data['date'],
                time_slot=data['time_slot'],
                defaults={
                    'doctor_name': f'{doctor.first_name} {doctor.last_name}',
                    'specialty': doctor.specialty,
                    'patient_name': f'{patient.first_name} {patient.last_name}',
                    'time': data['time'],
                    'status': data['status'],
                    'paid': data.get('paid', False),
                    'notes': data.get('notes', ''),
                },
            )
            if was:
                created.append(obj)

        self.stdout.write(self.style.SUCCESS(f'Created {len(created)} sample appointments:'))
        for a in created:
            status_icon = '🟡' if a.status == 'pending' else '🟢' if a.status == 'confirmed' else '✅' if a.status == 'completed' else '⚫'
            self.stdout.write(f'  {status_icon} ID={a.id} | {a.date} {a.time} | {a.status} | paid={a.paid} | "{a.notes}"')
        pending = [a for a in created if a.status == 'pending']
        if pending:
            self.stdout.write('\nTest payment on pending appointment:')
            self.stdout.write(f'  POST /api/appointments/{pending[0].id}/payment/')
