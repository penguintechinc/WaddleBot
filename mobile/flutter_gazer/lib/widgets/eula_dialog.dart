import 'package:flutter/material.dart';

/// EULA acceptance dialog — must be accepted to use the app.
class EulaDialog extends StatefulWidget {
  const EulaDialog({super.key});

  /// Shows the EULA dialog and returns true if accepted.
  static Future<bool?> show(BuildContext context) {
    return showDialog<bool>(
      context: context,
      barrierDismissible: false,
      builder: (_) => const EulaDialog(),
    );
  }

  @override
  State<EulaDialog> createState() => _EulaDialogState();
}

class _EulaDialogState extends State<EulaDialog> {
  bool _agreed = false;

  @override
  Widget build(BuildContext context) {
    return AlertDialog(
      title: const Text('End User License Agreement'),
      content: SizedBox(
        width: double.maxFinite,
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            const Expanded(
              child: SingleChildScrollView(
                child: Text(_eulaText),
              ),
            ),
            const SizedBox(height: 16),
            CheckboxListTile(
              title: const Text('I have read and agree to the EULA'),
              value: _agreed,
              onChanged: (v) => setState(() => _agreed = v ?? false),
              controlAffinity: ListTileControlAffinity.leading,
              contentPadding: EdgeInsets.zero,
            ),
          ],
        ),
      ),
      actions: [
        TextButton(
          onPressed: () => Navigator.pop(context, false),
          child: const Text('Decline'),
        ),
        FilledButton(
          onPressed: _agreed ? () => Navigator.pop(context, true) : null,
          child: const Text('Accept'),
        ),
      ],
    );
  }

  static const _eulaText = '''END USER LICENSE AGREEMENT

Gazer Mobile Stream Studio

IMPORTANT - READ CAREFULLY: This End User License Agreement ("EULA") is a legal agreement between you (either an individual or a single entity) and Penguin Technologies Inc. for the Gazer Mobile Stream Studio software product.

By installing, copying, or otherwise using the Software Product, you agree to be bound by the terms of this EULA.

1. GRANT OF LICENSE
Penguin Technologies Inc. grants you a non-exclusive, non-transferable license to use the Software Product solely for your personal or commercial streaming purposes.

2. COPYRIGHT
The Software Product is protected by copyright laws and international copyright treaties.

3. RESTRICTIONS
You may not: reverse engineer, decompile, or disassemble the Software Product; redistribute, sublicense, or transfer the Software Product; remove or modify any copyright notices; use the Software Product for any illegal activities.

4. STREAMING CONTENT
You are solely responsible for all content you stream using the Software Product.

5. PRIVACY
The Software Product may collect anonymous usage statistics to improve functionality.

6. WARRANTY DISCLAIMER
THE SOFTWARE PRODUCT IS PROVIDED "AS IS" WITHOUT WARRANTY OF ANY KIND.

7. LIMITATION OF LIABILITY
IN NO EVENT SHALL PENGUIN TECHNOLOGIES INC. BE LIABLE FOR ANY SPECIAL, INCIDENTAL, INDIRECT, OR CONSEQUENTIAL DAMAGES.

8. TERMINATION
This license is effective until terminated. Your rights under this license will terminate automatically without notice if you fail to comply with any terms.

Copyright 2024 Penguin Technologies Inc. All rights reserved.''';
}
