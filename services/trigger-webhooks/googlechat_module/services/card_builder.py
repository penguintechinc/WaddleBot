"""
Google Chat Card v2 Builder - Build Card v2 JSON components
Supports messages, interactions, and relay cards
"""
from typing import Dict, Any, List, Optional


class CardBuilder:
    """
    Utility class for building Google Chat Card v2 components.
    Card v2 is the new Google Chat card format with improved styling and interactivity.
    """

    @staticmethod
    def build_message_card(text: str, title: Optional[str] = None) -> Dict[str, Any]:
        """Build a simple text message card (Card v2)"""
        sections = []

        if title:
            sections.append({
                "header": {
                    "title": title,
                }
            })

        sections.append({
            "widgets": [
                {
                    "textParagraph": {
                        "text": text
                    }
                }
            ]
        })

        return {
            "cardsV2": [
                {
                    "cardId": "message_card",
                    "card": {
                        "header": {
                            "title": title or "WaddleBot"
                        },
                        "sections": sections
                    }
                }
            ]
        }

    @staticmethod
    def build_relay_card(config: Dict[str, Any]) -> Dict[str, Any]:
        """Build a relay message card from configuration"""
        title = config.get('title', 'Message')
        content = config.get('content', config.get('text', ''))
        author = config.get('author', {})
        fields = config.get('fields', [])
        actions = config.get('actions', [])

        sections = []

        # Author/header section
        if author:
            sections.append({
                "widgets": [
                    {
                        "textParagraph": {
                            "text": f"<b>From:</b> {author.get('username', 'Unknown')} (via {author.get('platform', 'hub')})"
                        }
                    }
                ]
            })

        # Main content section
        if content:
            sections.append({
                "widgets": [
                    {
                        "textParagraph": {
                            "text": content
                        }
                    }
                ]
            })

        # Fields section (key-value pairs)
        if fields:
            field_widgets = []
            for field in fields[:10]:  # Max 10 fields
                field_text = f"<b>{field.get('label', '')}:</b> {field.get('value', '')}"
                field_widgets.append({
                    "textParagraph": {
                        "text": field_text
                    }
                })
            if field_widgets:
                sections.append({"widgets": field_widgets})

        # Actions section (buttons)
        if actions:
            button_list = []
            for action in actions[:5]:  # Max 5 buttons
                button = CardBuilder._build_button(action)
                if button:
                    button_list.append(button)
            if button_list:
                sections.append({
                    "widgets": [
                        {
                            "buttonList": {
                                "buttons": button_list
                            }
                        }
                    ]
                })

        return {
            "cardsV2": [
                {
                    "cardId": "relay_card",
                    "card": {
                        "header": {
                            "title": title
                        },
                        "sections": sections
                    }
                }
            ]
        }

    @staticmethod
    def build_command_response_card(
        title: str,
        content: str,
        fields: Optional[List[Dict[str, str]]] = None,
        actions: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """Build a command response card"""
        sections = []

        # Main content
        if content:
            sections.append({
                "widgets": [
                    {
                        "textParagraph": {
                            "text": content
                        }
                    }
                ]
            })

        # Optional fields
        if fields:
            field_widgets = []
            for field in fields[:10]:
                field_text = f"<b>{field.get('label', '')}:</b> {field.get('value', '')}"
                field_widgets.append({
                    "textParagraph": {
                        "text": field_text
                    }
                })
            if field_widgets:
                sections.append({"widgets": field_widgets})

        # Optional actions
        if actions:
            button_list = []
            for action in actions[:5]:
                button = CardBuilder._build_button(action)
                if button:
                    button_list.append(button)
            if button_list:
                sections.append({
                    "widgets": [
                        {
                            "buttonList": {
                                "buttons": button_list
                            }
                        }
                    ]
                })

        return {
            "cardsV2": [
                {
                    "cardId": "response_card",
                    "card": {
                        "header": {
                            "title": title
                        },
                        "sections": sections
                    }
                }
            ]
        }

    @staticmethod
    def build_welcome_card() -> Dict[str, Any]:
        """Build a welcome card for when bot is added to space"""
        return {
            "cardsV2": [
                {
                    "cardId": "welcome_card",
                    "card": {
                        "header": {
                            "title": "Welcome to WaddleBot!",
                            "subtitle": "Your AI-powered community bot"
                        },
                        "sections": [
                            {
                                "widgets": [
                                    {
                                        "textParagraph": {
                                            "text": "Hi! I'm WaddleBot, your community assistant. I can help with:\n\n• Running commands\n• Managing forms and polls\n• Creating tickets and reminders\n• And much more!\n\nTry typing <b>/help</b> to see available commands."
                                        }
                                    }
                                ]
                            },
                            {
                                "widgets": [
                                    {
                                        "buttonList": {
                                            "buttons": [
                                                {
                                                    "text": "View Commands",
                                                    "onClick": {
                                                        "action": {
                                                            "actionMethodName": "open_help",
                                                            "parameters": [
                                                                {
                                                                    "key": "command",
                                                                    "value": "help"
                                                                }
                                                            ]
                                                        }
                                                    }
                                                }
                                            ]
                                        }
                                    }
                                ]
                            }
                        ]
                    }
                }
            ]
        }

    @staticmethod
    def build_error_card(error_message: str) -> Dict[str, Any]:
        """Build an error card"""
        return {
            "cardsV2": [
                {
                    "cardId": "error_card",
                    "card": {
                        "header": {
                            "title": "Error",
                        },
                        "sections": [
                            {
                                "widgets": [
                                    {
                                        "textParagraph": {
                                            "text": f"<font color=\"#FF0000\"><b>Error:</b> {error_message}</font>"
                                        }
                                    }
                                ]
                            }
                        ]
                    }
                }
            ]
        }

    @staticmethod
    def _build_button(config: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Build a button element for Card v2"""
        text = config.get('label', config.get('text', 'Button'))
        action_id = config.get('action_id', 'button')

        button = {
            "text": text[:48],  # Google Chat has a limit on button text
            "onClick": {
                "action": {
                    "actionMethodName": action_id,
                    "parameters": []
                }
            }
        }

        # Add parameters
        if config.get('value'):
            button['onClick']['action']['parameters'].append({
                "key": "value",
                "value": str(config['value'])
            })

        # Add style if specified
        if config.get('style') == 'primary':
            button['color'] = {
                "rgba": {
                    "red": 0.25,
                    "green": 0.55,
                    "blue": 0.85,
                    "alpha": 1.0
                }
            }
        elif config.get('style') == 'danger':
            button['color'] = {
                "rgba": {
                    "red": 1.0,
                    "green": 0.0,
                    "blue": 0.0,
                    "alpha": 1.0
                }
            }

        return button

    @staticmethod
    def build_form_card(
        title: str,
        fields: List[Dict[str, Any]],
        submit_text: str = "Submit"
    ) -> Dict[str, Any]:
        """Build a form card with input fields"""
        sections = []

        # Add input fields
        for field in fields[:10]:  # Max 10 fields
            field_type = field.get('type', 'text')

            if field_type == 'text':
                widget = {
                    "textInput": {
                        "label": field.get('label', ''),
                        "name": field.get('name', field.get('id', '')),
                        "hintText": field.get('placeholder', ''),
                        "value": field.get('value', '')
                    }
                }
            elif field_type == 'select':
                widget = {
                    "selectionInput": {
                        "label": field.get('label', ''),
                        "name": field.get('name', field.get('id', '')),
                        "type": "DROPDOWN",
                        "items": [
                            {
                                "text": opt.get('label', opt.get('value', '')),
                                "value": opt.get('value', '')
                            }
                            for opt in field.get('options', [])[:20]  # Max 20 options
                        ]
                    }
                }
            else:
                continue

            sections.append({
                "widgets": [widget]
            })

        # Add submit button
        sections.append({
            "widgets": [
                {
                    "buttonList": {
                        "buttons": [
                            {
                                "text": submit_text,
                                "onClick": {
                                    "action": {
                                        "actionMethodName": "submit_form",
                                        "parameters": []
                                    }
                                }
                            }
                        ]
                    }
                }
            ]
        })

        return {
            "cardsV2": [
                {
                    "cardId": "form_card",
                    "card": {
                        "header": {
                            "title": title
                        },
                        "sections": sections
                    }
                }
            ]
        }

    @staticmethod
    def build_confirmation_dialog(
        title: str,
        message: str,
        confirm_text: str = "Confirm",
        cancel_text: str = "Cancel"
    ) -> Dict[str, Any]:
        """Build a confirmation dialog card"""
        return {
            "cardsV2": [
                {
                    "cardId": "confirmation_card",
                    "card": {
                        "header": {
                            "title": title
                        },
                        "sections": [
                            {
                                "widgets": [
                                    {
                                        "textParagraph": {
                                            "text": message
                                        }
                                    }
                                ]
                            },
                            {
                                "widgets": [
                                    {
                                        "buttonList": {
                                            "buttons": [
                                                {
                                                    "text": confirm_text,
                                                    "onClick": {
                                                        "action": {
                                                            "actionMethodName": "confirm_action",
                                                            "parameters": [
                                                                {
                                                                    "key": "confirmed",
                                                                    "value": "true"
                                                                }
                                                            ]
                                                        }
                                                    }
                                                },
                                                {
                                                    "text": cancel_text,
                                                    "onClick": {
                                                        "action": {
                                                            "actionMethodName": "confirm_action",
                                                            "parameters": [
                                                                {
                                                                    "key": "confirmed",
                                                                    "value": "false"
                                                                }
                                                            ]
                                                        }
                                                    }
                                                }
                                            ]
                                        }
                                    }
                                ]
                            }
                        ]
                    }
                }
            ]
        }
