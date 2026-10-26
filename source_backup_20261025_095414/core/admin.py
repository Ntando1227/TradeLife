from django.contrib import admin
from .models import Business, Customer, Quote, Invoice, Payment, Expense, Opportunity

admin.site.register(Business)
admin.site.register(Customer)
admin.site.register(Quote)
admin.site.register(Invoice)
admin.site.register(Payment)
admin.site.register(Expense)
admin.site.register(Opportunity)
