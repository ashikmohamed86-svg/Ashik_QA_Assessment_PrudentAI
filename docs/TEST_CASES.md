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
| C-08 | Fetch non-existing customer | GET | /customers/{id} | 404, error schema valid (error.type, error.message) |
| C-09 | Fetch with invalid ID format | GET | /customers/{id} | 404, error schema valid |
| C-10 | List customers with limit | GET | /customers?limit=3 | 200, list schema valid, ≤3 items |
| C-11 | Update customer name | POST | /customers/{id} | 200, name updated, other fields unchanged |
| C-12 | Update customer email | POST | /customers/{id} | 200, email updated, name unchanged |
| C-13 | Create customer with description | POST | /customers | 200, description field persisted |
| C-14 | Delete customer | DELETE | /customers/{id} | 200, `deleted: true` |

## 2. Customer API – Negative Tests

| # | Test Case | Method | Endpoint | Expected Result |
|---|-----------|--------|----------|-----------------|
| CN-01 | Create customer with invalid email string | POST | /customers | 400 (rejected by Stripe), error schema valid |
| CN-02 | Create customer with empty body | POST | /customers | 200 (Stripe allows), `id` starts with `cus_` |
| CN-03 | Create customer with extremely long name (5000 chars) | POST | /customers | 400 (rejected by Stripe), error schema valid |
| CN-04 | Retrieve deleted customer | GET | /customers/{id} | 200, `deleted: true` |
| CN-05 | Delete non-existing customer | DELETE | /customers/{id} | 404 error |
| CN-06 | Double delete (already-deleted customer) | DELETE | /customers/{id} | 404 error |
| CN-07 | Update non-existing customer | POST | /customers/{id} | 404 error |
| CN-08 | Create customer with invalid phone (abc123) | POST | /customers | Assert Stripe behavior + E.164 validator flags invalid format |

## 3. Customer API – Pagination Tests

| # | Test Case | Method | Endpoint | Expected Result |
|---|-----------|--------|----------|-----------------|
| CP-01 | Limit returns correct count | GET | /customers?limit=1 | 200, exactly 1 result |
| CP-02 | Paginate with starting_after cursor | GET | /customers?starting_after={id} | Different customer on page 2 |
| CP-03 | has_more flag is correct | GET | /customers?limit=1 | `has_more: true` when more data exists |
| CP-04 | Limit=0 edge case | GET | /customers?limit=0 | Stripe accepts gracefully or 400 |
| CP-05 | Limit=101 (over max) edge case | GET | /customers?limit=101 | Stripe caps or 400 |
| CP-06 | Invalid starting_after cursor | GET | /customers?starting_after=invalid | 400/404, error schema valid |
| CP-07 | Full pagination loop until has_more=false | GET | /customers | No duplicate IDs across pages |

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
| CB-05 | Duplicate email customers | POST | /customers | 200 for both, different IDs, same email |
| CB-06 | Max metadata keys (50 key-value pairs) | POST | /customers | 200, all 50 keys stored |

## 7. Customer API – Idempotency Tests

| # | Test Case | Method | Endpoint | Expected Result |
|---|-----------|--------|----------|-----------------|
| CI-01 | Same idempotency key returns same customer | POST | /customers | Both responses have identical `id` |

## 8. Customer API – Search & Update Fields

| # | Test Case | Method | Endpoint | Expected Result |
|---|-----------|--------|----------|-----------------|
| CS-01 | Search customers by email | GET | /customers?email={email} | 200, all results match email |
| CS-02 | Search non-existent email | GET | /customers?email={email} | 200, empty data array |
| CU-01 | Update customer phone | POST | /customers/{id} | 200, phone updated |
| CU-02 | Update customer description | POST | /customers/{id} | 200, description updated |
| CU-03 | Whitespace-only name accepted | POST | /customers | 200, Stripe accepts whitespace name |
| CU-04 | Timestamp is recent (within 60s of creation) | POST | /customers | `created` timestamp is within expected range |
| CU-05 | Unknown parameters rejected | POST | /customers | 400, parameter_unknown error |

