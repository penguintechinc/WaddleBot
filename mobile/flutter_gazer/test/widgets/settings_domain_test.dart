import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:matcher/matcher.dart';
import 'package:mockito/mockito.dart';
import 'package:gazer_waddlebot/models/domain_config.dart';
import 'package:gazer_waddlebot/models/stream_config.dart';
import 'package:gazer_waddlebot/models/overlay_settings.dart';
import 'package:gazer_waddlebot/services/settings_service.dart';

class MockSettingsService implements SettingsService {
  WaddleBotDomain? _domainToReturn;
  late WaddleBotDomain lastSavedDomain;
  int saveApiDomainCallCount = 0;

  void setupLoadDomain(WaddleBotDomain domain) {
    _domainToReturn = domain;
  }

  @override
  Future<WaddleBotDomain> loadApiDomain() async => _domainToReturn ?? WaddleBotDomain.production;

  @override
  Future<void> saveApiDomain(WaddleBotDomain domain) async {
    lastSavedDomain = domain;
    saveApiDomainCallCount++;
  }

  @override
  Future<StreamConfig> loadStreamConfig() async {
    throw UnimplementedError();
  }

  @override
  Future<void> saveStreamConfig({
    String? rtmpUrl,
    String? streamKey,
    int? resolutionIndex,
    int? bitrateIndex,
    int? fpsIndex,
  }) async {
    throw UnimplementedError();
  }

  @override
  Future<OverlaySettings> loadOverlaySettings() async {
    throw UnimplementedError();
  }

  @override
  Future<void> saveOverlaySettings(OverlaySettings settings) async {
    throw UnimplementedError();
  }

  @override
  Future<bool> isEulaAccepted() async {
    throw UnimplementedError();
  }

  @override
  Future<void> acceptEula() async {
    throw UnimplementedError();
  }
}

