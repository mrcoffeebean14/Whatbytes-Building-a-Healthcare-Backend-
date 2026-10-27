from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework.test import APITestCase

from .models import Doctor, Patient, PatientDoctorMapping

User = get_user_model()

CREDS = {"name": "Ada", "email": "ada@example.com", "password": "s3cret-pass-99"}
OTHER = {"name": "Eve", "email": "eve@example.com", "password": "s3cret-pass-98"}


class HealthcareFlowTests(APITestCase):
    def login(self, creds=CREDS):
        token = self.client.post(reverse("login"), {"email": creds["email"], "password": creds["password"]}).data
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token['access']}")

    def login_as_other_user(self):
        self.client.post(reverse("register"), OTHER)
        self.login(OTHER)

    def setUp(self):
        self.assertEqual(self.client.post(reverse("register"), CREDS).status_code, 201)
        self.user = User.objects.get(email=CREDS["email"])
        self.login()

    def test_endpoints_require_auth(self):
        self.client.credentials()
        self.assertEqual(self.client.get("/api/patients/").status_code, 401)
        self.assertEqual(self.client.get("/api/doctors/").status_code, 401)
        self.assertEqual(self.client.get("/api/mappings/").status_code, 401)

    def test_register_rejects_weak_password_and_duplicate_email(self):
        self.assertEqual(self.client.post(reverse("register"), {**CREDS, "email": "b@x.com", "password": "123"}).status_code, 400)
        self.assertEqual(self.client.post(reverse("register"), CREDS).status_code, 400)

    def test_login_rejects_wrong_password(self):
        self.client.credentials()
        self.assertEqual(self.client.post(reverse("login"), {"email": CREDS["email"], "password": "wrong"}).status_code, 401)

    def test_patient_crud(self):
        patient = self.client.post("/api/patients/", {"name": "Bob", "age": 40, "gender": "M"}, format="json")
        self.assertEqual(patient.status_code, 201)
        pid = patient.data["id"]
        self.assertEqual(self.client.get(f"/api/patients/{pid}/").data["name"], "Bob")
        self.assertEqual(self.client.put(f"/api/patients/{pid}/", {"name": "Bobby", "age": 41, "gender": "M"}, format="json").data["name"], "Bobby")
        self.assertEqual(self.client.post("/api/patients/", {"name": "Bad", "age": -1, "gender": "X"}, format="json").status_code, 400)
        self.assertEqual(self.client.delete(f"/api/patients/{pid}/").status_code, 204)
        self.assertEqual(Patient.objects.count(), 0)

    def test_patients_are_scoped_to_their_creator(self):
        mine = Patient.objects.create(created_by=self.user, name="Mine", age=30, gender="F")
        self.login_as_other_user()
        self.assertEqual(self.client.get("/api/patients/").data, [])
        self.assertEqual(self.client.get(f"/api/patients/{mine.id}/").status_code, 404)
        self.assertEqual(self.client.delete(f"/api/patients/{mine.id}/").status_code, 404)

    def test_doctor_crud_and_mappings(self):
        doctor = self.client.post("/api/doctors/", {"name": "House", "specialization": "Diagnostics", "email": "house@x.com"}, format="json")
        self.assertEqual(doctor.status_code, 201)
        did = doctor.data["id"]
        patient = self.client.post("/api/patients/", {"name": "Bob", "age": 40, "gender": "M"}, format="json").data

        mapping = self.client.post("/api/mappings/", {"patient": patient["id"], "doctor": did}, format="json")
        self.assertEqual(mapping.status_code, 201)
        # duplicate assignment is rejected
        self.assertEqual(self.client.post("/api/mappings/", {"patient": patient["id"], "doctor": did}, format="json").status_code, 400)
        # GET /api/mappings/<patient_id>/ returns that patient's doctors
        doctors = self.client.get(f"/api/mappings/{patient['id']}/").data
        self.assertEqual([d["doctor_detail"]["name"] for d in doctors], ["House"])
        self.assertEqual(self.client.get("/api/mappings/abc/").status_code, 404)
        self.assertEqual(self.client.delete(f"/api/mappings/{mapping.data['id']}/").status_code, 204)
        self.assertEqual(PatientDoctorMapping.objects.count(), 0)
        self.assertEqual(self.client.delete(f"/api/doctors/{did}/").status_code, 204)
        self.assertEqual(Doctor.objects.count(), 0)

    def test_mappings_are_scoped_to_patient_owner(self):
        doctor = Doctor.objects.create(name="House", specialization="Dx", email="h@x.com")
        patient = Patient.objects.create(created_by=self.user, name="Bob", age=40, gender="M")
        self.login_as_other_user()
        self.assertEqual(self.client.post("/api/mappings/", {"patient": patient.id, "doctor": doctor.id}, format="json").status_code, 400)
        mapping = PatientDoctorMapping.objects.create(patient=patient, doctor=doctor)
        self.assertEqual(self.client.get("/api/mappings/").data, [])
        self.assertEqual(self.client.get(f"/api/mappings/{patient.id}/").status_code, 404)
        self.assertEqual(self.client.delete(f"/api/mappings/{mapping.id}/").status_code, 404)
        self.assertTrue(PatientDoctorMapping.objects.filter(id=mapping.id).exists())
