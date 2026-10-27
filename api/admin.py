from django.contrib import admin

from .models import Doctor, Patient, PatientDoctorMapping, User

admin.site.register([User, Patient, Doctor, PatientDoctorMapping])
