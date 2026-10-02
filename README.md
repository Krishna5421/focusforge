<div align="center">

<img src="https://capsule-render.vercel.app/api?type=waving&color=0:f5a524,100:ff7a45&height=200&section=header&text=FocusForge&fontSize=64&fontColor=17120a&fontAlignY=36&desc=Build%20better%20days,%20one%20session%20at%20a%20time&descSize=18&descAlignY=58&animation=fadeIn" alt="FocusForge banner" width="100%">

<a href="https://github.com/Krishna5421/focusforge">
  <img src="https://readme-typing-svg.demolab.com?font=Inter&weight=600&size=22&duration=2800&pause=900&color=F5A524&center=true&vCenter=true&width=620&lines=Tasks+%E2%80%A2+Habits+%E2%80%A2+Goals+%E2%80%A2+Focus+%E2%80%A2+Study;An+AI+coach+that+keeps+you+on+track;Streaks%2C+XP+and+achievements+that+motivate" alt="Typing animation: Tasks, Habits, Goals, Focus, Study">
</a>

<p>
  <img src="https://img.shields.io/badge/Python-3.14-3776AB?logo=python&logoColor=white" alt="Python 3.14">
  <img src="https://img.shields.io/badge/Django-6.0-092E20?logo=django&logoColor=white" alt="Django 6.0">
  <img src="https://img.shields.io/badge/DRF-3.17-A30000?logo=django&logoColor=white" alt="Django REST Framework">
  <img src="https://img.shields.io/badge/PostgreSQL-ready-4169E1?logo=postgresql&logoColor=white" alt="PostgreSQL">
  <a href="https://focusforge-z9hy.onrender.com"><img src="https://img.shields.io/badge/Deployed%20on-Render-46E3B7?logo=render&logoColor=white" alt="Deployed on Render"></a>
</p>

**FocusForge** is an all-in-one productivity workspace: plan tasks with due times, build habits with streaks,
break goals into milestones, run Pomodoro and study sessions, and ask an AI coach what to do next.

<a href="https://focusforge-z9hy.onrender.com">
  <img src="https://img.shields.io/badge/%E2%96%B6%20Live%20demo-focusforge--z9hy.onrender.com-f5a524?style=for-the-badge" alt="Open the live demo">
</a>

<sub>Hosted on Render's free tier: the first visit after a quiet period can take 30–50 seconds while the server wakes up.</sub>

</div>

---

## Table of contents

