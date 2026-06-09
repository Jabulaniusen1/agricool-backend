# Base-API Service Endpoints & Integration Guide

The **Base-API** is a Django-based service providing the backend core of the Agricool/Coldtivate platform. It handles authentication, role-based access control, check-ins/check-outs, cold storage inventory telemetry, marketplace operations (cart, listings, paystack payments), and machine learning predictions.

---

## 1. Local Setup & Running Instructions

### Requirements
- Docker and Docker Compose
- Valkey/Redis instance running on port `6379`
- PostgreSQL/PostGIS database on port `5432`
- Python 3.8+ (if running bare-metal via `pipenv`)

### Database Initialization & Migration
Before running the Django service, ensure your PostgreSQL database is updated:
```bash
# Run migrations inside the docker container
docker compose exec web pipenv run python manage.py migrate

# Seed initial crops, crop types, and states
docker compose exec web pipenv run python manage.py loaddata initial_fixtures.json
```

---

## 2. Authentication & JWT Tokens

Agricool uses **SimpleJWT** for role-based authentication.

### Flow Sequence
1. The client sends a `POST /v1/login/` containing the phone number, password, and `user_type`.
2. The endpoint responds with an `access` and a `refresh` token, along with the user role and company metadata.
3. For subsequent authenticated calls, include the access token in headers: `Authorization: Bearer <access_token>`.
4. When the access token expires (15-minute lifetime), the client hits `POST /token/refresh/` using the refresh token (7-day lifetime) to obtain a new access token.

---

## 3. App-by-App API Endpoint Details

---

### Category 3.1: User App (`/user/`)

Handles service providers, operators, farmers, invitations, password resets, and user notifications.

#### 1. User Login
- **URL**: `/user/v1/login/`
- **Method**: `POST`
- **Headers**:
  - `Content-Type: application/json`
- **Request Body**:
  ```json
  {
    "username": "+2348000000000",
    "password": "mysecretpassword",
    "user_type": "op",
    "language": "en"
  }
  ```
  *(Note: `user_type` options are `"sp"` for Service Provider, `"op"` for Operator, or `"f"` for Farmer).*
- **Response (200 OK)**:
  ```json
  {
    "refresh": "eyJ0eXAi...",
    "access": "eyJ0eXAi...",
    "user": {
      "id": 10,
      "first_name": "John",
      "last_name": "Doe",
      "gender": "M",
      "phone": "+2348000000000",
      "last_login": "2026-06-09T12:00:00Z"
    },
    "role": "Operator",
    "company": {
      "id": 1,
      "name": "Coop Cold Storage"
    }
  }
  ```

#### 2. Get/List/Update Users
- **URLs**: 
  - `GET /user/v1/users/` (List all users)
  - `GET /user/v1/users/<id>/` (Retrieve user)
  - `PATCH /user/v1/users/<id>/` (Update user)
- **Method**: `GET` / `PATCH`
- **Headers**: `Authorization: Bearer <access_token>`
- **Response (200 OK - Retrieve)**:
  ```json
  {
    "id": 10,
    "first_name": "John",
    "last_name": "Doe",
    "phone": "+2348000000000",
    "email": "john.doe@example.com",
    "language": "en"
  }
  ```

#### 3. Delete/Deactivate User Account
- **URL**: `/user/v1/users/<id>/`
- **Method**: `DELETE`
- **Headers**: `Authorization: Bearer <access_token>`
- **Response (200 OK)**:
  ```json
  {
    "success": "Successfully deleted user"
  }
  ```

#### 4. Operator Proxy-Deactivates Farmer Account
- **URL**: `/user/v1/users/<farmer_user_id>/operator-proxy-delete/`
- **Method**: `DELETE`
- **Headers**: `Authorization: Bearer <access_token>` (Operator)
- **Response (200 OK)**:
  ```json
  {
    "success": "User deleted by operator"
  }
  ```
  *(Note: Farmer must be a non-smartphone user belonging to the same company).*

#### 5. List/Create Companies
- **URL**: `/user/v1/companies/`
- **Method**: `GET` / `POST`
- **Headers**: `Authorization: Bearer <access_token>`
- **Query Params**:
  - `marketplace_filter_scoped` (bool): If `true`, lists public companies open for marketplace transactions.
