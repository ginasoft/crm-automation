"""
Brevo CRM API client for extracting notes, companies, and deals.
"""
import os
import json
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any
import requests

from .utils import get_lookback_period, parse_iso_datetime

logger = logging.getLogger(__name__)


class BrevoClient:
    """Client for interacting with Brevo CRM API."""

    BASE_URL = "https://api.brevo.com"

    def __init__(self, api_key: Optional[str] = None, use_mock: bool = False):
        """
        Initialize Brevo API client.

        Args:
            api_key: Brevo API key (if None, reads from BREVO_API_KEY env var)
            use_mock: If True, use mock data instead of real API calls
        """
        self.use_mock = use_mock
        self.api_key = api_key or os.getenv("BREVO_API_KEY")

        if not self.use_mock and not self.api_key:
            raise ValueError("BREVO_API_KEY must be provided or set in environment")

        self.headers = {
            "accept": "application/json",
            "api-key": self.api_key or "mock-key",
            "content-type": "application/json"
        }

        logger.info(f"BrevoClient initialized (mock_mode={use_mock})")

    def _load_mock_data(self) -> Dict[str, Any]:
        """
        Load mock data from tests/mock_data.json.

        Returns:
            Dict containing mock data

        Raises:
            FileNotFoundError: If mock data file doesn't exist
        """
        mock_file = os.path.join(os.path.dirname(__file__), "..", "tests", "mock_data.json")
        logger.info(f"Loading mock data from {mock_file}")

        with open(mock_file, 'r') as f:
            return json.load(f)

    def _differentiate_deals(self, deals: List[Dict[str, Any]], start_time: datetime,
                             end_time: datetime) -> Dict[str, List[Dict[str, Any]]]:
        """
        Differentiate deals into new vs updated based on client requirements.

        New deals: created_at within the time range
        Updated deals: stage_updated_at within the time range but created_at before the range

        Args:
            deals: List of deal dictionaries
            start_time: Start of time range
            end_time: End of time range

        Returns:
            Dict with "new_deals" and "updated_deals" keys
        """
        new_deals = []
        updated_deals = []

        for deal in deals:
            # Parse timestamps
            created_at_str = deal.get("created_at")
            stage_updated_at_str = deal.get("stage_updated_at")

            if not created_at_str:
                logger.warning(f"Deal {deal.get('id')} missing created_at, skipping")
                continue

            created_at = parse_iso_datetime(created_at_str)

            # Check if this is a new deal (created within the time range)
            if start_time <= created_at <= end_time:
                new_deals.append(deal)
                logger.debug(f"Deal {deal.get('deal_name')} classified as NEW "
                           f"(created: {created_at_str})")
            else:
                # Check if it's an updated deal (stage updated within range, but created before)
                if stage_updated_at_str:
                    stage_updated_at = parse_iso_datetime(stage_updated_at_str)
                    if start_time <= stage_updated_at <= end_time:
                        updated_deals.append(deal)
                        logger.debug(f"Deal {deal.get('deal_name')} classified as UPDATED "
                                   f"(stage updated: {stage_updated_at_str})")

        logger.info(f"Differentiated {len(deals)} deals into {len(new_deals)} new, "
                   f"{len(updated_deals)} updated")

        return {
            "new_deals": new_deals,
            "updated_deals": updated_deals
        }

    def _filter_notes(self, notes: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Filter notes according to client requirements:
        1. Only company-level notes (must have companyIds, no contactIds or dealIds)
        2. Exclude Aura AI-generated notes (contains "Generated automatically by Aura" or starts with "Auto-generated")

        Args:
            notes: List of note dictionaries

        Returns:
            List of filtered notes
        """
        filtered_notes = []

        for note in notes:
            # Filter 1: Only company-level notes
            has_company = note.get("companyIds") and len(note.get("companyIds", [])) > 0
            has_contact = note.get("contactIds") and len(note.get("contactIds", [])) > 0
            has_deal = note.get("dealIds") and len(note.get("dealIds", [])) > 0

            if not has_company or has_contact or has_deal:
                logger.debug(f"Filtering out non-company-level note (ID: {note.get('id')})")
                continue

            # Filter 2: Exclude Aura AI-generated notes
            # Check for multiple patterns since Aura notes may contain HTML or different formats
            note_text = note.get("text", "").lower()
            is_aura_note = (
                "generated automatically by aura" in note_text or
                note_text.strip().startswith("auto-generated")
            )
            if is_aura_note:
                logger.debug(f"Filtering out Aura AI-generated note (ID: {note.get('id')})")
                continue

            filtered_notes.append(note)

        logger.info(f"Filtered {len(notes)} notes down to {len(filtered_notes)} company-level, non-Aura notes")
        return filtered_notes

    def _make_request(self, method: str, endpoint: str, **kwargs) -> Dict[str, Any]:
        """
        Make HTTP request to Brevo API.

        Args:
            method: HTTP method (GET, POST, etc.)
            endpoint: API endpoint path
            **kwargs: Additional arguments for requests

        Returns:
            Dict: JSON response

        Raises:
            requests.RequestException: If request fails
        """
        url = f"{self.BASE_URL}{endpoint}"
        logger.debug(f"{method} {url}")

        try:
            response = requests.request(
                method=method,
                url=url,
                headers=self.headers,
                timeout=30,
                **kwargs
            )
            response.raise_for_status()
            return response.json()

        except requests.exceptions.RequestException as e:
            logger.error(f"Brevo API request failed: {e}")
            raise

    def get_notes(self, start_time: Optional[datetime] = None,
                   end_time: Optional[datetime] = None) -> List[Dict[str, Any]]:
        """
        Retrieve CRM notes within the specified time range.

        Filters:
        - Only company-level notes (excludes notes with contactIds or dealIds)
        - Excludes Aura AI-generated notes (ending with "Generated automatically by Aura")

        Args:
            start_time: Start of time range (UTC). If None, uses lookback period.
            end_time: End of time range (UTC). If None, uses lookback period.

        Returns:
            List of note dictionaries with keys:
                - id: Note ID
                - text: Note content
                - author: User ID of note creator
                - companyIds: List of associated company IDs
                - createdAt: ISO datetime string

        Raises:
            requests.RequestException: If API request fails
        """
        if self.use_mock:
            mock_data = self._load_mock_data()
            notes = mock_data['notes']
            # Apply filters to mock data
            notes = self._filter_notes(notes)
            logger.info(f"Using mock notes data ({len(notes)} notes after filtering)")
            return notes

        if start_time is None or end_time is None:
            start_time, end_time = get_lookback_period()

        logger.info(f"Fetching notes from {start_time.isoformat()} to {end_time.isoformat()}")

        all_notes = []
        offset = 0
        limit = 50  # Brevo API pagination limit

        while True:
            params = {
                "offset": offset,
                "limit": limit,
                "sort": "desc"
            }

            try:
                response = self._make_request("GET", "/v3/crm/notes", params=params)
                # Handle both response formats: {"notes": [...]} or {"items": [...]} or direct list
                if isinstance(response, list):
                    notes = response
                else:
                    notes = response.get("items", response.get("notes", []))

                if not notes:
                    break

                # Filter notes by time range
                for note in notes:
                    created_at = parse_iso_datetime(note["createdAt"])

                    if start_time <= created_at <= end_time:
                        all_notes.append(note)
                    elif created_at < start_time:
                        # Notes are sorted by date desc, so we can stop
                        logger.info("Reached notes outside time range, stopping pagination")
                        # Apply filters before returning
                        all_notes = self._filter_notes(all_notes)
                        return all_notes

                offset += limit

                # Safety check to prevent infinite loops
                if offset > 1000:
                    logger.warning("Reached pagination safety limit (1000 notes)")
                    break

            except Exception as e:
                logger.error(f"Error fetching notes at offset {offset}: {e}")
                raise

        # Apply filters before returning
        all_notes = self._filter_notes(all_notes)
        logger.info(f"Retrieved {len(all_notes)} notes within time range (after filtering)")
        return all_notes

    def get_company(self, company_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve company details by ID.

        Args:
            company_id: Brevo company ID

        Returns:
            Dict with company attributes:
                - id: Company ID
                - name: Company name
                - distributor: Distribution channel
                - business_division: Business unit (from business_division_2 attribute in Brevo)
                - industry: Industry classification
            Returns None if company not found.

        Raises:
            requests.RequestException: If API request fails
        """
        if self.use_mock:
            mock_data = self._load_mock_data()
            company = next((c for c in mock_data['companies'] if c['id'] == company_id), None)

            if company:
                logger.debug(f"Found mock company: {company.get('name')}")
            else:
                logger.warning(f"Mock company {company_id} not found")

            return company

        logger.debug(f"Fetching company {company_id}")

        try:
            response = self._make_request("GET", f"/v3/companies/{company_id}")

            # Extract relevant attributes
            attributes = response.get("attributes", {})

            company_data = {
                "id": response.get("id"),
                "name": attributes.get("name", "Unknown Company"),
                "distributor": attributes.get("distributor"),
                "business_division": attributes.get("business_division_2"),
                "industry": attributes.get("industry")
            }

            logger.debug(f"Retrieved company: {company_data['name']}")
            return company_data

        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 404:
                logger.warning(f"Company {company_id} not found")
                return None
            raise

    def get_deals(self, start_time: Optional[datetime] = None,
                  end_time: Optional[datetime] = None) -> Dict[str, List[Dict[str, Any]]]:
        """
        Retrieve CRM deals created or updated within the specified time range.

        Args:
            start_time: Start of time range (UTC). If None, uses lookback period.
            end_time: End of time range (UTC). If None, uses lookback period.

        Returns:
            Dict with two keys:
                - "new_deals": Deals created within the time range
                - "updated_deals": Deals with stage updates within the time range (but created earlier)

            Each deal dict contains:
                - id: Deal ID
                - deal_name: Deal title
                - deal_owner: User ID of assigned sales rep
                - deal_stage: Current pipeline stage ID
                - pipeline_id: Pipeline ID
                - distributor: Distribution channel
                - amount: Deal value
                - yearly_spend_amount: Yearly spend amount
                - opportunity_type: Deal category
                - created_at: ISO datetime string
                - stage_updated_at: ISO datetime string
                - modified_at: ISO datetime string

        Raises:
            requests.RequestException: If API request fails
        """
        if self.use_mock:
            mock_data = self._load_mock_data()
            all_deals = mock_data['deals']
            # Apply differentiation to mock data
            result = self._differentiate_deals(all_deals, start_time or get_lookback_period()[0],
                                               end_time or get_lookback_period()[1])
            logger.info(f"Using mock deals data ({len(result['new_deals'])} new, "
                       f"{len(result['updated_deals'])} updated)")
            return result

        if start_time is None or end_time is None:
            start_time, end_time = get_lookback_period()

        logger.info(f"Fetching deals from {start_time.isoformat()} to {end_time.isoformat()}")

        all_deals = []
        offset = 0
        limit = 50

        while True:
            params = {
                "offset": offset,
                "limit": limit,
                "sort": "desc"
            }

            try:
                response = self._make_request("GET", "/v3/crm/deals", params=params)
                # Handle both response formats: {"deals": [...]} or {"items": [...]} or direct list
                if isinstance(response, list):
                    deals = response
                else:
                    deals = response.get("items", response.get("deals", []))

                if not deals:
                    break

                # Filter deals by creation or modification time
                for deal in deals:
                    # Handle both formats: attributes nested or flat structure
                    if "attributes" in deal:
                        attributes = deal.get("attributes", {})
                    else:
                        attributes = deal  # Fields are directly on deal object

                    # Parse timestamps - try multiple field names
                    created_at_str = attributes.get("created_at") or attributes.get("createdAt") or deal.get("createdAt")
                    created_at = parse_iso_datetime(created_at_str) if created_at_str else None

                    if not created_at:
                        logger.warning(f"Deal missing created_at timestamp, skipping: {deal.get('id')}")
                        continue
                    # Brevo uses "last_updated_date" for modification timestamp
                    modified_at_str = attributes.get("last_updated_date") or attributes.get("modified_at") or attributes.get("modifiedAt")

                    if modified_at_str:
                        modified_at = parse_iso_datetime(modified_at_str)
                    else:
                        modified_at = created_at

                    # Parse stage_updated_at for filtering
                    stage_updated_at_str = attributes.get("stage_updated_at")
                    stage_updated_at = parse_iso_datetime(stage_updated_at_str) if stage_updated_at_str else None

                    # Include if created, modified, or stage updated in time range
                    # This ensures we capture both new deals AND deals with stage changes
                    in_time_range = (
                        (start_time <= created_at <= end_time) or
                        (start_time <= modified_at <= end_time) or
                        (stage_updated_at and start_time <= stage_updated_at <= end_time)
                    )

                    if in_time_range:
                        # Extract deal_type from Brevo attributes
                        deal_type_value = attributes.get("deal_type")

                        deal_data = {
                            "id": deal.get("id"),
                            "deal_name": attributes.get("deal_name") or "Untitled Deal",
                            "deal_owner": attributes.get("deal_owner"),
                            "deal_stage": attributes.get("deal_stage"),
                            "pipeline_id": attributes.get("pipeline"),
                            "distributor": attributes.get("distributor"),
                            "amount": attributes.get("amount", 0),
                            "yearly_spend_amount": attributes.get("yearly_spend_amount", 0),
                            "deal_type": deal_type_value,  # Store deal_type directly (Brevo attribute name)
                            "opportunity_type": deal_type_value,  # Also store as opportunity_type for backward compatibility
                            "created_at": created_at_str,
                            "stage_updated_at": stage_updated_at_str,
                            "modified_at": modified_at_str or attributes.get("last_updated_date")
                        }

                        all_deals.append(deal_data)

                offset += limit

                # Safety check
                if offset > 1000:
                    logger.warning("Reached pagination safety limit (1000 deals)")
                    break

            except Exception as e:
                logger.error(f"Error fetching deals at offset {offset}: {e}")
                raise

        # Differentiate new deals from updated deals
        result = self._differentiate_deals(all_deals, start_time, end_time)
        logger.info(f"Retrieved {len(result['new_deals'])} new deals and "
                   f"{len(result['updated_deals'])} updated deals")
        return result

    def enrich_notes_with_companies(self, notes: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Enrich notes with company information.

        Args:
            notes: List of note dictionaries

        Returns:
            List of notes with added 'companies' field containing company details
        """
        enriched_notes = []

        for note in notes:
            enriched_note = note.copy()
            company_ids = note.get("companyIds", [])

            if company_ids:
                companies = []
                for company_id in company_ids:
                    try:
                        company = self.get_company(company_id)
                        if company:
                            companies.append(company)
                    except Exception as e:
                        logger.error(f"Error fetching company {company_id}: {e}")
                        # Continue processing other companies

                enriched_note["companies"] = companies
            else:
                enriched_note["companies"] = []

            enriched_notes.append(enriched_note)

        logger.info(f"Enriched {len(enriched_notes)} notes with company data")
        return enriched_notes
