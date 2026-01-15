"""
OpenAI API client for generating executive summaries from CRM data.
"""
import os
import json
import logging
from typing import Dict, List, Any, Optional
from openai import OpenAI

from .utils import (
    format_report_title,
    get_user_name,
    get_pipeline_name,
    get_stage_name,
    format_company_link,
    format_deal_link,
    format_currency
)

logger = logging.getLogger(__name__)


class OpenAIClient:
    """Client for generating CRM summaries using OpenAI GPT-4."""

    def __init__(self, api_key: Optional[str] = None, model: str = "gpt-5"):
        """
        Initialize OpenAI client.

        Args:
            api_key: OpenAI API key (if None, reads from OPENAI_API_KEY env var)
            model: Model to use (default: gpt-4)
        """
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")

        if not self.api_key:
            raise ValueError("OPENAI_API_KEY must be provided or set in environment")

        self.client = OpenAI(api_key=self.api_key)
        self.model = model

        logger.info(f"OpenAIClient initialized (model={model})")

    def _prepare_notes_context(self, notes: List[Dict[str, Any]]) -> str:
        """
        Prepare notes data as formatted text for the prompt.

        Args:
            notes: List of enriched notes with company data

        Returns:
            str: Formatted notes context
        """
        if not notes:
            return "No notes recorded during this period."

        context_parts = []

        for i, note in enumerate(notes, 1):
            author = get_user_name(note.get("author", "Unknown"))
            text = note.get("text", "No content")
            created_at = note.get("createdAt", "Unknown date")

            # Get company information
            companies = note.get("companies", [])
            company_info = []

            for company in companies:
                company_name = company.get("name", "Unknown")
                company_id = company.get("id", "")
                distributor = company.get("distributor", "N/A")
                business_division = company.get("business_division", "N/A")
                industry = company.get("industry", "N/A")

                company_link = format_company_link(company_id, company_name)

                company_info.append(
                    f"    - Company: {company_link}\n"
                    f"      Distributor: {distributor}\n"
                    f"      Business Division: {business_division}\n"
                    f"      Industry: {industry}"
                )

            companies_str = "\n".join(company_info) if company_info else "    - No associated companies"

            note_entry = (
                f"Note #{i}:\n"
                f"  Author: {author}\n"
                f"  Created: {created_at}\n"
                f"  Content: {text}\n"
                f"  Associated Companies:\n{companies_str}\n"
            )

            context_parts.append(note_entry)

        return "\n".join(context_parts)

    def _prepare_deals_context(self, deals_data: Dict[str, List[Dict[str, Any]]]) -> str:
        """
        Prepare deals data as formatted text for the prompt.

        Args:
            deals_data: Dict with "new_deals" and "updated_deals" keys

        Returns:
            str: Formatted deals context
        """
        new_deals = deals_data.get("new_deals", [])
        updated_deals = deals_data.get("updated_deals", [])

        if not new_deals and not updated_deals:
            return "No deals created or updated during this period."

        context_parts = []

        # Format new deals
        if new_deals:
            context_parts.append("=== NEW DEALS CREATED ===\n")
            for i, deal in enumerate(new_deals, 1):
                deal_name = deal.get("deal_name", "Untitled Deal")
                deal_id = deal.get("id", "")
                owner = get_user_name(deal.get("deal_owner", "Unknown"))
                pipeline_id = deal.get("pipeline_id", "")
                pipeline_name = get_pipeline_name(pipeline_id)
                stage_id = deal.get("deal_stage", "")
                stage_name = get_stage_name(pipeline_id, stage_id)
                amount = format_currency(deal.get("amount", 0))
                distributor = deal.get("distributor", "N/A")
                opportunity_type = deal.get("opportunity_type", "N/A")
                created_at = deal.get("created_at", "Unknown")

                deal_link = format_deal_link(deal_id, deal_name)

                deal_entry = (
                    f"New Deal #{i}:\n"
                    f"  Deal Name: {deal_link}\n"
                    f"  Owner: {owner}\n"
                    f"  Pipeline: {pipeline_name}\n"
                    f"  Stage: {stage_name}\n"
                    f"  Amount: {amount}\n"
                    f"  Distributor: {distributor}\n"
                    f"  Opportunity Type: {opportunity_type}\n"
                    f"  Created: {created_at}\n"
                )

                context_parts.append(deal_entry)

        # Format updated deals
        if updated_deals:
            context_parts.append("\n=== DEALS UPDATED (Stage Changes) ===\n")
            for i, deal in enumerate(updated_deals, 1):
                deal_name = deal.get("deal_name", "Untitled Deal")
                deal_id = deal.get("id", "")
                owner = get_user_name(deal.get("deal_owner", "Unknown"))
                pipeline_id = deal.get("pipeline_id", "")
                pipeline_name = get_pipeline_name(pipeline_id)
                stage_id = deal.get("deal_stage", "")
                stage_name = get_stage_name(pipeline_id, stage_id)
                amount = format_currency(deal.get("amount", 0))
                distributor = deal.get("distributor", "N/A")
                stage_updated_at = deal.get("stage_updated_at", "N/A")

                deal_link = format_deal_link(deal_id, deal_name)

                deal_entry = (
                    f"Updated Deal #{i}:\n"
                    f"  Deal Name: {deal_link}\n"
                    f"  Owner: {owner}\n"
                    f"  Pipeline: {pipeline_name}\n"
                    f"  Current Stage: {stage_name}\n"
                    f"  Amount: {amount}\n"
                    f"  Distributor: {distributor}\n"
                    f"  Stage Updated: {stage_updated_at}\n"
                )

                context_parts.append(deal_entry)

        return "\n".join(context_parts)

    def _build_system_prompt(self) -> str:
        """
        Build the system prompt for GPT-4.

        Returns:
            str: System prompt
        """
        return """You are an executive assistant generating daily CRM summary reports for senior leadership.

Your task is to analyze CRM activity data and create a professional, concise executive summary.

FORMATTING REQUIREMENTS:
1. Use the provided report title format exactly as given
2. Organize all activities by Owner (sales rep name)
3. For each owner, categorize their activities thematically with clear section headings
4. Use action-oriented bullet points (no narrative-style prose)
5. Preserve all markdown hyperlinks for companies and deals exactly as provided
6. Include all relevant attributes (distributor, business division, industry, pipeline, stage, amount, etc.)
7. Make the report easily scannable with clear hierarchy
8. Use professional, concise language appropriate for C-level executives

CONTENT ORGANIZATION:
- Group by Owner first (use ## for owner name as section header)
- Within each owner's section, organize by activity type (e.g., "New Business Development", "Client Meetings", "Deal Progress", "Strategic Initiatives")
- For DEALS: Always show Owner name, Deal name (with link), Stage, Amount, Distributor, and Opportunity Type
- For NOTES: Summarize the specific content and key action items from each note - be detailed and specific about what was discussed or decided
- Summarize key insights or notable patterns at the end

OUTPUT FORMAT:
Use markdown formatting with:
- # for main title
- ## for owner names 
- ### for category headings within each owner section
- Bullet points for individual items
- **Bold** for emphasis on key metrics or outcomes

IMPORTANT FOR NOTES:
- Extract and summarize the SPECIFIC content of each note
- Include key details, action items, decisions, and next steps mentioned
- Do NOT write generic summaries - be specific about what was discussed

Do NOT include:
- Unnecessary pleasantries or conversational language
- Redundant information
- Generic or vague summaries that don't reflect actual note content
"""

    def _build_user_prompt(self, notes: List[Dict[str, Any]],
                          deals_data: Dict[str, List[Dict[str, Any]]]) -> str:
        """
        Build the user prompt with CRM data.

        Args:
            notes: List of enriched notes
            deals_data: Dict with "new_deals" and "updated_deals" keys

        Returns:
            str: User prompt with data
        """
        report_title = format_report_title()
        notes_context = self._prepare_notes_context(notes)
        deals_context = self._prepare_deals_context(deals_data)

        prompt = f"""Generate an executive CRM summary report with the following data:

REPORT TITLE: {report_title}

CRM NOTES:
{notes_context}

DEALS:
{deals_context}

Please generate the executive summary report following all formatting requirements."""

        return prompt

    def generate_summary(self, notes: List[Dict[str, Any]],
                        deals_data: Dict[str, List[Dict[str, Any]]],
                        temperature: float = 0.3) -> str:
        """
        Generate executive summary from CRM data using GPT-4.

        Args:
            notes: List of enriched notes with company data
            deals_data: Dict with "new_deals" and "updated_deals" keys
            temperature: Model temperature (0.0-1.0, lower = more deterministic)
                         Note: gpt-5 model only supports temperature=1

        Returns:
            str: Generated markdown summary

        Raises:
            Exception: If OpenAI API call fails
        """
        new_count = len(deals_data.get("new_deals", []))
        updated_count = len(deals_data.get("updated_deals", []))
        logger.info(f"Generating summary for {len(notes)} notes, {new_count} new deals, "
                   f"{updated_count} updated deals")

        try:
            system_prompt = self._build_system_prompt()
            user_prompt = self._build_user_prompt(notes, deals_data)

            # Build request parameters
            request_params = {
                "model": self.model,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                "max_completion_tokens": 4000
            }

            # gpt-5 model only supports temperature=1, so we set it to 1 or omit it
            # For other models, use the provided temperature
            if self.model == "gpt-5":
                request_params["temperature"] = 1.0
            else:
                request_params["temperature"] = temperature

            response = self.client.chat.completions.create(**request_params)

            summary = response.choices[0].message.content

            logger.info(f"Summary generated successfully ({len(summary)} characters)")
            logger.debug(f"Tokens used: {response.usage.total_tokens}")

            return summary

        except Exception as e:
            logger.error(f"Error generating summary with OpenAI: {e}")
            raise

    def generate_error_summary(self, errors: List[str]) -> str:
        """
        Generate a partial report when some data is unavailable due to errors.

        Args:
            errors: List of error messages

        Returns:
            str: Error summary report
        """
        report_title = format_report_title()

        error_list = "\n".join([f"- {error}" for error in errors])

        summary = f"""# {report_title}

## ⚠️ Partial Report - Errors Encountered

The following errors occurred while generating this report:

{error_list}

Please contact the system administrator to investigate these issues.

**Note:** This is a partial report and may not contain all CRM activity data.
"""

        logger.warning(f"Generated error summary with {len(errors)} errors")
        return summary

    def generate_empty_report(self) -> str:
        """
        Generate report when no activity is found.

        Returns:
            str: Empty report message
        """
        report_title = format_report_title()

        summary = f"""# {report_title}

## No CRM Activity

No notes or deals were created or updated during this reporting period.
"""

        logger.info("Generated empty report")
        return summary
