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
    format_currency,
    format_note_for_display,
    format_deal_for_display
)

logger = logging.getLogger(__name__)


class OpenAIClient:

    def __init__(self, api_key: Optional[str] = None, model: str = "gpt-5"):
        """
        Initialize OpenAI client.

        Args:
            api_key: OpenAI API key (if None, reads from OPENAI_API_KEY env var)
            model: Model to use 
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
        Applies display formatting to convert raw API keys to display names.

        Args:
            notes: List of enriched notes with company data

        Returns:
            str: Formatted notes context
        """
        if not notes:
            return "No notes recorded during this period."

        context_parts = []

        for i, note in enumerate(notes, 1):
            # Format note to convert raw API keys to display names
            formatted_note = format_note_for_display(note)
            
            author = get_user_name(formatted_note.get("author", "Unknown"))
            text = formatted_note.get("text", "No content")
            created_at = formatted_note.get("createdAt", "Unknown date")

            # Get company information (already formatted)
            companies = formatted_note.get("companies", [])
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
        Applies display formatting to convert raw API keys to display names.

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
                # Format deal to convert raw API keys to display names
                formatted_deal = format_deal_for_display(deal)
                
                deal_name = formatted_deal.get("deal_name", "Untitled Deal")
                deal_id = formatted_deal.get("id", "")
                owner = get_user_name(formatted_deal.get("deal_owner", "Unknown"))
                pipeline_id = formatted_deal.get("pipeline_id", "")
                pipeline_name = get_pipeline_name(pipeline_id)
                stage_id = formatted_deal.get("deal_stage", "")
                stage_name = get_stage_name(pipeline_id, stage_id)
                amount = format_currency(formatted_deal.get("amount", 0))
                distributor = formatted_deal.get("distributor", "N/A")
                # Check both deal_type and opportunity_type (Brevo uses deal_type)
                opportunity_type = formatted_deal.get("deal_type") or formatted_deal.get("opportunity_type", "N/A")
                created_at = formatted_deal.get("created_at", "Unknown")

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
                # Format deal to convert raw API keys to display names
                formatted_deal = format_deal_for_display(deal)
                
                deal_name = formatted_deal.get("deal_name", "Untitled Deal")
                deal_id = formatted_deal.get("id", "")
                owner = get_user_name(formatted_deal.get("deal_owner", "Unknown"))
                pipeline_id = formatted_deal.get("pipeline_id", "")
                pipeline_name = get_pipeline_name(pipeline_id)
                stage_id = formatted_deal.get("deal_stage", "")
                stage_name = get_stage_name(pipeline_id, stage_id)
                amount = format_currency(formatted_deal.get("amount", 0))
                distributor = formatted_deal.get("distributor", "N/A")
                # Check both deal_type and opportunity_type (Brevo uses deal_type)
                # This fixes the issue where deal_type was not being passed to updated deals
                opportunity_type = formatted_deal.get("deal_type") or formatted_deal.get("opportunity_type", "N/A")
                stage_updated_at = formatted_deal.get("stage_updated_at", "N/A")

                deal_link = format_deal_link(deal_id, deal_name)

                deal_entry = (
                    f"Updated Deal #{i}:\n"
                    f"  Deal Name: {deal_link}\n"
                    f"  Owner: {owner}\n"
                    f"  Pipeline: {pipeline_name}\n"
                    f"  Current Stage: {stage_name}\n"
                    f"  Amount: {amount}\n"
                    f"  Distributor: {distributor}\n"
                    f"  Opportunity Type: {opportunity_type}\n"
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
        return """You are an executive assistant generating daily CRM summary reports.



Create a brief, factual summary of CRM activity following the exact structure and formatting below. This will be posted in Microsoft Teams (including mobile). Readability is critical.

STRUCTURE (must follow exactly):

1) First line: CRM Daily Executive Summary
2) Second line: {REPORT TITLE}
3) Blank line

4) Highlights
- Notes: X
- New deals: Y
- Updated deals: Z
Blank line

5) CRM Notes
Group by Author. For each author:
{Author Name}
Blank line

For each note (repeat as needed):
- [Company name](URL)
Business Division: {Business Division}
Distributor: {Distributor}
Note: {Note summary}

Blank line between notes
Blank line between authors
If none: None
Blank line

6) New Deals
Group by Owner. For each owner:
{Owner Name}
Blank line

For each deal (repeat as needed):
- [Deal name](URL)
Deal Type: {Deal Type}
Distributor: {Distributor}
Stage: {Stage}
Amount: {Amount}

Blank line between deals
Blank line between owners
If none: None
Blank line

7) Updated Deals
Group by Owner. For each owner:
{Owner Name}
Blank line

For each deal (repeat as needed):
- [Deal name](URL)
Deal Type: {Deal Type}
Distributor: {Distributor}
Stage: {Stage}
Amount: {Amount}

Blank line between deals
Blank line between owners
If none: None

FORMATTING RULES (must follow exactly):
- Output the header line CRM Daily Executive Summary only once. Do not repeat it.
- A "blank line" means one empty line (two newline characters in a row).
- Bullets must start at the beginning of the line with "- " (no leading spaces)
- Attribute lines must be on their own lines and indented by exactly two spaces
- After every author/owner line, include exactly one blank line before the first bullet
- Never put a section heading and a name on the same line
- The line containing a markdown link must contain ONLY the link and must end immediately after the closing ")". No extra characters after the link. No period, comma, colon, dash, or trailing spaces.
- Preserve all markdown hyperlinks exactly as provided in the data
- Bold only for: section headings, author/owner names, Stage values, Amount values
- If any field is missing, write "None"
- Note summaries must be factual and short
- For notes created by "Solutions" only: if the first word of the note is a name followed by a colon, treat that name as required context and always include it in the summary. Never omit or replace the name

EXAMPLE OF REQUIRED ITEM FORMATTING (spacing matters exactly):
- [Example Deal](URL)
Deal Type: Reactivation
Distributor: Wurth Canada
Stage: Identified
Amount: $0.00
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

            # Log the data being sent to AI for debugging
            logger.info("=" * 60)
            logger.info("DATA BEING SENT TO AI:")
            logger.info("=" * 60)
            logger.info(f"USER PROMPT:\n{user_prompt}")
            logger.info("=" * 60)

            # Build request parameters
            request_params = {
                "model": self.model,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                "max_completion_tokens": 24000
            }

            # gpt-5 model only supports temperature=1, so we set it to 1 or omit it
            # For other models, use the provided temperature
            if self.model == "gpt-5":
                request_params["temperature"] = 1.0
            else:
                request_params["temperature"] = temperature

            response = self.client.chat.completions.create(**request_params)

            # Log response details for debugging
            choice = response.choices[0]
            finish_reason = choice.finish_reason
            summary = choice.message.content or ""

            logger.info(f"OpenAI finish_reason: {finish_reason}")
            logger.info(f"Tokens used: prompt={response.usage.prompt_tokens}, "
                       f"completion={response.usage.completion_tokens}, "
                       f"total={response.usage.total_tokens}")

            if not summary:
                logger.error(f"OpenAI returned empty content. finish_reason={finish_reason}, "
                           f"refusal={choice.message.refusal if hasattr(choice.message, 'refusal') else 'N/A'}")
                raise Exception(f"OpenAI returned empty response (finish_reason={finish_reason})")

            logger.info(f"Summary generated successfully ({len(summary)} characters)")

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
