import hashlib
import json
from datetime import timedelta
from urllib.parse import quote

from django.core.cache import cache
from django.core.paginator import Paginator
from django.db.models import Case, IntegerField, Q, Value, When
from django.http import JsonResponse
from django.shortcuts import render
from django.utils import timezone

from .models import Business, Opportunity
from .views import owned_business


def _opportunity_queryset(params):
    today = timezone.localdate()
    queryset = Opportunity.objects.filter(is_active=True).filter(
        Q(closing_date__isnull=True) | Q(closing_date__gte=today)
    )

    search = (params.get("q") or "").strip()[:120]
    sector = (params.get("sector") or "").strip()[:80]
    region = (params.get("region") or "").strip()[:100]
    country = (params.get("country") or "").strip()[:80]
    closing = (params.get("closing") or "").strip().lower()

    if search:
        queryset = queryset.filter(
            Q(title__icontains=search)
            | Q(organisation__icontains=search)
            | Q(description__icontains=search)
            | Q(requirements__icontains=search)
            | Q(sector__icontains=search)
            | Q(region__icontains=search)
            | Q(country__icontains=search)
        )

    if sector:
        queryset = queryset.filter(sector__iexact=sector)
    if region:
        queryset = queryset.filter(region__icontains=region)
    if country:
        queryset = queryset.filter(country__iexact=country)
    if closing == "soon":
        queryset = queryset.filter(
            closing_date__isnull=False,
            closing_date__lte=today + timedelta(days=30),
        )

    return queryset, search, sector, region, country, closing


def _business_for_user(user):
    if not user.is_authenticated:
        return None
    try:
        return owned_business(user)
    except Exception:
        return None


def _fit_for_business(opportunity, business):
    if not business:
        return False, "Complete a business profile to see a sector and location fit check."

    sector_match = not opportunity.sector or opportunity.sector.casefold() == business.sector.casefold()
    country_match = not opportunity.country or opportunity.country.casefold() == (business.country or "South Africa").casefold()

    opportunity_region = (opportunity.region or "").strip().casefold()
    business_region = (business.region or "").strip().casefold()
    business_town = (business.town or "").strip().casefold()
    region_match = (
        not opportunity_region
        or opportunity_region == business_region
        or opportunity_region == business_town
    )

    if sector_match and country_match and region_match:
        return True, "Fits your business sector and location."
    if sector_match and country_match:
        return False, "Sector and country fit. Check the regional requirements."
    if sector_match:
        return False, "Sector fit. Check the country and regional requirements."
    return False, "Review the sector and location requirements."


def opportunity_list(request):
    queryset, search, sector, region, country, closing = _opportunity_queryset(request.GET)
    business = _business_for_user(request.user)

    if business:
        sector_fit = Q(sector="") | Q(sector__iexact=business.sector)
        country_fit = Q(country="") | Q(country__iexact=business.country or "South Africa")
        location_fit = Q(region="")

        if business.region:
            location_fit |= Q(region__iexact=business.region)
        if business.town:
            location_fit |= Q(region__iexact=business.town)

        queryset = queryset.annotate(
            business_fit=Case(
                When(sector_fit & country_fit & location_fit, then=Value(0)),
                default=Value(1),
                output_field=IntegerField(),
            )
        ).order_by("business_fit", "closing_date", "title")
    else:
        queryset = queryset.order_by("closing_date", "title")

    paginator = Paginator(queryset, 12)
    page_obj = paginator.get_page(request.GET.get("page"))
    opportunities = list(page_obj.object_list)

    for opportunity in opportunities:
        opportunity.fit_match, opportunity.fit_reason = _fit_for_business(opportunity, business)
        message = (
            f"{opportunity.title} — {opportunity.organisation}. "
            f"Country: {opportunity.country}. "
            f"Closing date: {opportunity.closing_date or 'Not listed'}. "
            f"{opportunity.source_url}"
        )
        opportunity.whatsapp_url = "https://wa.me/?text=" + quote(message, safe="")

    query_params = request.GET.copy()
    query_params.pop("page", None)

    sectors = Opportunity.objects.filter(is_active=True).exclude(sector="").order_by("sector").values_list("sector", flat=True).distinct()
    regions = Opportunity.objects.filter(is_active=True).exclude(region="").order_by("region").values_list("region", flat=True).distinct()
    countries = Opportunity.objects.filter(is_active=True).order_by("country").values_list("country", flat=True).distinct()

    return render(request, "core/opportunities.html", {
        "opportunities": opportunities,
        "page_obj": page_obj,
        "sectors": sectors,
        "regions": regions,
        "countries": countries,
        "selected_search": search,
        "selected_sector": sector,
        "selected_region": region,
        "selected_country": country,
        "closing_soon": closing == "soon",
        "business": business,
        "query_string": query_params.urlencode(),
        "total_opportunities": paginator.count,
    })


