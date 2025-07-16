# WaddleBot Premium Mobile App

A React Native mobile application for premium WaddleBot community managers.

## Overview

The WaddleBot Premium Mobile App provides community managers with full access to their community management tools on mobile devices. This app is exclusively available to WaddleBot Premium subscribers.

## Features

### 🔐 Premium Access Control
- Premium subscription verification
- Secure authentication with JWT tokens
- Role-based access control

### 👥 Member Management
- View and search community members
- Update member roles and permissions
- Ban/unban members from community, portal, and app
- Member activity tracking and analytics
- Bulk member operations

### 🔧 Module Management
- Browse and install community modules
- Enable/disable installed modules
- Module configuration and settings
- Module performance monitoring

### 📊 Analytics Dashboard
- Real-time community statistics
- Member activity metrics
- Module usage analytics
- Engagement and growth tracking

### 🎨 Design System
- Color palette: White, Yellow, Black
- Consistent Material Design components
- Responsive layout for all screen sizes
- Dark mode support (planned)

## Technical Stack

- **Framework**: React Native 0.72.6
- **Navigation**: React Navigation 6
- **State Management**: React Context + Hooks
- **HTTP Client**: Axios with interceptors
- **Storage**: AsyncStorage + Keychain
- **UI Components**: Custom components with Material Design
- **Icons**: React Native Vector Icons
- **Charts**: React Native Chart Kit
- **Animations**: React Native Reanimated

## Prerequisites

- Node.js 18+
- React Native development environment
- Android Studio (for Android)
- Xcode (for iOS)
- WaddleBot Premium subscription

## Installation

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd Premium
   ```

2. **Install dependencies**
   ```bash
   npm install
   ```

3. **iOS Setup**
   ```bash
   cd ios && pod install && cd ..
   ```

4. **Configure environment**
   ```bash
   cp .env.example .env
   # Edit .env with your API endpoints
   ```

## Development

### Start Metro bundler
```bash
npm start
```

### Run on Android
```bash
npm run android
```

### Run on iOS
```bash
npm run ios
```

### Run tests
```bash
npm test
```

### Lint code
```bash
npm run lint
```

## Building for Production

### Android
```bash
npm run build:android
```

### iOS
```bash
npm run build:ios
```

## API Configuration

The app connects to WaddleBot APIs at:
- **Base URL**: `https://api.waddlebot.io`
- **Community API**: `https://api.waddlebot.io/community`
- **Router API**: `https://api.waddlebot.io/router`
- **Marketplace API**: `https://api.waddlebot.io/marketplace`

## Authentication

The app uses JWT token-based authentication with automatic token refresh. Users must have an active premium subscription to access the app.

## Premium Features

- Mobile community management
- Real-time member monitoring
- Advanced module controls
- Comprehensive analytics
- Priority support access

## Security

- All API communications use HTTPS
- JWT tokens stored securely in Keychain
- Premium subscription verification
- Role-based permission checking

## License

This software is exclusively available to WaddleBot Premium subscribers. See LICENSE file for full terms.

## Support

For premium support, contact: premium@waddlebot.com

## Contributing

This is proprietary software for premium subscribers only. Contributing guidelines are available to authorized developers.

---

© 2024 WaddleBot - Premium Mobile App