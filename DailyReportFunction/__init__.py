"""
Azure Function: Daily CRM Report Generator

Runs daily at 7:00 AM Toronto time (Monday-Friday).
Extracts CRM activity, generates AI summary, and sends to Teams.
"""
import logging
import os
import sys
from typing import Dict, List, Any
import azure.functions as func

# Add parent directory to path for shared modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from shared.brevo_client import BrevoClient
from shared.openai_client import OpenAIClient
from shared.teams_client import TeamsClient
from shared.utils import get_lookback_period

# Configure logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


def main(mytimer: func.TimerRequest) -> None:
    """
    Main Azure Function entry point.

    Args:
        mytimer: Timer trigger request object
    """
    logger.info("=" * 80)
    logger.info("CRM Daily Report Function - Starting execution")
    logger.info("=" * 80)

    # Check if function is running on schedule or manually triggered
    if mytimer.past_due:
        logger.warning("Timer is past due - function execution was delayed")

    # Read configuration
    use_mock_data = os.getenv("USE_MOCK_DATA", "false").lower() == "true"
    logger.info(f"Configuration: USE_MOCK_DATA={use_mock_data}")

    errors = []
    notes = []
    deals_data = {"new_deals": [], "updated_deals": []}

    # Step 1: Extract data from Brevo CRM
    logger.info("Step 1: Extracting CRM data from Brevo")
    try:
        brevo_client = BrevoClient(use_mock=use_mock_data)
        start_time, end_time = get_lookback_period()

        logger.info(f"Time range: {start_time.isoformat()} to {end_time.isoformat()}")

        # Fetch notes
        try:
            logger.info("Fetching CRM notes...")
            notes = brevo_client.get_notes(start_time, end_time)
            logger.info(f"Retrieved {len(notes)} company-level notes (Aura AI notes excluded)")

            # Enrich notes with company data
            logger.info("Enriching notes with company information...")
            notes = brevo_client.enrich_notes_with_companies(notes)
            logger.info("Notes enriched successfully")

        except Exception as e:
            error_msg = f"Failed to fetch notes: {str(e)}"
            logger.error(error_msg)
            errors.append(error_msg)

        # Fetch deals
        try:
            logger.info("Fetching CRM deals...")
            deals_data = brevo_client.get_deals(start_time, end_time)
            new_count = len(deals_data.get("new_deals", []))
            updated_count = len(deals_data.get("updated_deals", []))
            logger.info(f"Retrieved {new_count} new deals and {updated_count} updated deals")

        except Exception as e:
            error_msg = f"Failed to fetch deals: {str(e)}"
            logger.error(error_msg)
            errors.append(error_msg)

    except Exception as e:
        error_msg = f"Failed to initialize Brevo client: {str(e)}"
        logger.error(error_msg)
        errors.append(error_msg)

    # Step 2: Generate summary with OpenAI
    logger.info("Step 2: Generating executive summary with OpenAI")
    summary = None

    try:
        openai_client = OpenAIClient()

        # Check if there's any activity to report
        has_deals = bool(deals_data.get("new_deals") or deals_data.get("updated_deals"))

        if not notes and not has_deals:
            # No activity to report
            logger.info("No CRM activity found - generating empty report")
            summary = openai_client.generate_empty_report()

        elif errors:
            # Partial data available
            logger.warning("Generating partial report due to errors")
            if notes or has_deals:
                # Try to generate summary with available data
                try:
                    summary = openai_client.generate_summary(notes, deals_data)
                    # Prepend error notice
                    error_notice = "⚠️ **Note:** Some data may be incomplete due to API errors.\n\n"
                    summary = error_notice + summary
                except Exception as e:
                    logger.error(f"Failed to generate summary with partial data: {e}")
                    summary = openai_client.generate_error_summary(errors)
            else:
                # No data at all
                summary = openai_client.generate_error_summary(errors)

        else:
            # Normal operation - generate full summary
            logger.info("Generating full summary report")
            summary = openai_client.generate_summary(notes, deals_data)

        logger.info("Summary generated successfully")

    except Exception as e:
        error_msg = f"Failed to generate summary: {str(e)}"
        logger.error(error_msg)
        errors.append(error_msg)

        # Try to create a basic error summary
        try:
            openai_client_fallback = OpenAIClient()
            summary = openai_client_fallback.generate_error_summary(errors)
        except:
            # Last resort - create manual error message
            summary = f"""# CRM Daily Report - Error

## Critical Error

The automated report generation failed with the following errors:

{chr(10).join([f'- {err}' for err in errors])}

Please contact the system administrator immediately.
"""

    # Step 3: Send report to Teams
    logger.info("Step 3: Sending report to Microsoft Teams")
    try:
        teams_client = TeamsClient()

        if summary:
            teams_client.send_report(summary, title="CRM Daily Executive Summary")
            logger.info("Report sent to Teams successfully")
        else:
            raise Exception("No summary content available to send")

    except Exception as e:
        error_msg = f"Failed to send report to Teams: {str(e)}"
        logger.error(error_msg)

        # Try to send error notification
        try:
            teams_client = TeamsClient()
            teams_client.send_error_notification(
                error_message="Failed to send daily CRM report",
                context=error_msg
            )
        except Exception as notify_error:
            logger.error(f"Failed to send error notification: {notify_error}")

    # Final status
    logger.info("=" * 80)
    if errors:
        logger.warning(f"Function completed with {len(errors)} error(s)")
        logger.warning("Errors: " + "; ".join(errors))
    else:
        logger.info("Function completed successfully")
    logger.info("=" * 80)