## 9. PaymentIntent API – Positive Tests

| # | Test Case | Method | Endpoint | Expected Result |
|---|-----------|--------|----------|-----------------|
| P-01 | Create basic PaymentIntent | POST | /payment_intents | 200, `id` starts with `pi_`, status = `requires_payment_method`, headers valid |
| P-02 | Amount stored in minor units (cents) | POST | /payment_intents | `amount` is integer = 2000 |
| P-03 | Currency is ISO 4217 (3-letter lowercase) | POST | /payment_intents | Currency matches `^[a-z]{3}$` |
| P-04 | Create with receipt email | POST | /payment_intents | 200, `receipt_email` matches input |
| P-05 | Create with manual capture method | POST | /payment_intents | 200, `capture_method` = manual |
| P-06 | Response schema validation | POST | /payment_intents | Matches PaymentIntent JSON schema |
| P-07 | Create with customer attached | POST | /payment_intents | 200, `customer` matches input ID |
| P-08 | Confirm with valid Visa card | POST | /payment_intents/{id}/confirm | 200, status = `succeeded` |
| P-09 | Confirm with Mastercard | POST | /payment_intents/{id}/confirm | 200, status = `succeeded` |
| P-10 | Create with EUR currency | POST | /payment_intents | 200, currency = `eur` |
| P-11 | Create with GBP currency | POST | /payment_intents | 200, currency = `gbp` |
| P-12 | Partial capture (less than authorized) | POST | /payment_intents/{id}/capture | 200, `amount_received` = partial amount |
| P-13 | Cancel uncaptured PaymentIntent | POST | /payment_intents/{id}/cancel | 200, status = `canceled` |
| P-14 | Capture after confirm (manual) | POST | /payment_intents/{id}/capture | 200, status = `succeeded`, `amount_received` = amount |
| P-15 | Fetch existing PaymentIntent | GET | /payment_intents/{id} | 200, correct details, headers valid |
| P-16 | Status transition: created → succeeded | GET | /payment_intents/{id} | Status changes after confirm |
| P-17 | Status transition: created → requires_capture → succeeded | GET | /payment_intents/{id} | Status changes through manual-capture flow |
| P-18 | Verify timestamps stability across fetches | GET | /payment_intents/{id} | `created` is stable; does not change after confirm |

## 10. PaymentIntent API – Negative Tests

| # | Test Case | Method | Endpoint | Expected Result |
|---|-----------|--------|----------|-----------------|
| PN-01 | Confirm without payment method | POST | /payment_intents/{id}/confirm | 400 error |
| PN-02 | Confirm already-succeeded intent | POST | /payment_intents/{id}/confirm | 400 error |
| PN-03 | Confirm non-existing PaymentIntent | POST | /payment_intents/{id}/confirm | 404, error schema valid |
| PN-04 | Capture before confirm | POST | /payment_intents/{id}/capture | 400 error |
| PN-05 | Double capture | POST | /payment_intents/{id}/capture | 400 error |
| PN-06 | Fetch non-existing PaymentIntent | GET | /payment_intents/{id} | 404 error |
| PN-07 | Cancel already-succeeded intent | POST | /payment_intents/{id}/cancel | 400, error schema valid |
| PN-08 | Confirm with invalid payment method token | POST | /payment_intents/{id}/confirm | 400, error schema valid |
| PN-09 | Float amount (non-integer) | POST | /payment_intents | 400, error schema valid |
| PN-10 | Fetch with invalid ID format | GET | /payment_intents/{id} | 404 error |
| PN-11 | Invalid currency code (`zzz`) | POST | /payment_intents | 400, error schema valid |
| PN-12 | Missing amount | POST | /payment_intents | 400, error schema valid |
| PN-13 | Negative amount | POST | /payment_intents | 400 |
| PN-14 | Zero amount | POST | /payment_intents | 400 |
| PN-15 | String (non-numeric) amount | POST | /payment_intents | 400 |
| PN-16 | Missing currency | POST | /payment_intents | 400 |
| PN-17 | Various invalid currencies (partial, numeric) | POST | /payment_intents | 400 or auto-normalised |
| PN-18 | Capture amount > authorized | POST | /payment_intents/{id}/capture | 400 |
| PN-19 | Missing payment_method_types | POST | /payment_intents | Assert Stripe default or 400 |
| PN-20 | Empty payment_method_types | POST | /payment_intents | Assert Stripe behavior or 400 |
| PN-21 | Invalid receipt_email format | POST | /payment_intents | Assert Stripe behavior + validator flags |
| PN-22 | Error schema contract validation | POST | /payment_intents | error.type, error.message non-empty; optional code/param are strings |

