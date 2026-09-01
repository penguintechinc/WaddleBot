import Flutter
import AVFoundation
import UIKit

/// Flutter plugin for UVC capture on iPad via AVFoundation external camera API.
/// On iPhone or older iPadOS, returns notSupported — UI shows camera-only mode.
public class UvcCapturePlugin: NSObject, FlutterPlugin, FlutterStreamHandler {
    private var methodChannel: FlutterMethodChannel?
    private var eventChannel: FlutterEventChannel?
    private var eventSink: FlutterEventSink?
    private var textureRegistry: FlutterTextureRegistry?

    private var captureSession: AVCaptureSession?
    private var currentDevice: AVCaptureDevice?
    private var textureId: Int64 = -1

    public static func register(with registrar: FlutterPluginRegistrar) {
        let instance = UvcCapturePlugin()
        instance.textureRegistry = registrar.textures()

        let method = FlutterMethodChannel(
            name: "io.waddlebot.gazer/usb_capture",
            binaryMessenger: registrar.messenger()
        )
        registrar.addMethodCallDelegate(instance, channel: method)
        instance.methodChannel = method

        let event = FlutterEventChannel(
            name: "io.waddlebot.gazer/usb_state",
            binaryMessenger: registrar.messenger()
        )
        event.setStreamHandler(instance)
        instance.eventChannel = event
    }

    public func handle(_ call: FlutterMethodCall, result: @escaping FlutterResult) {
        switch call.method {
        case "scanForDevices":
            scanForDevices(result: result)
        case "connectDevice":
            let args = call.arguments as? [String: Any]
            let name = args?["deviceName"] as? String ?? ""
            connectDevice(name: name, result: result)
        case "disconnectDevice":
            disconnect()
            sendState("disconnected")
            result(true)
        case "startCapture":
            result(true) // capture starts on connect
        case "stopCapture":
            stopCapture()
            result(true)
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

    // MARK: - Device Discovery

    private func scanForDevices(result: FlutterResult) {
        guard isUvcSupported() else {
            sendState("error", extras: ["message": "UVC not supported on this device"])
            result(false)
            return
        }

        if #available(iOS 17.0, *) {
            let discovery = AVCaptureDevice.DiscoverySession(
                deviceTypes: [.external],
                mediaType: .video,
                position: .unspecified
            )
            if let device = discovery.devices.first {
                currentDevice = device
                sendState("found", extras: ["deviceName": device.localizedName])
                result(true)
            } else {
                sendState("disconnected")
                result(false)
            }
        } else {
            sendState("error", extras: ["message": "Requires iPadOS 17+"])
            result(false)
        }
    }

    private func connectDevice(name: String, result: FlutterResult) {
        guard let device = currentDevice else {
            result(FlutterError(code: "NOT_FOUND", message: "No device", details: nil))
            return
        }
        sendState("connecting")

        let session = AVCaptureSession()
        session.sessionPreset = .high
        do {
            let input = try AVCaptureDeviceInput(device: device)
            if session.canAddInput(input) {
                session.addInput(input)
            }
        } catch {
            sendState("error", extras: ["message": error.localizedDescription])
            result(false)
            return
        }

        captureSession = session
        session.startRunning()

        sendState("connected", extras: [
            "deviceName": device.localizedName,
            "textureId": textureId
        ])
        result(true)
    }

    private func disconnect() {
        captureSession?.stopRunning()
        captureSession = nil
        currentDevice = nil
    }

    private func stopCapture() {
        captureSession?.stopRunning()
    }

    private func isUvcSupported() -> Bool {
        // UVC requires iPad with USB-C running iPadOS 17+
        if #available(iOS 17.0, *) {
            return UIDevice.current.userInterfaceIdiom == .pad
        }
        return false
    }

    private func sendState(_ state: String, extras: [String: Any] = [:]) {
        var data: [String: Any] = ["state": state]
        for (k, v) in extras { data[k] = v }
        eventSink?(data)
    }
}
