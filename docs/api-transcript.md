# Captured API transcript

Recorded against `manage.py runserver 127.0.0.1:8730` with SQLite, seeded with
one user (`demo`) and one OAuth2 Application (`GreetingApi Client`).
Every block below is the literal stdout of the command above it.

## 1. Health check — no token required

```console
$ curl -s -i http://127.0.0.1:8730/healthz
HTTP/1.1 200 OK
Date: Fri, 25 Sep 2026 10:54:43 GMT
Server: WSGIServer/0.2 CPython/3.12.6
Content-Type: application/json
X-Frame-Options: DENY
Content-Length: 34
X-Content-Type-Options: nosniff
Referrer-Policy: same-origin
Cross-Origin-Opener-Policy: same-origin

{"status": "ok", "database": "ok"}
```

## 2. The greeting endpoint refuses an unauthenticated request

```console
$ curl -s -i -X POST http://127.0.0.1:8730/greeting -H 'Content-Type: application/json' -d '{"greeting": "Hello"}'
HTTP/1.1 403 Forbidden
Date: Fri, 25 Sep 2026 10:54:43 GMT
Server: WSGIServer/0.2 CPython/3.12.6
Content-Type: application/json
X-Frame-Options: DENY
Content-Length: 45
X-Content-Type-Options: nosniff
Referrer-Policy: same-origin
Cross-Origin-Opener-Policy: same-origin

{"error": "A valid bearer token is required"}
```

## 3. Sign in with the wrong password

```console
$ curl -s -i -X POST http://127.0.0.1:8730/signin -H 'Content-Type: application/json' -d '{"username": "demo", "password": "wrong"}'
HTTP/1.1 400 Bad Request
Date: Fri, 25 Sep 2026 10:54:43 GMT
Server: WSGIServer/0.2 CPython/3.12.6
Content-Type: application/json
X-Frame-Options: DENY
Content-Length: 38
X-Content-Type-Options: nosniff
Referrer-Policy: same-origin
Cross-Origin-Opener-Policy: same-origin

{"error": "User did not authenticate"}
```

## 4. Sign in successfully and receive a bearer token

```console
$ curl -s -X POST http://127.0.0.1:8730/signin -H 'Content-Type: application/json' -d '{"username": "demo", "password": "demo-pass-9876"}'
{"access_token": "JbQuC0nBzdCxKvn1cfUecS7IYfV2hF"}
```

## 5. Greet with "Hello" — the documented special case

```console
$ TOKEN=$(...)   # from step 4
$ curl -s -X POST http://127.0.0.1:8730/greeting -H "Authorization: Bearer $TOKEN" -H 'Content-Type: application/json' -d '{"greeting": "Hello"}'
{"message": "Goodbye!"}
```

## 6. Any other greeting

```console
$ curl -s -X POST http://127.0.0.1:8730/greeting -H "Authorization: Bearer $TOKEN" -H 'Content-Type: application/json' -d '{"greeting": "good morning"}'
{"message": "Greeting received!"}
```

## 7. Matching ignores case and surrounding whitespace

```console
$ curl -s -X POST http://127.0.0.1:8730/greeting -H "Authorization: Bearer $TOKEN" -H 'Content-Type: application/json' -d '{"greeting": "  HELLO  "}'
{"message": "Goodbye!"}
```

## 8. Validation errors

```console
$ curl -s -X POST http://127.0.0.1:8730/greeting -H "Authorization: Bearer $TOKEN" -H 'Content-Type: application/json' -d 'not json'
{"error": "Invalid JSON data"}
$ curl -s -X POST http://127.0.0.1:8730/greeting -H "Authorization: Bearer $TOKEN" -H 'Content-Type: application/json' -d '{}'
{"error": "Field 'greeting' must be a non-empty string"}
$ curl -s -X POST http://127.0.0.1:8730/greeting -H "Authorization: Bearer $TOKEN" -H 'Content-Type: application/json' -d '[1, 2]'
{"error": "Invalid JSON data"}
$ curl -s -X GET http://127.0.0.1:8730/greeting -H "Authorization: Bearer $TOKEN"
{"error": "Only POST requests are allowed"}
```

## 9. What was persisted

```console
$ python manage.py shell -c "from core.models import Greeting; [print(g.created_at.isoformat(), repr(g.greeting)) for g in Greeting.objects.all()]"
2026-09-25T10:54:43.936472+00:00 '  HELLO  '
2026-09-25T10:54:43.923457+00:00 'good morning'
2026-09-25T10:54:43.907239+00:00 'Hello'
```
