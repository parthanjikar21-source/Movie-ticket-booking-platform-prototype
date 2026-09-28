# CineBook — Django Cinema Ticket Booking

CineBook is a production-oriented Django movie-ticket platform using Django templates, PostgreSQL, Razorpay, Redis/Celery, ReportLab, QR codes and S3-compatible persistent storage. The web application is structured for direct GitHub-to-Vercel deployment using Vercel's current zero-configuration Django support.

## Features

- User registration, login, logout, password reset and profile editing
- Movie, genre, language, cast, gallery, trailer and certification management through Django Admin
- Theater, screen, seat, show and price management
- Movie discovery, search, filters, sorting and pagination
- Genre/language/history-based recommendations foundation and popular fallback
- Verified-viewer reviews with one review per user/movie and reporting
- Server-authoritative seat availability
- Two-minute seat holds with database row locking and expiry cleanup
- Concurrent booking protection using `transaction.atomic()` and `select_for_update()`
- Razorpay order creation, payment-signature verification and webhook verification
- Idempotent payment/webhook processing
- PDF tickets with QR verification
- Celery email delivery with automatic retries
- Staff dashboard with revenue, trends, occupancy, theater/movie performance, cancellations, refunds and CSV export
- PostgreSQL-ready schema with indexes and constraints
- S3-compatible persistent media storage for production
- Automated tests covering authentication, discovery, reviews, seat locking, payment failure/webhooks, ownership, PDF tickets and staff access

## Requirements

- Python 3.12 or 3.13
- PostgreSQL
- Redis
- A Razorpay account for payments
- SMTP email provider for production ticket/password emails
- S3-compatible object storage for production media/files
- Vercel account for the Django web deployment
- A separate Celery worker environment for background jobs

Vercel currently provides first-class/zero-configuration Django deployment and detects the Django `manage.py`/WSGI structure. Do not add an old-style `/api` Django wrapper or redirect configuration just to make this project work on Vercel. Static files are served through Vercel's deployment/CDN integration. 

## Project layout

```text
config/          Django project, settings, WSGI, ASGI and Celery
accounts/        Authentication and profiles
movies/          Movies, cast, reviews and discovery
theaters/        Cities, theaters, screens, seats and shows
bookings/        Seat state, bookings and seat locking
payments/        Razorpay orders, verification and webhook
tickets/         PDF/QR tickets and email task
dashboard/       Staff analytics and CSV export
templates/       Django templates
static/          CSS and JavaScript
media/           Local-development media location; ignored by Git
manage.py
requirements.txt
pyproject.toml
.env.example
.gitignore
README.md
```

## Local setup

Create a virtual environment:

```bash
python -m venv .venv
```

Activate it on macOS/Linux:

```bash
source .venv/bin/activate
```

On Windows PowerShell:

```powershell
.venv\Scripts\Activate.ps1
```

Install dependencies:

```bash
pip install -r requirements.txt
```

Copy the environment template:

```bash
cp .env.example .env
```

For local development, set `DEBUG=True` in `.env` and use a local `DATABASE_URL` or omit it to use SQLite. Never commit `.env`.

## PostgreSQL setup

Create a PostgreSQL database and user, then set `DATABASE_URL` in `.env`:

```text
DATABASE_URL=postgresql://user:password@host:5432/cinema
```

Production requires PostgreSQL through `DATABASE_URL`. SQLite is only a local-development fallback when `DEBUG=True` and `DATABASE_URL` is absent; production settings fail fast if `DATABASE_URL` is missing.

Run migrations:

```bash
python manage.py migrate
```

Create an admin user:

```bash
python manage.py createsuperuser
```

Run the local server:

```bash
python manage.py runserver
```

Optional sample data:

```bash
python manage.py seed_data
```

The seed command creates fictional movies, a sample Pune theater, screens, seats and shows. It contains no credentials.

## Environment variables

`.env.example` contains the complete variable set used by the application. Important production variables are:

- `DJANGO_SECRET_KEY`
- `DEBUG`
- `DATABASE_URL`
- `ALLOWED_HOSTS`
- `CSRF_TRUSTED_ORIGINS`
- `RAZORPAY_KEY_ID`
- `RAZORPAY_KEY_SECRET`
- `RAZORPAY_WEBHOOK_SECRET`
- `REDIS_URL`
- `EMAIL_HOST`
- `EMAIL_PORT`
- `EMAIL_HOST_USER`
- `EMAIL_HOST_PASSWORD`
- `EMAIL_USE_TLS`
- `DEFAULT_FROM_EMAIL`
- `AWS_ACCESS_KEY_ID`
- `AWS_SECRET_ACCESS_KEY`
- `AWS_STORAGE_BUCKET_NAME`
- `AWS_S3_REGION_NAME`
- `AWS_S3_ENDPOINT_URL`
- `AWS_S3_CUSTOM_DOMAIN`

