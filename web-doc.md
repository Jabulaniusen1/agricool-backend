# Agricool Backend — Next.js Integration Guide

> Base API: `Base-API/`
> Framework: Django REST Framework + SimpleJWT
> Primary language: Python

---

## Table of Contents

1. [Setup & Configuration](#1-setup--configuration)
2. [Authentication](#2-authentication)
3. [User App Endpoints](#3-user-app-endpoints)
4. [Storage App Endpoints](#4-storage-app-endpoints)
5. [Operation App Endpoints](#5-operation-app-endpoints)
6. [Prediction App Endpoints](#6-prediction-app-endpoints)
7. [Marketplace App Endpoints](#7-marketplace-app-endpoints)
8. [External Services & Webhooks](#8-external-services--webhooks)
9. [Error Handling](#9-error-handling)
10. [Implementation Guide for Next.js](#10-implementation-guide-for-nextjs)

---

## 1. Setup & Configuration

### Base URLs

| Environment | Base URL |
|-------------|----------|
| Development | `http://localhost:8000` |
| Production | Configured via `ALLOWED_HOSTS` env var |

### Route Prefixes

| Prefix | App |
|--------|-----|
| `/user/` | Auth, users, farmers, operators, companies |
| `/storage/` | Cooling units, crates, crops, sensors |
| `/operation/` | Check-ins, check-outs, movements, surveys |
| `/prediction/` | Price predictions (India & Nigeria) |
| `/marketplace/` | Buyer/seller listings, orders, payments |

### JWT Token Configuration

| Setting | Value |
|---------|-------|
| Access token lifetime | **15 minutes** |
| Refresh token lifetime | **7 days** |
| Rotate refresh tokens | `true` |
| Blacklist after rotation | `true` |
| Algorithm | `HS256` |
| Header format | `Authorization: Bearer <token>` |

### CORS

- Development: All origins allowed (`CORS_ORIGIN_ALLOW_ALL: True`)
- Production: Whitelist-based (`CORS_ORIGIN_WHITELIST`)

### File Uploads

- Max file size: **10 MB**
- Media served at `/media/`

### reCAPTCHA

Required on: Login, Registration, Password Reset, Invitations
Frontend must obtain a reCAPTCHA token from Google and include it in the request body as `recaptcha_token`.
Disabled in development (`RECAPTCHA_ENABLED=False`).

---

## 2. Authentication

### User Types

| `user_type` | Role |
|-------------|------|
| `"f"` | Farmer |
| `"op"` | Operator |
| `"sp"` | Service Provider |

---

### `POST /user/token/obtain/` — Login

**Auth:** Public

**Request:**
```json
{
  "username": "string",
  "password": "string",
  "user_type": "f | op | sp",
  "language": "string (optional)"
}
```

**Response (Farmer):**
```json
{
  "refresh": "string",
  "access": "string",
  "role": "Farmer",
  "user": {
    "id": 1,
    "first_name": "string",
    "last_name": "string",
    "gender": "string",
    "phone": "string",
    "last_login": "2024-01-01T00:00:00Z"
  },
  "parent_name": "string"
}
```

**Response (Operator / Service Provider):**
```json
{
  "refresh": "string",
  "access": "string",
  "role": "Operator | Service Provider",
  "user": {
    "id": 1,
    "first_name": "string",
    "last_name": "string",
    "email": "string",
    "gender": "string",
    "phone": "string",
    "last_login": "2024-01-01T00:00:00Z"
  },
  "company": { "...CompanyObject" }
}
```

> **Note:** `username` is phone number for Farmers & Operators; email for Service Providers.

---

### `POST /user/token/refresh/` — Refresh Token

**Auth:** Public

**Request:**
```json
{ "refresh": "string" }
```

**Response:**
```json
{ "access": "string" }
```

---

### `POST /user/v1/login/` — Login (Alias)

Same as `/user/token/obtain/`.

---

### `POST /user/v1/logout/` — Logout

**Auth:** Required

**Request:**
```json
{ "refresh": "string" }
```

**Response:** `205 Reset Content`
```json
{ "message": "Successfully logged out" }
```

> Blacklists the refresh token. Always call this on user sign-out.

---

## 3. User App Endpoints

### Users

#### `GET /user/v1/users/` — List Users
**Auth:** Required

**Response:**
```json
[
  {
    "id": 1,
    "username": "string",
    "phone": "string",
    "email": "string",
    "gender": "string",
    "first_name": "string",
    "last_name": "string",
    "last_login": "datetime",
    "language": "string",
    "is_email_public": true,
    "is_phone_public": true
  }
]
```

> Phone/email visibility is controlled by `is_email_public` / `is_phone_public` and company membership.

---

#### `GET /user/v1/users/{user_id}/` — Retrieve User
**Auth:** Required
**Response:** Single user object (same shape as list).

---

#### `PATCH /user/v1/users/{user_id}/` — Update User
**Auth:** Required

**Request (partial):**
```json
{
  "phone": "string",
  "email": "string",
  "gender": "string",
  "first_name": "string",
  "last_name": "string",
  "language": "string",
  "is_email_public": true,
  "is_phone_public": true
}
```

---

#### `DELETE /user/v1/users/{user_id}/` — Deactivate Account
**Auth:** Required (own account only)

**Response:**
```json
{ "success": "Successfully deleted user" }
```

> Marks the user as **inactive** — not a hard delete.

---

#### `DELETE /user/v1/users/{farmer_user_id}/operator-proxy-delete/` — Operator Deletes Farmer
**Auth:** Required (Operator only)

**Error responses:**
- `403` — Requesting user is not an Operator
- `400` — Target is not a farmer
- `403` — Farmer does not belong to operator's company
- `400` — Cannot delete smartphone users

---

### Farmers

#### `GET /user/v1/farmers/` — List Farmers
**Auth:** Public

**Query params:**
| Param | Type | Description |
|-------|------|-------------|
| `user_id` | integer | Filter by user |
| `operator` | integer | Filter by operator's company |

**Response:**
```json
[
  {
    "id": 1,
    "user": { "...UserObject" },
    "parent_name": "string",
    "phone": "string",
    "user_code": "string | null",
    "smartphone": true,
    "companies": [1, 2],
    "profile_image_url": "string | null"
  }
]
```

---

#### `POST /user/v1/farmers/` — Create Farmer
**Auth:** Public (reCAPTCHA required if `create_user: true`)

**Request:**
```json
{
  "user": {
    "phone": "string",
    "first_name": "string",
    "last_name": "string",
    "password": "string (min 8 chars)",
    "gender": "string",
    "email": "string (optional)"
  },
  "parent_name": "string",
  "companies": [1],
  "create_user": true,
  "user_code": "string (optional)"
}
```

---

#### `GET /user/v1/farmers/{farmer_id}/` — Retrieve Farmer
**Auth:** Public

---

#### `PATCH /user/v1/farmers/{farmer_id}/` — Update Farmer
**Auth:** Required

---

#### `GET /user/v1/farmers/by-code/?user_code={code}` — Get Farmer by Code
**Auth:** Required (Operator only)

**Response:** Farmer object with limited user data.

---

### Operators

#### `GET /user/v1/operators/` — List Operators
**Auth:** Public

**Response:**
```json
[
  {
    "id": 1,
    "user": { "...UserObject" },
    "company": 1
  }
]
```

#### `GET /user/v1/operators/{id}/` — Retrieve Operator
**Auth:** Public

---

### Service Providers

#### `GET /user/v1/service-providers/` — List
**Auth:** Public

#### `POST /user/v1/service-providers/` — Create
**Auth:** Required

**Request:**
```json
{
  "user": {
    "phone": "string",
    "email": "string",
    "first_name": "string",
    "last_name": "string",
    "password": "string (min 8 chars)"
  },
  "company": 1
}
```

#### `GET /user/v1/service-providers/{id}/` — Retrieve
**Auth:** Public

---

### Companies

#### `PATCH /user/v1/companies/{company_id}/` — Update Company
**Auth:** Required

**Request (partial):**
```json
{
  "name": "string",
  "address": "string",
  "phone": "string",
  "email": "string"
}
```

---

### Registration

#### `POST /user/v1/service-provider-signup/` — Service Provider Signup
**Auth:** Public (reCAPTCHA required)

**Request:**
```json
{
  "phone": "string",
  "email": "string",
  "first_name": "string",
  "last_name": "string",
  "password": "string (min 8 chars)",
  "company": 1
}
```

---

#### `POST /user/v1/operator-invite-signup/` — Operator Registration via Invitation
**Auth:** Public (reCAPTCHA required)

**Request:**
```json
{
  "invitation_code": "string",
  "password": "string (min 8 chars)",
  "first_name": "string",
  "last_name": "string"
}
```

---

#### `POST /user/v1/service-provider-invite-signup/` — Service Provider Registration via Invitation
**Auth:** Public (reCAPTCHA required)

**Request:**
```json
{
  "invitation_code": "string",
  "password": "string (min 8 chars)",
  "first_name": "string",
  "last_name": "string",
  "email": "string"
}
```

---

### Invitations

#### `POST /user/v1/operator-invite/` — Send Operator Invitation
**Auth:** Required | Permission: `user.add_invitation_operator`

**Request:**
```json
{
  "user_id": 1,
  "phone": "string",
  "expiration_date": "datetime (optional)"
}
```

**Response:**
```json
{
  "code": "string",
  "phone": "string",
  "expiration_date": "datetime",
  "user_type": 2
}
```

> Frontend signup link format: `/auth/signup-invitation/?user-type=2&invitation-code={code}&phoneNumber={phone}`

---

#### `POST /user/v1/service-provider-invite/` — Send Service Provider Invitation
**Auth:** Required | Permission: `user.add_invitation_serviceprovider`

Same shape as operator invite but `user_type: 1`.

> Frontend signup link format: `/auth/signup-invitation/?user-type=1&invitation-code={code}&phoneNumber={phone}`

---

#### `GET /user/v1/service-provider-invite/` — List Invitations
**Auth:** Required

**Query params:** `company` (integer, optional)

---

#### `GET /user/v1/service-provider-invite/{code}/` — Retrieve Invitation
**Auth:** Required

---

### Password Reset

#### `POST /user/v1/reset-password/` — Request Reset
**Auth:** Public (reCAPTCHA required)

**Request:**
```json
{ "phoneNumber": "string" }
```

> Sends SMS & email with reset link. Rate limited to **once every 2 hours** per phone number. Code expires in **6 hours**.

Frontend reset link format: `/auth/reset/?resetcode={code}&phoneNumber={phone}`

---

#### `POST /user/v1/reset-password/` — Complete Reset
**Auth:** Public

**Request:**
```json
{
  "phone": "string",
  "password": "string (min 8 chars)",
  "code": "string"
}
```

**Response:**
```json
{ "success": "Password reset successfully" }
```

---

### Notifications

#### `POST /user/v1/notification/` — Create Notification
**Auth:** Required

**Request:**
```json
{
  "user": 1,
  "title": "string",
  "message": "string",
  "type": "ALERT | INFO | WARNING"
}
```

#### `PATCH /user/v1/notification/{id}/` — Update Notification
**Auth:** Required

**Request (partial):**
```json
{
  "read": true,
  "message": "string"
}
```

---

### Farmer Survey

#### `POST /user/v1/farmer-survey/` — Create Survey
**Auth:** Required

**Request:**
```json
{
  "farmer": 1,
  "farm_size": 10.5,
  "crops_grown": "string",
  "irrigation_method": "string",
  "annual_production": 100.0
}
```

#### `PATCH /user/v1/farmer-survey/{id}/` — Update Survey
**Auth:** Required

---

## 4. Storage App Endpoints

### Crops

#### `GET /storage/v1/crops/` — List Crops
**Auth:** Required

**Response:**
```json
[
  {
    "id": 1,
    "name": "string",
    "crop_type": 1,
    "description": "string"
  }
]
```

#### `POST /storage/v1/crops/` — Create Crop
#### `PATCH /storage/v1/crops/{id}/` — Update Crop

---

### Crop Types

#### `GET /storage/v1/crop-types/` — List Crop Types
**Auth:** Required

**Response:**
```json
[{ "id": 1, "name": "string", "description": "string" }]
```

---

### Locations

#### `GET /storage/v1/locations/` — List Locations
**Auth:** Required

**Response:**
```json
[
  {
    "id": 1,
    "name": "string",
    "latitude": 0.0,
    "longitude": 0.0,
    "company": 1,
    "address": "string"
  }
]
```

#### `POST /storage/v1/locations/` — Create Location
**Auth:** Required

---

### Cooling Units

#### `GET /storage/v1/cooling-units/` — List Cooling Units
**Auth:** Required

**Query params:**
| Param | Type | Description |
|-------|------|-------------|
| `not_empty` | boolean | Only non-empty units |
| `is_farmer` | boolean | Farmer's units |
| `user` | integer | Farmer user ID |
| `company` | integer | Company ID |

**Response:**
```json
[
  {
    "id": 1,
    "name": "string",
    "location": 1,
    "metric": "string",
    "sensor": 1,
    "sensor_list": [],
    "capacity_in_metric_tons": 5.0,
    "capacity_in_number_crates": 100,
    "occupancy": 0.5,
    "occupancy_modified_date": "datetime",
    "cooling_unit_type": "string",
    "crops": [],
    "room_height": 3.0,
    "room_length": 10.0,
    "room_width": 8.0,
    "operators": [1],
    "latest_temperature": 4.5,
    "latest_temperature_timestamp": "datetime",
    "crate_weight": 25.0,
    "crate_width": 0.4,
    "crate_length": 0.6,
    "crate_height": 0.3,
    "commodity_infos": [],
    "food_capacity_in_metric_tons": 4.5,
    "public": false,
    "common_pricing_type": "string",
    "sensor_error": false,
    "last_checkin_date": "datetime",
    "can_delete": true,
    "commodity_total": 10,
    "power_options": []
  }
]
```

#### `POST /storage/v1/cooling-units/` — Create Cooling Unit
**Auth:** Required

**Request:**
```json
{
  "name": "string",
  "location": 1,
  "metric": "string",
  "capacity_in_metric_tons": 5.0,
  "capacity_in_number_crates": 100,
  "cooling_unit_type": "string",
  "room_height": 3.0,
  "room_length": 10.0,
  "room_width": 8.0,
  "crate_weight": 25.0,
  "crate_width": 0.4,
  "crate_length": 0.6,
  "crate_height": 0.3,
  "sensor": 1,
  "operators": [1],
  "public": false
}
```

#### `GET /storage/v1/cooling-units/{id}/` — Retrieve
#### `PATCH /storage/v1/cooling-units/{id}/` — Update

#### `DELETE /storage/v1/cooling-units/{id}/` — Delete
**Constraints:** Unit must have no active check-ins.

**Error:**
```json
{ "detail": "This cooling unit cannot be deleted because it has active check-ins" }
```

---

### Crates

#### `GET /storage/v1/crates/` — List Crates
**Auth:** Required

**Query params:** `produce`, `cooling_unit`, `weight_gt`

**Response:**
```json
[
  {
    "id": 1,
    "produce": 1,
    "cooling_unit": 1,
    "weight": 25.0,
    "width": 0.4,
    "length": 0.6,
    "height": 0.3,
    "quantity": 5,
    "date_creation": "datetime"
  }
]
```

#### `POST /storage/v1/crates/` — Create Crate
**Auth:** Required

---

### Produce

#### `GET /storage/v1/produces/` — List Produce
**Auth:** Required

**Response:**
```json
[
  {
    "id": 1,
    "crop": 1,
    "quantity": 100.0,
    "unit": "kg",
    "harvest_date": "datetime",
    "description": "string"
  }
]
```

#### `POST /storage/v1/produces/` — Create Produce
**Auth:** Required

---

### Cooling Unit Crops

#### `POST /storage/v1/cooling-unit-crops/` — Associate Crop with Unit
**Auth:** Required

**Request:**
```json
{
  "cooling_unit": 1,
  "crop": 1,
  "optimal_temperature": 4.0
}
```

---

### Cooling Unit Specifications

#### `GET /storage/v1/cooling-unit-specifications/` — List Specs
**Auth:** Required

**Query params:** `cooling_unit`, `specification_type`

**Response:**
```json
[
  {
    "id": 1,
    "cooling_unit": 1,
    "specification_type": "TEMPERATURE | HUMIDITY",
    "value": 4.0,
    "datetime_stamp": "datetime"
  }
]
```

#### `POST /storage/v1/cooling-unit-specifications/` — Create Spec
**Auth:** Required

---

### Cooling Unit Capacity

#### `GET /storage/v1/cooling-unit-capacity/` — List Capacities
**Auth:** Required

**Response:**
```json
[
  {
    "id": 1,
    "cooling_unit": 1,
    "total_capacity": 5.0,
    "current_occupancy": 2.5,
    "last_updated": "datetime"
  }
]
```

---

### Cooling Unit Temperature

#### `GET /storage/v1/cooling-unit-temperatures/` — Temperature History
**Auth:** Required

**Query params:** `cooling_unit`, `date_from`, `date_to`

---

### Sensors

#### `GET /storage/v1/user-sensor/` — List User Sensors
**Auth:** Required | **Query param:** `user`

#### `POST /storage/v1/user-sensor/` — Link Sensor to User
**Auth:** Required

**Request:**
```json
{
  "user": 1,
  "sensor": 1,
  "cooling_unit": 1
}
```

#### `GET /storage/v1/ecozen/` — List Ecozen Sensors
**Auth:** Required

#### `POST /storage/v1/ecozen/` — Create Ecozen Sensor
**Auth:** Required

**Request:**
```json
{
  "cooling_unit": 1,
  "model": "string",
  "serial_number": "string"
}
```

---

### COMSOL Callback (Internal)

#### `POST /storage/v1/comsol/` — COMSOL Webhook
**Auth:** Required (internal service)

> Called by the COMSOL Digital Twins service only. Not for frontend use.

---

### Mobile App Version

#### `GET /storage/version-code/` — Minimum App Version
**Auth:** Public

**Response:**
```json
{
  "ios_minimum_version": "string",
  "android_minimum_version": "string",
  "current_version": "string"
}
```

---

## 5. Operation App Endpoints

### Check-ins

#### `POST /operation/checkins/` — Create Check-in
**Auth:** Public

**Request:**
```json
{
  "farmer_id": 1,
  "owned_by_user_id": 1,
  "owned_on_behalf_of_company_id": 1,
  "produces": [
    {
      "crates": [
        {
          "cooling_unit_id": 1,
          "produce_id": 1,
          "weight": 25.0,
          "quantity": 5
        }
      ]
    }
  ]
}
```

**Response:**
```json
{
  "id": 1,
  "movement": 1,
  "owned_by_user": 1,
  "owned_on_behalf_of_company": 1,
  "farmer": 1,
  "date_creation": "datetime",
  "produces": [],
  "crates": []
}
```

> Either `farmer_id` or `owned_by_user_id` is required.

#### `GET /operation/checkins/` — List Check-ins
**Auth:** Public

**Query params:** `movement_id`, `code`

#### `GET /operation/checkins/{id}/` — Retrieve Check-in
**Auth:** Public

---

### Check-outs

#### `POST /operation/checkouts/` — Create Check-out
**Auth:** Public

**Request:**
```json
{
  "movement": 1,
  "crates": [
    {
      "crate_id": 1,
      "weight": 25.0,
      "quantity": 3
    }
  ]
}
```

**Response:**
```json
{
  "id": 1,
  "movement": 1,
  "movement_id": 1,
  "date_creation": "datetime",
  "crates": []
}
```

#### `GET /operation/checkouts/` — List Check-outs
**Auth:** Public | **Query param:** `code`

---

#### `POST /operation/checkouts/{movement_id}/send_sms_report/` — Send SMS Report
**Auth:** Required

**Response:** `{ "status": 200 }`

> Triggers an async Celery task to send the SMS. Delivery may be slightly delayed.

---

### Movements

#### `GET /operation/movements/` — List Movements
**Auth:** Required

**Query params:**
| Param | Type | Description |
|-------|------|-------------|
| `operator` | integer | Filter by operator |
| `initiated_for` | string | `CHECK_IN` or `CHECK_OUT` |
| `date_from` | date | Start date |
| `date_to` | date | End date |

**Response:**
```json
[
  {
    "id": 1,
    "code": "string",
    "date": "date",
    "operator": 1,
    "initiated_for": "CHECK_IN | CHECK_OUT",
    "checkin": 1,
    "checkout": null
  }
]
```

---

### Checkout → Check-in Movement

#### `POST /operation/move-checkout/` — Move Produce Between Units
**Auth:** Required

**Request:**
```json
{
  "checkout_id": 1,
  "cooling_unit_id": 2,
  "crates": [
    {
      "crate_id": 1,
      "weight": 25.0,
      "quantity": 3
    }
  ]
}
```

**Response:**
```json
{
  "id": 1,
  "checkout": 1,
  "checkin": 2,
  "movement": 1,
  "date_creation": "datetime"
}
```

---

### Market Surveys

#### `POST /operation/market-survey/` — Create Survey
**Auth:** Required

**Request:**
```json
{
  "movement": 1,
  "location": "string",
  "market_price": 500.0,
  "commodity": "string",
  "unit": "kg",
  "date_surveyed": "datetime"
}
```

#### `GET /operation/market-survey/` — List Surveys
**Auth:** Required | **Query params:** `movement`, `commodity`

---

## 6. Prediction App Endpoints

### States

#### `GET /prediction/states/` — List States (India)
**Auth:** Required

**Response:**
```json
[{ "id": 1, "name": "string", "code": "string" }]
```

#### `GET /prediction/statesng/` — List States (Nigeria)
**Auth:** Required

---

### Markets

#### `GET /prediction/markets/` — List Markets
**Auth:** Required

**Query params:** `state` (integer), `country` (`IN` | `NG`)

**Response:**
```json
[
  {
    "id": 1,
    "name": "string",
    "state": 1,
    "latitude": 0.0,
    "longitude": 0.0
  }
]
```

---

### Price Predictions

#### `POST /prediction/predictions/get_data_graph` — Graph Data (India)
**Auth:** Required

**Request:**
```json
{
  "marketId": 1,
  "cropId": 1
}
```

**Response:**
```json
{
  "past_values": [
    { "date": "2024-01-01", "price": 450.0 }
  ],
  "forecast_values": [
    { "date": "2024-01-15", "price": 480.0, "interpolated": false }
  ]
}
```

> Past values: last **28 days**. Forecast: next **14 days**.

#### `POST /prediction/predictions/get_data_table` — Table Data (India)
**Auth:** Required | Same request body as graph.

#### `POST /prediction/predictions/get_data_graph_ng` — Graph Data (Nigeria)
**Auth:** Required

#### `POST /prediction/predictions/get_data_table_ng` — Table Data (Nigeria)
**Auth:** Required

---

## 7. Marketplace App Endpoints

> **Important:** Marketplace is currently only active in **Nigeria (NG)**.

### Public Listings (Buyer)

#### `GET /marketplace/buyer/available-listings/` — Browse Listings
**Auth:** Public

**Query params:**
| Param | Type | Description |
|-------|------|-------------|
| `latitude` | float | Buyer's latitude |
| `longitude` | float | Buyer's longitude |
| `cooling_unit_ids` | string | Comma-separated IDs |
| `max_distance_km` | float | Distance filter |
| `sort_by` | string | `price-asc`, `price-desc`, `distance` |
| `page` | integer | Default: 1 |
| `page_size` | integer | Default: 20 |

**Response:**
```json
{
  "count": 100,
  "next": "string | null",
  "previous": "string | null",
  "results": [
    {
      "id": 1,
      "crate_id": 1,
      "crate": {},
      "price_per_unit": 500.0,
      "available_weight_in_kg": 200.0,
      "distance_km": 5.2,
      "seller": {},
      "location": {}
    }
  ]
}
```

#### `GET /marketplace/buyer/available-listings/{id}/` — Retrieve Listing
**Auth:** Public

---

### Buyer Cart

#### `GET /marketplace/buyer/cart/` — Get Cart
**Auth:** Required

**Response:**
```json
{
  "id": 1,
  "user": 1,
  "items_count": 2,
  "subtotal": 1000.0,
  "discount_amount": 50.0,
  "coupon_applied": {},
  "total_amount": 950.0,
  "items": [
    {
      "id": 1,
      "listing_id": 1,
      "quantity": 10.0,
      "price_per_unit": 50.0,
      "total": 500.0
    }
  ]
}
```

#### `POST /marketplace/buyer/cart/items/` — Add Item to Cart
**Auth:** Required

**Request:**
```json
{
  "listing_id": 1,
  "quantity": 10.0
}
```

**Response:** `201 Created` — Updated cart object.

#### `PATCH /marketplace/buyer/cart/items/{item_id}/` — Update Cart Item
**Auth:** Required

**Request:**
```json
{ "quantity": 15.0 }
```

#### `DELETE /marketplace/buyer/cart/items/{item_id}/` — Remove Item
**Auth:** Required

#### `POST /marketplace/buyer/cart/` — Apply / Clear Coupon
**Auth:** Required

**Request:**
```json
{
  "coupon_code": "SAVE10",
  "action": "apply | clear"
}
```

---

### Buyer Orders

#### `GET /marketplace/buyer/orders/` — List Orders
**Auth:** Required | **Query param:** `status`

**Response:**
```json
[
  {
    "id": 1,
    "order_id": "string",
    "seller": {},
    "items": [],
    "subtotal": 950.0,
    "discount": 50.0,
    "total_amount": 900.0,
    "status": "PENDING | CONFIRMED | SHIPPED | DELIVERED | CANCELLED",
    "payment_status": "string",
    "date_created": "datetime",
    "delivery_details": {}
  }
]
```

#### `GET /marketplace/buyer/orders/{order_id}/` — Retrieve Order
**Auth:** Required

#### `POST /marketplace/buyer/orders/` — Place Order
**Auth:** Required

**Request:**
```json
{
  "delivery_contact_id": 1,
  "pickup_method": "PICK_UP_SAME_DAY | DELIVERY"
}
```

**Response:** `201 Created`
```json
{
  "order_id": "string",
  "order": {},
  "checkout_url": "https://paystack.com/pay/..."
}
```

> Redirect the user to `checkout_url` to complete payment via Paystack.

#### `POST /marketplace/buyer/orders/{order_id}/set-pickup-details/` — Set Pickup Details
**Auth:** Required

**Request:**
```json
{
  "pickup_method": "DELIVERY",
  "delivery_contact_id": 1,
  "pickup_date": "2024-02-01",
  "pickup_time": "10:00",
  "special_instructions": "string (optional)"
}
```

---

### Seller Listings

#### `GET /marketplace/seller/listed-crates/` — List My Listings
**Auth:** Required

**Query params:**
| Param | Description |
|-------|-------------|
| `operator_on_behalf_of_seller_user_id` | integer |
| `operator_on_behalf_of_seller_company_id` | integer |
| `operator_on_behalf_of_seller_farmer_id` | integer |

**Response:**
```json
[
  {
    "id": 1,
    "crate_id": 1,
    "crate": {},
    "price_per_unit": 500.0,
    "cmp_available_weight_in_kg": 200.0,
    "is_listed": true,
    "date_listed": "datetime",
    "cooling_unit_location": {}
  }
]
```

#### `GET /marketplace/seller/listed-crates/{crate_id}/` — Retrieve Listing
#### `POST /marketplace/seller/listed-crates/` — Create Listing
#### `PATCH /marketplace/seller/listed-crates/{crate_id}/` — Update Listing

**Request:**
```json
{
  "crate_id": 1,
  "price_per_unit": 500.0,
  "available_weight_in_kg": 200.0,
  "operator_on_behalf_of_seller_user_id": 1,
  "operator_on_behalf_of_seller_company_id": 1
}
```

#### `DELETE /marketplace/seller/listed-crates/{crate_id}/` — Remove Listing

---

### Seller Coupons

#### `GET /marketplace/seller/coupons/` — List Coupons
**Auth:** Required

#### `POST /marketplace/seller/coupons/` — Create Coupon
**Auth:** Required

**Request:**
```json
{
  "code": "SAVE10",
  "discount_percentage": 10.0,
  "discount_amount": null,
  "valid_from": "datetime",
  "valid_until": "datetime",
  "max_usage": 100
}
```

---

### Seller Payment Accounts

#### `GET /marketplace/seller/paystack-accounts/` — List Accounts
**Auth:** Required

#### `POST /marketplace/seller/paystack-accounts/` — Add Paystack Account
**Auth:** Required

**Request:**
```json
{
  "account_number": "string",
  "bank_code": "string"
}
```

> Account is validated with Paystack before saving.

---

### Seller Orders

#### `GET /marketplace/seller/orders/` — List Orders
**Auth:** Required | **Query params:** `status`, `operator_on_behalf_of_seller_user_id`, etc.

---

### Company Marketplace

#### `GET /marketplace/company/orders/` — Company Orders
**Auth:** Required | **Query param:** `company_id`

#### `GET /marketplace/company/delivery-contacts/` — List Delivery Contacts
**Auth:** Required

#### `POST /marketplace/company/delivery-contacts/` — Create Delivery Contact
**Auth:** Required

**Request:**
```json
{
  "company": 1,
  "name": "string",
  "phone": "string",
  "email": "string",
  "address": "string",
  "latitude": 0.0,
  "longitude": 0.0,
  "is_default": false
}
```

#### `GET|POST /marketplace/company/setup/` — Marketplace Setup
**Auth:** Required

**POST Request:**
```json
{
  "company": 1,
  "is_seller_enabled": true,
  "is_buyer_enabled": true,
  "paystack_account": 1
}
```

---

### Marketplace Master Data

#### `GET /marketplace/data/` — Reference Data
**Auth:** Public

**Response:**
```json
{
  "countries": [],
  "states": [],
  "crops": [],
  "cooling_units": [],
  "markets": [],
  "bank_codes": []
}
```

---

## 8. External Services & Webhooks

### Paystack Payment Webhook

#### `POST /marketplace/webhooks/paystack/`
**Auth:** Public (verified via `X-Paystack-Signature` header)

> **Do not call this endpoint from the frontend.** It is exclusively for Paystack to notify the backend of payment events.

**Events handled internally:**
- `charge.success` → Order confirmed, seller payout queued
- `charge.failed` → Order payment failed
- `transfer.success` → Payout to seller completed
- `transfer.failed` → Payout failed, retry logic triggered

**Marketplace commission rate:** 3.5%

---

## 9. Error Handling

All error responses follow DRF conventions:

```json
{
  "detail": "Human-readable error message"
}
```

Or for field-level validation:
```json
{
  "field_name": ["Error message"]
}
```

### Common HTTP Status Codes

| Code | Meaning |
|------|---------|
| `200` | OK |
| `201` | Created |
| `205` | Reset Content (Logout) |
| `400` | Bad Request — validation error |
| `401` | Unauthorized — missing or invalid token |
| `403` | Forbidden — insufficient permissions |
| `404` | Not Found |
| `500` | Server error |

---

## 10. Implementation Guide for Next.js

### API Client Setup

```ts
// lib/api.ts
const BASE_URL = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000';

export async function apiFetch(
  path: string,
  options: RequestInit & { auth?: boolean } = {}
) {
  const { auth = true, ...fetchOptions } = options;

  const headers: HeadersInit = {
    'Content-Type': 'application/json',
    ...fetchOptions.headers,
  };

  if (auth) {
    const token = getAccessToken(); // your token storage helper
    if (token) {
      (headers as Record<string, string>)['Authorization'] = `Bearer ${token}`;
    }
  }

  const res = await fetch(`${BASE_URL}${path}`, { ...fetchOptions, headers });

  if (res.status === 401) {
    // Token expired — attempt refresh
    const refreshed = await refreshAccessToken();
    if (refreshed) return apiFetch(path, options); // retry once
    signOut(); // redirect to login
  }

  return res;
}
```

---

### Auth Token Storage

Store tokens in `httpOnly` cookies (safest) or `localStorage` (simpler, less secure).

```ts
// lib/tokens.ts
export const getAccessToken = () =>
  typeof window !== 'undefined' ? localStorage.getItem('access_token') : null;

export const setTokens = (access: string, refresh: string) => {
  localStorage.setItem('access_token', access);
  localStorage.setItem('refresh_token', refresh);
};

export const clearTokens = () => {
  localStorage.removeItem('access_token');
  localStorage.removeItem('refresh_token');
};

export const refreshAccessToken = async (): Promise<boolean> => {
  const refresh = localStorage.getItem('refresh_token');
  if (!refresh) return false;

  const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/user/token/refresh/`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ refresh }),
  });

  if (!res.ok) {
    clearTokens();
    return false;
  }

  const { access } = await res.json();
  localStorage.setItem('access_token', access);
  return true;
};
```

---

### Login Flow

```ts
// actions/auth.ts
export async function login(username: string, password: string, userType: 'f' | 'op' | 'sp') {
  const res = await apiFetch('/user/token/obtain/', {
    method: 'POST',
    auth: false,
    body: JSON.stringify({ username, password, user_type: userType }),
  });

  if (!res.ok) throw new Error('Login failed');

  const data = await res.json();
  setTokens(data.access, data.refresh);
  return data; // { access, refresh, role, user, company? }
}
```

---

### Logout Flow

```ts
export async function logout() {
  const refresh = localStorage.getItem('refresh_token');
  await apiFetch('/user/v1/logout/', {
    method: 'POST',
    body: JSON.stringify({ refresh }),
  });
  clearTokens();
}
```

---

### reCAPTCHA Integration

Install: `npm install react-google-recaptcha-v3`

```tsx
// In your login/register forms
import { useGoogleReCaptcha } from 'react-google-recaptcha-v3';

const { executeRecaptcha } = useGoogleReCaptcha();

const handleSubmit = async () => {
  const recaptchaToken = await executeRecaptcha('login');
  await apiFetch('/user/token/obtain/', {
    method: 'POST',
    auth: false,
    body: JSON.stringify({ ...formData, recaptcha_token: recaptchaToken }),
  });
};
```

> Wrap your app with `<GoogleReCaptchaProvider reCaptchaKey={process.env.NEXT_PUBLIC_RECAPTCHA_SITE_KEY}>`.

---

### Paginated Requests (Marketplace)

```ts
export async function fetchListings(page = 1, lat: number, lng: number) {
  const params = new URLSearchParams({
    page: String(page),
    page_size: '20',
    latitude: String(lat),
    longitude: String(lng),
  });

  const res = await apiFetch(`/marketplace/buyer/available-listings/?${params}`, { auth: false });
  return res.json();
  // { count, next, previous, results: [...] }
}
```

---

### Marketplace Checkout Flow

```
1. User browses listings       GET /marketplace/buyer/available-listings/
2. Add items to cart           POST /marketplace/buyer/cart/items/
3. (Optional) Apply coupon     POST /marketplace/buyer/cart/
4. Add delivery contact        POST /marketplace/company/delivery-contacts/
5. Place order                 POST /marketplace/buyer/orders/
   → Returns checkout_url
6. Redirect user to Paystack   window.location.href = checkout_url
7. Paystack calls webhook      POST /marketplace/webhooks/paystack/
   → Order status updates automatically
8. Poll/redirect back to app   GET /marketplace/buyer/orders/{order_id}/
```

---

### Environment Variables (`.env.local`)

```bash
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_RECAPTCHA_SITE_KEY=your_recaptcha_site_key
```

---

### Datetime Format

All datetime fields use **ISO 8601 with timezone**:
```
2024-01-15T10:30:00Z
```

Parse with `new Date(value)` or `date-fns`/`dayjs`.

---

### Important Notes

1. **Token expiry** — Access token expires in 15 minutes. Implement silent refresh automatically on `401` responses.
2. **reCAPTCHA** — Disabled in development (`RECAPTCHA_ENABLED=False`). Test without it locally; add before deploying.
3. **Rate limiting** — Password reset is limited to once every 2 hours per phone number.
4. **SMS/Email delivery** — Async via Celery. Do not wait for immediate delivery; show a "check your phone" message.
5. **Marketplace country** — Currently only active for Nigeria (`NG`). Filter by country code where applicable.
6. **Paystack redirect** — After creating an order, redirect the user to the returned `checkout_url`. Do not implement payment UI yourself.
7. **File uploads** — Max 10 MB per file. Use `multipart/form-data` content type; do not send `Content-Type: application/json` for file requests.
8. **Geospatial** — Latitude/longitude are stored using PostGIS. Always send numeric float values, not strings.
9. **Pagination** — Only marketplace listings are paginated by default (page size: 20). All other list endpoints return full arrays.
10. **User visibility** — Phone and email on user profiles are conditionally hidden based on `is_phone_public` / `is_email_public` flags and company membership. Handle `null` values gracefully.
