import 'package:flutter/material.dart';
import 'package:flutter_libs/flutter_libs.dart';
import 'config/theme.dart';
import 'screens/main_screen.dart';
import 'services/api_client.dart';

/// Root application widget for Gazer Mobile Stream Studio.
class GazerApp extends StatefulWidget {
  const GazerApp({super.key});

  @override
  State<GazerApp> createState() => _GazerAppState();
}

class _GazerAppState extends State<GazerApp> {
  final GlobalKey<NavigatorState> _navigatorKey = GlobalKey<NavigatorState>();

  @override
  void initState() {
    super.initState();
    // Set navigator key for LicenseInterceptor to show premium gate dialogs
    LicenseInterceptor.navigatorKey = _navigatorKey;
  }

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'Gazer Stream Studio',
      theme: GazerTheme.lightTheme,
      darkTheme: GazerTheme.darkTheme,
      themeMode: ThemeMode.dark,
      home: const MainScreen(),
      navigatorKey: _navigatorKey,
      debugShowCheckedModeBanner: false,
    );
  }
}