- **Request Body (POST)**:
  ```json
  {
    "name": "New Agro Tech",
    "country": "NG"
  }
  ```
- **Response (200 OK - List)**:
  ```json
  [
    {
      "id": 1,
      "name": "Coop Cold Storage",
      "country": "NG",
      "digital_twin": true
    }
  ]
  ```

#### 6. Farmers ViewSet
- **URL**: `/user/v1/farmers/`
- **Method**: `GET` / `POST` / `PATCH`
- **Headers**: `Authorization: Bearer <access_token>`
- **Query Params**:
  - `user_id` (int): Get farmer linked to user ID.
  - `operator` (int): Get farmers linked to operator's company.
- **Request Body (POST)**:
  ```json
  {
    "parent_name": "Adebayo",
    "create_user": true,
    "user": {
      "first_name": "Ali",
      "last_name": "Adebayo",
      "phone": "+2348123456789",
      "password": "Password123"
    }
  }
  ```

#### 7. Retrieve Farmer by User Code
- **URL**: `/user/v1/farmers/by-code/`
- **Method**: `GET`
- **Headers**: `Authorization: Bearer <access_token>`
- **Query Params**:
  - `user_code` (str, required): The farmer's unique lookup identifier.
- **Response (200 OK)**:
  ```json
  {
    "id": 8,
    "user": { "first_name": "Ali", "last_name": "Adebayo", "phone": "+2348123456789" },
    "user_code": "FMR-8349",
    "parent_name": "Adebayo"
  }
  ```

#### 8. Operator ViewSet
- **URL**: `/user/v1/operators/`
- **Method**: `GET`
- **Query Params**: `company`, `user_id`, `produce_id`, `movement_id`
- **Response (200 OK)**:
  ```json
  [
    {
      "id": 2,
      "user": {"id": 10, "first_name": "John", "last_name": "Doe"},
      "company": 1
    }
  ]
  ```

#### 9. Service Provider ViewSet
- **URL**: `/user/v1/service-providers/`
- **Method**: `GET` / `POST`
- **Query Params**: `company` (int, required)
- **Response (200 OK)**:
  ```json
  [
    {
      "id": 3,
      "user": {"id": 11, "first_name": "Jane", "last_name": "Smith"},
      "company": 1
    }
  ]
  ```

#### 10. Invite Service Provider (Registered Employee)
- **URL**: `/user/v1/service-provider-invite/`
- **Method**: `POST`
- **Headers**: `Authorization: Bearer <access_token>`
- **Request Body**:
  ```json
  {
    "phone": "+2348011112222",
    "email": "employee@example.com",
    "first_name": "Jane",
    "last_name": "Smith",
    "expiration_date": "2026-06-12T12:00:00Z"
  }
  ```
- **Response (200 OK)**: `{}`

#### 11. Invite Operator
- **URL**: `/user/v1/operator-invite/`
- **Method**: `POST`
- **Headers**: `Authorization: Bearer <access_token>`
- **Request Body**:
  ```json
  {
    "phone": "+2348099998888",
    "email": "operator@example.com",
    "first_name": "Frank",
    "last_name": "Miller",
    "expiration_date": "2026-06-12T12:00:00Z"
  }
  ```

#### 12. Register Service Provider (With or Without Invite)
- **URLs**:
  - `/user/v1/service-provider-signup/` (Direct signup)
  - `/user/v1/service-provider-invite-signup/` (Invite-based)
- **Method**: `POST`
- **Request Body (Direct)**:
  ```json
  {
    "user": {
      "first_name": "Abe",
      "last_name": "Lincoln",
      "phone": "+2348077777777",
      "password": "SecurePassword"
    },
    "company": {
      "name": "Lincoln Storage",
      "country": "NG",
      "bank_account": {
        "bank_name": "Access Bank",
        "account_name": "Lincoln Storage Co",
        "account_number": "1234567890"
      }
    }
  }
  ```

#### 13. Register Operator with Invitation
- **URL**: `/user/v1/operator-invite-signup/`
- **Method**: `POST`
- **Request Body**:
  ```json
  {
    "invitation_code": "XYZ987",
    "password": "OperatorSecurePassword",
    "language": "en"
  }
  ```

