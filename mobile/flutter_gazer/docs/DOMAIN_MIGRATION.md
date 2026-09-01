# Domain Migration Guide - Flutter Gazer

Production-ready documentation for migrating between WaddleBot API domains in Flutter Gazer mobile application.

---

## Feature Overview

Flutter Gazer supports seamless switching between three distinct API domains:

1. **PenguinTech Development** (`waddlebot.penguintech.io`) - Internal development environment
2. **Waddles Development** (`waddles.penguintech.io`) - Collaborative development environment
3. **Production** (`app.waddlebot.io`) - Live production environment

### Key Capabilities

- **Runtime Domain Switching**: Change API domains without rebuilding the application
- **Persistent Configuration**: Domain preference survives app restarts
- **Automatic Re-authentication**: Session management during domain transitions
- **Real-time Validation**: Verify domain connectivity and API compatibility
- **Rollback Protection**: Safe recovery mechanisms if migration fails

### Domain Properties

| Property | PenguinTech Dev | Waddles Dev | Production |
|----------|-----------------|------------|-----------|
| **Host** | `waddlebot.penguintech.io` | `waddles.penguintech.io` | `app.waddlebot.io` |
| **Display Name** | PenguinTech Dev | Waddles Dev | Waddles |
| **API Version** | v2 | v2 | v2 |
| **WebSocket Protocol** | wss | wss | wss |
| **API URL** | `https://waddlebot.penguintech.io/api/v2` | `https://waddles.penguintech.io/api/v2` | `https://app.waddlebot.io/api/v2` |
| **WebSocket URL** | `wss://waddlebot.penguintech.io/api/v1/ws` | `wss://waddles.penguintech.io/api/v1/ws` | `wss://app.waddlebot.io/api/v1/ws` |

---

## Breaking Changes

### None Expected

This migration maintains **full backward compatibility** with existing user data, authentication tokens, and API contracts across all three domains.

**Important Notes:**
- Domain switching requires re-authentication (secure logout)
- User sessions are tied to the original domain
- Token formats remain unchanged across domains
- API endpoint responses are consistent across all domains
- No database schema changes required

---

## Testing Instructions for Developers

### Prerequisites

- Flutter SDK 3.2.0+
- Access to all three domain environments
- Active user accounts on each domain with different license tiers
- Valid credentials for testing authentication flows

### Unit Testing

#### 1. Domain Configuration Tests

```bash
# Run domain configuration unit tests
flutter test test/models/domain_config_test.dart

# Expected outcomes:
# - Domain enum resolves to correct hosts
# - Display names match domain types
# - API URLs format correctly
# - WebSocket URLs include wss protocol
# - fromHost() method correctly identifies domains
# - fromIndex() method handles all indices and defaults
```

#### 2. API Client Domain Switching Tests

```bash
# Run API client tests
flutter test test/services/api_client_test.dart

# Expected outcomes:
# - setDomain() updates base URL correctly
# - Domain validation prevents empty URLs
# - HTTP client configuration updates on domain change
# - Request headers preserved across domain switches
# - Error handling for invalid domains
```

#### 3. Settings Service Persistence Tests

```bash
# Run settings service tests
flutter test test/services/settings_service_test.dart

# Expected outcomes:
# - saveApiDomain() stores domain preference
# - loadApiDomain() retrieves stored preference
# - Default domain is production
# - Domain preference survives app restart
# - Settings isolation between domains
```

### Integration Testing

#### 1. Authentication Flow Across Domains

```bash
# Run authentication integration tests
flutter test integration_test/auth_domain_test.dart

# Test steps:
1. Launch app and verify default domain (production)
2. Log in with PenguinTech Dev credentials
3. Confirm API calls go to correct domain
4. Switch to Waddles Dev domain
5. Verify logout and re-authentication required
6. Log in with Waddles Dev credentials
7. Confirm API calls go to new domain
8. Switch to production domain
9. Complete authentication cycle
10. Verify all features accessible on each domain

# Expected outcomes:
# - Successful login on each domain
# - Session properly invalidated during switch
# - API calls routed to correct domain
# - No cross-domain token leakage
# - User data consistent per domain
```

#### 2. Streaming Feature Validation

