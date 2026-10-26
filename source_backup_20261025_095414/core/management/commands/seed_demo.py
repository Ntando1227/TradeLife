from datetime import timedelta
from decimal import Decimal
from django.contrib.auth.models import User
from django.core.management.base import BaseCommand
from django.utils import timezone
from core.models import Business, Customer, Quote, Invoice, Payment, Expense, Opportunity


class Command(BaseCommand):
    help = "Create a demo user, business records and illustrative opportunities."

    def handle(self, *args, **options):
        user, created = User.objects.get_or_create(username="demo", defaults={"email": "demo@example.com"})
        if created:
            user.set_password("TradeLifeDemo123!"); user.save()
        business, _ = Business.objects.get_or_create(owner=user, defaults={
            "name": "Lerato M. Kganya Catering", "sector": "Catering", "town": "Polokwane",
            "region": "Limpopo", "phone": "071 000 0000", "email": "lerato@example.com",
            "registration_status": "in_progress", "has_business_bank_account": True,
        })
        customer, _ = Customer.objects.get_or_create(business=business, name="Mahlako Community Centre", defaults={"contact_name": "Ms. Mokoena", "phone": "015 000 0000"})
        invoice, _ = Invoice.objects.get_or_create(business=business, reference="INV-DEMO-001", defaults={
            "customer": customer, "description": "Lunch catering for community workshop", "amount": Decimal("6800.00"),
            "issue_date": timezone.localdate() - timedelta(days=3), "due_date": timezone.localdate() + timedelta(days=12),
        })
        Payment.objects.get_or_create(business=business, invoice=invoice, reference="DEMO-PAY-001", defaults={"amount": Decimal("2500.00"), "method": "eft", "payment_date": timezone.localdate() - timedelta(days=1)})
        Expense.objects.get_or_create(business=business, description="Food ingredients for upcoming order", defaults={"category": "Stock and supplies", "amount": Decimal("2100.00"), "expense_date": timezone.localdate(), "due_date": timezone.localdate() + timedelta(days=5), "is_paid": False})
        Quote.objects.get_or_create(business=business, reference="Q-DEMO-001", defaults={"customer": customer, "description": "Catering for staff meeting", "amount": Decimal("4200.00"), "status": "accepted", "issue_date": timezone.localdate()})
        Opportunity.objects.get_or_create(title="Local supplier: community catering", organisation="Demo Local Procurement Office", defaults={
            "description": "Illustrative request for quotations for catering at community training sessions.",
            "sector": "Catering", "region": "Limpopo", "closing_date": timezone.localdate() + timedelta(days=21),
            "requirements": "Business profile\nRecent quotation or invoice\nSupplier and food safety details\nPrice proposal", "is_active": True,
        })
        Opportunity.objects.get_or_create(title="Youth enterprise growth support", organisation="Demo Enterprise Support Desk", defaults={
            "description": "Illustrative support opportunity for early-stage businesses seeking business development assistance.",
            "sector": "", "region": "", "closing_date": timezone.localdate() + timedelta(days=35),
            "requirements": "Business description\nBasic income and expense records\nGrowth objective\nOwner contact details", "is_active": True,
        })
        self.stdout.write(self.style.SUCCESS("Demo data is ready. Sign in with username demo and password TradeLifeDemo123!."))
