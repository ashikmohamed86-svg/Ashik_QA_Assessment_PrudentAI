# Test Cases Document – Stripe API Automation

## 1. Customer API – Positive Tests

| # | Test Case | Method | Endpoint | Expected Result |
|---|-----------|--------|----------|-----------------|
| C-01 | Create customer with all fields (name, email, phone) | POST | /customers | 200, `id` starts with `cus_`, all fields echoed back, schema valid |
| C-02 | Create customer with only email | POST | /customers | 200, `id` starts with `cus_`, email matches |
| C-03 | Create customer without email | POST | /customers | 200, `email` is null |
| C-04 | Validate email format in response | POST | /customers | Email matches RFC-5322 pattern |
| C-05 | Validate phone format in response | POST | /customers | Phone matches E.164 pattern |
| C-06 | Response schema validation | POST | /customers | Matches JSON schema (id, object, created, livemode, etc.) |
| C-07 | Fetch existing customer | GET | /customers/{id} | 200, correct details returned, response headers valid |
| C-08 | Fetch non-existing customer | GET | /customers/{id} | 404 error |
| C-09 | Fetch with invalid ID format | GET | /customers/{id} | 404 error |
| C-10 | List customers with limit | GET | /customers?limit=3 | 200, list schema valid, ≤3 items |
| C-11 | Update customer name | POST | /customers/{id} | 200, name updated, other fields unchanged |
| C-12 | Update customer email | POST | /customers/{id} | 200, email updated, name unchanged |
| C-13 | Create customer with description | POST | /customers | 200, description field persisted |
| C-14 | Delete customer | DELETE | /customers/{id} | 200, `deleted: true` |

## 2. Customer API – Negative Tests

| # | Test Case | Method | Endpoint | Expected Result |
|---|-----------|--------|----------|-----------------|
| CN-01 | Create customer with invalid email string | POST | /customers | 400 (rejected by Stripe) |
| CN-02 | Create customer with empty body | POST | /customers | 200 (Stripe allows) |
| CN-03 | Create customer with extremely long name (5000 chars) | POST | /customers | 400 (rejected by Stripe) |
| CN-04 | Retrieve deleted customer | GET | /customers/{id} | 200, `deleted: true` |
| CN-05 | Delete non-existing customer | DELETE | /customers/{id} | 404 error |
| CN-06 | Double delete (already-deleted customer) | DELETE | /customers/{id} | 404 error |
| CN-07 | Update non-existing customer | POST | /customers/{id} | 404 error |

## 3. Customer API – Pagination Tests

| # | Test Case | Method | Endpoint | Expected Result |
|---|-----------|--------|----------|-----------------|
| CP-01 | Limit returns correct count | GET | /customers?limit=1 | 200, exactly 1 result |
| CP-02 | Paginate with starting_after cursor | GET | /customers?starting_after={id} | Different customer on page 2 |
| CP-03 | has_more flag is correct | GET | /customers?limit=1 | `has_more: true` when more data exists |

## 4. Customer API – Metadata Tests

| # | Test Case | Method | Endpoint | Expected Result |
|---|-----------|--------|----------|-----------------|
| CM-01 | Create customer with metadata | POST | /customers | 200, metadata key-values persisted |
| CM-02 | Update metadata on existing customer | POST | /customers/{id} | Metadata value updated |
| CM-03 | Clear metadata by setting empty value | POST | /customers/{id} | Metadata key cleared |

## 5. Customer API – Performance Tests

| # | Test Case | Method | Endpoint | Threshold |
|---|-----------|--------|----------|-----------|
| CPERF-01 | Create customer response time | POST | /customers | < 5 seconds |
| CPERF-02 | Fetch customer response time | GET | /customers/{id} | < 5 seconds |
| CPERF-03 | List customers response time | GET | /customers | < 5 seconds |
| CPERF-04 | Update customer response time | POST | /customers/{id} | < 5 seconds |
| CPERF-05 | Delete customer response time | DELETE | /customers/{id} | < 5 seconds |

## 6. Customer API – Boundary & Limit Tests

| # | Test Case | Method | Endpoint | Expected Result |
|---|-----------|--------|----------|-----------------|
| CB-01 | Special characters (unicode) in name | POST | /customers | 200, name stored correctly |
| CB-02 | Empty string name | POST | /customers | 200, accepted |
| CB-03 | Empty string phone | POST | /customers | 200, accepted |
| CB-04 | List with max limit (100) | GET | /customers?limit=100 | 200, ≤100 results, schema valid |

## 7. PaymentIntent API – Positive Tests

