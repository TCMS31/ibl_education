# Proof the test suite can fail

A suite that always passes proves nothing. This is the output of
re-introducing three of the defects this uplift fixed, running the suite, then
restoring the fixes and running it again. Both blocks are literal output from
`python manage.py test`, filtered to the result lines.

The three re-introduced defects:

1. `core/services.authenticate_user` — back to `user.password == password`
   (plaintext compared against the stored hash).
2. `core/services.record_greeting` — back to `objects.create(...)` followed by
   a redundant `.save()`.
3. `core/http.parse_json_object` — the `isinstance(payload, dict)` guard
   removed, so a JSON scalar or array body raises `AttributeError`.

## With the three defects re-introduced

```console
ERROR: test_a_json_scalar_body_is_rejected_rather_than_crashing (core.tests.test_greeting_view.GreetingEndpointTests.test_a_json_scalar_body_is_rejected_rather_than_crashing)
ERROR: test_a_normally_created_user_can_authenticate (core.tests.test_services.AuthenticateUserTests.test_a_normally_created_user_can_authenticate)
ERROR: test_a_json_scalar_body_is_rejected_rather_than_crashing (core.tests.test_signin_view.SignInViewTests.test_a_json_scalar_body_is_rejected_rather_than_crashing) (body='"just-a-string"')
ERROR: test_a_json_scalar_body_is_rejected_rather_than_crashing (core.tests.test_signin_view.SignInViewTests.test_a_json_scalar_body_is_rejected_rather_than_crashing) (body='[1, 2]')
ERROR: test_a_json_scalar_body_is_rejected_rather_than_crashing (core.tests.test_signin_view.SignInViewTests.test_a_json_scalar_body_is_rejected_rather_than_crashing) (body='42')
ERROR: test_a_json_scalar_body_is_rejected_rather_than_crashing (core.tests.test_signin_view.SignInViewTests.test_a_json_scalar_body_is_rejected_rather_than_crashing) (body='null')
FAIL: test_sign_in_then_greet (core.tests.test_greeting_view.EndToEndJourneyTests.test_sign_in_then_greet)
FAIL: test_the_request_costs_a_token_lookup_and_one_insert (core.tests.test_greeting_view.GreetingEndpointTests.test_the_request_costs_a_token_lookup_and_one_insert)
FAIL: test_the_stored_hash_is_never_accepted_as_a_password (core.tests.test_services.AuthenticateUserTests.test_the_stored_hash_is_never_accepted_as_a_password)
FAIL: test_costs_a_single_insert (core.tests.test_services.RecordGreetingTests.test_costs_a_single_insert)
FAIL: test_valid_credentials_return_a_token (core.tests.test_signin_view.SignInViewTests.test_valid_credentials_return_a_token)
FAIL: test_returns_503_rather_than_an_unusable_token (core.tests.test_signin_view.SignInWithoutApplicationTests.test_returns_503_rather_than_an_unusable_token)
Ran 68 tests in 3.990s
FAILED (failures=6, errors=6)
```

## With the fixes restored

```console
Ran 68 tests in 4.655s
OK
```