#### 14. Reset Password
- **URL**: `/user/v1/reset-password/`
- **Method**: `POST`
- **Request Body (Step 1: Request Code)**:
  ```json
  {
    "phoneNumber": "+2348000000000"
  }
  ```
- **Request Body (Step 2: Submit Reset)**:
  ```json
  {
    "phone": "+2348000000000",
    "code": "RST-3482",
    "password": "NewSecurePassword123"
  }
  ```

#### 15. Farmer Post-Harvest Surveys
- **URL**: `/user/v1/farmer-survey/`
- **Method**: `GET` / `POST` / `PATCH`
- **Headers**: `Authorization: Bearer <access_token>`
- **Query Params**: `farmer_id` (required for GET)
- **Request Body (POST/PATCH)**:
  ```json
  {
    "farmer": 8,
    "user_type": 2,
    "experience": "yes",
    "experience_duration": "5 years",
    "commodities": [
      {
        "crop_id": 37,
        "average_price": 250,
        "unit": "bags",
        "kg_in_unit": 50,
        "reason_for_loss": "Rotting due to heat",
        "quantity_total": 100,
        "quantity_self_consumed": 10,
        "quantity_sold": 80,
        "quantity_below_market_price": 10,
        "average_season_in_months": 3,
        "currency": "NGN"
      }
    ]
  }
  ```

#### 16. In-App Notifications
- **URL**: `/user/v1/notification/`
- **Method**: `GET` / `PATCH` / `POST`
- **Headers**: `Authorization: Bearer <access_token>`
- **Query Params**: `user_id` (required for GET; must match token user)
- **Request Body (PATCH - Mark as Seen)**:
  ```json
  {
    "seen": true
  }
  ```

#### 17. Generate Generic User Code
- **URL**: `/user/v1/code/`
- **Method**: `POST`
- **Request Body**:
  ```json
  {
    "user": 10,
    "type": "REGISTRATION"
  }
  ```

---

### Category 3.2: Storage App (`/storage/`)

Tracks crops, cooling units, crates, sensor logs, next checkouts, and COMSOL callback integrations.

#### 1. Crop Types
- **URL**: `/storage/v1/crop-types/`
- **Method**: `GET`
- **Response (200 OK)**:
  ```json
  [
    { "id": 1, "name": "Roots and Tubers" },
    { "id": 2, "name": "Vegetables" }
  ]
  ```

#### 2. Crops (Filtered by Country)
- **URL**: `/storage/v1/crops/`
- **Method**: `GET`
- **Headers**: `Authorization: Bearer <access_token>`
- **Response (200 OK)**:
  ```json
  [
    { "id": 37, "name": "Onion", "crop_type": 2, "digital_twin_identifier": "onion" },
    { "id": 56, "name": "Tomato", "crop_type": 2, "digital_twin_identifier": "tomato" }
  ]
  ```

#### 3. Cooling Units ViewSet
- **URL**: `/storage/v1/cooling-units/`
- **Method**: `GET` / `POST` / `PATCH` / `DELETE`
- **Headers**: `Authorization: Bearer <access_token>`
- **Query Params**:
  - `company` (int): Filter by company.
  - `operator` (int): Filter by operator.
  - `farmer_id` (int): Filter units accessible to farmer.
  - `not_empty` (bool): Filter only units with active checkins.
- **Request Body (POST)**:
  ```json
  {
    "name": "Cold Room A",
    "location": 1,
    "metric": "kg",
    "occupancy": 0.0,
    "public": true
  }
  ```
- **Response (200 OK - Delete)**:
  ```json
  {
    "success": "Successfully deleted cooling unit"
  }
  ```

#### 4. Retrieve Cooling Unit Sensors Data
- **URL**: `/storage/v1/cooling-units/<cooling_unit_id>/sensor-data/`
- **Method**: `GET`
- **Headers**: `Authorization: Bearer <access_token>` (Operator or Service Provider)
- **Response (200 OK)**:
  ```json
  {
    "sensor_data": [
      {
        "id": 1,
        "source_id": "ECOZ-9231",
        "type": "ecozen",
        "username": "user@ecozen.ai",
        "date_sensor_first_linked": "2026-05-10T12:00:00Z"
      }
    ]
  }
  ```

