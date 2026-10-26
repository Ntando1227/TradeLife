import json
import re
import time
from datetime import date
from html.parser import HTMLParser
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urljoin
from urllib.request import Request, urlopen

from django.core.management.base import BaseCommand
from django.utils import timezone

from core.models import Opportunity


OFFICIAL_LISTING_PAGES = [
    {
        "name": "NYDA Opportunities",
        "url": "https://www.nyda.gov.za/Opportunities.html",
        "organisation": "National Youth Development Agency",
    },
    {
        "name": "Department of Small Business Development programmes",
        "url": "https://www.dsbd.gov.za/programmes/",
        "organisation": "Department of Small Business Development",
    },
    {
        "name": "SEDFA funding and business support",
        "url": "https://www.sedfa.org.za/",
        "organisation": "Small Enterprise Development and Finance Agency",
    },
]

KNOWN_PROGRAMMES = [
    {
        "title": "NYDA Grant Programme",
        "url": "https://www.nyda.gov.za/Products-Services/NYDA-Grant-Programme.html",
        "organisation": "National Youth Development Agency",
    },
    {
        "title": "Township and Rural Entrepreneurship Programme",
        "url": "https://www.dsbd.gov.za/township-and-rural-entrepreneurship-programme-trep/",
        "organisation": "Department of Small Business Development",
    },
    {
        "title": "SEDFA Township and Rural Entrepreneurship Programme",
        "url": "https://www.sedfa.org.za/trep.html",
        "organisation": "Small Enterprise Development and Finance Agency",
    },
    {
        "title": "SEDFA Youth Challenge Fund",
        "url": "https://www.sedfa.org.za/youth-challenge-fund.html",
        "organisation": "Small Enterprise Development and Finance Agency",
    },
]

ETENDERS_API = "https://ocds-api.etenders.gov.za/api/OCDSReleases"

INCLUDE_TERMS = (
    "fund", "grant", "funding", "loan", "voucher", "supplier", "tender",
    "procurement", "market link", "business", "entrepreneur", "enterprise",
    "small business", "sme", "smme", "co-operative", "cooperative",
    "spaza", "asset assist", "trep", "youth challenge", "export",
)

EXCLUDE_TERMS = (
    "vacanc", "internship", "bursary", "learnership", "job preparedness",
    "careers", "career opportunity",
)


class AnchorParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.links = []
        self.current_href = None
        self.current_text = []

    def handle_starttag(self, tag, attrs):
        if tag.lower() == "a":
            self.current_href = dict(attrs).get("href")
            self.current_text = []

    def handle_data(self, data):
        if self.current_href is not None:
            self.current_text.append(data)

    def handle_endtag(self, tag):
        if tag.lower() == "a" and self.current_href is not None:
            label = " ".join(" ".join(self.current_text).split())
            self.links.append((self.current_href, label))
            self.current_href = None
            self.current_text = []


def fetch_bytes(url, timeout=20, attempts=3):
    headers = {
        "User-Agent": "TradeLifeOpportunityFinder/1.0",
        "Accept": "text/html,application/json",
    }

    last_error = None
    for attempt in range(attempts):
        try:
            request = Request(url, headers=headers)
            with urlopen(request, timeout=timeout) as response:
                return response.read(), response.headers.get_content_charset()
        except (HTTPError, URLError, TimeoutError, OSError) as exc:
            last_error = exc
            status = getattr(exc, "code", None)
            if status not in (None, 429, 500, 502, 503, 504) and attempt < attempts - 1:
                raise
            if attempt < attempts - 1:
                time.sleep(2 ** attempt)

    raise RuntimeError(f"Could not fetch {url}: {last_error}")


def fetch_html(url):
    raw, charset = fetch_bytes(url)
    return raw.decode(charset or "utf-8", errors="replace")


def fetch_json(url):
    raw, _ = fetch_bytes(url)
    return json.loads(raw.decode("utf-8", errors="replace"))