void main() {
  group('Domain Selection Card', () {
    testWidgets('renders all 3 domain options', (WidgetTester tester) async {
      final mock = MockSettingsService();
      mock.setupLoadDomain(WaddleBotDomain.production);

      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(body: DomainSelectionTest(settingsService: mock)),
        ),
      );
      await tester.pumpAndSettle();

      expect(find.text('API Domain'), findsOneWidget);
      expect(find.text('PenguinTech Dev'), findsOneWidget);
      expect(find.text('Waddles Dev'), findsOneWidget);
      expect(find.text('Waddles'), findsOneWidget);
      expect(find.text('waddlebot.penguintech.io'), findsOneWidget);
      expect(find.text('waddles.penguintech.io'), findsOneWidget);
      expect(find.text('app.waddlebot.io'), findsOneWidget);
    });

    testWidgets('renders all 3 radio options correctly',
        (WidgetTester tester) async {
      final mock = MockSettingsService();
      mock.setupLoadDomain(WaddleBotDomain.production);

      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(body: DomainSelectionTest(settingsService: mock)),
        ),
      );
      await tester.pumpAndSettle();

      expect(find.byType(RadioListTile<WaddleBotDomain>), findsWidgets);
      final radioCount =
          find.byType(RadioListTile<WaddleBotDomain>).evaluate().length;
      expect(radioCount, equals(3));
    });

    testWidgets('confirmation dialog appears on domain change',
        (WidgetTester tester) async {
      final mock = MockSettingsService();
      mock.setupLoadDomain(WaddleBotDomain.production);

      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(body: DomainSelectionTest(settingsService: mock)),
        ),
      );
      await tester.pumpAndSettle();

      final radioTiles = find.byType(RadioListTile<WaddleBotDomain>);
      await tester.tap(radioTiles.at(0));
      await tester.pumpAndSettle();

      expect(find.byType(AlertDialog), findsOneWidget);
      expect(find.text('Change API Domain'), findsOneWidget);
      expect(find.text('Change API domain? This will log you out.'),
          findsOneWidget);
    });

    testWidgets('dialog shows cancel and change domain buttons',
        (WidgetTester tester) async {
      final mock = MockSettingsService();
      mock.setupLoadDomain(WaddleBotDomain.production);

      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(body: DomainSelectionTest(settingsService: mock)),
        ),
      );
      await tester.pumpAndSettle();

      final radioTiles = find.byType(RadioListTile<WaddleBotDomain>);
      await tester.tap(radioTiles.at(1));
      await tester.pumpAndSettle();

      expect(find.text('Cancel'), findsOneWidget);
      expect(find.text('Change Domain'), findsOneWidget);
    });

    testWidgets('cancel button closes dialog without saving',
        (WidgetTester tester) async {
      final mock = MockSettingsService();
      mock.setupLoadDomain(WaddleBotDomain.production);

      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(body: DomainSelectionTest(settingsService: mock)),
        ),
      );
      await tester.pumpAndSettle();

      final radioTiles = find.byType(RadioListTile<WaddleBotDomain>);
      await tester.tap(radioTiles.at(1));
      await tester.pumpAndSettle();

      await tester.tap(find.text('Cancel'));
      await tester.pumpAndSettle();

      expect(find.byType(AlertDialog), findsNothing);
    });

    testWidgets('domain change saves preference via SettingsService',
        (WidgetTester tester) async {
      final mock = MockSettingsService();
      mock.setupLoadDomain(WaddleBotDomain.production);

      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(body: DomainSelectionTest(settingsService: mock)),
        ),
      );
      await tester.pumpAndSettle();

      final radioTiles = find.byType(RadioListTile<WaddleBotDomain>);
      await tester.tap(radioTiles.at(0));
      await tester.pumpAndSettle();

      await tester.tap(find.text('Change Domain'));
      await tester.pumpAndSettle();

      expect(mock.saveApiDomainCallCount, equals(1));
      expect(mock.lastSavedDomain, equals(WaddleBotDomain.penguintech));
    });

    testWidgets('domain change saves correct domain index',
        (WidgetTester tester) async {
      final mock = MockSettingsService();
      mock.setupLoadDomain(WaddleBotDomain.production);

      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(body: DomainSelectionTest(settingsService: mock)),
        ),
      );
      await tester.pumpAndSettle();

      final radioTiles = find.byType(RadioListTile<WaddleBotDomain>);
      await tester.tap(radioTiles.at(1));
      await tester.pumpAndSettle();

      await tester.tap(find.text('Change Domain'));
      await tester.pumpAndSettle();

      expect(mock.saveApiDomainCallCount, equals(1));
      expect(mock.lastSavedDomain, equals(WaddleBotDomain.waddles));
    });

    testWidgets('selected domain radio button is marked',
        (WidgetTester tester) async {
      final mock = MockSettingsService();
      mock.setupLoadDomain(WaddleBotDomain.waddles);

      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(body: DomainSelectionTest(settingsService: mock)),
        ),
      );
      await tester.pumpAndSettle();

      final radioTiles = find.byWidgetPredicate(
        (widget) =>
            widget is RadioListTile<WaddleBotDomain> &&
            widget.value == WaddleBotDomain.waddles,
      );

      expect(radioTiles, findsOneWidget);
    });

    testWidgets('domain selection card displays current domain subtitle',
        (WidgetTester tester) async {
      final mock = MockSettingsService();
      mock.setupLoadDomain(WaddleBotDomain.production);

      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(body: DomainSelectionTest(settingsService: mock)),
        ),
      );
      await tester.pumpAndSettle();

      expect(find.text('Select Waddles API endpoint'), findsOneWidget);
    });

    testWidgets('domain options have correct host URLs',
        (WidgetTester tester) async {
      final mock = MockSettingsService();
      mock.setupLoadDomain(WaddleBotDomain.production);

      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(body: DomainSelectionTest(settingsService: mock)),
        ),
      );
      await tester.pumpAndSettle();

      expect(find.text('waddlebot.penguintech.io'), findsOneWidget);
      expect(find.text('waddles.penguintech.io'), findsOneWidget);
      expect(find.text('app.waddlebot.io'), findsOneWidget);
    });

    testWidgets('dialog closes after successful domain change',
        (WidgetTester tester) async {
      final mock = MockSettingsService();
      mock.setupLoadDomain(WaddleBotDomain.production);

      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(body: DomainSelectionTest(settingsService: mock)),
        ),
      );
      await tester.pumpAndSettle();

      final radioTiles = find.byType(RadioListTile<WaddleBotDomain>);
      await tester.tap(radioTiles.at(0));
      await tester.pumpAndSettle();

      expect(find.byType(AlertDialog), findsOneWidget);

      await tester.tap(find.text('Change Domain'));
      await tester.pumpAndSettle();

      expect(find.byType(AlertDialog), findsNothing);
    });

    testWidgets('no dialog shown when tapping same domain',
        (WidgetTester tester) async {
      final mock = MockSettingsService();
      mock.setupLoadDomain(WaddleBotDomain.penguintech);

      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(body: DomainSelectionTest(settingsService: mock)),
        ),
      );
      await tester.pumpAndSettle();

      final radioTiles = find.byType(RadioListTile<WaddleBotDomain>);
      await tester.tap(radioTiles.at(0));
      await tester.pumpAndSettle();

      expect(find.byType(AlertDialog), findsNothing);
    });

    testWidgets('card displays cloud icon for domain section',
        (WidgetTester tester) async {
      final mock = MockSettingsService();
      mock.setupLoadDomain(WaddleBotDomain.production);

      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(body: DomainSelectionTest(settingsService: mock)),
        ),
      );
      await tester.pumpAndSettle();

      expect(find.byIcon(Icons.cloud), findsOneWidget);
    });

    testWidgets('card is rendered with proper styling',
        (WidgetTester tester) async {
      final mock = MockSettingsService();
      mock.setupLoadDomain(WaddleBotDomain.production);

      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(body: DomainSelectionTest(settingsService: mock)),
        ),
      );
      await tester.pumpAndSettle();

      final cardFinder = find.byType(Card);
      expect(cardFinder, findsOneWidget);

      final card = cardFinder.evaluate().first.widget as Card;
      expect(card.elevation, equals(2));
    });
  });
}

