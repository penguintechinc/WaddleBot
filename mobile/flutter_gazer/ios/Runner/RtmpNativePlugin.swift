import Flutter

/// Flutter plugin wrapping HaishinKit for RTMP streaming on iOS.
/// Provides MethodChannel for control and EventChannel for state updates.
public class RtmpNativePlugin: NSObject, FlutterPlugin, FlutterStreamHandler {
    private var methodChannel: FlutterMethodChannel?
    private var eventChannel: FlutterEventChannel?
    private var eventSink: FlutterEventSink?
    private var isStreaming = false

    public static func register(with registrar: FlutterPluginRegistrar) {
        let instance = RtmpNativePlugin()

        let method = FlutterMethodChannel(
            name: "io.waddlebot.gazer/rtmp",
            binaryMessenger: registrar.messenger()
        )
        registrar.addMethodCallDelegate(instance, channel: method)
        instance.methodChannel = method

        let event = FlutterEventChannel(
            name: "io.waddlebot.gazer/rtmp_state",
            binaryMessenger: registrar.messenger()
        )
        event.setStreamHandler(instance)
        instance.eventChannel = event
    }

    public func handle(_ call: FlutterMethodCall, result: @escaping FlutterResult) {
        switch call.method {
        case "startStreaming":
            let args = call.arguments as? [String: Any] ?? [:]
            let url = args["url"] as? String ?? ""
            startStreaming(url: url, result: result)
        case "stopStreaming":
            stopStreaming()
            result(true)
        case "updateBitrate":
            result(true)
        case "getStreamStats":
            result([
                "isConnected": isStreaming,
                "bitrate": 0,
                "fps": 0,
                "droppedFrames": 0,
                "sentPackets": 0,
                "sentBytes": 0
            ] as [String: Any])
        default:
            result(FlutterMethodNotImplemented)
        }
    }

    // MARK: - FlutterStreamHandler

    public func onListen(withArguments arguments: Any?,
                         eventSink events: @escaping FlutterEventSink) -> FlutterError? {
        self.eventSink = events
        return nil
    }

    public func onCancel(withArguments arguments: Any?) -> FlutterError? {
        self.eventSink = nil
        return nil
    }

    // MARK: - Streaming

    private func startStreaming(url: String, result: FlutterResult) {
        sendState("connecting")
        // TODO: Initialize HaishinKit RTMPConnection + RTMPStream
        isStreaming = true
        sendState("streaming")
        result(true)
    }

    private func stopStreaming() {
        guard isStreaming else { return }
        // TODO: Disconnect HaishinKit
        isStreaming = false
        sendState("disconnected")
    }

    private func sendState(_ state: String, message: String? = nil) {
        var data: [String: Any] = ["state": state]
        if let msg = message { data["message"] = msg }
        eventSink?(data)
    }
}
