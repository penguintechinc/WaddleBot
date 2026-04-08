# -*- coding: utf-8 -*-
"""Generated protocol buffer message classes for browser_source

Note: These classes are simplified implementations designed to work with grpcio.
For production use, regenerate these files using:
    python -m grpc_tools.protoc -I. --python_out=. --grpc_python_out=. proto/browser_source.proto
"""


class SendCaptionRequest:
    """Message class for SendCaptionRequest"""

    def __init__(self, token='', community_id=0, platform='', username='',
                 original_message='', translated_message='', detected_language='',
                 target_language='', confidence=0.0):
        self.token = token
        self.community_id = community_id
        self.platform = platform
        self.username = username
        self.original_message = original_message
        self.translated_message = translated_message
        self.detected_language = detected_language
        self.target_language = target_language
        self.confidence = confidence

    def SerializeToString(self):
        """Serialize to bytes (placeholder for gRPC)"""
        import json
        data = {
            'token': self.token,
            'community_id': self.community_id,
            'platform': self.platform,
            'username': self.username,
            'original_message': self.original_message,
            'translated_message': self.translated_message,
            'detected_language': self.detected_language,
            'target_language': self.target_language,
            'confidence': self.confidence,
        }
        return json.dumps(data).encode('utf-8')

    @staticmethod
    def FromString(data):
        """Deserialize from bytes"""
        import json
        obj = json.loads(data.decode('utf-8'))
        return SendCaptionRequest(**obj)


class SendOverlayEventRequest:
    """Message class for SendOverlayEventRequest"""

    def __init__(self, token='', community_id=0, event_type='', event_data=''):
        self.token = token
        self.community_id = community_id
        self.event_type = event_type
        self.event_data = event_data

    def SerializeToString(self):
        """Serialize to bytes"""
        import json
        data = {
            'token': self.token,
            'community_id': self.community_id,
            'event_type': self.event_type,
            'event_data': self.event_data,
        }
        return json.dumps(data).encode('utf-8')

    @staticmethod
    def FromString(data):
        """Deserialize from bytes"""
        import json
        obj = json.loads(data.decode('utf-8'))
        return SendOverlayEventRequest(**obj)


class SuccessResponse:
    """Message class for SuccessResponse"""

    def __init__(self, success=False, message='', error=''):
        self.success = success
        self.message = message
        self.error = error

    def SerializeToString(self):
        """Serialize to bytes"""
        import json
        data = {
            'success': self.success,
            'message': self.message,
            'error': self.error,
        }
        return json.dumps(data).encode('utf-8')

    @staticmethod
    def FromString(data):
        """Deserialize from bytes"""
        import json
        obj = json.loads(data.decode('utf-8'))
        return SuccessResponse(**obj)
