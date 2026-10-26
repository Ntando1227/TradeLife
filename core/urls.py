from . import team_views
from . import market_views
from . import dashboard_views
from . import visual_views
from . import action_views
from . import extra_views
from django.contrib.auth import views as auth_views
from django.urls import path
from django.views.generic import RedirectView

from . import office_views, quote_views, views

urlpatterns = [
    path("team/", team_views.team_manage, name="team_manage"),
    path("api/v1/", market_views.api_docs, name="api_docs"),
    path("api/v1/opportunities/", market_views.api_opportunities, name="api_opportunities"),
    path("action-centre/", RedirectView.as_view(pattern_name="dashboard", permanent=False), name="action_centre"),
    path("dashboard/", dashboard_views.unified_dashboard, name="dashboard"),
    path("quotes/manage/", RedirectView.as_view(pattern_name="quote_list", permanent=False), name="quote_manage"),
    path("quotes/<int:pk>/edit/", extra_views.quote_edit, name="quote_edit"),
    path("quotes/<int:pk>/delete/", extra_views.quote_delete, name="quote_delete"),
    path("", views.home, name="home"),
    path("signup/", views.signup, name="signup"),
    path("login/", auth_views.LoginView.as_view(template_name="registration/login.html"), name="login"),
    path("logout/", auth_views.LogoutView.as_view(), name="logout"),
    path("profile/", views.business_profile, name="business_profile"),
    path("readiness/", views.readiness_page, name="readiness"),
    path("forecast/", views.forecast_page, name="forecast"),
    path("customers/", views.customer_list, name="customer_list"),
    path("customers/new/", views.customer_create, name="customer_create"),
    path("quotes/", views.quote_list, name="quote_list"),
    path("quotes/new/", views.quote_create, name="quote_create"),
    path("quotes/<int:quote_id>/", views.quote_detail, name="quote_detail"),
    path("quotes/<int:quote_id>/edit/", quote_views.quote_update, name="quote_update"),
    path("quotes/<int:quote_id>/delete/", quote_views.quote_delete, name="quote_delete"),
    path("quotes/<int:quote_id>/invoice/", views.quote_to_invoice, name="quote_to_invoice"),
    path("invoices/", views.invoice_list, name="invoice_list"),
    path("invoices/new/", views.invoice_create, name="invoice_create"),
    path("invoices/<int:invoice_id>/", views.invoice_detail, name="invoice_detail"),
    path("invoices/<int:invoice_id>/payment/", views.payment_create, name="payment_create"),
    path("expenses/", views.expense_list, name="expense_list"),
    path("expenses/new/", views.expense_create, name="expense_create"),
    path("opportunities/", market_views.opportunity_list, name="opportunity_list"),
    path("updates/", office_views.my_updates, name="my_updates"),
    path("office/businesses/", office_views.office_businesses, name="office_businesses"),
    path("office/customers/", office_views.office_customers, name="office_customers"),
    path("office/updates/", office_views.office_updates, name="office_updates"),
    path("office/updates/<int:update_id>/status/", office_views.office_update_status, name="office_update_status"),
]