## 11. PaymentIntent API – Performance Tests

| # | Test Case | Method | Endpoint | Threshold |
|---|-----------|--------|----------|-----------|
| PPERF-01 | Create PaymentIntent response time | POST | /payment_intents | < 5 seconds |
| PPERF-02 | Fetch PaymentIntent response time | GET | /payment_intents/{id} | < 5 seconds |
| PPERF-03 | Confirm PaymentIntent response time | POST | /payment_intents/{id}/confirm | < 5 seconds |
| PPERF-04 | Capture PaymentIntent response time | POST | /payment_intents/{id}/capture | < 5 seconds |

## 12. PaymentIntent API – Boundary & Limit Tests

| # | Test Case | Method | Endpoint | Expected Result |
|---|-----------|--------|----------|-----------------|
| PB-01 | Minimum valid amount (50 cents USD) | POST | /payment_intents | 200, amount = 50 |
| PB-02 | Very large amount (99,999,999) | POST | /payment_intents | 200, accepted |
| PB-03 | Below minimum amount (49 cents) | POST | /payment_intents | 400, rejected |
| PB-04 | Amount boundary: 1 cent | POST | /payment_intents | Assert actual Stripe behavior (400 for USD) |

## 13. Idempotency Tests

| # | Test Case | Method | Endpoint | Expected Result |
|---|-----------|--------|----------|-----------------|
| I-01 | Same idempotency key returns same PaymentIntent | POST | /payment_intents | Both responses have identical `id` |
| I-02 | Different idempotency keys create different PaymentIntents | POST | /payment_intents | Responses have different `id` values |

## 14. Decline Scenario Tests (Stripe Test Cards)

| # | Test Case | Card Token | Expected Result |
|---|-----------|------------|-----------------|
| D-01 | Generic card decline | `pm_card_chargeDeclined` | 402, code = `card_declined` |
| D-02 | Insufficient funds | `pm_card_chargeDeclinedInsufficientFunds` | 402, decline_code contains `insufficient` |
| D-03 | Expired card | `pm_card_chargeDeclinedExpiredCard` | 402, code = `expired_card` |
| D-04 | Incorrect CVC | `pm_card_chargeDeclinedIncorrectCvc` | 402, code = `incorrect_cvc` |
| D-05 | Processing error | `pm_card_chargeDeclinedProcessingError` | 402, code = `processing_error` |
| D-06 | Stolen/fraudulent card | `pm_card_chargeDeclinedFraudulent` | 402, decline_code contains `fraudulent` |
| D-07 | Lost card | `pm_card_chargeDeclinedLostCard` | 402, decline_code = `lost_card` |
| D-08 | Radar block (fraud detection) | `pm_card_radarBlock` | 402, code = `card_declined` or `blocked` |

## 15. End-to-End Tests

| # | Test Case | Flow | Expected Result |
|---|-----------|------|-----------------|
| E-01 | Full automatic-capture flow | Create Customer → Create PI → Confirm → Fetch | Status = `succeeded`, amount & customer match |
| E-02 | Full manual-capture flow | Create Customer → Create PI(manual) → Confirm → Capture → Fetch | Status = `succeeded`, `amount_received` matches |
| E-03 | Payment declined E2E | Create Customer → Create PI → Confirm(declined) → Fetch | Status ≠ `succeeded`, error assertions |
| E-04 | Confirm without PM then recover | Create PI → Confirm(no PM, 400) → Confirm(visa) → Fetch | Recovers to `succeeded` |

## 16. Authentication & Headers Tests

