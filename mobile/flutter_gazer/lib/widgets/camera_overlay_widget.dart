import 'package:camera/camera.dart';
import 'package:flutter/material.dart';
import '../models/overlay_settings.dart';

/// Draggable, resizable camera overlay on top of the video preview.
class CameraOverlayWidget extends StatefulWidget {
  final OverlaySettings settings;

  const CameraOverlayWidget({super.key, required this.settings});

  @override
  State<CameraOverlayWidget> createState() => _CameraOverlayWidgetState();
}

class _CameraOverlayWidgetState extends State<CameraOverlayWidget> {
  CameraController? _cameraController;
  Offset _position = const Offset(20, 20);
  bool _cameraReady = false;

  @override
  void initState() {
    super.initState();
    _initCamera();
    _setInitialPosition();
  }

  void _setInitialPosition() {
    // Position will be set after first build in didChangeDependencies
  }

  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    final size = MediaQuery.of(context).size;
    const margin = 20.0;
    final overlayW = size.width * widget.settings.sizeFraction;
    switch (widget.settings.position) {
      case OverlayCorner.topLeft:
        _position = Offset(margin, margin);
      case OverlayCorner.topRight:
        _position = Offset(size.width - overlayW - margin, margin);
      case OverlayCorner.bottomLeft:
        _position = Offset(margin, size.height * 0.6);
      case OverlayCorner.bottomRight:
        _position = Offset(size.width - overlayW - margin, size.height * 0.6);
    }
  }

  Future<void> _initCamera() async {
    final cameras = await availableCameras();
    if (cameras.isEmpty) return;
    // Prefer front camera for overlay
    final camera = cameras.firstWhere(
      (c) => c.lensDirection == CameraLensDirection.front,
      orElse: () => cameras.first,
    );
    _cameraController = CameraController(camera, ResolutionPreset.medium);
    await _cameraController!.initialize();
    if (mounted) setState(() => _cameraReady = true);
  }

  @override
  void dispose() {
    _cameraController?.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    if (!_cameraReady || _cameraController == null) {
      return const SizedBox.shrink();
    }

    final screenWidth = MediaQuery.of(context).size.width;
    final overlayWidth = screenWidth * widget.settings.sizeFraction;
    final overlayHeight = overlayWidth * 9 / 16;

    return Positioned(
      left: _position.dx,
      top: _position.dy,
      child: GestureDetector(
        onPanUpdate: (details) {
          setState(() {
            _position += details.delta;
          });
        },
        child: Container(
          width: overlayWidth,
          height: overlayHeight,
          decoration: BoxDecoration(
            border: Border.all(color: Colors.white, width: 2),
            borderRadius: BorderRadius.circular(4),
          ),
          clipBehavior: Clip.antiAlias,
          child: CameraPreview(_cameraController!),
        ),
      ),
    );
  }
}
