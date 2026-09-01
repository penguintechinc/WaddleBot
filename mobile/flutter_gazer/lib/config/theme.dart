import 'package:flutter/material.dart';
import 'package:flutter_libs/flutter_libs.dart';

/// Material Design 3 theme for Gazer Mobile Stream Studio using Elder colors.
/// Uses slate/amber palette from penguin-libs for consistent theming.
class GazerTheme {
  GazerTheme._();

  // Elder color palette - primary is amber, base is slate
  static const Color _primaryColor = ElderColors.amber500;
  static const Color _streamingRed = ElderColors.red500;
  static const Color _connectedGreen = ElderColors.green500;
  static const Color _warningAmber = ElderColors.amber600;

  static Color get streamingRed => _streamingRed;
  static Color get connectedGreen => _connectedGreen;
  static Color get warningAmber => _warningAmber;

  static ThemeData get darkTheme {
    return ThemeData(
      useMaterial3: true,
      brightness: Brightness.dark,
      colorSchemeSeed: _primaryColor,
      appBarTheme: const AppBarTheme(
        centerTitle: true,
        elevation: 0,
        backgroundColor: ElderColors.slate800,
      ),
      scaffoldBackgroundColor: ElderColors.slate950,
      extensions: const [ElderThemeData.dark],
    );
  }

  static ThemeData get lightTheme {
    return ThemeData(
      useMaterial3: true,
      brightness: Brightness.light,
      colorSchemeSeed: _primaryColor,
      appBarTheme: const AppBarTheme(
        centerTitle: true,
        elevation: 0,
        backgroundColor: ElderColors.slate100,
      ),
      scaffoldBackgroundColor: ElderColors.white,
    );
  }
}