| # | Test Case | Method | Endpoint | Expected Result |
|---|-----------|--------|----------|-----------------|
| AUTH-01 | Missing Authorization header | GET | /customers | 401, error schema valid |
| AUTH-02 | Invalid API key | GET | /customers | 401, error schema valid |
| AUTH-03 | Missing auth on POST /customers | POST | /customers | 401 |
| AUTH-04 | Missing auth on POST /payment_intents | POST | /payment_intents | 401 |
| AUTH-05 | Missing auth on GET /payment_intents | GET | /payment_intents | 401 |
| AUTH-06 | Missing auth on POST /refunds | POST | /refunds | 401 |
| AUTH-07 | Basic auth instead of Bearer | GET | /customers | 401 |
| AUTH-08 | API key without Bearer prefix | GET | /customers | 401 |
| AUTH-09 | Empty Authorization header | GET | /customers | 401 |
| HDR-01 | JSON body instead of form-encoded | POST | /payment_intents | 400, Stripe rejects JSON encoding |

## 17. Security Tests – Injection Payloads

| # | Test Case | Method | Endpoint | Expected Result |
|---|-----------|--------|----------|-----------------|
| SEC-01 | SQL injection in customer name | POST | /customers | 200, payload stored literally, not executed |
| SEC-02 | XSS payload in customer name | POST | /customers | 200, `<script>` stored literally |
| SEC-03 | Path traversal in resource ID | GET | /customers/{id} | 404, no server file exposure |
| SEC-04 | Null byte injection in customer name | POST | /customers | Safely handled (200 or 400) |
| SEC-05 | HTML entity injection in description | POST | /customers | 200, stored literally |
| SEC-06 | SQL injection in PI description | POST | /payment_intents | 200, stored literally |
| SEC-07 | XSS in PI metadata values | POST | /payment_intents | 200, stored literally |
| SEC-08 | XSS in customer metadata values | POST | /customers | 200, stored literally |

## 18. Security Tests – Security Headers

| # | Test Case | Method | Endpoint | Expected Result |
|---|-----------|--------|----------|-----------------|
| SEC-09 | Strict-Transport-Security header present | GET | /customers | HSTS header with max-age |
| SEC-10 | X-Content-Type-Options header check | GET | /customers | `nosniff` if present; documented finding if absent |
| SEC-11 | Cache-Control prevents caching | GET | /customers | Contains no-cache, no-store, or must-revalidate |
| SEC-12 | Stripe-Version header returned | GET | /customers | Non-empty version string |

## 19. Security Tests – HTTP Method Validation

| # | Test Case | Method | Endpoint | Expected Result |
|---|-----------|--------|----------|-----------------|
| SEC-13 | PUT to /customers rejected | PUT | /customers | 405, 404, or 400 |
| SEC-14 | PATCH to /payment_intents rejected | PATCH | /payment_intents | 405, 404, 403, or 400 |
| SEC-15 | HEAD to /customers returns headers only | HEAD | /customers | 200, empty body, Content-Type present |

## 20. Security Tests – Content Negotiation

| # | Test Case | Method | Endpoint | Expected Result |
|---|-----------|--------|----------|-----------------|
| SEC-16 | Accept: text/xml still returns JSON | GET | /customers | 200, Content-Type is application/json |
| SEC-17 | Empty Content-Type handled | POST | /customers | 200 or clear error (400/415) |

## 21. Security Tests – Idempotency Edge Cases

| # | Test Case | Method | Endpoint | Expected Result |
|---|-----------|--------|----------|-----------------|
| SEC-18 | Same idempotency key with different payload | POST | /payment_intents | 400 conflict or original cached response |
| SEC-19 | Very long idempotency key (>255 chars) | POST | /payment_intents | 200 or 400 |
| SEC-20 | Empty string idempotency key | POST | /payment_intents | 200 or 400 |

## 22. Security Tests – CORS & HTTP Method Edge Cases

| # | Test Case | Method | Endpoint | Expected Result |
|---|-----------|--------|----------|-----------------|
| SEC-21 | OPTIONS preflight request | OPTIONS | /customers | 200/204/400/405 |
| SEC-22 | DELETE PaymentIntent rejected | DELETE | /payment_intents/{id} | 405, 404, or 400 |

