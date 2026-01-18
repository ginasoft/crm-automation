"""
Local test script - Does NOT send to Teams
Runs the complete flow and displays output in console.
"""
import logging
import os
import sys

# Configure logging to display everything in console
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)

logger = logging.getLogger(__name__)

# Load environment variables from local.settings.json
import json
try:
    with open('local.settings.json', 'r') as f:
        settings = json.load(f)
        for key, value in settings.get('Values', {}).items():
            os.environ[key] = value
except FileNotFoundError:
    logger.error("local.settings.json not found")

from datetime import datetime, timedelta, timezone

from shared.brevo_client import BrevoClient
from shared.openai_client import OpenAIClient
from shared.utils import get_lookback_period

# =============================================================================
# TEST CONFIGURATION - Change as needed
# =============================================================================
DAYS_BACK = 3  # Number of days to look back for data (Friday-Sunday)
# =============================================================================


def main():
    logger.info("=" * 80)
    logger.info("LOCAL TEST - Not sending to Teams")
    logger.info("=" * 80)

    # Use real Brevo data (not mock)
    use_mock = os.getenv("USE_MOCK_DATA", "false").lower() == "true"
    logger.info(f"USE_MOCK_DATA: {use_mock}")
    logger.info(f"DAYS_BACK: {DAYS_BACK} days")

    errors = []
    notes = []
    deals_data = {"new_deals": [], "updated_deals": []}

    # Step 1: Extract data from Brevo
    logger.info("\n" + "=" * 80)
    logger.info("STEP 1: Extracting data from Brevo CRM")
    logger.info("=" * 80)

    try:
        brevo_client = BrevoClient(use_mock=use_mock)

        # Use custom time range for testing
        end_time = datetime.now(timezone.utc)
        start_time = end_time - timedelta(days=DAYS_BACK)
        logger.info(f"Time range: {start_time.isoformat()} to {end_time.isoformat()}")

        # Fetch notes
        try:
            logger.info("Fetching notes...")
            notes = brevo_client.get_notes(start_time, end_time)
            logger.info(f"Retrieved {len(notes)} notes")

            logger.info("Enriching notes with company info...")
            notes = brevo_client.enrich_notes_with_companies(notes)
            logger.info("Notes enriched")

        except Exception as e:
            error_msg = f"Error fetching notes: {str(e)}"
            logger.error(error_msg)
            errors.append(error_msg)

        # Fetch deals
        try:
            logger.info("Fetching deals...")
            deals_data = brevo_client.get_deals(start_time, end_time)
            new_count = len(deals_data.get("new_deals", []))
            updated_count = len(deals_data.get("updated_deals", []))
            logger.info(f"Retrieved {new_count} new deals and {updated_count} updated deals")

        except Exception as e:
            error_msg = f"Error fetching deals: {str(e)}"
            logger.error(error_msg)
            errors.append(error_msg)

    except Exception as e:
        error_msg = f"Error initializing Brevo client: {str(e)}"
        logger.error(error_msg)
        errors.append(error_msg)

    # Step 2: Generate summary with OpenAI
    logger.info("\n" + "=" * 80)
    logger.info("STEP 2: Generating summary with OpenAI")
    logger.info("=" * 80)

    summary = None
    try:
        openai_client = OpenAIClient()
        has_deals = bool(deals_data.get("new_deals") or deals_data.get("updated_deals"))

        if not notes and not has_deals:
            logger.info("No CRM activity - generating empty report")
            summary = openai_client.generate_empty_report()
        else:
            logger.info("Generating full summary...")
            summary = openai_client.generate_summary(notes, deals_data)

        logger.info("Summary generated successfully")

    except Exception as e:
        error_msg = f"Error generating summary: {str(e)}"
        logger.error(error_msg)
        errors.append(error_msg)

    # Step 3: Display result (NOT sending to Teams)
    logger.info("\n" + "=" * 80)
    logger.info("STEP 3: FINAL RESULT (NOT sent to Teams)")
    logger.info("=" * 80)

    if summary:
        print("\n" + "=" * 80)
        print("GENERATED SUMMARY:")
        print("=" * 80)
        print(summary)
        print("=" * 80)
    else:
        print("\nNo summary generated")

    if errors:
        print("\nERRORS:")
        for err in errors:
            print(f"  - {err}")

    logger.info("\n" + "=" * 80)
    logger.info("TEST COMPLETED")
    logger.info("=" * 80)


if __name__ == "__main__":
    main()
