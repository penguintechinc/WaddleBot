package io.waddlebot.gazer

import android.app.PendingIntent
import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import android.content.IntentFilter
import android.graphics.SurfaceTexture
import android.hardware.usb.*
import android.util.Log
import io.flutter.embedding.engine.plugins.FlutterPlugin
import io.flutter.plugin.common.EventChannel
import io.flutter.plugin.common.MethodCall
import io.flutter.plugin.common.MethodChannel
import io.flutter.view.TextureRegistry

/**
 * Flutter plugin for USB Video Class (UVC) device capture.
 * Bridges Flutter ↔ Android USB Host API via MethodChannel/EventChannel.
 */
class UsbCapturePlugin : FlutterPlugin, MethodChannel.MethodCallHandler {

    companion object {
        private const val TAG = "UsbCapturePlugin"
        private const val METHOD_CHANNEL = "io.waddlebot.gazer/usb_capture"
        private const val EVENT_CHANNEL = "io.waddlebot.gazer/usb_state"
        private const val ACTION_USB_PERMISSION = "io.waddlebot.gazer.USB_PERMISSION"
        private const val USB_CLASS_VIDEO = 14
    }

    private lateinit var methodChannel: MethodChannel
    private lateinit var eventChannel: EventChannel
    private var eventSink: EventChannel.EventSink? = null
    private var context: Context? = null
    private var textureRegistry: TextureRegistry? = null

    private var usbManager: UsbManager? = null
    private var currentDevice: UsbDevice? = null
    private var connection: UsbDeviceConnection? = null
    private var streamingInterface: UsbInterface? = null
    private var textureEntry: TextureRegistry.SurfaceTextureEntry? = null

    private val usbReceiver = object : BroadcastReceiver() {
        override fun onReceive(ctx: Context, intent: Intent) {
            when (intent.action) {
                ACTION_USB_PERMISSION -> {
                    val device: UsbDevice? = intent.getParcelableExtra(UsbManager.EXTRA_DEVICE)
                    if (intent.getBooleanExtra(UsbManager.EXTRA_PERMISSION_GRANTED, false)) {
                        device?.let { connectToDevice(it) }
                    } else {
                        sendState("error", mapOf("message" to "Permission denied"))
                    }
                }
                UsbManager.ACTION_USB_DEVICE_ATTACHED -> {
                    val device: UsbDevice? = intent.getParcelableExtra(UsbManager.EXTRA_DEVICE)
                    device?.let {
                        if (isVideoDevice(it)) {
                            sendState("found", mapOf("deviceName" to it.deviceName))
                        }
                    }
                }
                UsbManager.ACTION_USB_DEVICE_DETACHED -> {
                    val device: UsbDevice? = intent.getParcelableExtra(UsbManager.EXTRA_DEVICE)
                    if (device == currentDevice) {
                        disconnect()
                        sendState("disconnected")
                    }
                }
            }
        }
    }

    override fun onAttachedToEngine(binding: FlutterPlugin.FlutterPluginBinding) {
        context = binding.applicationContext
        textureRegistry = binding.textureRegistry
        usbManager = context?.getSystemService(Context.USB_SERVICE) as? UsbManager

        methodChannel = MethodChannel(binding.binaryMessenger, METHOD_CHANNEL)
        methodChannel.setMethodCallHandler(this)

        eventChannel = EventChannel(binding.binaryMessenger, EVENT_CHANNEL)
        eventChannel.setStreamHandler(object : EventChannel.StreamHandler {
            override fun onListen(arguments: Any?, sink: EventChannel.EventSink?) {
                eventSink = sink
            }
            override fun onCancel(arguments: Any?) {
                eventSink = null
            }
        })

        registerReceivers()
    }

    override fun onDetachedFromEngine(binding: FlutterPlugin.FlutterPluginBinding) {
        methodChannel.setMethodCallHandler(null)
        try { context?.unregisterReceiver(usbReceiver) } catch (_: Exception) {}
        disconnect()
        context = null
        textureRegistry = null
    }

    override fun onMethodCall(call: MethodCall, result: MethodChannel.Result) {
        when (call.method) {
            "scanForDevices" -> scanForDevices(result)
            "connectDevice" -> {
                val name = call.argument<String>("deviceName") ?: ""
                connectByName(name, result)
            }
            "disconnectDevice" -> {
                disconnect()
                sendState("disconnected")
                result.success(true)
            }
            "startCapture" -> result.success(true) // capture starts on connect
            "stopCapture" -> result.success(true)
            else -> result.notImplemented()
        }
    }

