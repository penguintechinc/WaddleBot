"""
Adaptive Card Builder - Build Adaptive Card JSON for Microsoft Teams messages
"""
from typing import Dict, Any, List, Optional


class AdaptiveCardBuilder:
    """
    Utility class for building Microsoft Adaptive Cards for Teams messages.
    Supports rich message formatting, nested layouts, and interactive elements.
    """

    @staticmethod
    def build_message_card(text: str, author: Optional[str] = None) -> Dict[str, Any]:
        """Build a simple Adaptive Card with text content.

        Args:
            text: The message text
            author: Optional author/sender name

        Returns:
            Adaptive Card dict (schema version 1.4)
        """
        body = []

        if author:
            body.append({
                "type": "TextBlock",
                "text": f"**{author}**",
                "weight": "bolder",
                "size": "medium"
            })

        body.append({
            "type": "TextBlock",
            "text": text,
            "wrap": True
        })

        return {
            "type": "AdaptiveCard",
            "version": "1.4",
            "body": body
        }

    @staticmethod
    def build_relay_card(content: str, author: Dict[str, Any]) -> Dict[str, Any]:
        """Build an Adaptive Card for bridged messages with author information.

        Args:
            content: The message content
            author: Author dict with 'username' and 'platform' keys

        Returns:
            Adaptive Card dict suitable for mirror relay
        """
        username = author.get('username', 'Unknown')
        platform = author.get('platform', 'hub')
        display_name = author.get('display_name', username)

        return {
            "type": "AdaptiveCard",
            "version": "1.4",
            "body": [
                {
                    "type": "TextBlock",
                    "text": f"{display_name} (via {platform})",
                    "weight": "bolder",
                    "size": "medium",
                    "color": "accent"
                },
                {
                    "type": "TextBlock",
                    "text": content,
                    "wrap": True
                }
            ]
        }

    @staticmethod
    def build_command_response_card(
        title: str,
        body: str,
        fields: Optional[List[Dict[str, str]]] = None
    ) -> Dict[str, Any]:
        """Build an Adaptive Card for command responses.

        Args:
            title: Card title
            body: Main content/body text
            fields: Optional list of {label, value} dicts for side-by-side display

        Returns:
            Adaptive Card dict
        """
        card_body = [
            {
                "type": "TextBlock",
                "text": title,
                "weight": "bolder",
                "size": "large"
            },
            {
                "type": "TextBlock",
                "text": body,
                "wrap": True
            }
        ]

        # Add field columns if provided
        if fields:
            field_items = []
            for field in fields[:10]:  # Limit to 10 fields
                field_items.append({
                    "type": "TextBlock",
                    "text": f"**{field.get('label', '')}**",
                    "weight": "bolder",
                    "size": "small"
                })
                field_items.append({
                    "type": "TextBlock",
                    "text": field.get('value', ''),
                    "wrap": True,
                    "spacing": "small"
                })

            # Group in sets of 2 for columns
            for i in range(0, len(field_items), 2):
                column_items = field_items[i:i+2]
                card_body.append({
                    "type": "Container",
                    "items": column_items
                })

        return {
            "type": "AdaptiveCard",
            "version": "1.4",
            "body": card_body
        }

    @staticmethod
    def build_button_card(
        text: str,
        buttons: List[Dict[str, str]]
    ) -> Dict[str, Any]:
        """Build an Adaptive Card with action buttons.

        Args:
            text: Card text content
            buttons: List of {label, action_id, value, style?} dicts

        Returns:
            Adaptive Card dict with action buttons
        """
        actions = []
        for btn in buttons[:5]:  # Max 5 buttons
            action = {
                "type": "Action.OpenUrl",
                "title": btn.get('label', 'Button'),
                "url": btn.get('value', '#')
            }
            actions.append(action)

        return {
            "type": "AdaptiveCard",
            "version": "1.4",
            "body": [
                {
                    "type": "TextBlock",
                    "text": text,
                    "wrap": True
                }
            ],
            "actions": actions
        }

    @staticmethod
    def build_form_card(
        title: str,
        fields: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Build an Adaptive Card for form input.

        Args:
            title: Form title
            fields: List of field dicts with type, id, label, placeholder, required

        Returns:
            Adaptive Card dict with input elements
        """
        body = [
            {
                "type": "TextBlock",
                "text": title,
                "weight": "bolder",
                "size": "large"
            }
        ]

        for field in fields[:10]:  # Max 10 fields
            field_type = field.get('type', 'text')

            if field_type == 'text':
                body.append({
                    "type": "Input.Text",
                    "id": field.get('id', 'input'),
                    "label": field.get('label', ''),
                    "placeholder": field.get('placeholder', ''),
                    "required": field.get('required', False),
                    "isMultiline": field.get('multiline', False)
                })

            elif field_type == 'select':
                choices = [
                    {"title": opt.get('label', ''), "value": opt.get('value', '')}
                    for opt in field.get('options', [])[:50]
                ]
                body.append({
                    "type": "Input.ChoiceSet",
                    "id": field.get('id', 'select'),
                    "label": field.get('label', ''),
                    "placeholder": field.get('placeholder', ''),
                    "choices": choices,
                    "required": field.get('required', False)
                })

            elif field_type == 'number':
                body.append({
                    "type": "Input.Number",
                    "id": field.get('id', 'number'),
                    "label": field.get('label', ''),
                    "placeholder": field.get('placeholder', ''),
                    "required": field.get('required', False)
                })

        return {
            "type": "AdaptiveCard",
            "version": "1.4",
            "body": body,
            "actions": [
                {
                    "type": "Action.Submit",
                    "title": "Submit"
                }
            ]
        }

    @staticmethod
    def build_error_card(error_message: str, details: Optional[str] = None) -> Dict[str, Any]:
        """Build an error Adaptive Card.

        Args:
            error_message: Main error message
            details: Optional detailed error info

        Returns:
            Adaptive Card dict styled as error
        """
        body = [
            {
                "type": "TextBlock",
                "text": "Error",
                "weight": "bolder",
                "size": "large",
                "color": "attention"
            },
            {
                "type": "TextBlock",
                "text": error_message,
                "wrap": True
            }
        ]

        if details:
            body.append({
                "type": "TextBlock",
                "text": details,
                "wrap": True,
                "size": "small",
                "spacing": "medium",
                "color": "warning"
            })

        return {
            "type": "AdaptiveCard",
            "version": "1.4",
            "body": body
        }