```bash
# Run streaming integration tests
flutter test integration_test/streaming_domain_test.dart

# Test steps:
1. Test USB capture device enumeration per domain
2. Test RTMP configuration persistence per domain
3. Test stream start/stop across domains
4. Verify bitrate control per domain
5. Test quality preset selection per domain

# Expected outcomes:
# - USB devices detected consistently
# - RTMP endpoints vary correctly by domain
# - Stream lifecycle independent per domain
# - Settings isolated per domain
```

#### 3. Community Features Validation

```bash
# Run community integration tests
flutter test integration_test/community_domain_test.dart

# Test steps:
1. Fetch community list from each domain
2. Verify community data consistency
3. Test real-time chat (Socket.io) per domain
4. Verify member directory per domain
5. Test permission-based feature access

# Expected outcomes:
# - Community lists vary per domain
# - Chat connections to correct domain
# - Member data matches domain
# - Permissions enforced per domain
```

### Manual Testing Checklist

#### Domain Switching (30 minutes)

- [ ] **Initial Setup**
  - [ ] Launch app on fresh install
  - [ ] Verify default domain is production
  - [ ] Navigate to Settings → API Configuration
  - [ ] Confirm current domain displayed

- [ ] **Switch to PenguinTech Dev**
  - [ ] Select "PenguinTech Dev" from domain dropdown
  - [ ] Confirm logout dialog appears
  - [ ] Review confirmation message
  - [ ] Tap "Change Domain" to confirm
  - [ ] Verify user is logged out
  - [ ] Log in with PenguinTech Dev credentials
  - [ ] Verify successful login (home screen loads)
  - [ ] Check that API calls use correct endpoint

- [ ] **Switch to Waddles Dev**
  - [ ] Navigate to Settings → API Configuration
  - [ ] Select "Waddles Dev" from dropdown
  - [ ] Confirm logout dialog
  - [ ] Tap "Change Domain"
  - [ ] Log in with Waddles Dev credentials
  - [ ] Verify successful login
  - [ ] Confirm community list loads from Waddles Dev

- [ ] **Return to Production**
  - [ ] Navigate to Settings
  - [ ] Select "Waddles" (production) domain
  - [ ] Confirm logout and re-authentication
  - [ ] Log in with production credentials
  - [ ] Verify home screen loads correctly

#### Feature Validation Per Domain (1.5 hours)

**PenguinTech Dev Domain:**
- [ ] Login successful
- [ ] Communities load from correct endpoint
- [ ] Real-time chat connects to correct WebSocket
- [ ] USB devices enumerate correctly
- [ ] RTMP settings load/save properly
- [ ] License tier displays (dev tier)
- [ ] Settings persist after restart

**Waddles Dev Domain:**
- [ ] Login successful with different credentials
- [ ] Communities load (may differ from PenguinTech)
- [ ] Chat functionality operational
- [ ] Streaming preview renders
- [ ] Member directory accessible
- [ ] License information displays
- [ ] App theme renders correctly

**Production Domain:**
- [ ] Login successful
- [ ] Community list matches live environment
- [ ] Real-time chat works
- [ ] Streaming quality presets available
- [ ] RTMP streaming endpoints configured
- [ ] Premium features gated correctly
- [ ] Performance acceptable

#### Session Management (30 minutes)

- [ ] **Token Expiration**
  - [ ] Log in on any domain
  - [ ] Wait for token near expiration
  - [ ] Verify auto-refresh occurs
  - [ ] Confirm session continues

- [ ] **Session Invalidation**
  - [ ] Switch domains during active session
  - [ ] Verify old tokens cleared
  - [ ] Confirm re-authentication required
  - [ ] No cross-domain token leakage

- [ ] **Logout Behavior**
  - [ ] Log out from each domain
  - [ ] Verify all tokens cleared
  - [ ] Confirm return to login screen
  - [ ] No residual session data

#### Error Handling (30 minutes)

- [ ] **Network Errors**
  - [ ] Disable network connectivity
  - [ ] Attempt domain switch
  - [ ] Verify graceful error message
  - [ ] Reconnect and retry
  - [ ] Confirm successful switch

- [ ] **Invalid Credentials**
  - [ ] Switch to new domain
  - [ ] Enter invalid username
  - [ ] Verify error message displays
  - [ ] Retry with correct credentials
  - [ ] Confirm login succeeds