| # | Test Case | Method | Endpoint | Expected Result |
|---|-----------|--------|----------|-----------------|
| P-01 | Create basic PaymentIntent | POST | /payment_intents | 200, `id` starts with `pi_`, status = `requires_payment_method`, headers valid |
| P-02 | Amount stored in minor units (cents) | POST | /payment_intents | `amount` is integer = 2000 |
| P-03 | Currency is ISO 4217 (3-letter lowercase) | POST | /payment_intents | Currency matches `^[a-z]{3}$` |
| P-04 | Create with receipt email | POST | /payment_intents | 200, `receipt_email` matches input |
| P-05 | Create with manual capture method | POST | /payment_intents | 200, `capture_method` = manual |
| P-06 | Response schema validation | POST | /payment_intents | Matches PaymentIntent JSON schema |
| P-07 | Confirm with valid Visa card | POST | /payment_intents/{id}/confirm | 200, status = `succeeded` |
| P-08 | Confirm with Mastercard | POST | /payment_intents/{id}/confirm | 200, status = `succeeded` |
| P-09 | Create with EUR currency | POST | /payment_intents | 200, currency = `eur` |
| P-10 | Create with GBP currency | POST | /payment_intents | 200, currency = `gbp` |
| P-11 | Partial capture (less than authorized) | POST | /payment_intents/{id}/capture | 200, `amount_received` = partial amount |
| P-12 | Cancel uncaptured PaymentIntent | POST | /payment_intents/{id}/cancel | 200, status = `canceled` |
| P-13 | Capture after confirm (manual) | POST | /payment_intents/{id}/capture | 200, status = `succeeded`, `amount_received` = amount |
| P-14 | Fetch existing PaymentIntent | GET | /payment_intents/{id} | 200, correct details, headers valid |
| P-15 | Status transition: created → succeeded | GET | /payment_intents/{id} | Status changes after confirm |
| P-16 | Status transition: created → requires_capture → succeeded | GET | /payment_intents/{id} | Status changes through manual-capture flow |
| P-17 | Verify timestamps | GET | /payment_intents/{id} | `created` is positive integer |

## 8. PaymentIntent API – Negative Tests

| # | Test Case | Method | Endpoint | Expected Result |
|---|-----------|--------|----------|-----------------|
| PN-01 | Confirm without payment method | POST | /payment_intents/{id}/confirm | 400 error |
| PN-02 | Confirm already-succeeded intent | POST | /payment_intents/{id}/confirm | 400 error |
| PN-03 | Capture before confirm | POST | /payment_intents/{id}/capture | 400 error |
| PN-04 | Double capture | POST | /payment_intents/{id}/capture | 400 error |
| PN-05 | Fetch non-existing PaymentIntent | GET | /payment_intents/{id} | 404 error |
| PN-06 | Cancel already-succeeded intent | POST | /payment_intents/{id}/cancel | 400 error |
| PN-07 | Confirm with invalid payment method token | POST | /payment_intents/{id}/confirm | 400 error |
| PN-08 | Float amount (non-integer) | POST | /payment_intents | 400 error |
| PN-09 | Fetch with invalid ID format | GET | /payment_intents/{id} | 404 error |
| PN-10 | Invalid currency code (`zzz`) | POST | /payment_intents | 400, error schema valid |
| PN-11 | Missing amount | POST | /payment_intents | 400 |
| PN-12 | Negative amount | POST | /payment_intents | 400 |
| PN-13 | Zero amount | POST | /payment_intents | 400 |
| PN-14 | String (non-numeric) amount | POST | /payment_intents | 400 |
| PN-15 | Missing currency | POST | /payment_intents | 400 |
| PN-16 | Various invalid currencies (partial, numeric) | POST | /payment_intents | 400 or auto-normalised |
| PN-17 | Capture amount > authorized | POST | /payment_intents/{id}/capture | 400 |

## 9. PaymentIntent API – Performance Tests

| # | Test Case | Method | Endpoint | Threshold |
|---|-----------|--------|----------|-----------|
| PPERF-01 | Create PaymentIntent response time | POST | /payment_intents | < 5 seconds |
| PPERF-02 | Fetch PaymentIntent response time | GET | /payment_intents/{id} | < 5 seconds |
| PPERF-03 | Confirm PaymentIntent response time | POST | /payment_intents/{id}/confirm | < 5 seconds |
| PPERF-04 | Capture PaymentIntent response time | POST | /payment_intents/{id}/capture | < 5 seconds |

## 10. PaymentIntent API – Boundary & Limit Tests

| # | Test Case | Method | Endpoint | Expected Result |
|---|-----------|--------|----------|-----------------|
| PB-01 | Minimum valid amount (50 cents USD) | POST | /payment_intents | 200, amount = 50 |
| PB-02 | Very large amount (99,999,999) | POST | /payment_intents | 200, accepted |
| PB-03 | Below minimum amount (49 cents) | POST | /payment_intents | 400, rejected |

## 11. Idempotency Tests

| # | Test Case | Method | Endpoint | Expected Result |
|---|-----------|--------|----------|-----------------|
| I-01 | Same idempotency key returns same PaymentIntent | POST | /payment_intents | Both responses have identical `id` |
| I-02 | Different idempotency keys create different PaymentIntents | POST | /payment_intents | Responses have different `id` values |

## 12. Decline Scenario Tests (Stripe Test Cards)

| # | Test Case | Card Token | Expected Result |
|---|-----------|------------|-----------------|
| D-01 | Generic card decline | `pm_card_chargeDeclined` | 402, code = `card_declined` |
| D-02 | Insufficient funds | `pm_card_chargeDeclinedInsufficientFunds` | 402, decline_code contains `insufficient` |
| D-03 | Expired card | `pm_card_chargeDeclinedExpiredCard` | 402, code = `expired_card` |
| D-04 | Incorrect CVC | `pm_card_chargeDeclinedIncorrectCvc` | 402, code = `incorrect_cvc` |
| D-05 | Processing error | `pm_card_chargeDeclinedProcessingError` | 402, code = `processing_error` |

## 13. End-to-End Tests

| # | Test Case | Flow | Expected Result |
|---|-----------|------|-----------------|
| E-01 | Full automatic-capture flow | Create Customer → Create PI → Confirm → Fetch | Status = `succeeded`, amount & customer match |
| E-02 | Full manual-capture flow | Create Customer → Create PI(manual) → Confirm → Capture → Fetch | Status = `succeeded`, `amount_received` matches |