def is_relevant_title(title):
    text = title.lower()
    if any(term in text for term in EXCLUDE_TERMS):
        return False
    return any(term in text for term in INCLUDE_TERMS)


def extract_releases(payload):
    found = []

    def walk(value):
        if isinstance(value, list):
            for item in value:
                walk(item)
            return

        if not isinstance(value, dict):
            return

        releases = value.get("releases")
        if isinstance(releases, list):
            for release in releases:
                if isinstance(release, dict) and isinstance(release.get("tender"), dict):
                    found.append(release)
                else:
                    walk(release)
            return

        if isinstance(value.get("tender"), dict):
            found.append(value)
            return

        for key in ("data", "items", "results", "records", "packages"):
            if key in value:
                walk(value[key])

    walk(payload)

    unique = {}
    for release in found:
        tender = release.get("tender") or {}
        tender_id = str(tender.get("id") or release.get("ocid") or "")
        unique[tender_id or str(id(release))] = release
    return list(unique.values())


def parse_close_date(value):
    if not value:
        return None
    try:
        return date.fromisoformat(str(value)[:10])
    except (TypeError, ValueError):
        return None


def procurement_sector(text):
    value = text.lower()
    if any(word in value for word in ("agricultur", "farming", "livestock")):
        return "Agriculture"
    if any(word in value for word in ("construction", "building", "maintenance")):
        return "Construction"
    if any(word in value for word in ("software", "computer", "ict", "technology")):
        return "ICT"
    if any(word in value for word in ("catering", "food", "meal")):
        return "Catering"
    if any(word in value for word in ("transport", "vehicle", "logistics")):
        return "Transport"
    if any(word in value for word in ("cleaning", "hygiene")):
        return "Cleaning"
    return ""


