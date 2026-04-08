"""
Slack Block Kit Builder - Build Block Kit components from configuration
"""
from typing import Dict, Any, List, Optional


class BlockKitBuilder:
    """
    Utility class for building Slack Block Kit components from configuration.
    Supports modals, messages, buttons, selects, and other interactive elements.
    """

    @staticmethod
    def build_modal(config: Dict[str, Any]) -> Dict[str, Any]:
        """Build a modal view from configuration"""
        modal = {
            "type": "modal",
            "callback_id": config.get('callback_id', 'modal_callback'),
            "title": {
                "type": "plain_text",
                "text": config.get('title', 'Form')[:24]  # Max 24 chars
            },
            "submit": {
                "type": "plain_text",
                "text": config.get('submit_text', 'Submit')[:24]
            },
            "close": {
                "type": "plain_text",
                "text": config.get('close_text', 'Cancel')[:24]
            },
            "blocks": []
        }

        if config.get('private_metadata'):
            modal['private_metadata'] = config['private_metadata']

        # Build blocks from fields
        for field in config.get('fields', []):
            block = BlockKitBuilder._build_input_block(field)
            if block:
                modal['blocks'].append(block)

        return modal

    @staticmethod
    def _build_input_block(field: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Build an input block for modal"""
        field_type = field.get('type', 'text')
        block_id = field.get('id', f"block_{field.get('label', 'input')}")
        action_id = field.get('action_id', f"input_{field.get('label', 'input')}")

        if field_type == 'text':
            return {
                "type": "input",
                "block_id": block_id,
                "optional": not field.get('required', True),
                "label": {
                    "type": "plain_text",
                    "text": field.get('label', 'Input')
                },
                "element": {
                    "type": "plain_text_input",
                    "action_id": action_id,
                    "placeholder": {
                        "type": "plain_text",
                        "text": field.get('placeholder', '')
                    },
                    "multiline": field.get('multiline', False)
                }
            }

        elif field_type == 'select':
            return {
                "type": "input",
                "block_id": block_id,
                "optional": not field.get('required', True),
                "label": {
                    "type": "plain_text",
                    "text": field.get('label', 'Select')
                },
                "element": {
                    "type": "static_select",
                    "action_id": action_id,
                    "placeholder": {
                        "type": "plain_text",
                        "text": field.get('placeholder', 'Choose an option')
                    },
                    "options": [
                        {
                            "text": {"type": "plain_text", "text": opt.get('label', '')},
                            "value": opt.get('value', opt.get('label', ''))
                        }
                        for opt in field.get('options', [])
                    ]
                }
            }

        elif field_type == 'datepicker':
            return {
                "type": "input",
                "block_id": block_id,
                "optional": not field.get('required', True),
                "label": {
                    "type": "plain_text",
                    "text": field.get('label', 'Date')
                },
                "element": {
                    "type": "datepicker",
                    "action_id": action_id,
                    "placeholder": {
                        "type": "plain_text",
                        "text": field.get('placeholder', 'Select a date')
                    }
                }
            }

        return None

    @staticmethod
    def build_message_blocks(config: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Build message blocks from configuration"""
        blocks = []

        # Header section
        if config.get('header'):
            blocks.append({
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": config['header'][:150]
                }
            })

        # Main text section
        if config.get('text'):
            blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": config['text']
                }
            })

        # Fields (side-by-side)
        if config.get('fields'):
            blocks.append({
                "type": "section",
                "fields": [
                    {"type": "mrkdwn", "text": f"*{f.get('label')}*\n{f.get('value')}"}
                    for f in config['fields'][:10]  # Max 10 fields
                ]
            })

        # Image
        if config.get('image_url'):
            blocks.append({
                "type": "image",
                "image_url": config['image_url'],
                "alt_text": config.get('image_alt', 'Image')
            })

        # Divider
        if config.get('divider'):
            blocks.append({"type": "divider"})

        # Actions (buttons, selects)
        if config.get('actions'):
            blocks.append(BlockKitBuilder.build_actions_block(config['actions']))

        # Context (footer-like)
        if config.get('context'):
            blocks.append({
                "type": "context",
                "elements": [
                    {"type": "mrkdwn", "text": config['context']}
                ]
            })

        return blocks

    @staticmethod
    def build_actions_block(actions: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Build an actions block with buttons/selects"""
        elements = []

        for action in actions[:5]:  # Max 5 elements
            action_type = action.get('type', 'button')

            if action_type == 'button':
                elements.append(BlockKitBuilder.build_button(action))
            elif action_type == 'select':
                elements.append(BlockKitBuilder.build_select(action))

        return {
            "type": "actions",
            "elements": elements
        }

    @staticmethod
    def build_button(config: Dict[str, Any]) -> Dict[str, Any]:
        """Build a button element"""
        button = {
            "type": "button",
            "action_id": config.get('action_id', 'button_action'),
            "text": {
                "type": "plain_text",
                "text": config.get('label', 'Button')[:75]
            }
        }

        if config.get('value'):
            button['value'] = config['value']

        if config.get('url'):
            button['url'] = config['url']

        # Style: primary (green), danger (red), or default
        style = config.get('style')
        if style in ('primary', 'danger'):
            button['style'] = style

        if config.get('confirm'):
            button['confirm'] = BlockKitBuilder.build_confirm_dialog(config['confirm'])

        return button

    @staticmethod
    def build_select(config: Dict[str, Any]) -> Dict[str, Any]:
        """Build a select menu element"""
        return {
            "type": "static_select",
            "action_id": config.get('action_id', 'select_action'),
            "placeholder": {
                "type": "plain_text",
                "text": config.get('placeholder', 'Select an option')[:150]
            },
            "options": [
                {
                    "text": {"type": "plain_text", "text": opt.get('label', '')[:75]},
                    "value": opt.get('value', opt.get('label', ''))[:75]
                }
                for opt in config.get('options', [])[:100]  # Max 100 options
            ]
        }

    @staticmethod
    def build_confirm_dialog(config: Dict[str, Any]) -> Dict[str, Any]:
        """Build a confirmation dialog"""
        return {
            "title": {
                "type": "plain_text",
                "text": config.get('title', 'Confirm')[:24]
            },
            "text": {
                "type": "mrkdwn",
                "text": config.get('text', 'Are you sure?')
            },
            "confirm": {
                "type": "plain_text",
                "text": config.get('confirm_text', 'Yes')[:24]
            },
            "deny": {
                "type": "plain_text",
                "text": config.get('deny_text', 'No')[:24]
            }
        }

    @staticmethod
    def build_rich_text(content: str) -> Dict[str, Any]:
        """Build a rich text block"""
        return {
            "type": "rich_text",
            "elements": [
                {
                    "type": "rich_text_section",
                    "elements": [
                        {"type": "text", "text": content}
                    ]
                }
            ]
        }

    @staticmethod
    def build_attachment(config: Dict[str, Any]) -> Dict[str, Any]:
        """Build a message attachment (legacy but still useful)"""
        attachment = {
            "color": config.get('color', '#5865F2'),
            "blocks": BlockKitBuilder.build_message_blocks(config)
        }

        if config.get('fallback'):
            attachment['fallback'] = config['fallback']

        return attachment
