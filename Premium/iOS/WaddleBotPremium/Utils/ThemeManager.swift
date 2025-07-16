import SwiftUI

class ThemeManager: ObservableObject {
    static let shared = ThemeManager()
    
    private init() {}
    
    func applyTheme() {
        // Apply global theme settings
        UINavigationBar.appearance().largeTitleTextAttributes = [
            .foregroundColor: UIColor(AppColors.textPrimary)
        ]
        UINavigationBar.appearance().titleTextAttributes = [
            .foregroundColor: UIColor(AppColors.textPrimary)
        ]
        UINavigationBar.appearance().tintColor = UIColor(AppColors.secondary)
        UINavigationBar.appearance().backgroundColor = UIColor(AppColors.background)
        
        UITabBar.appearance().backgroundColor = UIColor(AppColors.cardBackground)
        UITabBar.appearance().tintColor = UIColor(AppColors.secondary)
        UITabBar.appearance().unselectedItemTintColor = UIColor(AppColors.textSecondary)
    }
}

struct AppColors {
    // Primary brand colors (white, yellow, black)
    static let primary = Color(red: 1.0, green: 0.84, blue: 0.0) // Gold/Yellow
    static let secondary = Color(red: 1.0, green: 0.84, blue: 0.0) // Gold/Yellow
    static let accent = Color(red: 1.0, green: 0.96, blue: 0.72) // Light yellow
    
    // Background colors
    static let background = Color.white
    static let cardBackground = Color(red: 0.98, green: 0.98, blue: 0.98)
    static let inputBackground = Color(red: 0.95, green: 0.95, blue: 0.95)
    
    // Text colors
    static let textPrimary = Color.black
    static let textSecondary = Color(red: 0.4, green: 0.4, blue: 0.4)
    static let textMuted = Color(red: 0.6, green: 0.6, blue: 0.6)
    static let textLight = Color.white
    
    // Border colors
    static let border = Color(red: 0.9, green: 0.9, blue: 0.9)
    static let inputBorder = Color(red: 0.85, green: 0.85, blue: 0.85)
    
    // Status colors
    static let success = Color(red: 0.3, green: 0.69, blue: 0.31)
    static let warning = Color(red: 1.0, green: 0.6, blue: 0.0)
    static let error = Color(red: 0.96, green: 0.26, blue: 0.21)
    static let info = Color(red: 0.13, green: 0.59, blue: 0.95)
    
    // Reputation colors
    static let reputationExcellent = Color(red: 0.3, green: 0.69, blue: 0.31)
    static let reputationGood = Color(red: 0.13, green: 0.59, blue: 0.95)
    static let reputationFair = Color(red: 1.0, green: 0.6, blue: 0.0)
    static let reputationPoor = Color(red: 0.96, green: 0.26, blue: 0.21)
    static let reputationBanned = Color(red: 0.46, green: 0.46, blue: 0.46)
    
    // Overlay
    static let overlay = Color.black.opacity(0.5)
}

struct AppFonts {
    static let largeTitle = Font.system(size: 28, weight: .bold)
    static let title = Font.system(size: 24, weight: .bold)
    static let headline = Font.system(size: 20, weight: .bold)
    static let title2 = Font.system(size: 18, weight: .semibold)
    static let body = Font.system(size: 16, weight: .regular)
    static let callout = Font.system(size: 14, weight: .regular)
    static let caption = Font.system(size: 12, weight: .regular)
    static let caption2 = Font.system(size: 10, weight: .regular)
}

struct AppSpacing {
    static let tiny: CGFloat = 4
    static let small: CGFloat = 8
    static let medium: CGFloat = 16
    static let large: CGFloat = 24
    static let xlarge: CGFloat = 32
    static let xxlarge: CGFloat = 48
}

struct AppSizes {
    static let buttonHeight: CGFloat = 44
    static let inputHeight: CGFloat = 44
    static let cardCornerRadius: CGFloat = 12
    static let buttonCornerRadius: CGFloat = 8
    static let screenMargin: CGFloat = 16
}

struct AppShadows {
    static let light = Shadow(color: Color.black.opacity(0.1), radius: 2, x: 0, y: 1)
    static let medium = Shadow(color: Color.black.opacity(0.15), radius: 4, x: 0, y: 2)
    static let heavy = Shadow(color: Color.black.opacity(0.2), radius: 8, x: 0, y: 4)
}

struct Shadow {
    let color: Color
    let radius: CGFloat
    let x: CGFloat
    let y: CGFloat
}

extension View {
    func applyShadow(_ shadow: Shadow) -> some View {
        self.shadow(color: shadow.color, radius: shadow.radius, x: shadow.x, y: shadow.y)
    }
}