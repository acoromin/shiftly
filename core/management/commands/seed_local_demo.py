import os
import secrets
from datetime import datetime, time, timedelta
from pathlib import Path

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from companies.models import Company, Workplace
from employees.models import EmployeeProfile
from incidents.models import Incident
from leaves.models import LeaveRequest
from scheduling.models import Shift
from timeclock.models import TimeClockEntry


DEMO_USERS = (
    ('demo_admin', 'Martina Soler', EmployeeProfile.Role.ADMIN, EmployeeProfile.Position.WAITER),
    ('demo_ana', 'Ana García', EmployeeProfile.Role.WORKER, EmployeeProfile.Position.WAITER),
    ('demo_luis', 'Luis Pérez', EmployeeProfile.Role.WORKER, EmployeeProfile.Position.COOK),
)
DEMO_NOTE = 'Cuenta ficticia de la demo local.'
ACCESS_FILE = Path(settings.BASE_DIR) / 'backups' / 'demo-access.txt'


class Command(BaseCommand):
    help = 'Crea cuentas y actividad ficticia solo en la base SQLite de desarrollo.'

    def handle(self, *args, **options):
        if not settings.DEBUG or settings.DATABASES['default']['ENGINE'] != 'django.db.backends.sqlite3':
            raise CommandError('La demo solo puede crearse con DEBUG=True y SQLite local.')
        User = get_user_model()
        names = [username for username, _full_name, _role, _position in DEMO_USERS]
        existing = User.objects.filter(username__in=names)
        if existing.exists():
            if existing.count() != len(names) or not ACCESS_FILE.exists():
                raise CommandError('Hay cuentas demo parciales o faltan credenciales; revisar antes de continuar.')
            self.stdout.write(f'La demo ya existe. Credenciales: {ACCESS_FILE}')
            return
        if EmployeeProfile.objects.exists():
            raise CommandError('La base contiene perfiles reales; no se mezclarán con la demo local.')
        if ACCESS_FILE.exists():
            raise CommandError('Ya existe el archivo de credenciales de demo; revisar antes de continuar.')

        password = secrets.token_urlsafe(18)
        today = timezone.localdate()
        now = timezone.localtime()
        with transaction.atomic():
            company, _created = Company.objects.get_or_create(
                name='Café Brisa', defaults={'business_type': Company.BusinessType.CAFE},
            )
            workplace, _created = Workplace.objects.get_or_create(
                company=company, name='Local principal',
            )
            if workplace.qr_token_hash:
                raise CommandError('El centro ya tiene un QR real configurado; no se reemplazará.')
            qr_token = Workplace.generate_qr_token()
            workplace.public_wifi_ip = workplace.public_wifi_ip or '127.0.0.1'
            workplace.set_qr_token(qr_token)
            workplace.save(update_fields=['public_wifi_ip', 'qr_token_hash'])

            profiles = {}
            for username, full_name, role, position in DEMO_USERS:
                user = User.objects.create_user(username=username, password=password)
                profiles[username] = EmployeeProfile.objects.create(
                    user=user, company=company, primary_workplace=workplace,
                    full_name=full_name, role=role, primary_position=position,
                    start_date=today - timedelta(days=90), internal_notes=DEMO_NOTE,
                )
            admin = profiles['demo_admin']
            for username, start_hour in (('demo_ana', 9), ('demo_luis', 10)):
                employee = profiles[username]
                for offset in (-3, -2, -1, 0, 1, 2, 3):
                    day = today + timedelta(days=offset)
                    shift = Shift.objects.create(
                        employee=employee, company=company, workplace=workplace,
                        date=day, start_time=time(start_hour), end_time=time(start_hour + 8),
                        planned_break_minutes=30, position=employee.primary_position,
                        created_by=admin.user,
                    )
                    if offset > 0:
                        continue
                    clock_in = timezone.make_aware(datetime.combine(day, time(start_hour)))
                    clock_out = timezone.make_aware(datetime.combine(day, time(start_hour + 8)))
                    if offset < 0 or now >= clock_in + timedelta(minutes=15):
                        TimeClockEntry.objects.create(
                            employee=employee, company=company, workplace=workplace,
                            related_shift=shift, entry_type=TimeClockEntry.EntryType.IN,
                            timestamp=clock_in, status=TimeClockEntry.Status.VALID,
                            created_by=employee.user, qr_token_label='demo',
                        )
                    if offset < 0 or now >= clock_out + timedelta(minutes=15):
                        TimeClockEntry.objects.create(
                            employee=employee, company=company, workplace=workplace,
                            related_shift=shift, entry_type=TimeClockEntry.EntryType.OUT,
                            timestamp=clock_out, status=TimeClockEntry.Status.VALID,
                            created_by=employee.user, qr_token_label='demo',
                        )
            LeaveRequest.objects.create(
                employee=profiles['demo_ana'], company=company,
                request_type=LeaveRequest.RequestType.VACATION,
                start_date=today + timedelta(days=10), end_date=today + timedelta(days=12),
                worker_comment='Viaje familiar de ejemplo.',
            )
            LeaveRequest.objects.create(
                employee=profiles['demo_luis'], company=company,
                request_type=LeaveRequest.RequestType.DAY_OFF,
                start_date=today + timedelta(days=7), end_date=today + timedelta(days=7),
                status=LeaveRequest.Status.APPROVED, reviewed_by=admin.user,
                reviewed_at=timezone.now(), admin_comment='Aprobado para la demo.',
            )
            Incident.objects.create(
                employee=profiles['demo_luis'], company=company,
                date=today - timedelta(days=1),
                incident_type=Incident.IncidentType.CLOCK_ERROR,
                description='Ejemplo: olvidé indicar la pausa del turno.',
                created_by=profiles['demo_luis'].user,
            )

        ACCESS_FILE.parent.mkdir(exist_ok=True)
        fd = os.open(ACCESS_FILE, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, 'w') as output:
            output.write('DEMO LOCAL — no publicar ni subir a Git\n')
            output.write('Web: http://127.0.0.1:8000/\n')
            output.write('Usuario administrador: demo_admin\n')
            output.write('Usuarios trabajadores: demo_ana, demo_luis\n')
            output.write(f'Contraseña para los tres: {password}\n')
            output.write('La cuenta técnica existente no se ha modificado.\n')
            output.write('QR de prueba: válido solo desde este ordenador (IP 127.0.0.1):\n')
            output.write(workplace.qr_url('http://127.0.0.1:8000/fichar/', qr_token) + '\n')
        self.stdout.write(f'Demo local creada: 3 cuentas, 14 turnos y actividad ficticia. Credenciales: {ACCESS_FILE}')