#### 5. List and Retrieve Crates
- **URL**: `/storage/v1/crates/`
- **Method**: `GET`
- **Query Params**: `cooling_unit`, `farmer`
- **Response (200 OK)**:
  ```json
  [
    {
      "id": 101,
      "produce": 45,
      "cooling_unit": 1,
      "weight": 20.0,
      "initial_weight": 20.0,
      "temperature_dt": 24.3,
      "quality_dt": 0.95,
      "remaining_shelf_life": 12.5
    }
  ]
  ```

#### 6. Locations ViewSet
- **URL**: `/storage/v1/locations/`
- **Method**: `GET` / `POST` / `PATCH` / `DELETE`
- **Query Params**: `company`, `farmer_id`
- **Request Body (POST)**:
  ```json
  {
    "name": "Kano Market Hub",
    "company": 1,
    "point": "SRID=4326;POINT(8.522 11.996)"
  }
  ```

#### 7. Next Checkouts View
- **URL**: `/storage/v1/next-checkouts/`
- **Method**: `GET`
- **Query Params**:
  - `cooling_unit` (int, required): The ID of the cooling unit.
- **Response (200 OK)**:
  *(Returns sorted list of active Produce records scheduled to be checked out next, prioritized by lowest remaining shelf life first, followed by planned days expiry)*.

#### 8. Ecozen Connection Tester
- **URL**: `/storage/v1/ecozen/test-connection/`
- **Method**: `POST`
- **Headers**: `Authorization: Bearer <access_token>`
- **Request Body**:
  ```json
  {
    "username": "ecozen_account@example.com",
    "password": "SecretPassword123",
    "source_id": "ECOZ-59301"
  }
  ```
- **Response (200 OK)**:
  ```json
  {
    "success": "Successfully connected"
  }
  ```

#### 9. Sensor Integration ViewSet
- **URLs**:
  - `POST /storage/v1/user-sensor/sources/` (List sources/devices from sensor vendor)
  - `DELETE /storage/v1/user-sensor/<sensor_integration_id>/` (Delete integration)
- **Headers**: `Authorization: Bearer <access_token>`
- **Request Body (POST sources)**:
  ```json
  {
    "integration_type": "figorr",
    "username": "figorr_user",
    "password": "figorr_password"
  }
  ```

#### 10. COMSOL Simulation Result Callback
- **URL**: `/storage/v1/comsol/callback/`
- **Method**: `POST`
- **Headers**:
  - `X-Comsol-Callback-Key: <secret_callback_token>`
- **Request Body (Success)**:
  ```json
  {
    "crate_id": 101,
    "outputs": {
      "shelf_life": 12.5,
      "quality_dt": 0.95,
      "temperature_dt": 24.3
    }
  }
  ```
- **Request Body (Failure)**:
  ```json
  {
    "crate_id": 101,
    "error": "Simulation failed to converge"
  }
  ```
- **Response (200 OK)**: `{"status": "success"}`

#### 11. List Produce inside Cooling Unit (Operator View)
- **URL**: `/storage/v1/cooling-units/<cooling_unit_id>/produces/`
- **Method**: `GET`
- **Headers**: `Authorization: Bearer <access_token>` (Operator / Employee)
- **Response (200 OK)**:
  ```json
  [
    {
      "id": 45,
      "crop": { "id": 37, "name": "Onion" },
      "crates": [
        {
          "id": 101,
          "weight": 20.0,
          "is_listed_in_the_marketplace": false,
          "is_locked_within_pending_orders": false
        }
      ]
    }
  ]
  ```

#### 12. List Produce inside Cooling Unit (Farmer View)
- **URL**: `/storage/v1/cooling-units/<cooling_unit_id>/farmers/<farmer_id>/produces/`
- **Method**: `GET`
- **Headers**: `Authorization: Bearer <access_token>` (Farmer)

---

### Category 3.3: Operations App (`/operation/`)

Manages the actual movement transactions (inward check-ins, outward check-outs, and relocations).