Set `DEBUG=False` in production. `ALLOWED_HOSTS` is a comma-separated list. `CSRF_TRUSTED_ORIGINS` is a comma-separated list of complete origins including `https://`.

## Static files

Run:

```bash
python manage.py collectstatic --noinput
```

The project uses Django's staticfiles system with WhiteNoise's compressed manifest storage. Vercel's current Django support also handles static assets through its deployment/CDN layer.

## Media and persistent storage

Do not rely on Vercel's local filesystem for persistent uploads. When `AWS_STORAGE_BUCKET_NAME` is configured, Django uses `django-storages` with S3-compatible storage for movie posters, cast images, profile avatars and ticket PDFs.

For AWS S3, provide the AWS access key, secret, bucket and region. For another S3-compatible provider, also set `AWS_S3_ENDPOINT_URL` and use the provider's credentials/bucket.

For local development without an S3 bucket, files are stored under `media/`, which is intentionally ignored by Git.

## Redis and Celery

Start Redis locally with your installed Redis service or Docker. The Django application reads the broker URL from `REDIS_URL`.

Run a Celery worker:

```bash
celery -A config worker -l INFO
```

Run Celery Beat for automatic two-minute hold cleanup:

```bash
celery -A config beat -l INFO
```

A production deployment should run the Celery worker and Beat separately from Vercel. Vercel functions are not intended to be a permanent Celery worker process.

The cleanup task is defensive: booking attempts also release expired holds before checking seats, so correctness does not depend exclusively on Beat being available.

## Email

Configure SMTP in `.env`:

```text
EMAIL_HOST=smtp.example.com
EMAIL_PORT=587
EMAIL_HOST_USER=replace-me
EMAIL_HOST_PASSWORD=replace-me
EMAIL_USE_TLS=True
DEFAULT_FROM_EMAIL=Cinema <noreply@example.com>
```

Ticket email is dispatched through Celery and retries on failure. Password reset uses Django's email system.

## Razorpay

Create Razorpay API credentials and set:

```text
RAZORPAY_KEY_ID=...
RAZORPAY_KEY_SECRET=...
RAZORPAY_WEBHOOK_SECRET=...
```

The browser receives only the public key ID. The secret remains server-side.

The payment flow is:

1. User selects seats.
2. Server locks the selected `ShowSeat` rows inside a database transaction.
3. Server creates a pending booking and two-minute hold.
4. Server creates a Razorpay order.
5. Razorpay Checkout handles payment.
6. The callback sends payment IDs/signature to Django.
7. Django verifies the Razorpay signature server-side.
8. Django locks the booking and its show seats again.
9. Django re-checks that the hold is still valid.
10. Only then are seats changed to `booked` and the booking becomes `confirmed`.

The application does not treat a client-side success message as proof of payment.

## Razorpay webhook

After deployment, configure Razorpay's webhook to:

```text
https://YOUR-VERCEL-DOMAIN/payments/webhook/razorpay/
```

Use the same value configured as `RAZORPAY_WEBHOOK_SECRET` in Vercel. Razorpay webhook signatures are verified using the raw request body. Event IDs are stored uniquely so duplicate webhook deliveries are safe.

Only payment-captured events finalize a booking. Failed payment events release the held seats.

## Seat locking and concurrency

`ShowSeat` is the authoritative availability record for every seat/show combination. A hold stores the user, booking token and expiry timestamp.

Booking code uses:

- `transaction.atomic()` for the complete seat allocation transaction
- `select_for_update()` on the selected `ShowSeat` rows
- a unique `(show, seat)` database constraint
- server-side revalidation immediately before confirmation
- status transitions from `available` → `held` → `booked`

The browser's seat display is only a convenience UI. It is never trusted for the final booking decision.

## Tests

Run the Django test suite with:

```bash
python manage.py test
```

The concurrency test uses database transactions and is intended for a transactional production database such as PostgreSQL. Run the full suite against PostgreSQL before production deployment.

## Django Admin

Open:

```text
/admin/
```

Create a production administrator against the production database with:

```bash
python manage.py createsuperuser
```

Do not put administrator credentials in source code or environment templates.

## Production database migrations

The repository contains migrations. Against the production database run:

```bash
python manage.py migrate
```

Do this using the production `DATABASE_URL`.

For Vercel, run migrations from a trusted deployment/admin environment rather than expecting a long-running migration process inside a request. The deployment itself does not need a custom `vercel.json` wrapper for Django.

