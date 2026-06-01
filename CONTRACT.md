# Medica — Full API Contract

> **Project:** Medica Healthcare Appointment Booking System  
> **Frontend:** React 19 + TypeScript + Vite + MUI 9 + Redux Toolkit  
> **Backend:** Django REST Framework (to be implemented)  
> **Base URL:** `http://localhost:3000/api`  
> **Auth:** JWT (access + refresh tokens)

---

## Table of Contents

1. [Authentication](#1-authentication)
2. [Users](#2-users)
3. [Doctors](#3-doctors)
4. [Appointments](#4-appointments)
5. [Specialties](#5-specialties)
6. [Error Handling Conventions](#6-error-handling-conventions)
7. [App Status Machine](#7-appointment-status-machine)
8. [Data Models](#8-data-models)
9. [Frontend Route Map](#9-frontend-route-map)
10. [Auth Flows](#10-auth-flows)

---

## 1. Authentication

### `POST /api/auth/register/`

Register a new user.

**Request Body:**

```json
{
  "email": "string (required, valid email)",
  "password": "string (required, min 8 chars, must contain 1 uppercase + 1 number)",
  "first_name": "string (required, min 2 chars)",
  "last_name": "string (required, min 2 chars)",
  "role": "string (required, one of: 'patient' | 'doctor')",
  "specialty": "string (required if role='doctor')"
}
```

**Success Response (201 Created):**

```json
{
  "id": 1,
  "email": "user@example.com",
  "first_name": "John",
  "last_name": "Doe",
  "role": "patient",
  "phone": "",
  "avatar": "",
  "verified": null
}
```

> **Note:** When `role=doctor`, `verified` starts as `false`. A corresponding doctor profile record is also created.

**Error Responses:**
- `400` — Validation error (missing fields, invalid email, password too weak, duplicate email). Returns `{ "field_name": "error message" }` or `{ "non_field_errors": [...] }`.
- `409` — "An account with this email already exists".

---

### `POST /api/auth/token/`

Login — obtain JWT tokens.

**Request Body:**

```json
{
  "email": "string (required, valid email)",
  "password": "string (required, min 8 chars)"
}
```

**Success Response (200 OK):**

```json
{
  "access": "string (JWT access token)",
  "refresh": "string (JWT refresh token)",
  "user": {
    "id": 1,
    "email": "user@example.com",
    "first_name": "John",
    "last_name": "Doe",
    "role": "patient",
    "phone": "",
    "avatar": "",
    "verified": null
  }
}
```

**Error Responses:**
- `401` — "Invalid email or password".

---

### `POST /api/auth/token/refresh/`

Refresh an expired access token.

**Request Body:**

```json
{
  "refresh": "string (JWT refresh token)"
}
```

**Success Response (200 OK):**

```json
{
  "access": "string (new JWT access token)"
}
```

**Error Responses:**
- `401` — Invalid or expired refresh token.

---

### `POST /api/auth/logout/`

Invalidate the refresh token (client-side also clears localStorage).

**Request Body:**

```json
{
  "refresh": "string (JWT refresh token)"
}
```

**Success Response (200 OK):**

```json
{
  "message": "Logged out successfully"
}
```

---

### `GET /api/auth/me/`

Get the currently authenticated user's profile. Requires `Authorization: Bearer <access_token>`.

**Success Response (200 OK):**

```json
{
  "id": 1,
  "email": "user@example.com",
  "first_name": "John",
  "last_name": "Doe",
  "role": "patient",
  "phone": "",
  "avatar": "",
  "verified": null
}
```

**Error Responses:**
- `401` — Missing or invalid token. Returns `null` user.

---

## 2. Users

All endpoints require `Authorization: Bearer <access_token>`.

### `GET /api/users/`

List all users. **Admin only.**

**Query Parameters:**
- `search` — string, filter by name or email
- `role` — filter by role (`patient`, `doctor`, `admin`)
- `is_active` — boolean
- `verified` — boolean (for doctors)

**Success Response (200 OK):**

```json
[
  {
    "id": 1,
    "email": "user@example.com",
    "first_name": "John",
    "last_name": "Doe",
    "role": "patient",
    "phone": "",
    "avatar": "",
    "is_active": true,
    "verified": null
  }
]
```

---

### `GET /api/users/{id}/`

Get a single user's details. **Admin only.**

**Success Response (200 OK):**

```json
{
  "id": 1,
  "email": "user@example.com",
  "first_name": "John",
  "last_name": "Doe",
  "role": "patient",
  "phone": "",
  "avatar": "",
  "is_active": true,
  "verified": null
}
```

**Error Responses:**
- `404` — User not found.

---

### `PATCH /api/users/{id}/`

Update user profile. Users can update their own profile; admins can update any profile.

**Request Body** (all fields optional):

```json
{
  "first_name": "string",
  "last_name": "string",
  "email": "string (valid email)",
  "phone": "string (11 digits)",
  "avatar": "string (base64 or URL)",
  "is_active": "boolean",
  "verified": "boolean",
  "role": "string (admin only)"
}
```

**Frontend uses this for:**
- **Patient Profile** (`PatientProfile.tsx`): updates `first_name`, `last_name`, `email`, `phone`, `avatar`
- **Admin User Management** (`AdminUsers.tsx`): toggles `is_active`, sets `verified`, sets `role`

**Success Response (200 OK):** Returns the updated user object.

**Error Responses:**
- `400` — Validation error.
- `403` — Not authorized.
- `404` — User not found.

---

### `DELETE /api/users/{id}/` (Soft Delete)

Soft-delete a user. **Admin only.**

**Request Body:**

```json
{
  "soft": true
}
```

**Success Response (200 OK):**

```json
{
  "id": 1,
  "is_active": false,
  "deleted_at": "2025-06-01T12:00:00Z"
}
```

---

## 3. Doctors

### `GET /api/doctors/`

List all doctors. **Public.**

**Query Parameters:**
- `specialty` — string (filter by specialty name, case-insensitive partial match)
- `name` — string (filter by `first_name` + `last_name`, case-insensitive partial match)
- `search` — string (searches both name and specialty)

**Success Response (200 OK):**

```json
[
  {
    "id": 1,
    "first_name": "Ahmed",
    "last_name": "Hassan",
    "specialty": "Cardiology",
    "bio": "Experienced cardiologist with 15 years of practice.",
    "contact": "ahmed.hassan@medica.com",
    "session_price": 500,
    "availability": [
      { "id": 1, "day": "Monday", "start_time": "09:00", "end_time": "12:00" },
      { "id": 2, "day": "Wednesday", "start_time": "14:00", "end_time": "17:00" }
    ]
  }
]
```

---

### `GET /api/doctors/{id}/`

Get a single doctor's public profile. **Public.**

**Success Response (200 OK):**

```json
{
  "id": 1,
  "first_name": "Ahmed",
  "last_name": "Hassan",
  "specialty": "Cardiology",
  "bio": "Experienced cardiologist with 15 years of practice.",
  "contact": "ahmed.hassan@medica.com",
  "session_price": 500,
  "availability": [
    { "id": 1, "day": "Monday", "start_time": "09:00", "end_time": "12:00" }
  ]
}
```

**Error Responses:**
- `404` — Doctor not found.

---

### `PATCH /api/doctors/{id}/`

Update doctor profile. **Doctor (own profile) or Admin.**

**Request Body:**

```json
{
  "specialty": "string",
  "bio": "string (max 1000 chars)",
  "contact": "string (email or phone)",
  "session_price": "number (integer)"
}
```

> Frontend (`DoctorProfilePage.tsx`) sends: `specialty`, `bio`, `contact`. The `session_price` field is read by `PaymentPage.tsx` but not edited in the current UI.

**Success Response (200 OK):** Returns the updated doctor object.

---

### `GET /api/doctors/{id}/availability/`

Get a doctor's availability blocks. **Public.**

**Success Response (200 OK):**

```json
[
  { "id": 1, "day": "Monday", "start_time": "09:00", "end_time": "12:00" },
  { "id": 2, "day": "Wednesday", "start_time": "14:00", "end_time": "17:00" }
]
```

---

### `POST /api/doctors/{id}/availability/`

Add a new availability block. **Doctor (own) or Admin.**

**Request Body:**

```json
{
  "day": "string (required, one of: Monday–Sunday)",
  "start_time": "string (required, HH:MM format, 24h)",
  "end_time": "string (required, HH:MM format, 24h, must be after start_time)"
}
```

**Success Response (201 Created):**

```json
{
  "id": 31,
  "day": "Friday",
  "start_time": "09:00",
  "end_time": "12:00"
}
```

---

### `PUT /api/doctors/{id}/availability/{slot_id}/`

Edit an availability block. **Doctor (own) or Admin.**

**Request Body:**

```json
{
  "day": "string",
  "start_time": "string (HH:MM)",
  "end_time": "string (HH:MM)"
}
```

> Note: The frontend (`DoctorAvailabilityPage.tsx`) currently edits availability blocks locally without a dedicated API call for updates (it manages state in the UI). The backend should expose this endpoint for completeness.

**Success Response (200 OK):** Returns the updated slot.

---

### `DELETE /api/doctors/{id}/availability/{slot_id}/`

Delete an availability block. **Doctor (own) or Admin.**

**Success Response (200 OK):**

```json
{
  "deleted": true,
  "id": 31
}
```

---

## 4. Appointments

All appointment endpoints require `Authorization: Bearer <access_token>`.

### `GET /api/appointments/`

List all appointments.

**Permissions:**
- **Admin:** sees all appointments.
- **Doctor:** sees only their own appointments (filtered by `doctor` field matching the logged-in user's linked doctor ID).
- **Patient:** sees only their own appointments (filtered by `patient` field matching their user ID).

**Query Parameters:**
- `status` — filter by status (`pending`, `confirmed`, `completed`, `cancelled`)
- `specialty` — filter by specialty
- `search` — search by `doctor_name` or `patient_name`
- `doctor` — filter by doctor ID
- `patient` — filter by patient ID
- `date_from` — filter by start date (YYYY-MM-DD)
- `date_to` — filter by end date (YYYY-MM-DD)
- `page` — page number (1-indexed)
- `page_size` — items per page (default 20)

**Success Response (200 OK):**

```json
[
  {
    "id": 1,
    "doctor": 1,
    "doctor_name": "Ahmed Hassan",
    "specialty": "Cardiology",
    "patient": 14,
    "patient_name": "Youssef Tarek",
    "date": "2025-05-25",
    "time_slot": 1,
    "time": "09:00",
    "status": "confirmed",
    "notes": "",
    "doctor_notes": "",
    "paid": true
  }
]
```

---

### `GET /api/appointments/{id}/`

Get a single appointment.

**Success Response (200 OK):**

```json
{
  "id": 1,
  "doctor": 1,
  "doctor_name": "Ahmed Hassan",
  "specialty": "Cardiology",
  "patient": 14,
  "patient_name": "Youssef Tarek",
  "date": "2025-05-25",
  "time_slot": 1,
  "time": "09:00",
  "status": "confirmed",
  "notes": "",
  "doctor_notes": "",
  "paid": true
}
```

**Error Responses:**
- `404` — Appointment not found.
- `403` — Not authorized (not your appointment unless admin).

---

### `POST /api/appointments/`

Book a new appointment. **Patient or Admin.**

**Request Body:**

```json
{
  "doctor": "integer (required — doctor ID)",
  "date": "string (required — YYYY-MM-DD, must be today or future)",
  "time_slot": "number (required — slot identifier)",
  "time": "string (required — HH:MM format, the start time of the slot)",
  "notes": "string (optional — max 500 chars)"
}
```

> The frontend (`BookingModal.tsx`) also sends `patient` and `patient_name` derived from the authenticated user. The backend should derive these from the JWT token.

**Validation Rules (from frontend):**
1. A patient cannot book two appointments with the same doctor on the same day (unless previous is cancelled).
2. The chosen time slot must not already be booked by a non-cancelled appointment for that doctor on that date.
3. The date must be today or in the future.
4. The slot must fall within the doctor's defined availability blocks for the corresponding weekday.

**Success Response (201 Created):**

```json
{
  "id": 34,
  "doctor": 1,
  "doctor_name": "Ahmed Hassan",
  "specialty": "Cardiology",
  "patient": 13,
  "patient_name": "Default Patient",
  "date": "2025-06-15",
  "time_slot": 1,
  "time": "09:00",
  "status": "pending",
  "paid": false,
  "notes": "",
  "doctor_notes": ""
}
```

**Error Responses:**
- `400` — Validation error or "You already have an appointment with this doctor on this day."
- `404` — Doctor not found.

---

### `PATCH /api/appointments/{id}/`

Update appointment status or details.

**Request Body (partial):**

```json
{
  "status": "string (one of: confirmed, cancelled, completed)",
  "doctor_notes": "string (doctor's clinical notes)",
  "date": "string (YYYY-MM-DD — for rescheduling)",
  "time_slot": "number (for rescheduling)",
  "time": "string (HH:MM — for rescheduling)",
  "paid": "boolean"
}
```

**Behavior by action:**

| Action | `status` sent | Notes |
|---|---|---|
| **Confirm payment** | `confirmed` | Also sets `paid: true`. See status machine below. |
| **Cancel (patient)** | `cancelled` | Frees the time slot. |
| **Reject (doctor)** | `cancelled` | Also sends `doctor_notes` with rejection reason. |
| **Add notes (doctor)** | (no status change) | Sends `doctor_notes` only. |
| **Reschedule** | `pending` | Updates `date`, `time_slot`, `time`, resets status to `pending`. |

**Success Response (200 OK):** Returns the updated appointment.

---

### `DELETE /api/appointments/{id}/`

Hard-delete an appointment (used by admin for specialty management cleanup; frontend uses soft-delete via status).

---

## 5. Specialties

All specialty endpoints require `Authorization: Bearer <access_token>` and **Admin role**.

### `GET /api/specialties/`

List all specialties.

**Success Response (200 OK):**

```json
[
  { "id": 1, "name": "Cardiology" },
  { "id": 2, "name": "Dermatology" }
]
```

---

### `POST /api/specialties/`

Create a new specialty.

**Request Body:**

```json
{
  "name": "string (required, unique)"
}
```

**Success Response (201 Created):**

```json
{
  "id": 9,
  "name": "Radiology"
}
```

---

### `PUT /api/specialties/{id}/`

Edit a specialty name.

**Request Body:**

```json
{
  "name": "string (required, unique)"
}
```

**Success Response (200 OK):**

```json
{
  "id": 9,
  "name": "Radiology & Imaging"
}
```

---

### `DELETE /api/specialties/{id}/`

Delete a specialty.

**Success Response (200 OK):**

```json
{
  "deleted": true,
  "id": 9
}
```

---

## 6. Error Handling Conventions

### HTTP Error Codes

| Code | Meaning | Typical Use |
|---|---|---|
| `200` | Success | GET, PUT, PATCH, DELETE |
| `201` | Created | POST |
| `400` | Bad Request | Validation errors, missing fields |
| `401` | Unauthorized | Missing/expired JWT, bad credentials |
| `403` | Forbidden | Role lacks permission |
| `404` | Not Found | Resource ID does not exist |
| `409` | Conflict | Duplicate email, duplicate booking |
| `500` | Server Error | Unexpected backend failure |

### Error Response Format (standard)

```json
{
  "error": "string (human-readable message)",
  "field_errors": {
    "field_name": "string (field-specific error message)"
  }
}
```

> The frontend `useApiError.ts` hook expects `error.response.status`, `error.response.data`, and a general `.message` fallback.

---

## 7. Appointment Status Machine

```
                    ┌──────────┐
                    │  PENDING │  ← Initial state on booking
                    └────┬─────┘
                         │
              ┌──────────┼──────────┐
              │                     │
         (pay)│              (cancel)│
              ▼                     ▼
      ┌───────────┐         ┌──────────┐
      │ CONFIRMED │         │CANCELLED │
      └─────┬─────┘         └──────────┘
            │
    (visit) │
            ▼
      ┌───────────┐
      │ COMPLETED │  ← Doctor marks after visit
      └───────────┘

Additional transitions:
  - CONFIRMED → CANCELLED (patient cancels after paying)
  - PENDING   → CANCELLED (doctor rejects)
  - PENDING   → PENDING   (reschedule — date/slot change, status stays pending)
```

**Status values:** `pending` | `confirmed` | `completed` | `cancelled`

---

## 8. Data Models

### User

| Field | Type | Required | Default | Notes |
|---|---|---|---|---|
| `id` | integer (auto) | — | — | Primary key |
| `email` | string (unique) | yes | — | Validated as email |
| `password` | string (hashed) | yes | — | Min 8 chars, 1 uppercase, 1 number |
| `first_name` | string | yes | — | Min 2 chars |
| `last_name` | string | yes | — | Min 2 chars |
| `role` | enum | yes | — | `patient`, `doctor`, `admin` |
| `phone` | string | no | `""` | 11 digits |
| `avatar` | string | no | `""` | URL or base64 |
| `is_active` | boolean | no | `true` | Soft-delete flag |
| `verified` | boolean | no | `null` | Only applies to `doctor` role |
| `deleted_at` | datetime | no | `null` | Set on soft delete |

---

### Doctor Profile

| Field | Type | Required | Default | Notes |
|---|---|---|---|---|
| `id` | integer (auto) | — | — | Primary key, matches `user.id` |
| `first_name` | string | yes | — | Denormalized from User |
| `last_name` | string | yes | — | Denormalized from User |
| `specialty` | string | yes | — | Must match a `Specialty.name` |
| `bio` | text | no | `""` | Max 1000 chars |
| `contact` | string | yes | — | Email or phone |
| `session_price` | integer | no | `0` | In EGP |
| `availability` | array | no | `[]` | See AvailabilityBlock |
| `bookedSlots` | object | no | `{}` | `{ "YYYY-MM-DD": ["HH:MM", ...] }` |

---

### Availability Block

| Field | Type | Required | Notes |
|---|---|---|---|
| `id` | integer (auto) | — | Unique within doctor |
| `day` | string | yes | `Monday`–`Sunday` |
| `start_time` | string (HH:MM) | yes | 24-hour format |
| `end_time` | string (HH:MM) | yes | Must be after `start_time` |

---

### Appointment

| Field | Type | Required | Default | Notes |
|---|---|---|---|---|
| `id` | integer (auto) | — | — | Primary key |
| `doctor` | integer (FK) | yes | — | References `Doctor.id` |
| `doctor_name` | string | yes | — | Denormalized for quick display |
| `specialty` | string | yes | — | Denormalized from doctor |
| `patient` | integer (FK) | yes | — | References `User.id` |
| `patient_name` | string | yes | — | Denormalized for quick display |
| `date` | string (YYYY-MM-DD) | yes | — | Must be today or future |
| `time_slot` | integer | yes | — | Slot identifier |
| `time` | string (HH:MM) | yes | — | Start time of the slot |
| `status` | enum | yes | `pending` | See status machine above |
| `notes` | text | no | `""` | Patient's notes, max 500 chars |
| `doctor_notes` | text | no | `""` | Doctor's clinical notes |
| `paid` | boolean | no | `false` | Payment status |

---

### Specialty

| Field | Type | Required | Notes |
|---|---|---|---|
| `id` | integer (auto) | — | Primary key |
| `name` | string (unique) | yes | Specialty name |

---

## 9. Frontend Route Map

| Path | Page | Type | Available To |
|---|---|---|---|
| `/login` | LoginPage | Auth | Guests only |
| `/register` | RegisterPage | Auth | Guests only |
| `/` | HomePage | Public | Everyone |
| `/search/results` | DoctorResults | Public | Everyone |
| `/doctors/:id` | DoctorProfile | Public | Everyone |
| `/doctor/profile` | DoctorProfilePage | Authenticated | Doctor |
| `/dashboard/patient` | PatientDashboard | Authenticated | Patient |
| `/appointments/patient` | PatientAppointments | Authenticated | Patient |
| `/profile/patient` | PatientProfile | Authenticated | Patient |
| `/appointments/:id` | AppointmentDetails | Authenticated | Patient |
| `/payment/:id` | PaymentPage | Authenticated | Patient |
| `/doctor/dashboard` | DoctorDashboardPage | RoleRoute | Doctor |
| `/doctor/appointments` | DoctorAppointmentsPage | RoleRoute | Doctor |
| `/doctor/availability` | DoctorAvailabilityPage | RoleRoute | Doctor |
| `/admin/dashboard` | AdminDashboard | RoleRoute | Admin |
| `/admin/users` | AdminUsers | RoleRoute | Admin |
| `/admin/users/:id` | AdminUserDetail | RoleRoute | Admin |
| `/admin/appointments` | AdminAppointments | RoleRoute | Admin |
| `/admin/specialties` | AdminSpecialties | RoleRoute | Admin |
| `*` | Navigate to `/` | Catch-all | Everyone |

---

## 10. Auth Flows

### Login Flow
1. User submits `email` + `password` → `POST /api/auth/token/`
2. Backend validates credentials, returns `{ access, refresh, user }`
3. Frontend stores `accessToken` + `refreshToken` in `localStorage`
4. Redux store is updated with the user object
5. User is redirected based on role:
   - `patient` → `/dashboard/patient`
   - `doctor` → `/doctor/dashboard`
   - `admin` → `/admin/dashboard`

### Registration Flow
1. User submits registration form → `POST /api/auth/register/`
2. Backend creates user + (if doctor) doctor profile
3. Backend auto-authenticates the user (returns user object)
4. Frontend stores session, redirects to `/`
5. If doctor — `verified` starts as `false`, pending admin approval

### Token Refresh Flow
1. Frontend detects `401` on any API call
2. Frontend calls `POST /api/auth/token/refresh/` with the stored `refresh` token
3. If refresh succeeds, retry the original request with the new `access` token
4. If refresh fails, clear session and redirect to `/login`

### Role-Based Access
- **Patient:** Can browse doctors, book appointments, view own appointments, make payments, manage own profile
- **Doctor:** Can manage own profile, set availability, view own appointments, add clinical notes, reject appointments
- **Admin:** Full access — manage users (activate/deactivate/verify/promote), manage specialties, view all appointments

---

> *This contract was generated by analyzing all frontend service files, page components, mock data, validation schemas, Redux store, and route definitions in the Medica frontend codebase.*
