# Healthcare Backend (Django + DRF + PostgreSQL)

REST API for managing patients, doctors and patient-doctor assignments, secured with JWT
(`djangorestframework-simplejwt`).

## Setup

```bash
python -m venv .venv
.venv\Scripts\activate          # macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt

cp .env.example .env            # then set SECRET_KEY and DATABASE_URL
createdb -U postgres healthcare # or create the database in pgAdmin

python manage.py migrate
python manage.py runserver
```

All configuration comes from `.env` (never committed). `SECRET_KEY` and `DATABASE_URL` are
required, and the app will not start without them:

| Variable | Example |
| --- | --- |
| `SECRET_KEY` | generate: `python -c "from django.core.management.utils import get_random_secret_key as k; print(k())"` |
| `DEBUG` | `True` locally, `False` in production |
| `ALLOWED_HOSTS` | `localhost,127.0.0.1` |
| `DATABASE_URL` | `postgres://postgres:<password>@localhost:5432/healthcare` |

## Endpoints

All routes except register, login and refresh require `Authorization: Bearer <access token>`.

| Method | Path | Description |
| --- | --- | --- |
| POST | `/api/auth/register/` | Register with `name`, `email`, `password` |
| POST | `/api/auth/login/` | Returns `access` + `refresh` JWT for `email`, `password` |
| POST | `/api/auth/refresh/` | New access token from a `refresh` token |
| POST | `/api/patients/` | Create a patient (owned by the caller) |
| GET | `/api/patients/` | List the caller's patients |
| GET | `/api/patients/<id>/` | Patient detail |
| PUT | `/api/patients/<id>/` | Update a patient |
| DELETE | `/api/patients/<id>/` | Delete a patient |
| POST | `/api/doctors/` | Create a doctor |
| GET | `/api/doctors/` | List all doctors |
| GET | `/api/doctors/<id>/` | Doctor detail |
| PUT | `/api/doctors/<id>/` | Update a doctor |
| DELETE | `/api/doctors/<id>/` | Delete a doctor |
| POST | `/api/mappings/` | Assign a doctor to one of the caller's patients (`patient`, `doctor`) |
| GET | `/api/mappings/` | List mappings for the caller's patients |
| GET | `/api/mappings/<patient_id>/` | Doctors assigned to that patient |
| DELETE | `/api/mappings/<id>/` | Remove an assignment (by mapping id) |

**Data access.** Patients belong to the user who created them: a user can only see, edit,
delete or assign doctors to their own patients, and the mapping endpoints are scoped the
same way, so one user can never read or remove another user's assignments. Doctors are a
shared directory visible to every authenticated user, as the spec's "retrieve all doctors"
describes.

**Errors** are JSON with standard status codes: `400` with per-field messages for invalid
input (weak password, duplicate email, bad gender choice, duplicate assignment, ...), `401`
for a missing or invalid token, `404` for records that don't exist or belong to another user.

## Project structure

```
healthcare/          project settings (env-driven) and root URLs
api/
  models.py          User (email login), Patient, Doctor, PatientDoctorMapping
  serializers.py     validation: password strength, ownership, unique assignment
  views.py           viewsets, each scoped to the authenticated user
  urls.py            /api/auth/* plus router-generated resource routes
  tests.py           end-to-end API tests
postman_collection.json
```

## Tests

```bash
python manage.py test
```

Covers registration and login validation, auth enforcement, patient and doctor CRUD, input
validation, per-user isolation of patients and mappings, and mapping create/list/delete
including duplicate rejection.

## Testing with Postman

1. Start the server: `python manage.py runserver`
2. In Postman: **Import** → select `postman_collection.json`.
3. Run the folders top to bottom, or use **Run collection** to run everything at once.

The 19 requests run in order and need no editing:

- **Register** creates a fresh user each run, so the collection can be re-run.
- **Login** stores the JWT in the `access_token` collection variable; the collection sends
  it as a Bearer token on every other request.
- Create requests store the new `patient_id`, `doctor_id` and `mapping_id` for the
  requests that follow.
- Every request asserts its expected status code, including the negative cases
  (unauthenticated request → `401`, duplicate assignment → `400`).
- The deletes are in the last folder, so the records exist while earlier folders use them.

`base_url` defaults to `http://127.0.0.1:8000`; change that collection variable to target
another host.