#### 1. Check-in Produce
- **URL**: `/operation/checkins/`
- **Method**: `POST`
- **Request Body**:
  ```json
  {
    "farmer_id": 8,
    "produces": "[{\"crop\": {\"id\": 37}, \"crates\": [{\"cooling_unit_id\": 1, \"weight\": 20.0, \"planned_days\": 15}], \"has_picture\": false}]"
  }
  ```
- **Response (200 OK)**: Returns serialzied check-in info.

#### 2. Edit Active Check-in
- **URL**: `/operation/checkins/<produce_id>/`
- **Method**: `PATCH`
- **Request Body**:
  ```json
  {
    "farmer_id": 9,
    "crop_id": 56,
    "planned_days": 10
  }
  ```
  *(Note: Only editable on the day of check-in and if editable_checkins is enabled for the unit).*

#### 3. Checkout Crates
- **URL**: `/operation/checkouts/`
- **Method**: `POST`
- **Request Body**:
  ```json
  {
    "crates": [101],
    "payment_through": "cash",
    "payment_method": "direct",
    "currency": "NGN"
  }
  ```
- **Response (200 OK)**:
  ```json
  {
    "id": 12,
    "movement": 98,
    "paid": true,
    "cmp_total_cooling_fees_amount": 1200.0,
    "cmp_total_amount": 1200.0
  }
  ```

#### 4. Get Checked-out Crates (Lookup by Movement Code)
- **URL**: `/operation/checkouts/`
- **Method**: `GET`
- **Query Params**:
  - `code` (str): The checkout movement code (e.g. `CHK-93041`).
- **Response (200 OK)**: Lists crates associated with that checkout.

#### 5. List Movements
- **URL**: `/operation/movements/`
- **Method**: `GET`
- **Query Params**: `cooling_unit`, `farmer_id`, `owned_by_user_id`
- **Response (200 OK)**:
  ```json
  [
    {
      "id": 98,
      "code": "CHK-93041",
      "date": "2026-06-09",
      "initiated_for": "CHECK_OUT",
      "operator": 2
    }
  ]
  ```

#### 6. Checkout-to-Checkin (Relocate Crates)
- **URLs**:
  - `GET /operation/move-checkout/?code=<movement_code>` (Fetch crates for checkout movement)
  - `POST /operation/move-checkout/` (Execute check-in move)
- **Request Body (POST)**:
  ```json
  {
    "params": {
      "code": "CHK-93041",
      "cooling_unit_id": 2,
      "farmer": 8,
      "days": 15
    }
  }
  ```

#### 7. Post Operator Market Survey
- **URL**: `/operation/market-survey/`
- **Method**: `POST`
- **Request Body**:
  ```json
  {
    "company": 1,
    "crop": 37,
    "price": 400.00,
    "currency": "NGN",
    "reason_for_loss": ["High Temperature", "Poor Handling"]
  }
  ```

---

### Category 3.4: Marketplace App (`/marketplace/`)

#### 1. Available Listings
- **URL**: `/marketplace/buyer/available-listings/`
- **Method**: `GET`
- **Query Params**:
  - `lat` (float), `lng` (float): Location coordinates.
  - `sort_by` (str): `price-asc`, `price-desc`, or `distance`.
  - `page` (int), `items_per_page` (int)

#### 2. Get/Recompute Cart
- **URL**: `/marketplace/buyer/cart/`
- **Method**: `GET` / `POST`
- **Headers**: `Authorization: Bearer <access_token>`

#### 3. Add/Update Cart Item
- **URL**: `/marketplace/buyer/cart/items/`
- **Method**: `POST`
- **Request Body**:
  ```json
  {
    "crate_id": 101,
    "update_strategy": "increase",
    "ordered_produce_weight": 5.0
  }
  ```

#### 4. Remove Cart Item
- **URL**: `/marketplace/buyer/cart/items/<crate_id>/`
- **Method**: `DELETE`

#### 5. Apply Coupon to Cart
- **URL**: `/marketplace/buyer/cart/apply-coupon/`
- **Method**: `POST`
- **Request Body**: `{"coupon_code": "DISCOUNT10"}`

