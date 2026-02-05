# CookieBanner Component Documentation

## Overview
The `CookieBanner.jsx` component is a GDPR-compliant cookie consent banner that appears at the bottom of the screen. It allows users to accept all cookies, reject non-essential cookies, or customize their preferences.

## File Location
```
/home/penguin/code/Waddles/admin/hub_module/frontend/src/components/CookieBanner.jsx
```

## Component Features

### Visual Design
- **Position**: Fixed bottom of screen, full width
- **Background**: Navy dark theme (#102a43) matching Waddles design system
- **Text**: Sky blue (#e0f2fe) for primary content, navy-300 for secondary
- **Animation**: Smooth slide-up animation on mount
- **Z-Index**: 50 (overlays all content)
- **Responsive**: Stacked buttons on mobile, inline on desktop

### Functionality
- **Auto-show**: Displays on first visit (when no consent saved)
- **Accept All**: Saves all cookie preferences and dismisses banner
- **Reject Non-Essential**: Saves only essential cookies and dismisses banner
- **Customize**: Triggers preferences modal (placeholder for hook integration)
- **Dismiss**: Close button (X) for user dismissal
- **Policy Link**: Opens /cookie-policy page in new tab

### Accessibility
- Full keyboard navigation support
- ARIA labels on all interactive elements
- Focus visible styles with visible rings
- Semantic HTML with proper button and link elements
- Live region with aria-live="polite" for screen readers

## Implementation Details

### State Management
```javascript
const [isVisible, setIsVisible] = useState(false);    // Banner visibility
const [isAnimating, setIsAnimating] = useState(false); // Animation state
```

### Key Methods
- `handleAcceptAll()`: Save all cookies accepted
- `handleRejectNonEssential()`: Save only essential cookies
- `handleCustomize()`: Open cookie preferences modal
- `dismissBanner()`: Hide banner with animation

### Storage Format
Saves consent to localStorage as JSON:
```json
{
  "essential": true,
  "analytics": true,
  "marketing": true,
  "preferences": true,
  "timestamp": "2024-12-09T10:30:00.000Z",
  "policyVersion": "1.0"
}
```

## Styling Breakdown

### Button Styles
| Button | Styling | Hover | Focus |
|--------|---------|-------|-------|
| Accept All | sky-600 | sky-700 | ring-sky-500 |
| Reject | navy-800 border | navy-700 | ring-sky-400 |
| Customize | sky-400 border | navy-700 | ring-sky-400 |
| Close | navy-400 | sky-100 | ring-sky-400 |

### Tailwind Classes Used
- **Layout**: `flex flex-col md:flex-row`, `gap-4 md:gap-6`
- **Positioning**: `fixed bottom-0 left-0 right-0 z-50`
- **Animation**: `transition-transform duration-300`, `translate-y-full/0`
- **Spacing**: `px-4 sm:px-6 lg:px-8 py-6`
- **Colors**: `navy-900`, `sky-100`, `sky-600`, `navy-400`

## Integration Guide

### 1. Import in App.jsx
```javascript
import CookieBanner from './components/CookieBanner';

function App() {
  return (
    <>
      {/* Other components */}
      <CookieBanner />
    </>
  );
}
```

### 2. Create useCookieConsent Hook (Optional)
The component is designed to work with a `useCookieConsent` hook. Create this hook to replace localStorage calls:

```javascript
// src/hooks/useCookieConsent.js
export function useCookieConsent() {
  const [showBanner, setShowBanner] = useState(false);
  
  const acceptAll = () => {
    // Save all cookies
    setShowBanner(false);
  };
  
  const rejectNonEssential = () => {
    // Save only essential cookies
    setShowBanner(false);
  };
  
  const openPreferences = () => {
    // Open preferences modal
  };
  
  return { showBanner, acceptAll, rejectNonEssential, openPreferences };
}
```

### 3. Update Component to Use Hook
Replace placeholder comments (lines 23-24, 47, 61, 67) with actual hook usage.

## Mobile Responsiveness

### Breakpoints
- **Mobile (< 640px)**: Stacked buttons, single column
- **Tablet (640px - 768px)**: Row buttons with reduced gap
- **Desktop (> 768px)**: Full horizontal layout with max-width

### CSS Classes
```tailwind
flex flex-col sm:flex-row              # Mobile: stacked, tablet+: row
gap-3 sm:gap-2 md:items-end           # Responsive gap
md:flex-shrink-0                        # Desktop: prevent shrink
```

## Animation Details

### Mount Animation
1. Component renders with `translate-y-full` (off-screen)
2. After 50ms, sets `isAnimating = true`
3. CSS transition slides banner up from bottom
4. Duration: 300ms with `transition-transform`

### Dismiss Animation
1. Sets `isAnimating = false`
2. CSS transition slides banner down
3. After 300ms, removes from DOM with `setIsVisible(false)`

## Browser Support
- Modern browsers with ES6+ support
- CSS Grid and Flexbox support required
- CSS Transitions/Transforms support required
- localStorage API support required

## Performance Considerations
- Lightweight component (187 lines)
- No external dependencies beyond React and React Router
- Minimal re-renders (only 2 state changes)
- Animation uses CSS transforms (GPU accelerated)

## Testing Recommendations

### Unit Tests
- [ ] Component mounts and shows banner on first visit
- [ ] localStorage is populated correctly
- [ ] Animation classes update properly
- [ ] Buttons call correct handlers
- [ ] Banner dismisses after selection

### Integration Tests
- [ ] Cookie policy link opens correctly
- [ ] Consent data persists across page reloads
- [ ] Banner doesn't show if consent already exists
- [ ] Keyboard navigation works

### Accessibility Tests
- [ ] Screen reader announces banner correctly
- [ ] All buttons are keyboard accessible
- [ ] Focus indicators are visible
- [ ] Color contrast passes WCAG AA

## Future Enhancements

1. **useCookieConsent Hook**: Replace localStorage with proper state management
2. **Cookie Preferences Modal**: Build modal for granular cookie selection
3. **Expiration Logic**: Auto-ask after 1 year
4. **Analytics Integration**: Track consent rates and user choices
5. **Internationalization**: Support multiple languages
6. **Cookie Categories**: Display and manage specific cookie categories
7. **Third-party Scripts**: Dynamically load scripts based on consent

## Troubleshooting

### Banner not appearing
- Check browser localStorage is enabled
- Verify component is imported in main App.jsx
- Check console for errors

### Animation stuttering
- Ensure CSS transitions are not disabled
- Check for conflicting CSS transitions
- Verify GPU acceleration available

### Buttons not responding
- Check JavaScript console for errors
- Verify React event handlers are bound
- Test with different browser

## CSS Color Reference
```
navy-900:   #102a43 (primary background)
navy-800:   #243b53
navy-700:   #334e68
navy-400:   #829ab1
navy-300:   #9fb3c8 (secondary text)
sky-600:    #0284c7 (primary button)
sky-400:    #38bdf8 (accent text)
sky-100:    #e0f2fe (primary text)
```

## Dependencies
- `react` (^18.0)
- `react-router-dom` (^6.0)
- `@heroicons/react` (^2.0)
- `tailwindcss` (^3.0)

---

*Last Updated: 2024-12-09*
*Component Version: 1.0*
