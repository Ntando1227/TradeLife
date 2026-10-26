from django.contrib.auth import views as auth_views
from django.urls import path
from . import views

urlpatterns = [
    path("", views.home, name="home"), path("signup/", views.signup, name="signup"),
    path("login/", auth_views.LoginView.as_view(template_name="registration/login.html"), name="login"),
    path("logout/", auth_views.LogoutView.as_view(), name="logout"),
    path("dashboard/", views.dashboard, name="dashboard"), path("profile/", views.business_profile, name="business_profile"),
    path("readiness/", views.readiness_page, name="readiness"), path("forecast/", views.forecast_page, name="forecast"),
    path("customers/", views.customer_list, name="customer_list"), path("customers/new/", views.customer_create, name="customer_create"),
    path("quotes/", views.quote_list, name="quote_list"), path("quotes/new/", views.quote_create, name="quote_create"), path("quotes/<int:quote_id>/", views.quote_detail, name="quote_detail"), path("quotes/<int:quote_id>/invoice/", views.quote_to_invoice, name="quote_to_invoice"),
    path("invoices/", views.invoice_list, name="invoice_list"), path("invoices/new/", views.invoice_create, name="invoice_create"), path("invoices/<int:invoice_id>/", views.invoice_detail, name="invoice_detail"), path("invoices/<int:invoice_id>/payment/", views.payment_create, name="payment_create"),
    path("expenses/", views.expense_list, name="expense_list"), path("expenses/new/", views.expense_create, name="expense_create"),
    path("opportunities/", views.opportunity_list, name="opportunity_list"),
]
