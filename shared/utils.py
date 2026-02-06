"""
Utility functions for timezone conversion and data mapping.
"""
from datetime import datetime, timedelta
from typing import Dict, Tuple, Any, Optional
import pytz
import logging

logger = logging.getLogger(__name__)

# Timezone constants
UTC = pytz.UTC
TORONTO_TZ = pytz.timezone('America/Toronto')

# Pipeline mappings
PIPELINE_MAPPINGS = {
    "69580298dc36c3319adb3093": {
        "name": "PACA Sales Pipeline",
        "stages": {
            "9uaj093j221p3oiiply9hd8": "Identified",
            "arxdo4r2w2sz1l8a7by4j19": "Qualifying + Assessment",
            "9divv1rw8nmfjerhzl3owz6": "Proposal Request",
            "85ngn6t35cnvpr8ig84vd0b": "Proposal Sent",
            "fy8rr3y4p9qdv6kj9136zjs": "In negotiation",
            "11iq446lg3w5dtgqjb5q21v": "On-Hold",
            "ip6ui0uc77xt7z5zyb10mpa": "Won",
            "3cmz5s63sq9hlftezdeyqkc": "Lost"
        }
    },
    "6849de42a68e1c112aa30e83": {
        "name": "WHD Sales Pipeline",
        "stages": {
            "e8b624a6-1639-4843-810e-db83a0595130": "Identified",
            "97b3a62e-e19f-4997-8bbd-809240d86a4b": "Qualifying + Assessment",
            "60g199y1nw0bcbku0mkv5a1": "Proposal Request",
            "gmkj3zvmk7pdrqkqnho1ziu": "Proposal Sent to rep",
            "e8d0451f-7036-4582-bdfd-16f61c1c57ab": "In negotiation",
            "9fb0aed8-af6e-4bd2-b138-a18fe113179c": "On-Hold",
            "121d283d-7cb5-4221-a427-4a1154e1e240": "Won",
            "368e8008-e0d6-402e-a9db-287e0ec9921a": "Lost"
        }
    }
}

# User ID mappings
USER_MAPPINGS = {
    "6849de2c8da98f55690819b3": "Nicolas Attieh",
    "6866dcf3af9c593d0806bb57": "Marvin Escalante",
    "697b82280cf6c54eb606a106": "Paul Quinn",
    "697bfb2d60ae0c5cda038a8b": "Neil Chezepock",
    "69820936066c7eb5ec00a151": "Solutions",
    "698265a735270dc6db0bb3bc": "Doug Degen"
}

# Display name mappings for raw API values
DISTRIBUTOR_DISPLAY_MAP = {
    "w_rth_canada": "Wurth Canada",
    "lawson_products": "Lawson Products",
    "fastenal_canada": "Fastenal Canada",
    "pr__distribution": "PR. Distribution",
    "agco": "AGCO",
    "brakequip": "Brakequip",
    "hansen": "Hansen",
    "kent_automotive": "Kent Automotive",
    "motion": "Motion",
    "msc": "MSC",
    "napa_jobber": "NAPA JOBBER",
    "paccar": "PACCAR",
    "uap": "UAP",
    "uni_direct": "UNI Direct",
    "us_direct_ship": "US Direct Ship",
    "vipar": "VIPAR",
    "independent": "Independent",
}

BUSINESS_DIVISION_DISPLAY_MAP = {
    "whd": "WHD",
    "paca": "PACA",
}


def get_toronto_now() -> datetime:
    """
    Get current datetime in Toronto timezone.

    Returns:
        datetime: Current Toronto time with timezone info
    """
    return datetime.now(TORONTO_TZ)


def get_lookback_period() -> Tuple[datetime, datetime]:
    """
    Calculate the time range for data extraction based on current day.

    - Monday: Include Friday's data (72-hour lookback)
    - Tuesday-Friday: Last 24 hours

    Returns:
        Tuple[datetime, datetime]: (start_time, end_time) in UTC
    """
    toronto_now = get_toronto_now()

    # Calculate end time (now in UTC)
    end_time = datetime.now(UTC)

    # Calculate start time based on day of week
    # Monday = 0, Sunday = 6
    if toronto_now.weekday() == 0:  # Monday
        hours_back = 72  # Include Friday + Weekend
        logger.info("Monday detected: Using 72-hour lookback period")
    else:
        hours_back = 24
        logger.info(f"{toronto_now.strftime('%A')} detected: Using 24-hour lookback period")

    start_time = end_time - timedelta(hours=hours_back)

    logger.info(f"Lookback period: {start_time.isoformat()} to {end_time.isoformat()} (UTC)")

    return start_time, end_time


def get_report_date() -> datetime:
    """
    Get the date that should be displayed in the report title.
    For Monday reports, this should be Friday's date.

    Returns:
        datetime: Date of activities being reported (Toronto timezone)
    """
    toronto_now = get_toronto_now()

    if toronto_now.weekday() == 0:  # Monday
        # Report on Friday's activities
        report_date = toronto_now - timedelta(days=3)
    else:
        # Report on yesterday's activities
        report_date = toronto_now - timedelta(days=1)

    return report_date


def format_report_title() -> str:
    """
    Format the report title with the correct date.

    Format: "[Day of Week], [Month] [Day], [Year] – CRM Executive Summary"
    Example: "Friday, January 10, 2026 – CRM Executive Summary"

    Returns:
        str: Formatted report title
    """
    report_date = get_report_date()
    return f"{report_date.strftime('%A, %B %-d, %Y')} – CRM Executive Summary"