#### 6. Toggle Cart Ownership (Personal vs. Company Purchase)
- **URL**: `/marketplace/buyer/cart/toggle-ownership/`
- **Method**: `POST`

#### 7. Set Cart Pickup Details
- **URL**: `/marketplace/buyer/cart/set-pickup-details/`
- **Method**: `POST`
- **Request Body**:
  ```json
  {
    "pickup_details": [
      {
        "cooling_unit_id": 1,
        "pickup_method": "pick_up_same_day"
      }
    ]
  }
  ```

#### 8. Cart Delivery Contacts
- **URL**: `/marketplace/buyer/cart/delivery-contacts/`
- **Method**: `GET`

#### 9. Checkout Cart via Paystack
- **URL**: `/marketplace/buyer/cart/checkout-with-paystack/`
- **Method**: `POST`
- **Response (200 OK)**:
  ```json
  {
    "order_id": 431,
    "authorization_url": "https://checkout.paystack.com/abcdefgh"
  }
  ```

#### 10. Buyer Orders ViewSet
- **URLs**:
  - `GET /marketplace/buyer/orders/` (List buyer orders)
  - `GET /marketplace/buyer/orders/<order_id>/` (Retrieve order details)
  - `POST /marketplace/buyer/orders/<order_id>/pay-with-paystack/` (Retry payment)
  - `POST /marketplace/buyer/orders/<order_id>/cancel/` (Cancel pending payment order)

#### 11. Company Orders ViewSet (Operator/Employee View)
- **URL**: `/marketplace/company/orders/`
- **Method**: `GET`
- **Query Params**: `cooling_unit_id` (int, required)
- **Response (200 OK)**: Lists paid orders referencing crates in that cooling unit.

#### 12. Company Delivery Contacts Management
- **URL**: `/marketplace/company/delivery-contacts/`
- **Method**: `GET` / `POST` / `DELETE`
- **Request Body (POST)**:
  ```json
  {
    "delivery_company_name": "FastExpress",
    "contact_name": "Musa Ali",
    "phone": "+2348033334444"
  }
  ```

#### 13. Paystack Webhook Hook
- **URL**: `/marketplace/webhooks/paystack/`
- **Method**: `POST`
- **Authentication**: Validated via Paystack Signature headers
- **Response (200 OK)**: `{"status": "success"}`

---

### Category 3.5: Prediction App (`/prediction/`)

#### 1. Fetch Prediction State Parameters (India)
- **URL**: `/prediction/v1/states/get_parameters_for_prediction/`
- **Method**: `GET`
- **Response (200 OK)**: Returns lists of `available_crops` and `available_markets` mapped by State and District.

#### 2. Fetch Prediction State Parameters (Nigeria)
- **URL**: `/prediction/v1/statesng/get_parameters_for_prediction/`
- **Method**: `GET`
- **Response (200 OK)**: Returns lists of `available_crops` and `available_states`.

#### 3. Markets ViewSet
- **URL**: `/prediction/markets/`
- **Method**: `GET` / `POST`
- **Query Params**: `country` (str, filter by country code e.g. "IN")
- **Request Body (POST)**:
  ```json
  {
    "name": "Kano Central Market",
    "district": "Kano",
    "state_name": "Kano State",
    "country": "NG"
  }
  ```

#### 4. India Graph Data
- **URL**: `/prediction/predictions/get_data_graph`
- **Method**: `POST`
- **Request Body**: `{"marketId": 1, "cropId": 37}`

#### 5. India Table Data
- **URL**: `/prediction/predictions/get_data_table`
- **Method**: `POST`
- **Request Body**: `{"marketsIds": [1, 2], "cropId": 37, "days": ["2026-06-10"]}`

#### 6. Nigeria Graph Data
- **URL**: `/prediction/predictions/get_data_graph_ng`
- **Method**: `POST`
- **Request Body**: `{"stateId": 1, "cropId": 37}`

#### 7. Nigeria Table Data
- **URL**: `/prediction/predictions/get_data_table_ng`
- **Method**: `POST`
- **Request Body**: `{"statesIds": [1, 2], "cropId": 37, "days": ["2026-07-01"]}`