- [ ] **Domain Unavailable**
  - [ ] Configure invalid domain (mock)
  - [ ] Attempt to switch
  - [ ] Verify error handling
  - [ ] Fallback to previous domain
  - [ ] Confirm app remains stable

### Performance Testing

```bash
# Measure domain switch latency
# Expected: < 3 seconds from confirmation to login screen

# Measure API response times per domain
# Expected: < 500ms for standard requests

# Measure memory usage across domains
# Expected: < 5% increase per domain switch
# Expected: < 150MB total app memory
```

### Testing Schedule

| Phase | Duration | Focus |
|-------|----------|-------|
| Unit Tests | 30 min | Domain configuration, API client, settings |
| Integration Tests | 2 hours | Authentication, streaming, communities |
| Manual Testing | 2.5 hours | Full feature validation, error handling |
| Performance Testing | 1 hour | Response times, memory usage |
| **Total** | **~6 hours** | All aspects covered |

---

## Rollback Plan

### If Migration Fails

#### Immediate Actions (< 2 minutes)

1. **Force Return to Production Domain**
   ```dart
   // In API client initialization
   _domain = WaddleBotDomain.production;
   _baseUrl = WaddleBotDomain.production.apiUrl;
   ```

2. **Clear Corrupted Settings**
   ```bash
   # Via app settings screen or programmatically
   flutter run --verbose
   # Manually clear SharedPreferences cache
   ```

3. **Force Re-authentication**
   ```dart
   // In auth service
   await secureStorage.deleteAll();
   navigateToLoginScreen();
   ```

#### Recovery Steps

**Scenario 1: Settings Data Corrupted**

```dart
// In SettingsService
Future<WaddleBotDomain> loadApiDomain() async {
  try {
    final domainIndex = _prefs.getInt('api_domain_index');
    if (domainIndex == null) {
      return WaddleBotDomain.production; // Safe default
    }
    return WaddleBotDomain.fromIndex(domainIndex);
  } catch (e) {
    // Fallback to production on any error
    ConsoleVersion.error(
      'Error loading domain: $e',
      name: 'SettingsService.loadApiDomain.fallback',
    );
    return WaddleBotDomain.production;
  }
}
```

**Scenario 2: API Client Inconsistency**

```dart
// Verify and repair API client state
Future<void> repairApiClient() async {
  final storedDomain = await settingsService.loadApiDomain();
  final expectedUrl = storedDomain.apiUrl;

  if (apiClient.baseUrl != expectedUrl) {
    apiClient.setDomain(storedDomain);
  }
}
```

**Scenario 3: Session Token Invalid**

```dart
// Clear session and require re-authentication
Future<void> invalidateSession() async {
  await secureStorage.deleteAll();
  await settingsService.clearUserData();
  navigateToLoginScreen();
}
```

#### Rollback Hotline

If users encounter critical issues during migration:

1. **Immediate Support** (< 30 min response)
   - technical.support@penguintech.io
   - Include: App version, domain attempted, error message, device info

2. **Emergency Procedures**
   - Disable domain switching via server-side feature flag
   - Force all users to production domain temporarily
   - Provide offline mode while issue investigated

3. **Post-Incident Review**
   - Root cause analysis
   - Code review of failing integration
   - Update testing procedures
   - Deploy fix in patch release

---

## Support Matrix

### Supported Environments

#### Development Environments

**PenguinTech Dev Domain**
- **Purpose**: Internal development and testing
- **Stability**: Experimental (features in development)
- **Uptime SLA**: None (development)
- **Data Persistence**: Not guaranteed (may reset)
- **Use Case**: Developer testing, feature development
- **User Base**: Internal developers only
- **Access**: VPN required

**Waddles Dev Domain**
- **Purpose**: Feature staging and collaborative testing
- **Stability**: Beta (tested, unstable)
- **Uptime SLA**: Best effort (no guarantees)
- **Data Persistence**: 48-hour retention
- **Use Case**: QA testing, partner feedback, pre-release validation
- **User Base**: Internal team + selected partners
- **Access**: PenguinTech credentials

#### Production Environment

**Production Domain**
- **Purpose**: Live user-facing application
- **Stability**: Stable (production-grade)
- **Uptime SLA**: 99.5% (monthly)
- **Data Persistence**: Indefinite (backed up)
- **Use Case**: End-user consumption
- **User Base**: General public
- **Access**: Public (login required)