## Vercel deployment

This project intentionally follows Vercel's current Django zero-configuration deployment model. Vercel recognizes the Django project from `manage.py` and the WSGI entrypoint; no `/api` directory or legacy redirect `vercel.json` is required.

### Deployment sequence

1. Put this repository directly into GitHub.
2. Import the GitHub repository into Vercel.
3. Let Vercel detect Django/Python from the repository.
4. Add production environment variables under **Vercel Dashboard → Project → Settings → Environment Variables**.
5. Set `DJANGO_SECRET_KEY` to a newly generated production secret.
6. Set `DEBUG=False`.
7. Set the production PostgreSQL `DATABASE_URL`.
8. Set `ALLOWED_HOSTS` to the Vercel hostname(s), for example `.vercel.app` plus any custom domain.
9. Set `CSRF_TRUSTED_ORIGINS` to the exact HTTPS origins, for example `https://your-project.vercel.app`.
10. Add Razorpay production credentials and webhook secret.
11. Add the Redis URL used by your separately hosted Celery infrastructure.
12. Add SMTP credentials.
13. Add S3-compatible storage credentials and bucket details.
14. Deploy.
15. Run production migrations against the production PostgreSQL database:

```bash
python manage.py migrate
```

16. Create the production superuser against that PostgreSQL database:

```bash
python manage.py createsuperuser
```

17. Configure the Razorpay webhook to the deployed HTTPS URL.
18. Start the separate Celery worker and Celery Beat using the same production environment variables.
19. Verify media uploads, ticket PDF downloads, email delivery and payment webhooks.

### Production environment checklist

```text
DJANGO_SECRET_KEY=<real production secret>
DEBUG=False
DATABASE_URL=<production PostgreSQL URL>
ALLOWED_HOSTS=.vercel.app,<your-custom-domain>
CSRF_TRUSTED_ORIGINS=https://<your-vercel-domain>,https://<your-custom-domain>
RAZORPAY_KEY_ID=<production public key>
RAZORPAY_KEY_SECRET=<production secret>
RAZORPAY_WEBHOOK_SECRET=<webhook secret>
REDIS_URL=<managed Redis URL>
EMAIL_HOST=<SMTP host>
EMAIL_PORT=587
EMAIL_HOST_USER=<SMTP user>
EMAIL_HOST_PASSWORD=<SMTP password>
EMAIL_USE_TLS=True
DEFAULT_FROM_EMAIL=<verified sender>
AWS_ACCESS_KEY_ID=<storage key>
AWS_SECRET_ACCESS_KEY=<storage secret>
AWS_STORAGE_BUCKET_NAME=<bucket>
AWS_S3_REGION_NAME=<region>
AWS_S3_ENDPOINT_URL=<optional S3-compatible endpoint>
AWS_S3_CUSTOM_DOMAIN=<optional CDN/domain>
```

Do not copy the example values into production unless they are genuinely correct for your providers.

## GitHub safety

Before pushing, verify:

```bash
git status
```

`.gitignore` excludes `.env`, generated Python files, SQLite databases, media, static build output, virtual environments, IDE files, Vercel local metadata and other generated files.

Only `.env.example` belongs in Git. It contains placeholders and no credentials.

## Performance considerations

The booking and reporting paths use database-side filtering, aggregation, indexes, pagination and related-object loading. Dashboard reports use `Sum`, `Count` and date truncation rather than loading the entire booking table into Python. CSV export uses `iterator()` with a bounded chunk size.

Important indexes cover movie discovery, show schedules, booking ownership/status, show-seat state/expiry and payment state/reference fields. The intended 100,000+ booking workload should be run on PostgreSQL with appropriate managed database resources and connection limits.

## Production architecture

```text
Browser
   |
   v
Vercel Django application
   |       |       |
   |       |       +--> S3-compatible object storage
   |       +----------> Razorpay
   +------------------> PostgreSQL
   |
   +------------------> Redis <---- Celery worker / Celery Beat
```

Vercel hosts the request/response Django application. PostgreSQL, Redis, object storage, Razorpay and SMTP are external services. The Celery worker is intentionally separate because Vercel is not a permanent worker host.

## Known production requirements

- PostgreSQL must be provisioned and reachable from Vercel.
- Redis must be reachable from the Celery worker and Django request functions.
- A separate Celery worker and Beat process must be operated for asynchronous email and scheduled hold cleanup.
- Production uploads require S3-compatible persistent storage.
- Razorpay webhook configuration must point at the deployed HTTPS hostname.
- Production superuser creation and migrations must target the production `DATABASE_URL`.
- SMTP credentials and sender-domain requirements depend on the chosen email provider.