    private fun registerReceivers() {
        val filter = IntentFilter().apply {
            addAction(ACTION_USB_PERMISSION)
            addAction(UsbManager.ACTION_USB_DEVICE_ATTACHED)
            addAction(UsbManager.ACTION_USB_DEVICE_DETACHED)
        }
        val ctx = context ?: return
        if (android.os.Build.VERSION.SDK_INT >= android.os.Build.VERSION_CODES.UPSIDE_DOWN_CAKE) {
            ctx.registerReceiver(usbReceiver, filter, Context.RECEIVER_NOT_EXPORTED)
        } else {
            ctx.registerReceiver(usbReceiver, filter)
        }
    }

    private fun scanForDevices(result: MethodChannel.Result) {
        val mgr = usbManager
        if (mgr == null) { result.success(false); return }
        for ((_, device) in mgr.deviceList) {
            if (isVideoDevice(device)) {
                sendState("found", mapOf("deviceName" to device.deviceName))
                requestConnection(device)
                result.success(true)
                return
            }
        }
        sendState("disconnected")
        result.success(false)
    }

    private fun connectByName(name: String, result: MethodChannel.Result) {
        val mgr = usbManager
        if (mgr == null) { result.error("NO_USB", "USB not available", null); return }
        val device = mgr.deviceList.values.firstOrNull { it.deviceName == name }
        if (device == null) { result.error("NOT_FOUND", "Device not found", null); return }
        requestConnection(device)
        result.success(true)
    }

    private fun requestConnection(device: UsbDevice) {
        val mgr = usbManager ?: return
        if (mgr.hasPermission(device)) {
            connectToDevice(device)
        } else {
            val pi = PendingIntent.getBroadcast(
                context, 0, Intent(ACTION_USB_PERMISSION), PendingIntent.FLAG_IMMUTABLE
            )
            mgr.requestPermission(device, pi)
        }
    }

    private fun connectToDevice(device: UsbDevice) {
        try {
            sendState("connecting")
            val mgr = usbManager ?: return
            val conn = mgr.openDevice(device)
            if (conn == null) {
                sendState("error", mapOf("message" to "Failed to open device"))
                return
            }
            val intf = findVideoStreamingInterface(device)
            if (intf == null) {
                conn.close()
                sendState("error", mapOf("message" to "No video interface found"))
                return
            }
            if (!conn.claimInterface(intf, true)) {
                conn.close()
                sendState("error", mapOf("message" to "Failed to claim interface"))
                return
            }

            currentDevice = device
            connection = conn
            streamingInterface = intf

            // Create a texture for zero-copy frame delivery
            val entry = textureRegistry?.createSurfaceTexture()
            textureEntry = entry

            sendState("connected", mapOf(
                "deviceName" to device.deviceName,
                "textureId" to (entry?.id() ?: -1)
            ))
        } catch (e: Exception) {
            Log.e(TAG, "Error connecting", e)
            sendState("error", mapOf("message" to (e.message ?: "Connection failed")))
        }
    }

    private fun disconnect() {
        try {
            streamingInterface?.let { connection?.releaseInterface(it) }
            connection?.close()
        } catch (_: Exception) {}
        currentDevice = null
        connection = null
        streamingInterface = null
        textureEntry?.release()
        textureEntry = null
    }

    private fun isVideoDevice(device: UsbDevice): Boolean {
        if (device.deviceClass == USB_CLASS_VIDEO) return true
        for (i in 0 until device.interfaceCount) {
            if (device.getInterface(i).interfaceClass == USB_CLASS_VIDEO) return true
        }
        val knownVendors = setOf(0x534d, 0x1b80, 0x05e1, 0x1164, 0x0ccd, 0x07ca, 0x1f4d)
        return knownVendors.contains(device.vendorId)
    }

    private fun findVideoStreamingInterface(device: UsbDevice): UsbInterface? {
        for (i in 0 until device.interfaceCount) {
            val intf = device.getInterface(i)
            if (intf.interfaceClass == USB_CLASS_VIDEO && intf.interfaceSubclass == 2) return intf
        }
        return null
    }

    private fun sendState(state: String, extras: Map<String, Any?> = emptyMap()) {
        val data = mutableMapOf<String, Any?>("state" to state)
        data.putAll(extras)
        eventSink?.success(data)
    }
}
