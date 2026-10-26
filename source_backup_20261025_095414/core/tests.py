from datetime import timedelta
from decimal import Decimal
from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from .models import Business, Customer, Invoice, Payment, Expense, Opportunity, Quote
from .services import cash_forecast, readiness


class TradeLifeWorkflowTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="owner", password="LongPass123!")
        self.business = Business.objects.create(owner=self.user, name="Township Caterers", sector="Catering", region="Limpopo")
        self.customer = Customer.objects.create(business=self.business, name="Local School")

    def test_payment_reduces_invoice_balance_and_cash_estimate(self):
        invoice = Invoice.objects.create(business=self.business, customer=self.customer, reference="INV-1", description="Lunch", amount=Decimal("1000.00"), due_date=timezone.localdate() + timedelta(days=10))
        Payment.objects.create(business=self.business, invoice=invoice, amount=Decimal("400.00"))
        Expense.objects.create(business=self.business, description="Ingredients", category="Stock", amount=Decimal("150.00"), is_paid=False, due_date=timezone.localdate() + timedelta(days=5))
        invoice.refresh_from_db()
        forecast = cash_forecast(self.business)
        self.assertEqual(invoice.balance, Decimal("600.00"))
        self.assertEqual(forecast["expected_in"], Decimal("600.00"))
        self.assertEqual(forecast["expected_out"], Decimal("150.00"))
        self.assertEqual(forecast["net"], Decimal("450.00"))

    def test_business_workspace_requires_login(self):
        response = self.client.get(reverse("dashboard"))
        self.assertEqual(response.status_code, 302)

    def test_dashboard_is_available_after_login(self):
        self.client.login(username="owner", password="LongPass123!")
        response = self.client.get(reverse("dashboard"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Township Caterers")

    def test_readiness_is_transparent_and_starts_incomplete(self):
        result = readiness(self.business)
        self.assertEqual(result["score"], round(2 / 7 * 100))
        self.assertEqual(result["total"], 7)

    def test_main_pages_render_for_signed_in_business_owner(self):
        self.client.login(username="owner", password="LongPass123!")
        paths = ["dashboard", "business_profile", "readiness", "customer_list", "customer_create",
                 "quote_list", "quote_create", "invoice_list", "invoice_create", "expense_list",
                 "expense_create", "forecast", "opportunity_list"]
        for name in paths:
            with self.subTest(page=name):
                self.assertEqual(self.client.get(reverse(name)).status_code, 200)

    def test_document_pages_only_show_records_for_owner(self):
        invoice = Invoice.objects.create(business=self.business, customer=self.customer, reference="INV-1", description="Lunch", amount=Decimal("100.00"), due_date=timezone.localdate() + timedelta(days=7))
        quote = Quote.objects.create(business=self.business, customer=self.customer, reference="Q-1", description="Lunch", amount=Decimal("100.00"))
        self.client.login(username="owner", password="LongPass123!")
        self.assertEqual(self.client.get(reverse("invoice_detail", args=[invoice.id])).status_code, 200)
        self.assertEqual(self.client.get(reverse("quote_detail", args=[quote.id])).status_code, 200)

    def test_opportunity_screen_renders_match_guidance(self):
        Opportunity.objects.create(title="Catering request", organisation="Local buyer", description="Demo listing", sector="Catering", region="Limpopo", requirements="Profile\nRecent invoice")
        self.client.login(username="owner", password="LongPass123!")
        response = self.client.get(reverse("opportunity_list"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Catering request")