class Command(BaseCommand):
    help = "Collect public business support and procurement opportunities from official sources."

    def add_arguments(self, parser):
        parser.add_argument(
            "--max-pages",
            type=int,
            default=3,
            help="Maximum eTenders API pages to request. Each page is capped at 100 records.",
        )

    def handle(self, *args, **options):
        created = 0
        updated = 0
        failures = 0

        for programme in KNOWN_PROGRAMMES:
            try:
                was_created = self.save_opportunity(
                    title=programme["title"],
                    organisation=programme["organisation"],
                    source_url=programme["url"],
                    description=(
                        "Public business support or funding programme. "
                        "TradeLife found this programme on an official agency page. "
                        "The current application window may change. Check the official "
                        "page for eligibility, dates, and whether applications are open."
                    ),
                    requirements=(
                        "Verify current eligibility, application dates, and application status "
                        "on the official source page before applying."
                    ),
                    closing_date=None,
                    sector="",
                )
                created += int(was_created)
                updated += int(not was_created)
            except Exception as exc:
                failures += 1
                self.stderr.write(f"Could not save {programme['title']}: {exc}")

        for source in OFFICIAL_LISTING_PAGES:
            try:
                html = fetch_html(source["url"])
                parser = AnchorParser()
                parser.feed(html)

                source_count = 0
                for href, title in parser.links:
                    if not title or len(title) < 5 or not is_relevant_title(title):
                        continue

                    target_url = urljoin(source["url"], href)
                    if not target_url.startswith(("http://", "https://")):
                        continue

                    was_created = self.save_opportunity(
                        title=title[:180],
                        organisation=source["organisation"],
                        source_url=target_url[:200],
                        description=(
                            f"Listed on the official {source['name']} page. "
                            "This automated listing does not confirm that applications are open. "
                            "Check the original source for current dates, eligibility, and instructions."
                        ),
                        requirements=(
                            f"Found on: {source['url']}\n"
                            "Verify the current application status and eligibility on the source page."
                        ),
                        closing_date=None,
                        sector="",
                    )
                    created += int(was_created)
                    updated += int(not was_created)
                    source_count += 1

                self.stdout.write(f"{source['name']}: collected {source_count} relevant links.")
            except Exception as exc:
                failures += 1
                self.stderr.write(f"{source['name']} could not be checked: {exc}")

        try:
            tender_created, tender_updated = self.sync_etenders(options["max_pages"])
            created += tender_created
            updated += tender_updated
        except Exception as exc:
            failures += 1
            self.stderr.write(f"eTenders API could not be checked: {exc}")

        self.stdout.write(
            self.style.SUCCESS(
                f"Opportunity sync finished. Added: {created}. Updated: {updated}. "
                f"Source errors: {failures}."
            )
        )

    def sync_etenders(self, max_pages):
        created = 0
        updated = 0
        today = timezone.localdate()

        for page_number in range(1, max(1, min(max_pages, 10)) + 1):
            query = urlencode({"PageNumber": page_number, "PageSize": 100})
            payload = fetch_json(f"{ETENDERS_API}?{query}")
            releases = extract_releases(payload)

            if not releases:
                if page_number == 1:
                    self.stderr.write(
                        "eTenders returned no recognised release records. "
                        "The API response format may have changed."
                    )
                break

            for release in releases:
                tender = release.get("tender") or {}
                title = " ".join(str(tender.get("title") or "").split())
                if not title:
                    continue

                tender_id = str(tender.get("id") or release.get("ocid") or "")
                buyer = release.get("buyer") or {}
                organisation = buyer.get("name") if isinstance(buyer, dict) else str(buyer or "")
                organisation = organisation or "South African public sector"

                status = str(tender.get("status") or "").lower()
                if status in {"cancelled", "complete", "unsuccessful", "withdrawn"}:
                    continue

                period = tender.get("tenderPeriod") or {}
                closing_date = parse_close_date(period.get("endDate"))
                if closing_date and closing_date < today:
                    continue

                combined_text = " ".join([
                    title,
                    str(tender.get("description") or ""),
                    str(tender.get("mainProcurementCategory") or ""),
                ])
                if not is_relevant_title(combined_text):
                    continue

                documents = tender.get("documents") or []
                document_url = ""
                for document in documents:
                    if isinstance(document, dict):
                        candidate = document.get("url")
                        if isinstance(candidate, str) and candidate.startswith(("http://", "https://")):
                            document_url = candidate
                            break

                source_url = document_url or "https://www.etenders.gov.za/"
                if len(source_url) > 200:
                    source_url = "https://www.etenders.gov.za/"

                description = str(tender.get("description") or "").strip()
                details = []
                if tender_id:
                    details.append(f"Tender reference: {tender_id}")
                details.append("Source: National Treasury eTenders public procurement data.")
                details.append(
                    "Check the official eTenders portal for the complete notice, documents, "
                    "eligibility, and any amendments."
                )
                if not description:
                    description = title

                requirements = "\n".join(details)
                was_created = self.save_opportunity(
                    title=title[:180],
                    organisation=organisation[:140],
                    source_url=source_url,
                    description=description,
                    requirements=requirements,
                    closing_date=closing_date,
                    sector=procurement_sector(combined_text),
                )
                created += int(was_created)
                updated += int(not was_created)

        return created, updated

    def save_opportunity(
        self,
        title,
        organisation,
        source_url,
        description,
        requirements,
        closing_date,
        sector,
    ):
        field_names = {field.name for field in Opportunity._meta.fields}
        defaults = {
            "description": description,
            "sector": sector[:40],
            "region": "",
            "closing_date": closing_date,
            "requirements": requirements,
            "is_active": True,
        }

        if "country" in field_names:
            defaults["country"] = "South Africa"

        if "verification_status" in field_names:
            defaults["verification_status"] = "unverified"

        opportunity, was_created = Opportunity.objects.update_or_create(
            title=title[:180],
            organisation=organisation[:140],
            source_url=source_url,
            defaults=defaults,
        )
        return was_created