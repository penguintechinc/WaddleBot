package io.waddlebot.gazer

import android.util.Log
import io.flutter.embedding.engine.plugins.FlutterPlugin
import io.flutter.plugin.common.EventChannel
import io.flutter.plugin.common.MethodCall
import io.flutter.plugin.common.MethodChannel

/**
 * Flutter plugin wrapping rtmp-rtsp-stream-client-java for RTMP streaming.
 * Provides MethodChannel for control and EventChannel for state updates.
 */
class RtmpNativePlugin : FlutterPlugin, MethodChannel.MethodCallHandler {

    companion object {
        private const val TAG = "RtmpNativePlugin"
        private const val METHOD_CHANNEL = "io.waddlebot.gazer/rtmp"
        private const val EVENT_CHANNEL = "io.waddlebot.gazer/rtmp_state"
    }

    private lateinit var methodChannel: MethodChannel
    private lateinit var eventChannel: EventChannel
    private var eventSink: EventChannel.EventSink? = null
    private var isStreaming = false

    override fun onAttachedToEngine(binding: FlutterPlugin.FlutterPluginBinding) {
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
    }

    override fun onDetachedFromEngine(binding: FlutterPlugin.FlutterPluginBinding) {
        methodChannel.setMethodCallHandler(null)
        stopStreamingInternal()
    }

    override fun onMethodCall(call: MethodCall, result: MethodChannel.Result) {
        when (call.method) {
            "startStreaming" -> {
                val url = call.argument<String>("url") ?: ""
                val width = call.argument<Int>("width") ?: 1280
                val height = call.argument<Int>("height") ?: 720
                val fps = call.argument<Int>("fps") ?: 30
                val videoBitrate = call.argument<Int>("videoBitrate") ?: 3000000
                startStreamingInternal(url, width, height, fps, videoBitrate, result)
            }
            "stopStreaming" -> {
                stopStreamingInternal()
                result.success(true)
            }
            "updateBitrate" -> {
                val bitrate = call.argument<Int>("bitrate") ?: 3000000
                Log.d(TAG, "Bitrate updated: $bitrate")
                result.success(true)
            }
            "getStreamStats" -> {
                result.success(mapOf(
                    "isConnected" to isStreaming,
                    "bitrate" to 0,
                    "fps" to 0,
                    "droppedFrames" to 0L,
                    "sentPackets" to 0L,
                    "sentBytes" to 0L
                ))
            }
            else -> result.notImplemented()
        }
    }

    private fun startStreamingInternal(
        url: String, width: Int, height: Int, fps: Int, videoBitrate: Int,
        result: MethodChannel.Result
    ) {
        try {
            sendState("connecting")
            // TODO: Initialize rtmp-rtsp-stream-client-java here
            // For now, stub implementation
            isStreaming = true
            sendState("streaming")
            Log.d(TAG, "Streaming started to: $url (${width}x${height}@${fps}fps)")
            result.success(true)
        } catch (e: Exception) {
            Log.e(TAG, "Failed to start streaming", e)
            sendState("error", e.message ?: "Start failed")
            result.success(false)
        }
    }

    private fun stopStreamingInternal() {
        if (isStreaming) {
            // TODO: Stop rtmp-rtsp-stream-client-java here
            isStreaming = false
            sendState("disconnected")
            Log.d(TAG, "Streaming stopped")
        }
    }

    private fun sendState(state: String, message: String? = null) {
        val data = mutableMapOf<String, Any?>("state" to state)
        if (message != null) data["message"] = message
        eventSink?.success(data)
    }
}