### Feature Availability Matrix

| Feature | PenguinTech Dev | Waddles Dev | Production |
|---------|-----------------|------------|-----------|
| **Authentication** | ✅ Full | ✅ Full | ✅ Full |
| **User Profiles** | ✅ Yes | ✅ Yes | ✅ Yes |
| **Communities** | ✅ Limited | ✅ Standard | ✅ Full |
| **Real-time Chat** | ✅ Beta | ✅ Stable | ✅ Stable |
| **USB Capture** | ✅ Full | ✅ Full | ✅ Full |
| **RTMP Streaming** | ✅ Full | ✅ Full | ✅ Full |
| **License Gating** | ⚙️ Simulation | ✅ Full | ✅ Full |
| **Push Notifications** | ❌ Not Available | ⚙️ Beta | ✅ Production |
| **Offline Mode** | ❌ Not Available | ⚙️ Beta | ✅ Production |
| **Analytics** | ⚙️ Limited | ✅ Partial | ✅ Full |
| **Premium Features** | ✅ All Unlocked | ✅ License Gated | ✅ License Gated |

**Legend**: ✅ = Fully supported | ⚙️ = In development | ❌ = Not available

### Device Support per Domain

**All domains support:**
- iOS 12.0+ (iPad, iPhone)
- Android 5.0+ (API Level 31+)
- USB capture devices (Android platform channels)
- RTMP streaming (all platforms)

**Platform-specific notes:**
- iOS: App State restoration works consistently across domain switches
- Android: Multiple simultaneous domains not supported (one active domain)

### API Compatibility Matrix

| API Endpoint | PenguinTech Dev | Waddles Dev | Production |
|-------------|-----------------|------------|-----------|
| `POST /auth/login` | ✅ v2 | ✅ v2 | ✅ v2 |
| `GET /communities` | ✅ v2 | ✅ v2 | ✅ v2 |
| `POST /streams/start` | ✅ v2 | ✅ v2 | ✅ v2 |
| `GET /members` | ✅ v2 | ✅ v2 | ✅ v2 |
| `WebSocket /api/v1/ws` | ✅ wss | ✅ wss | ✅ wss |

### Known Issues by Domain

**PenguinTech Dev**
- Occasional API latency due to development load
- Premium features may be reset during testing
- Communities data not backed up
- License data simulated (not real)

**Waddles Dev**
- Data older than 48 hours auto-purged
- Limited concurrent user support
- Chat history not archived
- Performance not guaranteed

**Production**
- No known limitations
- Full feature support
- Production SLA compliance
- Data backed up daily

### Support Response Times

| Severity | PenguinTech | Waddles Dev | Production |
|----------|------------|------------|-----------|
| Critical | 4 hours | 4 hours | 30 minutes |
| High | 8 hours | 8 hours | 2 hours |
| Medium | 24 hours | 24 hours | 8 hours |
| Low | 48 hours | 48 hours | 24 hours |

---

## Known Limitations

### Technical Limitations

1. **Single Domain Per Session**
   - Only one domain can be active at a time
   - Switching domains requires logout and login
   - No simultaneous multi-domain sessions
   - **Workaround**: Use separate user accounts per domain if needed

2. **Token Cross-Domain Incompatibility**
   - Tokens issued by one domain cannot be used on another
   - Token refresh requires active session on target domain
   - JWT claims include domain-specific identifiers
   - **Workaround**: Complete re-authentication required for domain switch

3. **Data Not Synced Across Domains**
   - User profiles may differ per domain
   - Communities are domain-specific
   - Chat history not shared across domains
   - Stream settings isolated per domain
   - **Impact**: Users must recreate configuration per domain
   - **Workaround**: Export settings from one domain, manual import on another

4. **USB Device Persistence**
   - USB device list enumerated per domain switch
   - Device selection not retained across domains
   - Device permissions reset during domain switch
   - **Workaround**: Re-select device after domain switch

5. **Cache Invalidation**
   - Local cache cleared on domain switch
   - Image cache per domain
   - Community list cache rebuilt per switch
   - Member directory cache cleared
   - **Workaround**: Accept initial slower load on domain switch

### Behavioral Limitations

