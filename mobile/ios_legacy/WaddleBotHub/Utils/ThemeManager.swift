import SwiftUI

// MARK: - Theme Colors

enum Theme {
    // WaddleBot Brand Colors
    static let accent = Color(hex: "6366F1")
    static let accentLight = Color(hex: "818CF8")
    static let accentDark = Color(hex: "4F46E5")

    // Semantic Colors
    static let success = Color(hex: "10B981")
    static let warning = Color(hex: "F59E0B")
    static let error = Color(hex: "EF4444")

    // Background Colors
    static let backgroundPrimary = Color("BackgroundPrimary")
    static let backgroundSecondary = Color("BackgroundSecondary")
    static let backgroundTertiary = Color("BackgroundTertiary")

    // Text Colors
    static let textPrimary = Color("TextPrimary")
    static let textSecondary = Color("TextSecondary")
    static let textTertiary = Color("TextTertiary")

    // Platform Colors
    static func platformColor(_ platform: String) -> Color {
        switch platform.lowercased() {
        case "twitch": return Color(hex: "9146FF")
        case "discord": return Color(hex: "5865F2")
        case "youtube": return Color(hex: "FF0000")
        case "slack": return Color(hex: "4A154B")
        default: return accent
        }
    }
}

// MARK: - Color Extension

extension Color {
    init(hex: String) {
        let hex = hex.trimmingCharacters(in: CharacterSet.alphanumerics.inverted)
        var int: UInt64 = 0
        Scanner(string: hex).scanHexInt64(&int)

        let r, g, b, a: UInt64
        switch hex.count {
        case 6:
            (r, g, b, a) = ((int >> 16) & 0xFF, (int >> 8) & 0xFF, int & 0xFF, 255)
        case 8:
            (r, g, b, a) = ((int >> 24) & 0xFF, (int >> 16) & 0xFF, (int >> 8) & 0xFF, int & 0xFF)
        default:
            (r, g, b, a) = (0, 0, 0, 255)
        }

        self.init(
            .sRGB,
            red: Double(r) / 255,
            green: Double(g) / 255,
            blue: Double(b) / 255,
            opacity: Double(a) / 255
        )
    }
}

// MARK: - Adaptive Colors

extension Color {
    static func adaptiveBackground(_ colorScheme: ColorScheme) -> Color {
        colorScheme == .dark ? Color(hex: "1C1C1E") : Color(hex: "F2F2F7")
    }

    static func adaptiveCardBackground(_ colorScheme: ColorScheme) -> Color {
        colorScheme == .dark ? Color(hex: "2C2C2E") : .white
    }

    static func adaptiveText(_ colorScheme: ColorScheme) -> Color {
        colorScheme == .dark ? .white : .black
    }

    static func adaptiveSecondaryText(_ colorScheme: ColorScheme) -> Color {
        colorScheme == .dark ? Color(hex: "EBEBF5").opacity(0.6) : Color(hex: "3C3C43").opacity(0.6)
    }
}

// MARK: - View Modifiers

struct CardStyle: ViewModifier {
    @Environment(\.colorScheme) var colorScheme

    func body(content: Content) -> some View {
        content
            .background(Color.adaptiveCardBackground(colorScheme))
            .cornerRadius(12)
            .shadow(
                color: colorScheme == .dark ? .clear : Color.black.opacity(0.05),
                radius: 8,
                x: 0,
                y: 2
            )
    }
}

struct PrimaryButtonStyle: ButtonStyle {
    @Environment(\.isEnabled) var isEnabled

    func makeBody(configuration: Configuration) -> some View {
        configuration.label
            .font(.headline)
            .foregroundColor(.white)
            .frame(maxWidth: .infinity)
            .padding(.vertical, 14)
            .background(
                isEnabled
                    ? (configuration.isPressed ? Theme.accentDark : Theme.accent)
                    : Theme.accent.opacity(0.5)
            )
            .cornerRadius(10)
            .scaleEffect(configuration.isPressed ? 0.98 : 1.0)
            .animation(.easeInOut(duration: 0.1), value: configuration.isPressed)
    }
}

struct SecondaryButtonStyle: ButtonStyle {
    @Environment(\.colorScheme) var colorScheme

    func makeBody(configuration: Configuration) -> some View {
        configuration.label
            .font(.headline)
            .foregroundColor(Theme.accent)
            .frame(maxWidth: .infinity)
            .padding(.vertical, 14)
            .background(
                configuration.isPressed
                    ? Theme.accent.opacity(0.1)
                    : Color.clear
            )
            .overlay(
                RoundedRectangle(cornerRadius: 10)
                    .stroke(Theme.accent, lineWidth: 1.5)
            )
            .cornerRadius(10)
            .scaleEffect(configuration.isPressed ? 0.98 : 1.0)
            .animation(.easeInOut(duration: 0.1), value: configuration.isPressed)
    }
}

// MARK: - View Extensions

extension View {
    func cardStyle() -> some View {
        modifier(CardStyle())
    }

    func primaryButton() -> some View {
        buttonStyle(PrimaryButtonStyle())
    }

    func secondaryButton() -> some View {
        buttonStyle(SecondaryButtonStyle())
    }
}

// MARK: - Typography

enum Typography {
    static let largeTitle = Font.system(size: 34, weight: .bold)
    static let title = Font.system(size: 28, weight: .bold)
    static let title2 = Font.system(size: 22, weight: .bold)
    static let title3 = Font.system(size: 20, weight: .semibold)
    static let headline = Font.system(size: 17, weight: .semibold)
    static let body = Font.system(size: 17, weight: .regular)
    static let callout = Font.system(size: 16, weight: .regular)
    static let subheadline = Font.system(size: 15, weight: .regular)
    static let footnote = Font.system(size: 13, weight: .regular)
    static let caption = Font.system(size: 12, weight: .regular)
}

// MARK: - Spacing

enum Spacing {
    static let xxs: CGFloat = 4
    static let xs: CGFloat = 8
    static let sm: CGFloat = 12
    static let md: CGFloat = 16
    static let lg: CGFloat = 24
    static let xl: CGFloat = 32
    static let xxl: CGFloat = 48
}
