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

    # Step 2: Generate summaries with OpenAI (two-part report)
    logger.info("Step 2: Generating executive summaries with OpenAI")
    notes_summary = None
    deals_summary = None

    try:
        openai_client = OpenAIClient()

        has_notes = bool(notes)
        has_deals = bool(deals_data.get("new_deals") or deals_data.get("updated_deals"))

        if not has_notes and not has_deals:
            # No activity to report
            logger.info("No CRM activity found - generating empty report")
            notes_summary = openai_client.generate_empty_report()

        elif errors and not has_notes and not has_deals:
            # Errors and no data at all
            notes_summary = openai_client.generate_error_summary(errors)

        else:
            error_notice = ""
            if errors:
                logger.warning("Generating partial report due to errors")
                error_notice = "⚠️ **Note:** Some data may be incomplete due to API errors.\n\n"

            # Generate Part 1: Notes summary
            if has_notes:
                try:
                    logger.info("Generating Part 1: Notes summary")
                    notes_summary = openai_client.generate_notes_summary(notes)
                    if error_notice:
                        notes_summary = error_notice + notes_summary
                except Exception as e:
                    logger.error(f"Failed to generate notes summary: {e}")
                    notes_summary = openai_client.generate_error_summary(
                        [f"Failed to generate notes summary: {str(e)}"]
                    )

            # Generate Part 2: Deals summary
            if has_deals:
                try:
                    logger.info("Generating Part 2: Deals summary")
                    deals_summary = openai_client.generate_deals_summary(deals_data)
                    if error_notice:
                        deals_summary = error_notice + deals_summary
                except Exception as e:
                    logger.error(f"Failed to generate deals summary: {e}")
                    deals_summary = openai_client.generate_error_summary(
                        [f"Failed to generate deals summary: {str(e)}"]
                    )

        logger.info("Summary generation complete")

    except Exception as e:
        error_msg = f"Failed to generate summary: {str(e)}"
        logger.error(error_msg)
        errors.append(error_msg)

        # Try to create a basic error summary
        try:
            openai_client_fallback = OpenAIClient()
            notes_summary = openai_client_fallback.generate_error_summary(errors)
        except:
            # Last resort - create manual error message
            notes_summary = f"""# CRM Daily Report - Error

## Critical Error

The automated report generation failed with the following errors:

{chr(10).join([f'- {err}' for err in errors])}

Please contact the system administrator immediately.
"""

    # Step 3: Send report(s) to Teams
    logger.info("Step 3: Sending report to Microsoft Teams")
    try:
        teams_client = TeamsClient()

        # Build the list of parts to send
        # Teams displays newest message on top, so we send deals (2/2) first
        # and notes (1/2) second, so notes appears above deals in the channel
        report_parts = []
        if deals_summary:
            report_parts.append(("CRM Daily Executive Summary (2/2)", deals_summary))
        if notes_summary:
            report_parts.append(("CRM Daily Executive Summary (1/2)", notes_summary))

        if report_parts:
            teams_client.send_two_part_report(report_parts)
            logger.info(f"Report sent to Teams successfully ({len(report_parts)} part(s))")
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