def api_docs(request):
    return JsonResponse({
        "name": "TradeLife Market Opportunities API",
        "version": "v1",
        "access": "Public, read-only opportunity listings",
        "endpoint": "/api/v1/opportunities/",
        "method": "GET",
        "parameters": {
            "q": "Search title, organisation, description, requirements, sector, region or country.",
            "country": "Filter by country, for example South Africa, Botswana or Kenya.",
            "sector": "Filter by sector.",
            "region": "Filter by province, region or town.",
            "closing": "Use 'soon' for opportunities closing in the next 30 days.",
            "page": "Page number; defaults to 1.",
            "page_size": "Results per page; defaults to 20 and is capped at 50.",
        },
        "example": "/api/v1/opportunities/?country=South%20Africa&sector=Agriculture&page=1",
        "rate_limit": "60 requests per minute per client IP.",
    })


def api_opportunities(request):
    if request.method != "GET":
        return JsonResponse({"error": "Only GET requests are supported."}, status=405)

    ip_address = request.META.get("REMOTE_ADDR", "unknown")
    rate_key = "tradelife-opportunities-rate-" + hashlib.sha256(ip_address.encode()).hexdigest()

    if cache.add(rate_key, 1, timeout=60):
        request_count = 1
    else:
        try:
            request_count = cache.incr(rate_key)
        except ValueError:
            cache.set(rate_key, 1, timeout=60)
            request_count = 1

    if request_count > 60:
        response = JsonResponse({"error": "Rate limit reached. Try again in about one minute."}, status=429)
        response["Retry-After"] = "60"
        response["X-RateLimit-Limit"] = "60"
        response["X-RateLimit-Remaining"] = "0"
        return response

    queryset, search, sector, region, country, closing = _opportunity_queryset(request.GET)

    try:
        page_number = max(1, int(request.GET.get("page", "1")))
        page_size = max(1, min(50, int(request.GET.get("page_size", "20"))))
    except (TypeError, ValueError):
        page_number, page_size = 1, 20

    filters = {
        "q": search,
        "sector": sector,
        "region": region,
        "country": country,
        "closing": closing,
        "page": page_number,
        "page_size": page_size,
    }
    cache_key = "tradelife-opportunities-data-" + hashlib.sha256(
        json.dumps(filters, sort_keys=True).encode()
    ).hexdigest()
    payload = cache.get(cache_key)

    if payload is None:
        queryset = queryset.order_by("closing_date", "title")
        paginator = Paginator(queryset, page_size)
        page_obj = paginator.get_page(page_number)
        payload = {
            "count": paginator.count,
            "page": page_obj.number,
            "page_size": page_size,
            "pages": paginator.num_pages,
            "next_page": page_obj.next_page_number() if page_obj.has_next() else None,
            "previous_page": page_obj.previous_page_number() if page_obj.has_previous() else None,
            "results": [{
                "id": item.pk,
                "title": item.title,
                "organisation": item.organisation,
                "description": item.description,
                "sector": item.sector,
                "region": item.region,
                "country": item.country,
                "closing_date": item.closing_date.isoformat() if item.closing_date else None,
                "requirements": item.requirements,
                "source_url": item.source_url,
            } for item in page_obj.object_list],
        }
        cache.set(cache_key, payload, timeout=120)

    response = JsonResponse(payload)
    response["Cache-Control"] = "public, max-age=60"
    response["X-RateLimit-Limit"] = "60"
    response["X-RateLimit-Remaining"] = str(max(0, 60 - request_count))
    return response