## 23. Cross-Resource Integration – Customer & PaymentIntent

| # | Test Case | Flow | Expected Result |
|---|-----------|------|-----------------|
| XR-01 | Create PI with non-existent customer | POST /payment_intents with fake customer | 400 error |
| XR-02 | Create PI with deleted customer | Delete customer, then create PI | 400 error |
| XR-03 | Multiple PIs for same customer | Create 2 PIs for 1 customer | Independent PIs, different IDs, same customer |
| XR-04 | Delete customer, PI unaffected | Delete customer with active PI | PI still fetchable, status unchanged |
| XR-05 | Cancel PI, customer unchanged | Cancel PI linked to customer | Customer name/email intact |
| XR-06 | Metadata independence | Customer metadata vs PI metadata | Each resource's metadata is independent |

## 24. Cross-Resource Integration – Resource Lifecycle

| # | Test Case | Flow | Expected Result |
|---|-----------|------|-----------------|
| XR-07 | Full customer CRUD lifecycle | Create → Read → Update → Delete → Verify gone | All transitions correct, deleted=true at end |
| XR-08 | Full PI lifecycle | Create → Confirm → Capture → Fetch | Status transitions through all states correctly |
| XR-09 | Update deleted customer | Delete then update | Returns deleted=true or error |
| XR-10 | Cancel already-canceled PI | Cancel, then cancel again | 400 error |

## 25. Cross-Resource Integration – Refund E2E with Customer

| # | Test Case | Flow | Expected Result |
|---|-----------|------|-----------------|
| XR-11 | Full refund E2E with customer | Create Customer → Create PI → Confirm → Refund → Verify customer unaffected | Refund succeeds, customer unchanged |
| XR-12 | Multi-currency E2E | Create customer, PIs in USD/EUR/GBP/JPY, confirm each | All currencies succeed |

## 26. Refunds API – Positive Tests

| # | Test Case | Method | Endpoint | Expected Result |
|---|-----------|--------|----------|-----------------|
| R-01 | Full refund of succeeded PI | POST | /refunds | 200, amount matches original, status=succeeded |
| R-02 | Partial refund | POST | /refunds | 200, amount matches requested partial |
| R-03 | Multiple partial refunds | POST | /refunds | Each refund independent, different IDs |
| R-04 | Retrieve refund by ID | GET | /refunds/{id} | 200, details match creation |
| R-05 | Refund response time | POST | /refunds | < 5 seconds |
| R-06 | Refund response headers | POST | /refunds | Proper headers present |

## 27. Refunds API – Negative Tests

| # | Test Case | Method | Endpoint | Expected Result |
|---|-----------|--------|----------|-----------------|
| R-07 | Refund exceeds captured amount | POST | /refunds | 400 error |
| R-08 | Refund uncaptured PI | POST | /refunds | 400 error |
| R-09 | Double full refund | POST | /refunds | Second refund returns 400 |
| R-10 | Refund non-existent PI | POST | /refunds | 400/404 error |
| R-11 | Refund canceled PI | POST | /refunds | 400 error |

## 28. Refunds API – Lifecycle

| # | Test Case | Flow | Expected Result |
|---|-----------|------|-----------------|
| R-12 | Full refund lifecycle | Create PI → Confirm → Refund → Verify PI status | PI reflects refund |
| R-13 | Partial then remaining refund | Partial refund, then remaining, then try more | Third refund fails (400) |

## 29. Refunds API – List & Filter

| # | Test Case | Method | Endpoint | Expected Result |
|---|-----------|--------|----------|-----------------|
| R-14 | List refunds with limit | GET | /refunds?limit=5 | 200, list object, ≤5 items |
| R-15 | List refunds filtered by payment_intent | GET | /refunds?payment_intent={id} | All results match PI |

## 30. Refunds API – Reason, Metadata & Idempotency