1. **Rate Limiting Per Domain**
   - Each domain has independent rate limits
   - Switching domains resets rate limit counters
   - Rapid domain switching may trigger rate limiting
   - **Mitigation**: Space domain switches 30+ seconds apart

2. **License Tier Differences**
   - Free tier may differ by domain
   - Premium feature availability varies
   - License key valid only on issuing domain
   - **Impact**: Feature access may change with domain
   - **Workaround**: Match license tier across all domains

3. **Performance Variation**
   - Dev environments may have higher latency
   - Response times not guaranteed identical
   - Streaming quality may vary by domain
   - **Mitigation**: Use production domain for consistent performance

4. **Data Retention Policies**
   - Production: Indefinite retention
   - Waddles Dev: 48-hour retention
   - PenguinTech Dev: Variable (development resets)
   - **Impact**: Account data may be lost on dev domains
   - **Recommendation**: Only test accounts on dev domains

### Known Issues

1. **Domain Switch Logout Race Condition**
   - If user switches domains during active stream, stream may not properly terminate
   - **Fix**: Stop stream before changing domains
   - **Status**: Under investigation for v2.2.0

2. **WebSocket Reconnection Delay**
   - Chat connection may take 5-10 seconds after domain switch
   - **Cause**: WebSocket connection timeout handling
   - **Workaround**: Wait for "Connected" status before sending messages
   - **Status**: Improvement in development

3. **Settings Persistence on Rapid Switch**
   - Changing domains multiple times quickly may lose some settings
   - **Cause**: Async SharedPreferences write not completing
   - **Workaround**: Wait 5 seconds between domain switches
   - **Status**: Fixed in v2.2.0-beta

---

## User Migration Guide

### How to Switch API Domains

#### Step-by-Step Instructions

**For End Users**

1. **Open Settings**
   - Tap the menu button (☰) in bottom right
   - Tap "Settings" from the menu

2. **Navigate to API Configuration**
   - Scroll down to "Advanced Settings"
   - Tap "API Domain Configuration"

3. **Select New Domain**
   - Current domain shows at top
   - Tap the dropdown menu
   - Select desired domain:
     - "PenguinTech Dev" - Development testing
     - "Waddles Dev" - Feature staging
     - "Waddles" - Production (default)

4. **Confirm Domain Change**
   - Warning dialog appears: "Change API Domain? This will log you out."
   - Review the message
   - Tap "Change Domain" to proceed
   - Or tap "Cancel" to keep current domain

5. **Re-authenticate**
   - Login screen appears automatically
   - Enter your credentials for the selected domain
   - **Important**: Credentials may differ per domain
   - Tap "Login" to proceed

6. **Verify Successful Switch**
   - Home screen loads
   - Notice the domain displayed in Settings should change
   - API calls now go to new domain

#### Important Considerations for Users

**Before Switching Domains:**
- ⚠️ You will be logged out automatically
- ⚠️ Your current session will end
- ⚠️ Unsaved work may be lost (save first)
- ⚠️ Streaming will stop if active
- ⚠️ Chat connections will disconnect

**During Switch:**
- Active streams automatically stop
- Chat history not transferred
- All cached data cleared
- Local settings may be reset

**After Switching:**
- You must log in again
- Settings may need reconfiguration
- USB devices must be re-selected
- RTMP endpoints may change

### Feature Differences Between Domains

#### PenguinTech Dev
- **Best for**: Internal testing, development
- **Premium Features**: All enabled (for testing)
- **Data**: Unstable, may reset without notice
- **Uptime**: Variable, not guaranteed
- **Use Case**: Only for developers/internal team

#### Waddles Dev
- **Best for**: Pre-release testing, feature staging
- **Premium Features**: Available but may change
- **Data**: Retained 48 hours
- **Uptime**: Best effort, no SLA
- **Use Case**: QA, partner feedback, beta testing

#### Production
- **Best for**: End users, general streaming
- **Premium Features**: License-gated (paid features)
- **Data**: Permanently stored and backed up
- **Uptime**: 99.5% SLA guarantee
- **Use Case**: Live streaming, everyday use

### Troubleshooting Domain Switching

#### Problem: "Cannot Connect to Domain"

**Cause**: Domain server offline or unreachable

**Solution**:
1. Check internet connection
   - Open a web browser
   - Visit https://app.waddlebot.io
   - If page loads, domain is reachable

