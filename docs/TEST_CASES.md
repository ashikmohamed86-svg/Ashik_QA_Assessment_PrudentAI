# Test Cases Document – Stripe API Automation

## 1. Customer API Tests

| # | Test Case | Method | Endpoint | Expected Result |
|---|-----------|--------|----------|-----------------|
| C-01 | Create customer with all fields (name, email, phone) | POST | /customers | 200, `id` starts with `cus_`, all fields echoed back, schema valid |
| C-02 | Create customer with only email | POST | /customers | 200, `id` starts with `cus_`, email matches |
| C-03 | Create customer without email | POST | /customers | 200, `email` is null |
| C-04 | Validate email format in response | POST | /customers | Email matches RFC-5322 pattern |
| C-05 | Validate phone format in response | POST | /customers | Phone matches E.164 pattern |
| C-06 | Response schema validation | POST | /customers | Matches JSON schema (id, object, created, livemode, etc.) |
| C-07 | Fetch existing customer | GET | /customers/{id} | 200, correct details returned |
| C-08 | Fetch non-existing customer | GET | /customers/{id} | 404 error |
| C-09 | Fetch with invalid ID format | GET | /customers/{id} | 404 error |
| C-10 | List customers with limit | GET | /customers?limit=3 | 200, list schema valid, ≤3 items |
| C-11 | Update customer name | POST | /customers/{id} | 200, name updated, other fields unchanged |
| C-12 | Delete customer | DELETE | /customers/{id} | 200, `deleted: true` |
| C-13 | Create customer with invalid email string | POST | /customers | 200 (Stripe accepts it) |
| C-14 | Create customer with empty body | POST | /customers | 200 (Stripe allows) |
| C-15 | Create customer with extremely long name | POST | /customers | 200, name stored as-is |
| C-16 | Retrieve deleted customer | GET | /customers/{id} | 200, `deleted: true` |

## 2. PaymentIntent API Tests

| # | Test Case | Method | Endpoint | Expected Result |
|---|-----------|--------|----------|-----------------|
| P-01 | Create basic PaymentIntent | POST | /payment_intents | 200, `id` starts with `pi_`, status = `requires_payment_method` |
| P-02 | Amount stored in minor units (cents) | POST | /payment_intents | `amount` is integer = 2000 |
| P-03 | Currency is ISO 4217 (3-letter lowercase) | POST | /payment_intents | Currency matches `^[a-z]{3}$` |
| P-04 | Create with receipt email | POST | /payment_intents | 200, `receipt_email` matches input |
| P-05 | Create with manual capture method | POST | /payment_intents | 200, `capture_method` = manual |
| P-06 | Response schema validation | POST | /payment_intents | Matches PaymentIntent JSON schema |
| P-07 | Confirm with valid Visa card | POST | /payment_intents/{id}/confirm | 200, status = `succeeded` |
| P-08 | Confirm without payment method | POST | /payment_intents/{id}/confirm | 400 error |
| P-09 | Confirm already-succeeded intent | POST | /payment_intents/{id}/confirm | 400 error |
| P-10 | Capture after confirm (manual) | POST | /payment_intents/{id}/capture | 200, status = `succeeded`, `amount_received` = amount |
| P-11 | Capture before confirm | POST | /payment_intents/{id}/capture | 400 error |
| P-12 | Double capture | POST | /payment_intents/{id}/capture | 400 error |
| P-13 | Fetch existing PaymentIntent | GET | /payment_intents/{id} | 200, correct details |
| P-14 | Fetch non-existing PaymentIntent | GET | /payment_intents/{id} | 404 error |
| P-15 | Status transition: created → succeeded | GET | /payment_intents/{id} | Status changes after confirm |
| P-16 | Status transition: created → requires_capture → succeeded | GET | /payment_intents/{id} | Status changes through manual-capture flow |
| P-17 | Verify timestamps | GET | /payment_intents/{id} | `created` is positive integer |

## 3. Negative & Input Validation Tests

| # | Test Case | Method | Endpoint | Expected Result |
|---|-----------|--------|----------|-----------------|
| N-01 | Invalid currency code (`zzz`) | POST | /payment_intents | 400, error schema valid |
| N-02 | Missing amount | POST | /payment_intents | 400 |
| N-03 | Negative amount | POST | /payment_intents | 400 |
| N-04 | Zero amount | POST | /payment_intents | 400 |
| N-05 | String (non-numeric) amount | POST | /payment_intents | 400 |
| N-06 | Missing currency | POST | /payment_intents | 400 |
| N-07 | Various invalid currencies (uppercase, partial, numeric) | POST | /payment_intents | 400 or auto-normalised |
| N-08 | Capture amount > authorized | POST | /payment_intents/{id}/capture | 400 |
| N-09 | Capture before confirm | POST | /payment_intents/{id}/capture | 400 |

## 4. Decline Scenario Tests (Stripe Test Cards)

| # | Test Case | Card Token | Expected Result |
|---|-----------|------------|-----------------|
| D-01 | Generic card decline | `pm_card_chargeDeclined` | 402, code = `card_declined` |
| D-02 | Insufficient funds | `pm_card_chargeDeclinedInsufficientFunds` | 402, decline_code = `insufficient_funds` |
| D-03 | Expired card | `pm_card_chargeDeclinedExpiredCard` | 402, decline_code = `expired_card` |
| D-04 | Incorrect CVC | `pm_card_chargeDeclinedIncorrectCvc` | 402, decline_code = `incorrect_cvc` |
| D-05 | Confirm without payment method | — | 400, error present |

## 5. End-to-End Tests

| # | Test Case | Flow | Expected Result |
|---|-----------|------|-----------------|
| E-01 | Full automatic-capture flow | Create Customer → Create PI → Confirm → Fetch | Status = `succeeded`, amount & customer match |
| E-02 | Full manual-capture flow | Create Customer → Create PI(manual) → Confirm → Capture → Fetch | Status = `succeeded`, `amount_received` matches |