- [Why I built it](#why-i-built-it)
- [Features](#features)
- [Tech stack](#tech-stack)
- [How it works](#how-it-works)
- [Getting started](#getting-started)
- [Environment variables](#environment-variables)
- [Running tests](#running-tests)
- [Deployment on Render](#deployment-on-render)
- [REST API](#rest-api)
- [Project structure](#project-structure)

---

## Why I built it

My productivity was spread across too many apps: one for to-dos, another for habits, a timer for studying,
and notes for long-term goals. None of them talked to each other, so I never had one clear answer to the
question *"what should I work on right now?"*

FocusForge brings all of it into one place. Tasks, habits, goals, focus sessions, and study time share
the same data, so the dashboard, reminders, reports, and AI coach can see the whole picture. XP, streaks,
and achievements are there to make showing up every day feel rewarding, not like a chore.

---

## Features

| | Feature | What you get |
|---|---|---|
| ✅ | **Tasks** | Priorities, categories, tags, subtasks, repeating tasks, and an optional **due time**. Overdue tasks are highlighted, with filters for today, upcoming, and overdue. |
| ⏰ | **Smart reminders** | In-app pop-ups for tasks **due within the hour** and tasks that are **overdue**, plus a notification centre. |
| 🔁 | **Habits** | Daily habits, or weekly ones on chosen days, with current and longest streaks and a 7-day heatmap. |
| 🎯 | **Goals & milestones** | Deadlines, milestone checklists, and automatic progress percentages. |
| 🍅 | **Pomodoro focus** | A focus timer with a daily goal and a floating timer that keeps running while you move around the app. |
| 📚 | **Study sessions** | Timed sessions per subject, with file attachments and a study history. |
| 🏆 | **XP, levels & achievements** | 50+ achievements across focus, study, habits, tasks, and goals, with unlock pop-ups and progress for each one. |
| 🤖 | **AI assistant** | A FocusForge-focused coach (Groq) that reads your own tasks, habits, and goals. It answers general questions with "Add to FocusForge" suggestions and shows tables when they help. |
| 📊 | **Analytics & reports** | Dashboards and charts, plus a **weekly or monthly PDF report** with trends, an activity chart, habits, goals, and highlights. |
| 🔐 | **Accounts** | Sign in with **username or email**, **email verification** on sign-up, and password reset with 6-digit codes. |
| ✉️ | **Emails** | A branded HTML email with a plain-text version for verification, welcome, sign-in notices, password resets, and goal completions. |

---

## Tech stack

| Layer | Technology |
|---|---|
| Backend | Django 6, Django REST Framework, SimpleJWT, django-filter |
| Database | SQLite (local) · PostgreSQL via `DATABASE_URL` (production) |
| Frontend | Django templates, vanilla JavaScript, Bootstrap Icons, marked + DOMPurify for chat markdown |
| AI | Groq API (`openai/gpt-oss-20b`) |
| Email | Brevo transactional email API |
| Media & static | Cloudinary (uploads) · WhiteNoise (static files) |
| PDF | ReportLab |
| Hosting | Render (Gunicorn) |

---

## How it works

```mermaid
flowchart LR
    U[User] -->|browser| D[Django app]
    D --> DB[(PostgreSQL / SQLite)]
    D -->|AI coach| G[Groq API]
    D -->|verification, welcome, reset emails| B[Brevo]
    D -->|uploads| C[Cloudinary]
    D -->|PDF report| R[ReportLab]
    U -.->|polls every 30 s while the site is open| N[Toasts endpoint]
    N -->|due-soon / overdue / achievements| U
```

**Sign-up with email verification**

```mermaid
sequenceDiagram
    actor U as User
    participant F as FocusForge
    participant E as Brevo
    U->>F: Sign up (username, email, password)
    F->>F: Create account (inactive)
    F->>E: Send 6-digit code
    E-->>U: "482913 is your verification code"
    U->>F: Enter code on the Verify page
    F->>F: Activate account and log in
    F->>E: Send welcome email
```

> Reminders run **while the user is on the site** instead of on a background scheduler, so they work on Render's free tier, where the service sleeps when idle.

---

## Getting started

### Prerequisites

- Python **3.12+** (developed on 3.14)
- Git

### 1. Clone and install

```bash
git clone https://github.com/Krishna5421/focusforge.git
cd focusforge

python -m venv venv
# Windows
venv\Scripts\activate
# macOS / Linux
source venv/bin/activate

pip install -r requirements.txt
```

### 2. Configure environment

```bash
cp .env.example .env
```

Fill in at least `SECRET_KEY`, `DEBUG=True`, and the Cloudinary keys. See [Environment variables](#environment-variables) below.

### 3. Set up the database and run

```bash
python manage.py migrate
python manage.py collectstatic --noinput
python manage.py createsuperuser   # optional, for /admin
python manage.py runserver
```

Open **http://127.0.0.1:8000**, create an account, and enter the emailed code.

> **Tip:** without Brevo keys, the verification email cannot be sent. For local testing, create a user with `createsuperuser`; those accounts are active straight away.

---

## Environment variables

| Variable | Required | Description |
|---|:---:|---|
| `SECRET_KEY` | ✅ | Django secret key. |
| `DEBUG` | | `True` for local development. Defaults to `False`. |
| `DATABASE_URL` | | PostgreSQL URL. SQLite is used when empty. |
| `ALLOWED_HOSTS` / `CSRF_TRUSTED_ORIGINS` | | Extra hosts and origins (comma-separated). The Render hostname is added automatically. |
| `CLOUDINARY_CLOUD_NAME` / `CLOUDINARY_API_KEY` / `CLOUDINARY_API_SECRET` | ✅ | Storage for profile pictures and study files. |
| `GROQ_API_KEY` | | Enables the AI assistant. |
| `BREVO_API_KEY` / `BREVO_SENDER_EMAIL` / `BREVO_SENDER_NAME` | ✅ for sign-up | Transactional email. Required for sign-up verification. |
| `SITE_URL` | | Base URL used in email links. Falls back to `https://$RENDER_EXTERNAL_HOSTNAME` on Render. |
| `SECURE_SSL_REDIRECT`, `SESSION_COOKIE_SECURE`, `CSRF_COOKIE_SECURE`, `SECURE_HSTS_SECONDS` | | Production security settings. |

> For better email deliverability, send from **your own domain** and authenticate it in Brevo (SPF and DKIM) instead of using a free mailbox address.

---

## Running tests

```bash
python manage.py test
```

The suite has **95+ tests** covering tasks, habits, goals, reminders, achievements, the assistant (with a mocked AI client), PDF export, login, and email verification. Tests **never send real emails**.

> Run `python manage.py collectstatic` first. The test run uses the compressed static manifest, so it fails if new static files have not been collected.

---

## Deployment on Render

1. Create a **PostgreSQL** database and a **Web Service** from this repository.
2. **Build command:** `./build.sh`. It installs requirements, runs `collectstatic`, and runs `migrate`.
3. **Start command:** `gunicorn focusforge.wsgi:application`
4. Add the [environment variables](#environment-variables). Render sets `RENDER_EXTERNAL_HOSTNAME` automatically, which also configures `ALLOWED_HOSTS`, CSRF, and email links.

---

## REST API

JWT-authenticated JSON API under `/api/`:

| Endpoint | Purpose |
|---|---|
| `POST /api/auth/register/` | Create an account (inactive until the email is verified) |
| `POST /api/auth/verify-email/` · `/verify-email/resend/` | Confirm the 6-digit code / request a new one |
| `POST /api/auth/login/` · `/login/refresh/` | Get or refresh JWT tokens (username **or** email) |
| `GET /api/auth/me/` · `/api/auth/profile/` | Current user and profile |
| `/api/tasks/`, `/api/habits/`, `/api/goals/`, `/api/study-sessions/`, `/api/pomodoro-sessions/`, … | CRUD for each module |
| `POST /api/assistant/ask/` | Ask the AI coach (50 messages per day) |

---

## Project structure

```
focusforge/
├── accounts/        # Auth, profile, email verification, PDF reports
├── achievements/    # XP, levels, achievement catalog and unlock logic
├── assistant/       # Groq-powered AI coach with output safety checks
├── core/            # Dashboard, analytics, deadlines, error pages
├── goals/           # Goals and milestones
├── habits/          # Habits, logs, and streaks
├── notifications/   # In-app notifications, toasts, email delivery
├── pomodoro/        # Focus timer and sessions
├── study/           # Subjects, study sessions, and files
├── tasks/           # Tasks, categories, tags, and due reminders
├── templates/       # Django templates, including HTML and plain-text emails
├── static/          # CSS, JavaScript, and images
├── focusforge/      # Settings and root URLs
└── build.sh         # Render build script
```

---

<div align="center">

Made with ☕ and focus by **[Krishna5421](https://github.com/Krishna5421)**

<img src="https://capsule-render.vercel.app/api?type=waving&color=0:ff7a45,100:f5a524&height=110&section=footer&animation=fadeIn" alt="" width="100%">

</div>
