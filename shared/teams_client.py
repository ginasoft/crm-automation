"""
Microsoft Teams webhook client for sending formatted reports.
"""
import os
import logging
import time
from typing import Optional, List, Tuple
import requests

logger = logging.getLogger(__name__)


class TeamsClient:
    """Client for sending messages to Microsoft Teams via webhook."""

    def __init__(self, webhook_url: Optional[str] = None):
        """
        Initialize Teams webhook client.

        Args:
            webhook_url: Teams webhook URL (if None, reads from TEAMS_WEBHOOK_URL env var)
        """
        self.webhook_url = webhook_url or os.getenv("TEAMS_WEBHOOK_URL")

        if not self.webhook_url:
            raise ValueError("TEAMS_WEBHOOK_URL must be provided or set in environment")

        logger.info("TeamsClient initialized")

    def send_report(self, summary: str, title: Optional[str] = None) -> bool:
        """
        Send report summary to Teams channel.

        Args:
            summary: Markdown-formatted report content
            title: Optional message title (defaults to "CRM Daily Report")

        Returns:
            bool: True if sent successfully, False otherwise

        Raises:
            requests.RequestException: If webhook request fails
        """
        if not title:
            title = "CRM Daily Report"

        logger.info(f"Sending report to Teams: {title}")

        # Use simple message format which supports markdown links
        # Format: [text](url) renders as clickable links in Teams
        full_message = f"**{title}**\n\n{summary}"

        payload = {
            "text": full_message
        }

        try:
            response = requests.post(
                self.webhook_url,
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=30
            )

            response.raise_for_status()

            logger.info(f"Report sent successfully to Teams (status: {response.status_code})")
            return True

        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to send report to Teams: {e}")
            raise

    def send_two_part_report(self, parts: List[Tuple[str, str]], delay: float = 2.0) -> bool:
        """
        Send a multi-part report to Teams as sequential messages.

        Args:
            parts: List of (title, summary) tuples to send in order
            delay: Seconds to wait between messages to preserve ordering

        Returns:
            bool: True if all parts sent successfully

        Raises:
            requests.RequestException: If any webhook request fails
        """
        logger.info(f"Sending {len(parts)}-part report to Teams")

        for i, (title, summary) in enumerate(parts, 1):
            logger.info(f"Sending part {i}/{len(parts)}: {title}")
            self.send_report(summary, title=title)

            # Small delay between messages to ensure Teams preserves order
            if i < len(parts):
                logger.info(f"Waiting {delay}s before sending next part...")
                time.sleep(delay)

        logger.info("All parts sent successfully")
        return True

    def send_simple_message(self, text: str) -> bool:
        """
        Send a simple text message to Teams (without Adaptive Card).

        Useful for error notifications or simple alerts.

        Args:
            text: Message text

        Returns:
            bool: True if sent successfully, False otherwise

        Raises:
            requests.RequestException: If webhook request fails
        """
        logger.info("Sending simple message to Teams")

        payload = {
            "text": text
        }

        try:
            response = requests.post(
                self.webhook_url,
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=30
            )

            response.raise_for_status()

            logger.info(f"Message sent successfully to Teams (status: {response.status_code})")
            return True

        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to send message to Teams: {e}")
            raise

    def send_error_notification(self, error_message: str,
                               context: Optional[str] = None) -> bool:
        """
        Send error notification to Teams.

        Args:
            error_message: Error description
            context: Optional additional context

        Returns:
            bool: True if sent successfully, False otherwise
        """
        logger.info("Sending error notification to Teams")

        text = f"⚠️ **CRM Automation Error**\n\n{error_message}"

        if context:
            text += f"\n\n**Context:** {context}"

        text += "\n\nPlease check the Azure Function logs for more details."

        try:
            return self.send_simple_message(text)
        except Exception as e:
            logger.error(f"Failed to send error notification: {e}")
            return False