| # | Test Case | Method | Endpoint | Expected Result |
|---|-----------|--------|----------|-----------------|
| R-16 | Refund with reason=duplicate | POST | /refunds | 200, reason stored |
| R-17 | Refund with reason=fraudulent | POST | /refunds | 200, reason stored |
| R-18 | Refund with reason=requested_by_customer | POST | /refunds | 200, reason stored |
| R-19 | Refund with metadata | POST | /refunds | 200, metadata persisted |
| R-20 | Refund with amount=0 | POST | /refunds | 400 rejected |
| R-21 | Refund idempotency | POST | /refunds | Same key returns same refund ID |

## 31. Data Integrity – Response Field Completeness

| # | Test Case | Method | Endpoint | Expected Result |
|---|-----------|--------|----------|-----------------|
| DI-01 | Customer has all required fields | POST | /customers | id, object, created, livemode present |
| DI-02 | PI has all required fields | POST | /payment_intents | id, object, amount, currency, status present |
| DI-03 | Customer list contains only customer objects | GET | /customers | All items have object=customer |
| DI-04 | PI list contains only payment_intent objects | GET | /payment_intents | All items have object=payment_intent |

## 32. Data Integrity – Encoding & Internationalization

| # | Test Case | Method | Endpoint | Expected Result |
|---|-----------|--------|----------|-----------------|
| DI-05 | Emoji in customer name | POST | /customers | 200, emoji stored correctly |
| DI-06 | CJK characters in name | POST | /customers | 200, characters preserved |
| DI-07 | Arabic/RTL text in name | POST | /customers | 200, text stored correctly |
| DI-08 | Mixed-script name | POST | /customers | 200, all scripts preserved |

## 33. Data Integrity – Consistency & Versioning

| # | Test Case | Method | Endpoint | Expected Result |
|---|-----------|--------|----------|-----------------|
| DI-09 | Create and retrieve consistency (Customer) | POST+GET | /customers | Retrieved data matches creation |
| DI-10 | Create and retrieve consistency (PI) | POST+GET | /payment_intents | Retrieved data matches creation |
| DI-11 | Update preserves unchanged fields | POST+GET | /customers/{id} | Only specified field changes |
| DI-12 | Stripe-Version header present | GET | /customers | API version header in response |
| DI-13 | Expand[] parameter on PI (customer) | GET | /payment_intents/{id}?expand[]=customer | Expanded customer object returned |

## 34. Data Integrity – Error Message Quality

| # | Test Case | Method | Endpoint | Expected Result |
|---|-----------|--------|----------|-----------------|
| DI-14 | Error type is machine-readable | POST | /payment_intents | error.type is a known type string |
| DI-15 | Error message is human-readable | POST | /payment_intents | error.message is non-empty, descriptive |
| DI-16 | Error includes param for field errors | POST | /payment_intents | error.param identifies the problematic field |

## 35. Data Integrity – Metadata Edge Cases

| # | Test Case | Method | Endpoint | Expected Result |
|---|-----------|--------|----------|-----------------|
| DI-17 | Empty metadata object on create | POST | /customers | 200, metadata is empty dict |
| DI-18 | Long metadata value (500 chars) | POST | /customers | 200, full value stored |
| DI-19 | Many metadata keys (20) | POST | /customers | 200, all 20 keys persisted |
| DI-20 | Special characters in metadata key | POST | /customers | 200, key stored correctly |

## 36. Rate Limit & Resilience

| # | Test Case | Method | Endpoint | Expected Result |
|---|-----------|--------|----------|-----------------|
| RL-01 | 10 rapid sequential requests | POST | /customers | All succeed (200) |
| RL-02 | 10 rapid sequential PI requests | POST | /payment_intents | All succeed (200) |
| RL-03 | 5 concurrent customer creates | POST | /customers | All succeed, unique IDs |
| RL-04 | 5 concurrent PI creates | POST | /payment_intents | All succeed, unique IDs |
| RL-05 | Rate limit detection (429 handling) | GET | /customers | Framework handles 429 gracefully |
| RL-06 | Retry-After header parsing | GET | /customers | Retry logic respects header |
| RL-07 | Confirm with AMEX card | POST | /payment_intents/{id}/confirm | 200, status=succeeded |
| RL-08 | Confirm with Discover card | POST | /payment_intents/{id}/confirm | 200, status=succeeded |

