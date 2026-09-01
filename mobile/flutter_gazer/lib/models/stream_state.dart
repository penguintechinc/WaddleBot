/// Sealed class for RTMP stream states.
sealed class StreamState {
  const StreamState();
}

class StreamDisconnected extends StreamState {
  const StreamDisconnected();
}

class StreamConnecting extends StreamState {
  const StreamConnecting();
}

class StreamConnected extends StreamState {
  final String url;
  const StreamConnected(this.url);
}

class StreamStreaming extends StreamState {
  const StreamStreaming();
}

class StreamError extends StreamState {
  final String message;
  const StreamError(this.message);
}
