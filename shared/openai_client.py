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
                yearly_spend_amount = format_currency(formatted_deal.get("yearly_spend_amount", 0))
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
                    f"  Yearly Spend: {yearly_spend_amount}\n"
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
                yearly_spend_amount = format_currency(formatted_deal.get("yearly_spend_amount", 0))
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
                    f"  Yearly Spend: {yearly_spend_amount}\n"
                    f"  Distributor: {distributor}\n"
                    f"  Opportunity Type: {opportunity_type}\n"
                    f"  Stage Updated: {stage_updated_at}\n"
                )

                context_parts.append(deal_entry)

        return "\n".join(context_parts)

    def _build_notes_system_prompt(self) -> str:
        """
        Build the system prompt for Part 1 (Notes only).

        Returns:
            str: System prompt for notes summary
        """
        return """You are an executive assistant generating daily CRM summary reports.

Create a brief, factual summary of CRM notes activity following the exact structure and formatting below. This will be posted in Microsoft Teams (including mobile). Readability is critical.

STRUCTURE (must follow exactly):

1) First line: CRM Daily Executive Summary (1/2)
2) Second line: {REPORT TITLE}
3) Blank line

4) Highlights
- Total Notes: X
- Notes by user: {Name}: X, {Name}: X, ...
Blank line

5) Notes Summary
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

FORMATTING RULES (must follow exactly):
- Output the header line CRM Daily Executive Summary (1/2) only once. Do not repeat it.
- A "blank line" means one empty line (two newline characters in a row).
- Bullets must start at the beginning of the line with "- " (no leading spaces)
- Attribute lines must be on their own lines and indented by exactly two spaces
- After every author line, include exactly one blank line before the first bullet
- Never put a section heading and a name on the same line
- The line containing a markdown link must contain ONLY the link and must end immediately after the closing ")". No extra characters after the link. No period, comma, colon, dash, or trailing spaces.
- Preserve all markdown hyperlinks exactly as provided in the data
- Bold only for: section headings, author names
- If any field is missing, write "None"
- Note summaries must be factual and short
- For notes created by "Solutions" only: if the first word of the note is a name followed by a colon, treat that name as required context and always include it in the summary. Never omit or replace the name

EXAMPLE OF REQUIRED ITEM FORMATTING (spacing matters exactly):
- [Example Company](URL)
Business Division: PACA
Distributor: Wurth Canada
Note: Discussed pricing for new product line
"""

    def _build_deals_system_prompt(self) -> str:
        """
        Build the system prompt for Part 2 (Deals only).

        Returns:
            str: System prompt for deals summary
        """
        return """You are an executive assistant generating daily CRM summary reports.

Create a brief, factual summary of CRM deals activity following the exact structure and formatting below. This will be posted in Microsoft Teams (including mobile). Readability is critical.

STRUCTURE (must follow exactly):

1) First line: CRM Daily Executive Summary (2/2)
2) Second line: {REPORT TITLE}
3) Blank line

4) Highlights
- New Deals: X
- Updated Deals: Y
Blank line

5) New Deals
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

6) Updated Deals
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
- Output the header line CRM Daily Executive Summary (2/2) only once. Do not repeat it.
- A "blank line" means one empty line (two newline characters in a row).
- Bullets must start at the beginning of the line with "- " (no leading spaces)
- Attribute lines must be on their own lines and indented by exactly two spaces
- After every owner line, include exactly one blank line before the first bullet
- Never put a section heading and a name on the same line
- The line containing a markdown link must contain ONLY the link and must end immediately after the closing ")". No extra characters after the link. No period, comma, colon, dash, or trailing spaces.
- Preserve all markdown hyperlinks exactly as provided in the data
- Bold only for: section headings, owner names, Stage values, Amount values
- If any field is missing, write "None"

EXAMPLE OF REQUIRED ITEM FORMATTING (spacing matters exactly):
- [Example Deal](URL)
Deal Type: Reactivation
Distributor: Wurth Canada
Stage: Identified
Amount: $0.00
"""

    def _build_notes_user_prompt(self, notes: List[Dict[str, Any]]) -> str:
        """
        Build the user prompt for Part 1 (Notes only).

        Args:
            notes: List of enriched notes

        Returns:
            str: User prompt with notes data
        """
        report_title = format_report_title()
        notes_context = self._prepare_notes_context(notes)

        prompt = f"""Generate the Notes part of the CRM executive summary with the following data:

REPORT TITLE: {report_title}

CRM NOTES:
{notes_context}

Please generate the notes summary report following all formatting requirements."""

        return prompt

    def _build_deals_user_prompt(self, deals_data: Dict[str, List[Dict[str, Any]]]) -> str:
        """
        Build the user prompt for Part 2 (Deals only).

        Args:
            deals_data: Dict with "new_deals" and "updated_deals" keys

        Returns:
            str: User prompt with deals data
        """
        report_title = format_report_title()
        deals_context = self._prepare_deals_context(deals_data)

        prompt = f"""Generate the Deals part of the CRM executive summary with the following data:

REPORT TITLE: {report_title}

DEALS:
{deals_context}

Please generate the deals summary report following all formatting requirements."""

        return prompt

    # Token limits: initial cap and retry cap when output is truncated
    _INITIAL_MAX_TOKENS = 24000
    _RETRY_MAX_TOKENS = 32000

    def _call_openai(self, system_prompt: str, user_prompt: str,
                     temperature: float = 0.3, label: str = "summary") -> str:
        """
        Make an OpenAI API call and return the response content.
        If the response is truncated (finish_reason=length), retries once
        with a higher token cap to avoid sending incomplete reports.

        Args:
            system_prompt: System prompt
            user_prompt: User prompt
            temperature: Model temperature (gpt-5 forces 1.0)
            label: Label for logging

        Returns:
            str: Generated response content

        Raises:
            Exception: If OpenAI API call fails
        """
        # Log the data being sent to AI for debugging
        logger.info("=" * 60)
        logger.info(f"DATA BEING SENT TO AI ({label}):")
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
            "max_completion_tokens": self._INITIAL_MAX_TOKENS
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
        content = choice.message.content or ""

        logger.info(f"OpenAI finish_reason ({label}): {finish_reason}")
        logger.info(f"Tokens used ({label}): prompt={response.usage.prompt_tokens}, "
                   f"completion={response.usage.completion_tokens}, "
                   f"total={response.usage.total_tokens}")

        # Retry once with a higher cap if the output was truncated
        if finish_reason == "length":
            logger.warning(f"Output truncated ({label}), retrying with "
                         f"max_completion_tokens={self._RETRY_MAX_TOKENS}")
            request_params["max_completion_tokens"] = self._RETRY_MAX_TOKENS
            response = self.client.chat.completions.create(**request_params)

            choice = response.choices[0]
            finish_reason = choice.finish_reason
            content = choice.message.content or ""

            logger.info(f"OpenAI retry finish_reason ({label}): {finish_reason}")
            logger.info(f"Retry tokens used ({label}): prompt={response.usage.prompt_tokens}, "
                       f"completion={response.usage.completion_tokens}, "
                       f"total={response.usage.total_tokens}")

            if finish_reason == "length":
                logger.warning(f"Output still truncated after retry ({label}), "
                             f"returning best-effort content")

        if not content:
            logger.error(f"OpenAI returned empty content ({label}). finish_reason={finish_reason}, "
                       f"refusal={choice.message.refusal if hasattr(choice.message, 'refusal') else 'N/A'}")
            raise Exception(f"OpenAI returned empty response (finish_reason={finish_reason})")

        logger.info(f"{label} generated successfully ({len(content)} characters)")

        return content

    def generate_notes_summary(self, notes: List[Dict[str, Any]],
                               temperature: float = 0.3) -> str:
        """
        Generate Part 1: Notes summary.

        Args:
            notes: List of enriched notes with company data
            temperature: Model temperature (gpt-5 forces 1.0)

        Returns:
            str: Generated notes summary (Part 1/2)

        Raises:
            Exception: If OpenAI API call fails
        """
        logger.info(f"Generating notes summary for {len(notes)} notes")

        try:
            system_prompt = self._build_notes_system_prompt()
            user_prompt = self._build_notes_user_prompt(notes)
            return self._call_openai(system_prompt, user_prompt, temperature, label="notes-part1")

        except Exception as e:
            logger.error(f"Error generating notes summary: {e}")
            raise

    def generate_deals_summary(self, deals_data: Dict[str, List[Dict[str, Any]]],
                               temperature: float = 0.3) -> str:
        """
        Generate Part 2: Deals summary.

        Args:
            deals_data: Dict with "new_deals" and "updated_deals" keys
            temperature: Model temperature (gpt-5 forces 1.0)

        Returns:
            str: Generated deals summary (Part 2/2)

        Raises:
            Exception: If OpenAI API call fails
        """
        new_count = len(deals_data.get("new_deals", []))
        updated_count = len(deals_data.get("updated_deals", []))
        logger.info(f"Generating deals summary for {new_count} new deals, "
                   f"{updated_count} updated deals")

        try:
            system_prompt = self._build_deals_system_prompt()
            user_prompt = self._build_deals_user_prompt(deals_data)
            return self._call_openai(system_prompt, user_prompt, temperature, label="deals-part2")

        except Exception as e:
            logger.error(f"Error generating deals summary: {e}")
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
