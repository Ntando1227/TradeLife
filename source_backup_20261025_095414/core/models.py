from decimal import Decimal
from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models
from django.utils import timezone


class Business(models.Model):
    SECTORS = [(x, x) for x in ["Catering", "Retail", "Agriculture", "Beauty", "Construction", "Transport", "Professional services", "Other"]]
    owner = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="business")
    name = models.CharField(max_length=140)
    sector = models.CharField(max_length=40, choices=SECTORS, default="Other")
    region = models.CharField(max_length=100, blank=True)
    town = models.CharField(max_length=100, blank=True)
    phone = models.CharField(max_length=30, blank=True)
    email = models.EmailField(blank=True)
    registration_status = models.CharField(max_length=30, choices=[("not_started", "Not started"), ("in_progress", "In progress"), ("registered", "Registered")], default="not_started")
    has_business_bank_account = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


class Customer(models.Model):
    business = models.ForeignKey(Business, on_delete=models.CASCADE, related_name="customers")
    name = models.CharField(max_length=140)
    contact_name = models.CharField(max_length=120, blank=True)
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=30, blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name"]
        indexes = [models.Index(fields=["business", "name"])]

    def __str__(self):
        return self.name


class Quote(models.Model):
    STATUSES = [("draft", "Draft"), ("sent", "Sent"), ("accepted", "Accepted"), ("declined", "Declined"), ("invoiced", "Invoiced")]
    business = models.ForeignKey(Business, on_delete=models.CASCADE, related_name="quotes")
    customer = models.ForeignKey(Customer, on_delete=models.PROTECT, related_name="quotes")
    reference = models.CharField(max_length=24)
    description = models.CharField(max_length=240)
    amount = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(Decimal("0.01"))])
    status = models.CharField(max_length=12, choices=STATUSES, default="draft")
    issue_date = models.DateField(default=timezone.localdate)
    valid_until = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-issue_date", "-id"]
        constraints = [models.UniqueConstraint(fields=["business", "reference"], name="unique_quote_reference_per_business")]

    def __str__(self):
        return self.reference


class Invoice(models.Model):
    STATUSES = [("unpaid", "Unpaid"), ("part_paid", "Part paid"), ("paid", "Paid"), ("overdue", "Overdue")]
    business = models.ForeignKey(Business, on_delete=models.CASCADE, related_name="invoices")
    customer = models.ForeignKey(Customer, on_delete=models.PROTECT, related_name="invoices")
    quote = models.OneToOneField(Quote, null=True, blank=True, on_delete=models.SET_NULL, related_name="invoice")
    reference = models.CharField(max_length=24)
    description = models.CharField(max_length=240)
    amount = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(Decimal("0.01"))])
    issue_date = models.DateField(default=timezone.localdate)
    due_date = models.DateField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-issue_date", "-id"]
        constraints = [models.UniqueConstraint(fields=["business", "reference"], name="unique_invoice_reference_per_business")]
        indexes = [models.Index(fields=["business", "due_date"])]

    @property
    def amount_paid(self):
        if "payments" in getattr(self, "_prefetched_objects_cache", {}):
            return sum((payment.amount for payment in self._prefetched_objects_cache["payments"]), Decimal("0.00"))
        return self.payments.aggregate(total=models.Sum("amount"))["total"] or Decimal("0.00")

    @property
    def balance(self):
        return max(Decimal("0.00"), self.amount - self.amount_paid)

    @property
    def status(self):
        if self.balance <= 0:
            return "paid"
        if self.amount_paid > 0:
            return "part_paid"
        if self.due_date < timezone.localdate():
            return "overdue"
        return "unpaid"


class Payment(models.Model):
    METHODS = [("cash", "Cash"), ("eft", "EFT / bank transfer"), ("card", "Card"), ("other", "Other")]
    business = models.ForeignKey(Business, on_delete=models.CASCADE, related_name="payments")
    invoice = models.ForeignKey(Invoice, on_delete=models.CASCADE, related_name="payments")
    amount = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(Decimal("0.01"))])
    payment_date = models.DateField(default=timezone.localdate)
    method = models.CharField(max_length=10, choices=METHODS, default="eft")
    reference = models.CharField(max_length=100, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-payment_date", "-id"]


class Expense(models.Model):
    business = models.ForeignKey(Business, on_delete=models.CASCADE, related_name="expenses")
    description = models.CharField(max_length=180)
    category = models.CharField(max_length=80, default="General")
    amount = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(Decimal("0.01"))])
    expense_date = models.DateField(default=timezone.localdate)
    due_date = models.DateField(null=True, blank=True)
    is_paid = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-expense_date", "-id"]
        indexes = [models.Index(fields=["business", "due_date"])]


class Opportunity(models.Model):
    title = models.CharField(max_length=180)
    organisation = models.CharField(max_length=140)
    description = models.TextField()
    sector = models.CharField(max_length=40, blank=True, help_text="Leave blank for opportunities open to every sector")
    region = models.CharField(max_length=100, blank=True, help_text="Leave blank for opportunities open to every region")
    closing_date = models.DateField(null=True, blank=True)
    requirements = models.TextField(blank=True, help_text="Put each requirement on a new line")
    source_url = models.URLField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["closing_date", "title"]

    def __str__(self):
        return self.title
