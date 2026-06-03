from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import date, timedelta
from accounts.models import User
from doctors.models import DoctorProfile, AvailabilityBlock, DoctorReview
from appointments.models import Appointment
from specialties.models import Specialty


def _next_weekday(d, wday):
    days_ahead = wday - d.weekday()
    if days_ahead <= 0:
        days_ahead += 7
    return d + timedelta(days=days_ahead)


class Command(BaseCommand):
    help = 'Seed database with test data, users, and sample appointments'

    def add_arguments(self, parser):
        parser.add_argument(
            '--reset',
            action='store_true',
            help='Delete existing appointments for test patient before seeding',
        )

    def handle(self, *args, **options):
        password = 'Test1234'

        for name in ['Cardiology', 'Dermatology', 'Neurology', 'Pediatrics', 'Orthopedics', 'Ophthalmology', 'Psychiatry']:
            Specialty.objects.get_or_create(name=name)

        patient, _ = User.objects.get_or_create(
            email='patient@test.com',
            defaults={
                'first_name': 'Ahmed',
                'last_name': 'Ali',
                'role': 'patient',
                'phone': '01001234567',
                'email_verified': True,
            },
        )
        if not patient.email_verified:
            patient.email_verified = True
            patient.save(update_fields=['email_verified'])
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
                'email_verified': True,
            },
        )
        if not admin_user.email_verified:
            admin_user.email_verified = True
            admin_user.save(update_fields=['email_verified'])
        admin_user.set_password(password)
        admin_user.save()

        doctors_data = [
            {
                'email': 'doctor1@test.com', 'first': 'Mohamed', 'last': 'Hassan',
                'spec': 'Cardiology', 'price': 500, 'duration': 45,
                'availability': [
                    ('Monday', '09:00', '13:00'),
                    ('Wednesday', '09:00', '13:00'),
                ],
                'bio': 'Senior cardiologist with 15+ years of experience in interventional cardiology and cardiac imaging.',
            },
            {
                'email': 'doctor2@test.com', 'first': 'Ahmed', 'last': 'Youssef',
                'spec': 'Cardiology', 'price': 400, 'duration': 30,
                'availability': [
                    ('Monday', '10:00', '15:00'),
                    ('Wednesday', '10:00', '15:00'),
                    ('Friday', '10:00', '14:00'),
                ],
                'bio': 'Cardiologist specializing in preventive cardiology and heart failure management.',
            },
            {
                'email': 'doctor3@test.com', 'first': 'Sara', 'last': 'Khaled',
                'spec': 'Dermatology', 'price': 350, 'duration': 30,
                'availability': [
                    ('Monday', '09:00', '14:00'),
                    ('Tuesday', '09:00', '14:00'),
                    ('Thursday', '09:00', '14:00'),
                ],
                'bio': 'Board-certified dermatologist experienced in medical, surgical, and cosmetic dermatology.',
            },
            {
                'email': 'doctor4@test.com', 'first': 'Nadia', 'last': 'Fathy',
                'spec': 'Dermatology', 'price': 300, 'duration': 30,
                'availability': [
                    ('Tuesday', '11:00', '16:00'),
                    ('Thursday', '11:00', '16:00'),
                ],
                'bio': 'Dermatologist focused on acne treatment, skin cancer screening, and pediatric dermatology.',
            },
            {
                'email': 'doctor5@test.com', 'first': 'Karim', 'last': 'Mansour',
                'spec': 'Neurology', 'price': 600, 'duration': 60,
                'availability': [
                    ('Monday', '10:00', '14:00'),
                    ('Wednesday', '10:00', '14:00'),
                ],
                'bio': 'Consultant neurologist specializing in epilepsy, multiple sclerosis, and headache disorders.',
            },
            {
                'email': 'doctor6@test.com', 'first': 'Laila', 'last': 'Samy',
                'spec': 'Neurology', 'price': 550, 'duration': 45,
                'availability': [
                    ('Tuesday', '09:00', '13:00'),
                    ('Thursday', '09:00', '13:00'),
                ],
                'bio': 'Neurologist with expertise in movement disorders, stroke rehabilitation, and neurophysiology.',
            },
            {
                'email': 'doctor7@test.com', 'first': 'Tamer', 'last': 'Hussein',
                'spec': 'Pediatrics', 'price': 250, 'duration': 30,
                'availability': [
                    ('Monday', '09:00', '12:00'),
                    ('Tuesday', '09:00', '12:00'),
                    ('Wednesday', '09:00', '12:00'),
                    ('Thursday', '09:00', '12:00'),
                ],
                'bio': 'Experienced pediatrician providing compassionate care for children from infancy through adolescence.',
            },
            {
                'email': 'doctor8@test.com', 'first': 'Hoda', 'last': 'Ezzat',
                'spec': 'Orthopedics', 'price': 450, 'duration': 45,
                'availability': [
                    ('Monday', '09:00', '14:00'),
                    ('Wednesday', '09:00', '14:00'),
                    ('Friday', '09:00', '13:00'),
                ],
                'bio': 'Orthopedic surgeon specializing in sports medicine, joint reconstruction, and trauma surgery.',
            },
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
                    'email_verified': True,
                },
            )
            if not user.email_verified:
                user.email_verified = True
                user.save(update_fields=['email_verified'])
            user.set_password(password)
            user.save()

            doctor, _ = DoctorProfile.objects.update_or_create(
                user=user,
                defaults={
                    'first_name': d['first'],
                    'last_name': d['last'],
                    'specialty': d['spec'],
                    'bio': d['bio'],
                    'contact': d['email'],
                    'session_price': d['price'],
                    'session_duration': d['duration'],
                },
            )

            for day, start, end in d['availability']:
                AvailabilityBlock.objects.get_or_create(
                    doctor=doctor, day=day, start_time=start, end_time=end,
                )
            created_doctors.append(doctor)

        self.stdout.write(self.style.SUCCESS('Seed data created:'))
        self.stdout.write(f'  Patient: patient@test.com / {password}')
        self.stdout.write(f'  Admin:   admin@test.com / {password}')
        self.stdout.write(f'  Doctors ({len(created_doctors)}):')
        for d in created_doctors:
            block_count = d.availability.count()
            self.stdout.write(
                f'    ID={d.pk} | {d.first_name} {d.last_name} | {d.specialty} | '
                f'{d.session_price} EGP | {d.session_duration} min | {block_count} day(s)'
            )

        doctor = created_doctors[0]
        today = date.today()
        mon = _next_weekday(today, 0)
        wed = _next_weekday(today, 2)

        if options['reset']:
            deleted, _ = Appointment.objects.filter(patient=patient).delete()
            self.stdout.write(f'\n  Reset: cleared {deleted} existing appointments for patient@test.com')

        appointments_data = [
            {'date': mon, 'time_slot': 1, 'time': '09:00', 'status': 'pending', 'paid': False, 'notes': 'First visit — routine checkup'},
            {'date': mon, 'time_slot': 2, 'time': '09:45', 'status': 'confirmed', 'paid': True, 'notes': 'Follow up — lab results review'},
            {'date': wed, 'time_slot': 3, 'time': '09:00', 'status': 'completed', 'paid': True, 'notes': 'Annual cardiac assessment'},
            {'date': wed, 'time_slot': 4, 'time': '09:45', 'status': 'cancelled', 'paid': False, 'notes': 'Patient cancelled — rescheduled'},
        ]

        created_appts = []
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
                created_appts.append(obj)

        if created_appts:
            self.stdout.write(f'\n  Appointments ({len(created_appts)}) for Dr. {doctor.first_name} {doctor.last_name} (ID={doctor.pk}):')
            for a in created_appts:
                label = {'pending': '[PENDING]', 'confirmed': '[CONFIRMED]', 'completed': '[DONE]', 'cancelled': '[CANCELLED]'}.get(a.status, '[?]')
                self.stdout.write(f'    {label} ID={a.id} | {a.date} {a.time} | paid={a.paid}')
            pending = [a for a in created_appts if a.status == 'pending']
            if pending:
                self.stdout.write(f'\n  Test payment: POST /api/appointments/{pending[0].id}/payment/')

        # Seed reviews — create extra completed appointments for variety, then reviews
        review_configs = [
            {'doctor_idx': 0, 'rating': 5, 'comment': 'Excellent cardiologist! Very thorough and caring.'},
            {'doctor_idx': 1, 'rating': 4, 'comment': 'Good experience, very knowledgeable. Had to wait a bit though.'},
            {'doctor_idx': 2, 'rating': 5, 'comment': 'Dr. Sara is amazing! She really listens to her patients.'},
            {'doctor_idx': 4, 'rating': 3, 'comment': 'Decent neurologist but appointment felt rushed.'},
            {'doctor_idx': 6, 'rating': 5, 'comment': 'Wonderful pediatrician! My kids love visiting her.'},
            {'doctor_idx': 7, 'rating': 4, 'comment': 'Great orthopedic surgeon. Recovery went smoothly.'},
        ]

        created_reviews = []
        for cfg in review_configs:
            target_doctor = created_doctors[cfg['doctor_idx']]
            existing_review = DoctorReview.objects.filter(
                doctor=target_doctor, patient=patient
            ).first()
            if existing_review:
                continue

            extra_appt, _ = Appointment.objects.get_or_create(
                doctor=target_doctor,
                patient=patient,
                date=wed,
                time_slot=10 + cfg['doctor_idx'],
                defaults={
                    'doctor_name': f'{target_doctor.first_name} {target_doctor.last_name}',
                    'specialty': target_doctor.specialty,
                    'patient_name': f'{patient.first_name} {patient.last_name}',
                    'time': '09:00',
                    'status': Appointment.Status.COMPLETED,
                    'paid': True,
                },
            )
            review = DoctorReview.objects.create(
                doctor=target_doctor,
                patient=patient,
                appointment=extra_appt,
                rating=cfg['rating'],
                comment=cfg['comment'],
            )
            created_reviews.append(review)

        if created_reviews:
            self.stdout.write(f'\n  Reviews ({len(created_reviews)}):')
            for r in created_reviews:
                self.stdout.write(f'    {r.rating}/5 Dr. {r.doctor.first_name} {r.doctor.last_name} — "{r.comment}"')

        self.stdout.write('\n  Doctors are sorted by rating. Use GET /api/doctors/ to verify.')