2. If domain unreachable:
   - Try switching back to production
   - Contact support

3. If stuck on unavailable domain:
   - Uninstall and reinstall app
   - Or clear app data and login fresh

#### Problem: "Login Failed After Domain Switch"

**Cause**: Incorrect credentials or account not on new domain

**Solution**:
1. Verify credentials are correct for target domain
   - Development and production accounts are separate
   - May need different username/password

2. If account doesn't exist on target domain:
   - Create new account on that domain
   - Or switch back to domain with your account

3. If credentials correct but still fails:
   - Clear app cache: Settings > Apps > Flutter Gazer > Storage > Clear Cache
   - Try login again

#### Problem: "Features Not Available on New Domain"

**Cause**: Domain has different feature availability

**Solution**:
1. Check domain feature matrix above
2. If feature should be available:
   - Contact support for domain
3. If feature not in domain feature list:
   - Switch back to domain with feature
   - Or wait for feature rollout to your domain

#### Problem: "Settings Lost After Domain Switch"

**Cause**: Domain switching clears local cache

**Solution**:
1. Reconfigure USB capture device
2. Re-enter RTMP streaming settings
3. Adjust quality presets
4. These are domain-specific and must be set per domain

#### Problem: "Chat Not Connecting After Switch"

**Cause**: WebSocket reconnection delay or connection issue

**Solution**:
1. Wait 10 seconds for connection to establish
2. Watch "Chat Status" indicator
3. If still not connected:
   - Switch back to previous domain
   - Switch forward again
4. If chat never connects:
   - Clear app cache and try again
   - Contact support if persistent

### Recommended Domain for Different Use Cases

| Use Case | Recommended Domain | Reason |
|----------|---|---|
| Live Streaming (viewers) | Production | Stable, maximum uptime |
| Testing New Features | Waddles Dev | Safe sandbox, 48-hr data retention |
| Internal Development | PenguinTech Dev | Development environment, all features unlocked |
| Performance Testing | Production | Real-world performance metrics |
| Backup/Failover | Waddles Dev | Can switch quickly if production unavailable |
| Testing Permissions | PenguinTech Dev | All roles/tiers available for testing |

### Data Migration Between Domains

#### What Data Transfers Between Domains

✅ **Transfers Automatically**
- User account identity (if same account exists on both domains)
- License tier (if account has license on target domain)
- Authentication tokens (new tokens issued on switch)

❌ **Does NOT Transfer**
- Community memberships
- Chat history
- Local device preferences
- Saved RTMP settings
- Stream statistics
- Follower lists

#### Manual Data Transfer

If you need specific data on a different domain:

1. **Export Your Data**
   - Settings > Account > Export Profile
   - Saves JSON file to device

2. **Transfer to New Domain**
   - Switch domains
   - Log in with account on target domain
   - Settings > Account > Import Profile
   - Select exported JSON file

3. **Verify Import**
   - Check that settings loaded correctly
   - Verify community memberships not imported (domain-specific)
   - Confirm account preferences applied

---

## Support & Resources

### Getting Help

**For Technical Issues**
- Email: support@penguintech.io
- Include: Domain name, error message, device type, app version
- Response: 30 minutes - 2 hours (production) / 4-24 hours (dev domains)

**For Feature Requests**
- Email: product@penguintech.io
- Feedback: feedback.penguintech.io
- Response: 24-48 hours

**For Account Issues**
- Email: accounts@penguintech.io
- Include: Email address, domain, issue description
- Response: 2-4 hours

**For Emergency Issues (Production Down)**
- Call: +1-844-PENGUIN-1
- Email: emergency@penguintech.io
- Status: https://status.penguintech.io

### Additional Documentation

- **[Architecture Guide](ARCHITECTURE.md)** - System architecture and design patterns
- **[API Reference](API.md)** - Full API documentation
- **[Migration Guide](MIGRATION.md)** - Migrating from native Android/iOS apps
- **[Testing Guide](TESTING.md)** - Testing procedures and test cases

### Community

- **Flutter Community**: https://flutter.dev/community
- **Stack Overflow**: Tag with `flutter` and `waddlebot`
- **GitHub Issues**: Report bugs and request features

---

**Document Version**: 1.0
**Last Updated**: 2026-02-02
**Applies To**: Flutter Gazer v2.1.0+
**Status**: Production Ready
