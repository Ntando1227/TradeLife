from django.contrib import admin
from .models import Business, Customer, Quote, Invoice, Payment, Expense, Opportunity

admin.site.register(Business)
admin.site.register(Customer)
admin.site.register(Quote)
admin.site.register(Invoice)
admin.site.register(Payment)
admin.site.register(Expense)
admin.site.register(Opportunity)


from .models import BusinessUpdate

@admin.register(BusinessUpdate)
class BusinessUpdateAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "business",
        "category",
        "priority",
        "status",
        "follow_up_date",
        "visible_to_business",
    )
    list_filter = ("status", "category", "priority", "visible_to_business")
    search_fields = ("title", "body", "business__name")