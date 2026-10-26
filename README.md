# TradeLife

TradeLife is an editable Django starter app for small businesses. It brings together customer records, quotations, invoices, payment records, expenses, a simple cash-flow estimate, business-readiness guidance and sample market opportunities.

This is a learning and hackathon prototype. It is not connected to a bank, payment gateway, company-registration service or live procurement platform. Opportunity listings and sample figures are illustrative. Do not enter real identity, bank or payment-card information.

## What is included

- Sign up, sign in and sign out
- One private business workspace per user
- Dashboard with sales, unpaid invoices, expenses and a 30-day cash estimate
- Customers
- Quotations and conversion of a quotation into an invoice
- Printable quotation and invoice views (use the browser's Print / Save as PDF command)
- Invoices and partial or full payment recording
- Expenses
- Readiness checklist with explanations
- Sample market opportunities with requirements and matching guidance
- Django admin for inspecting and editing records
- Dockerfile and a small automated test suite

## Run locally on Windows

Open PowerShell in the `tradelife` folder and run:

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python manage.py migrate
python manage.py seed_demo
python manage.py runserver
```

Open `http://127.0.0.1:8000/` in your browser. The demo account is `demo` with password `TradeLifeDemo123!`. Change or remove that account before sharing the app.

If PowerShell blocks virtual-environment activation, run the commands using `.\.venv\Scripts\python.exe` instead. For example:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe manage.py migrate
.\.venv\Scripts\python.exe manage.py seed_demo
.\.venv\Scripts\python.exe manage.py runserver
```

## Run on macOS or Linux

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python manage.py migrate
python manage.py seed_demo
python manage.py runserver
```

## Main code locations

- `core/models.py`: database tables and business rules
- `core/forms.py`: input fields and validation
- `core/views.py`: pages and actions
- `core/services.py`: cash estimate, readiness and dashboard calculations
- `core/urls.py`: page addresses
- `core/templates/`: HTML screens
- `core/static/core/style.css`: visual styling
- `core/management/commands/seed_demo.py`: sample data
- `core/tests.py`: workflow checks

## Important design notes

- The starter uses SQLite so it runs without a database server. For a hosted or multi-user production system, use PostgreSQL and review security, privacy, backups, monitoring and deployment settings.
- Payment entries are records only. They do not move money.
- Cash-flow figures are estimates based on unpaid invoice balances due in the next 30 days and unpaid expenses due in the next 30 days. They do not include unrecorded activity.
- Readiness is a transparent checklist, not a credit score or guarantee of funding or procurement access.
- This project uses Django's standard session authentication and CSRF protection. Production deployment must use HTTPS, a private secret key, secure cookies, a proper application server and restricted allowed hosts.

## Run the checks

```bash
python manage.py test
python manage.py check
```

## Suggested manual improvement order

1. Change the business profile fields and layout to fit your target user.
2. Add line items to quotations and invoices.
3. Add a real opportunity source and show its requirements and closing date.
4. Improve the forecast with recurring expenses and scenario inputs.
5. Add PostgreSQL, deployment, audit logging and role permissions before using real business data.