def get_pipeline_name(pipeline_id: str) -> str:
    """
    Get human-readable pipeline name from ID.

    Args:
        pipeline_id: Brevo pipeline ID

    Returns:
        str: Pipeline name or "Unknown Pipeline" if not found
    """
    pipeline = PIPELINE_MAPPINGS.get(pipeline_id, {})
    return pipeline.get("name", "Unknown Pipeline")


def get_stage_name(pipeline_id: str, stage_id: str) -> str:
    """
    Get human-readable stage name from pipeline and stage IDs.

    Args:
        pipeline_id: Brevo pipeline ID
        stage_id: Brevo stage ID

    Returns:
        str: Stage name or "Unknown Stage" if not found
    """
    pipeline = PIPELINE_MAPPINGS.get(pipeline_id, {})
    stages = pipeline.get("stages", {})
    return stages.get(stage_id, "Unknown Stage")


def get_user_name(user_id) -> str:
    """
    Get human-readable user name from user ID.

    Args:
        user_id: Brevo user ID (string) or user object (dict with 'id' key)

    Returns:
        str: User name or the original ID if not found
    """
    # Handle case where user_id is a dict (Brevo returns owner as object)
    if isinstance(user_id, dict):
        user_id = user_id.get("id", str(user_id))

    # Ensure user_id is a string
    if user_id is None:
        return "Unknown"

    user_id = str(user_id)
    return USER_MAPPINGS.get(user_id, user_id)


def format_company_link(company_id: str, company_name: str) -> str:
    """
    Format company name as markdown link for Teams.

    Args:
        company_id: Brevo company ID
        company_name: Company name

    Returns:
        str: Markdown formatted link
    """
    url = f"https://app.brevo.com/companies/detail/{company_id}"
    return f"[{company_name}]({url})"


def format_deal_link(deal_id: str, deal_name: str) -> str:
    """
    Format deal name as markdown link for Teams.

    Args:
        deal_id: Brevo deal ID
        deal_name: Deal name

    Returns:
        str: Markdown formatted link
    """
    url = f"https://app.brevo.com/crm/deals/detail/{deal_id}"
    return f"[{deal_name}]({url})"


def format_currency(amount: float) -> str:
    """
    Format amount as currency string.

    Args:
        amount: Dollar amount

    Returns:
        str: Formatted currency (e.g., "$1,234.56")
    """
    return f"${amount:,.2f}"


def utc_to_toronto(utc_time: datetime) -> datetime:
    """
    Convert UTC datetime to Toronto timezone.

    Args:
        utc_time: Datetime in UTC

    Returns:
        datetime: Datetime in Toronto timezone
    """
    if utc_time.tzinfo is None:
        utc_time = UTC.localize(utc_time)
    return utc_time.astimezone(TORONTO_TZ)


def parse_iso_datetime(iso_string: str) -> datetime:
    """
    Parse ISO 8601 datetime string to datetime object.

    Args:
        iso_string: ISO formatted datetime string

    Returns:
        datetime: Parsed datetime with UTC timezone
    """
    try:
        # Handle various ISO 8601 formats
        if iso_string.endswith('Z'):
            iso_string = iso_string[:-1] + '+00:00'

        dt = datetime.fromisoformat(iso_string)

        # Ensure UTC timezone
        if dt.tzinfo is None:
            dt = UTC.localize(dt)
        else:
            dt = dt.astimezone(UTC)

        return dt
    except Exception as e:
        logger.error(f"Error parsing datetime '{iso_string}': {e}")
        raise


def format_distributor_display(raw_value: Optional[str]) -> str:
    """
    Format raw distributor API value to display name.

    Args:
        raw_value: Raw distributor value from API (e.g., "w_rth_canada") or None

    Returns:
        str: Display name (e.g., "Wurth Canada") or original value if not found
    """
    if not raw_value:
        return "N/A"
    return DISTRIBUTOR_DISPLAY_MAP.get(raw_value, raw_value)


def format_business_division_display(raw_value: Optional[str]) -> str:
    """
    Format raw business division API value to display name.

    Args:
        raw_value: Raw business division value from API (e.g., "whd") or None

    Returns:
        str: Display name (e.g., "WHD") or original value if not found
    """
    if not raw_value:
        return "N/A"
    return BUSINESS_DIVISION_DISPLAY_MAP.get(raw_value, raw_value)


def format_note_for_display(note: Dict[str, Any]) -> Dict[str, Any]:
    """
    Format note data by converting raw API keys to display names.
    Formats: business_division_2 and distributor in company info.

    Args:
        note: Note dictionary with company information

    Returns:
        Dict: Note with formatted display values
    """
    formatted_note = note.copy()
    
    # Format company information
    companies = formatted_note.get("companies", [])
    for company in companies:
        # Format business_division_2 (stored as business_division in company dict)
        if "business_division" in company:
            company["business_division"] = format_business_division_display(
                company["business_division"]
            )
        
        # Format distributor
        if "distributor" in company:
            company["distributor"] = format_distributor_display(
                company["distributor"]
            )
    
    return formatted_note


def format_deal_for_display(deal: Dict[str, Any]) -> Dict[str, Any]:
    """
    Format deal data by converting raw API keys to display names.
    Formats: distributor only.

    Args:
        deal: Deal dictionary

    Returns:
        Dict: Deal with formatted display values
    """
    formatted_deal = deal.copy()
    
    # Format distributor
    if "distributor" in formatted_deal:
        formatted_deal["distributor"] = format_distributor_display(
            formatted_deal["distributor"]
        )
    
    return formatted_deal
