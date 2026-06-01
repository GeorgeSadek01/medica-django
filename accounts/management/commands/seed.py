from django.core.management.base import BaseCommand
from django.utils import timezone
from accounts.models import User
from doctors.models import DoctorProfile, AvailabilityBlock
from appointments.models import Appointment
from specialties.models import Specialty


class Command(BaseCommand):
    help = 'Seed database with test data'

    def handle(self, *args, **options):
        password = 'Test1234'

        Specialty.objects.get_or_create(name='Cardiology')
        Specialty.objects.get_or_create(name='Dermatology')
        Specialty.objects.get_or_create(name='Neurology')
        Specialty.objects.get_or_create(name='Pediatrics')
        Specialty.objects.get_or_create(name='Orthopedics')

        patient, _ = User.objects.get_or_create(
            email='patient@test.com',
            defaults={
                'first_name': 'Ahmed',
                'last_name': 'Ali',
                'role': 'patient',
                'phone': '01001234567',
            },
        )
        patient.set_password(password)
        patient.save()

        admin_user, _ = User.objects.get_or_create(
            email='admin@test.com',
            defaults={
                'first_name': 'Admin',
                'last_name': 'User',
                'role': 'admin',
                'is_staff': True,
                'is_superuser': True,
                'verified': True,
            },
        )
        admin_user.set_password(password)
        admin_user.save()

        doctors_data = [
            {'email': 'doctor1@test.com', 'first': 'Mohamed', 'last': 'Hassan', 'spec': 'Cardiology', 'price': 500},
            {'email': 'doctor2@test.com', 'first': 'Ahmed', 'last': 'Youssef', 'spec': 'Cardiology', 'price': 400},
            {'email': 'doctor3@test.com', 'first': 'Sara', 'last': 'Khaled', 'spec': 'Dermatology', 'price': 350},
            {'email': 'doctor4@test.com', 'first': 'Nadia', 'last': 'Fathy', 'spec': 'Dermatology', 'price': 300},
            {'email': 'doctor5@test.com', 'first': 'Karim', 'last': 'Mansour', 'spec': 'Neurology', 'price': 600},
            {'email': 'doctor6@test.com', 'first': 'Laila', 'last': 'Samy', 'spec': 'Neurology', 'price': 550},
            {'email': 'doctor7@test.com', 'first': 'Tamer', 'last': 'Hussein', 'spec': 'Pediatrics', 'price': 250},
            {'email': 'doctor8@test.com', 'first': 'Hoda', 'last': 'Ezzat', 'spec': 'Orthopedics', 'price': 450},
        ]

        created_doctors = []
        for d in doctors_data:
            user, _ = User.objects.get_or_create(
                email=d['email'],
                defaults={
                    'first_name': d['first'],
                    'last_name': d['last'],
                    'role': 'doctor',
                    'verified': True,
                },
            )
            user.set_password(password)
            user.save()

            doctor, _ = DoctorProfile.objects.update_or_create(
                user=user,
                defaults={
                    'first_name': d['first'],
                    'last_name': d['last'],
                    'specialty': d['spec'],
                    'bio': f'Experienced {d["spec"].lower()} specialist.',
                    'contact': d['email'],
                    'session_price': d['price'],
                },
            )

            AvailabilityBlock.objects.get_or_create(
                doctor=doctor, day='Monday',
                defaults={'start_time': '09:00', 'end_time': '12:00'},
            )
            created_doctors.append(doctor)

        self.stdout.write(self.style.SUCCESS('Seed data created:'))
        self.stdout.write(f'  Patient: patient@test.com / {password}')
        self.stdout.write(f'  Admin:   admin@test.com / {password}')
        self.stdout.write(f'  Doctors ({len(created_doctors)}):')
        for d in created_doctors:
            self.stdout.write(f'    ID={d.pk} | {d.first_name} {d.last_name} | {d.specialty} | {d.session_price} EGP')
        self.stdout.write(f'\n  Use ?page=1&page_size=5 on GET /api/doctors/ to test pagination')