## 37. PaymentIntent – Zero-Decimal Currency & Description

| # | Test Case | Method | Endpoint | Expected Result |
|---|-----------|--------|----------|-----------------|
| PZ-01 | JPY zero-decimal currency | POST | /payment_intents | 200, amount=500 means 500 yen |
| PZ-02 | Create PI with description | POST | /payment_intents | 200, description field persisted |
| PZ-03 | Cancel with cancellation_reason | POST | /payment_intents/{id}/cancel | 200, cancellation_reason echoed |

## 38. PaymentIntent – List & Search

| # | Test Case | Method | Endpoint | Expected Result |
|---|-----------|--------|----------|-----------------|
| PL-01 | List payment intents with limit | GET | /payment_intents?limit=3 | 200, list schema valid, ≤3 items |
| PL-02 | Paginate payment intents | GET | /payment_intents?starting_after={id} | Different PI on next page |
| PL-03 | List returns only payment_intent objects | GET | /payment_intents | All items have object=payment_intent |
| PL-04 | List PIs filtered by customer | GET | /payment_intents?customer={id} | All results match customer |
| PL-05 | List PI response time | GET | /payment_intents | < 5 seconds |

## 39. PaymentIntent – Metadata & Update

| # | Test Case | Method | Endpoint | Expected Result |
|---|-----------|--------|----------|-----------------|
| PM-01 | Create PI with metadata | POST | /payment_intents | 200, metadata key-values persisted |
| PM-02 | Update PI metadata | POST | /payment_intents/{id} | 200, metadata values updated |
| PM-03 | Update PI amount | POST | /payment_intents/{id} | 200, amount changed |
| PM-04 | Update PI description | POST | /payment_intents/{id} | 200, description updated |
| PM-05 | Update currency on unconfirmed PI | POST | /payment_intents/{id} | 200, currency changed |
| PM-06 | Retrieve canceled PI full state | GET | /payment_intents/{id} | status=canceled, schema valid |

## 40. PaymentIntent – Cancellation Reasons

| # | Test Case | Method | Endpoint | Expected Result |
|---|-----------|--------|----------|-----------------|
| PC-01 | Cancel with reason=duplicate | POST | /payment_intents/{id}/cancel | 200, cancellation_reason echoed |
| PC-02 | Cancel with reason=fraudulent | POST | /payment_intents/{id}/cancel | 200, cancellation_reason echoed |
| PC-03 | Cancel with reason=requested_by_customer | POST | /payment_intents/{id}/cancel | 200, cancellation_reason echoed |
| PC-04 | Cancel with reason=abandoned | POST | /payment_intents/{id}/cancel | 200, cancellation_reason echoed |

## 41. PaymentIntent – Charge & Receipt Verification

| # | Test Case | Method | Endpoint | Expected Result |
|---|-----------|--------|----------|-----------------|
| CR-01 | latest_charge populated after successful payment | GET | /payment_intents/{id} | `latest_charge` starts with `ch_` |
| CR-02 | Expand charges — verify charge details | GET | /payment_intents/{id}?expand[]=latest_charge | Charge object: amount, currency, paid=true, status=succeeded |
| CR-03 | Receipt URL generated after payment | GET | /payment_intents/{id}?expand[]=latest_charge | `receipt_url` starts with `https://`, `receipt_email` matches |
| CR-04 | Payment method details — card brand & last4 | GET | /payment_intents/{id}?expand[]=latest_charge | `payment_method_details.card.brand=visa`, `last4` is 4 digits, exp_month/year present |
| CR-05 | Manual capture — charge not captured until capture() | GET | /payment_intents/{id}?expand[]=latest_charge | `captured=false` before capture, `captured=true` after |
| CR-06 | Declined payment — no succeeded charge | GET | /payment_intents/{id}?expand[]=latest_charge | PI status != succeeded, charge status = failed |

---

**Total: 236 tests across 9 test modules**
