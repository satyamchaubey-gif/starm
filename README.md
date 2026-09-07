# StarM

A platform-independent Flask application for connecting government departments
with startup solutions.

## Requirements

- Python 3.10 or newer
- `pip`

## Run locally

Create and activate a virtual environment using the command appropriate for
your operating system, then install the dependencies:

```text
python -m venv .venv
python -m pip install -r requirements.txt
```

Start the application:

```text
python app.py
```

The app is available at <http://127.0.0.1:5001>. The SQLite database is created
automatically on first run.

## Configuration

These environment variables are optional:

| Variable | Default | Purpose |
| --- | --- | --- |
| `APP_HOST` | `127.0.0.1` | Network interface for the development server |
| `APP_PORT` | `5001` | Development server port |
| `FLASK_DEBUG` | `0` | Set to `1` to enable Flask debug mode |
| `SECRET_KEY` | Development fallback | Secret used to sign sessions; set this in deployments |
| `COOKIE_SECURE` | `0` | Set to `1` when serving over HTTPS |
| `DATABASE_PATH` | `procure.db` beside `database.py` | SQLite database file location |
| `SMTP_HOST` | unset | SMTP server; when unset, the verification code is shown in the flash message for local development |
| `SMTP_PORT` | `587` | SMTP server port |
| `SMTP_FROM` | `no-reply@starm.local` | Sender address for verification emails |
| `SMTP_USERNAME` / `SMTP_PASSWORD` | unset | Optional SMTP credentials |
| `SMTP_PROVIDER` | unset | Set to `gmail` to default the host to `smtp.gmail.com` |
| `SMTP_USE_TLS` | `1` | Set to `0` to disable STARTTLS |

### Gmail setup

1. Enable 2-Step Verification on the sending Google account.
2. Create a Google App Password.
3. Export the variables from `.env.example` in your shell or configure them in your hosting provider.
4. Set `SMTP_USERNAME`, `SMTP_PASSWORD`, and `SMTP_FROM` to the sending account.
5. Restart the Flask application.

`SMTP_PASSWORD` must be the Google App Password. Never commit `.env` or share
the password in source control.

Environment variables use the same names on Windows, macOS, and Linux. For
production, use a production WSGI server rather than Flask's development
server.
