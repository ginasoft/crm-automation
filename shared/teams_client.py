"""
Microsoft Teams webhook client for sending formatted reports.
"""
import os
import logging
from typing import Optional
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
        self.webhook_url = webhook_url or os.getenv("Teams-Webhook-URL")

        if not self.webhook_url:
            raise ValueError("Teams-Webhook-URL must be provided or set in environment")

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

        # Create Adaptive Card payload
        # Adaptive Cards support markdown and provide rich formatting in Teams
        payload = {
            "type": "message",
            "attachments": [
                {
                    "contentType": "application/vnd.microsoft.card.adaptive",
                    "contentUrl": None,
                    "content": {
                        "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
                        "type": "AdaptiveCard",
                        "version": "1.4",
                        "body": [
                            {
                                "type": "TextBlock",
                                "text": title,
                                "weight": "Bolder",
                                "size": "Large",
                                "wrap": True
                            },
                            {
                                "type": "TextBlock",
                                "text": summary,
                                "wrap": True
                            }
                        ]
                    }
                }
            ]
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