/// Test widget that demonstrates domain selection functionality
class DomainSelectionTest extends StatefulWidget {
  final SettingsService settingsService;

  const DomainSelectionTest({
    super.key,
    required this.settingsService,
  });

  @override
  State<DomainSelectionTest> createState() => _DomainSelectionTestState();
}

class _DomainSelectionTestState extends State<DomainSelectionTest> {
  WaddleBotDomain? _selectedDomain;
  bool _isLoading = false;

  @override
  void initState() {
    super.initState();
    _loadDomain();
  }

  Future<void> _loadDomain() async {
    try {
      final domain = await widget.settingsService.loadApiDomain();
      if (!mounted) return;
      setState(() {
        _selectedDomain = domain;
      });
    } catch (e) {
      if (!mounted) return;
      setState(() {
        _selectedDomain = WaddleBotDomain.production;
      });
    }
  }

  Future<void> _handleDomainChange(WaddleBotDomain newDomain) async {
    if (newDomain == _selectedDomain) {
      return;
    }

    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Change API Domain'),
        content: const Text('Change API domain? This will log you out.'),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context),
            child: const Text('Cancel'),
          ),
          TextButton(
            onPressed: () async {
              Navigator.pop(context);
              setState(() => _isLoading = true);
              try {
                await widget.settingsService.saveApiDomain(newDomain);

                if (!mounted) return;
                setState(() {
                  _selectedDomain = newDomain;
                  _isLoading = false;
                });
              } catch (e) {
                if (!mounted) return;
                setState(() => _isLoading = false);
              }
            },
            child:
                const Text('Change Domain', style: TextStyle(color: Colors.orange)),
          ),
        ],
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    if (_selectedDomain == null) {
      return const Center(child: CircularProgressIndicator());
    }

    return Card(
      elevation: 2,
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(12),
        side: const BorderSide(color: Color(0xFF334155), width: 1),
      ),
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Container(
                  padding: const EdgeInsets.all(8),
                  decoration: BoxDecoration(
                    color: const Color(0xFFFBBF24).withOpacity(0.2),
                    borderRadius: BorderRadius.circular(8),
                  ),
                  child: const Icon(
                    Icons.cloud,
                    color: Color(0xFFFBBF24),
                    size: 24,
                  ),
                ),
                const SizedBox(width: 16),
                const Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        'API Domain',
                        style: TextStyle(
                          fontWeight: FontWeight.bold,
                          fontSize: 16,
                        ),
                      ),
                      Text(
                        'Select Waddles API endpoint',
                        style: TextStyle(fontSize: 12),
                      ),
                    ],
                  ),
                ),
              ],
            ),
            const SizedBox(height: 16),
            ...WaddleBotDomain.values.map(
              (domain) => RadioListTile<WaddleBotDomain>(
                value: domain,
                groupValue: _selectedDomain,
                onChanged: (WaddleBotDomain? newValue) {
                  if (newValue != null) {
                    _handleDomainChange(newValue);
                  }
                },
                title: Text(
                  domain.displayName,
                  style: const TextStyle(
                    color: Color(0xFFFBBF24),
                    fontWeight: FontWeight.w500,
                  ),
                ),
                subtitle: Text(
                  domain.host,
                  style: const TextStyle(fontSize: 12),
                ),
                dense: true,
              ),
            ),
          ],
        ),
      ),
    );
  }
}
