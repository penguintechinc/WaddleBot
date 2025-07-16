import Foundation
import SwiftUI

// MARK: - String Extensions
extension String {
    func isValidEmail() -> Bool {
        let emailRegEx = "[A-Z0-9a-z._%+-]+@[A-Za-z0-9.-]+\\.[A-Za-z]{2,64}"
        let emailPred = NSPredicate(format:"SELF MATCHES %@", emailRegEx)
        return emailPred.evaluate(with: self)
    }
    
    func capitalized() -> String {
        return self.prefix(1).capitalized + self.dropFirst()
    }
    
    func formatCurrency(_ currencyName: String = CurrencyConfig.defaultName) -> String {
        guard let amount = Double(self) else { return "0 \(currencyName)" }
        let formatter = NumberFormatter()
        formatter.numberStyle = .decimal
        formatter.groupingSeparator = ","
        return "\(formatter.string(from: NSNumber(value: amount)) ?? "0") \(currencyName)"
    }
    
    func formatCurrencyShort() -> String {
        guard let amount = Double(self) else { return "0" }
        if amount >= 1000000 {
            return String(format: "%.1fM", amount / 1000000)
        } else if amount >= 1000 {
            return String(format: "%.1fK", amount / 1000)
        } else {
            return String(format: "%.0f", amount)
        }
    }
}

// MARK: - Date Extensions
extension Date {
    func formatted(style: DateFormatter.Style = .medium) -> String {
        let formatter = DateFormatter()
        formatter.dateStyle = style
        formatter.timeStyle = .none
        return formatter.string(from: self)
    }
    
    func formattedDateTime() -> String {
        let formatter = DateFormatter()
        formatter.dateStyle = .medium
        formatter.timeStyle = .short
        return formatter.string(from: self)
    }
    
    func timeAgo() -> String {
        let calendar = Calendar.current
        let now = Date()
        let components = calendar.dateComponents([.minute, .hour, .day, .weekOfYear, .month, .year], from: self, to: now)
        
        if let year = components.year, year > 0 {
            return "\(year) year\(year == 1 ? "" : "s") ago"
        } else if let month = components.month, month > 0 {
            return "\(month) month\(month == 1 ? "" : "s") ago"
        } else if let week = components.weekOfYear, week > 0 {
            return "\(week) week\(week == 1 ? "" : "s") ago"
        } else if let day = components.day, day > 0 {
            return "\(day) day\(day == 1 ? "" : "s") ago"
        } else if let hour = components.hour, hour > 0 {
            return "\(hour) hour\(hour == 1 ? "" : "s") ago"
        } else if let minute = components.minute, minute > 0 {
            return "\(minute) minute\(minute == 1 ? "" : "s") ago"
        } else {
            return "Just now"
        }
    }
}

// MARK: - Double Extensions
extension Double {
    func formatCurrency(_ currencyName: String = CurrencyConfig.defaultName) -> String {
        let formatter = NumberFormatter()
        formatter.numberStyle = .decimal
        formatter.groupingSeparator = ","
        return "\(formatter.string(from: NSNumber(value: self)) ?? "0") \(currencyName)"
    }
    
    func formatCurrencyShort() -> String {
        if self >= 1000000 {
            return String(format: "%.1fM", self / 1000000)
        } else if self >= 1000 {
            return String(format: "%.1fK", self / 1000)
        } else {
            return String(format: "%.0f", self)
        }
    }
    
    func formatPayment(_ currency: String = PaymentConfig.defaultCurrency) -> String {
        let formatter = NumberFormatter()
        formatter.numberStyle = .currency
        formatter.currencyCode = currency
        return formatter.string(from: NSNumber(value: self)) ?? "$0.00"
    }
}

// MARK: - Int Extensions
extension Int {
    func formatCurrency(_ currencyName: String = CurrencyConfig.defaultName) -> String {
        return Double(self).formatCurrency(currencyName)
    }
    
    func formatCurrencyShort() -> String {
        return Double(self).formatCurrencyShort()
    }
    
    func formatDuration() -> String {
        let hours = self / 3600
        let minutes = (self % 3600) / 60
        let seconds = self % 60
        
        if hours > 0 {
            return "\(hours)h \(minutes)m \(seconds)s"
        } else if minutes > 0 {
            return "\(minutes)m \(seconds)s"
        } else {
            return "\(seconds)s"
        }
    }
}

// MARK: - View Extensions
extension View {
    func cornerRadius(_ radius: CGFloat, corners: UIRectCorner) -> some View {
        clipShape(RoundedCorner(radius: radius, corners: corners))
    }
    
    func hideKeyboard() {
        UIApplication.shared.sendAction(#selector(UIResponder.resignFirstResponder), to: nil, from: nil, for: nil)
    }
    
    func onTapGesture(perform action: @escaping () -> Void) -> some View {
        self.onTapGesture {
            action()
        }
    }
    
    @ViewBuilder
    func `if`<Content: View>(_ condition: Bool, transform: (Self) -> Content) -> some View {
        if condition {
            transform(self)
        } else {
            self
        }
    }
}

// MARK: - Color Extensions
extension Color {
    static func reputationColor(for score: Int) -> Color {
        switch score {
        case 750...ReputationConfig.maxScore:
            return AppColors.reputationExcellent
        case 650...749:
            return AppColors.reputationGood
        case 550...649:
            return AppColors.reputationFair
        case 500...549:
            return AppColors.reputationPoor
        default:
            return AppColors.reputationBanned
        }
    }
    
    static func reputationLabel(for score: Int) -> String {
        switch score {
        case 750...ReputationConfig.maxScore:
            return "Excellent"
        case 650...749:
            return "Good"
        case 550...649:
            return "Fair"
        case 500...549:
            return "Poor"
        default:
            return "Banned"
        }
    }
}

// MARK: - Custom Shapes
struct RoundedCorner: Shape {
    var radius: CGFloat = .infinity
    var corners: UIRectCorner = .allCorners

    func path(in rect: CGRect) -> Path {
        let path = UIBezierPath(
            roundedRect: rect,
            byRoundingCorners: corners,
            cornerRadii: CGSize(width: radius, height: radius)
        )
        return Path(path.cgPath)
    }
}

// MARK: - UserDefaults Extensions
extension UserDefaults {
    func setObject<T: Codable>(_ object: T, forKey key: String) {
        if let data = try? JSONEncoder().encode(object) {
            set(data, forKey: key)
        }
    }
    
    func getObject<T: Codable>(_ type: T.Type, forKey key: String) -> T? {
        guard let data = data(forKey: key) else { return nil }
        return try? JSONDecoder().decode(type, from: data)
    }
}

// MARK: - Array Extensions
extension Array {
    subscript(safe index: Int) -> Element? {
        return indices.contains(index) ? self[index] : nil
    }
}

// MARK: - Permission Utils
struct PermissionUtils {
    static func hasPermission(userRole: String?, permission: String) -> Bool {
        guard let role = userRole?.lowercased() else { return false }
        
        switch role {
        case "owner":
            return RolePermissions.owner.contains(permission)
        case "admin":
            return RolePermissions.admin.contains(permission)
        case "moderator":
            return RolePermissions.moderator.contains(permission)
        case "member":
            return RolePermissions.member.contains(permission)
        default:
            return false
        }
    }
    
    static func canBanMembers(userRole: String?) -> Bool {
        return hasPermission(userRole: userRole, permission: "ban_members")
    }
    
    static func canUnbanMembers(userRole: String?) -> Bool {
        return hasPermission(userRole: userRole, permission: "unban_members")
    }
    
    static func canEditReputation(userRole: String?) -> Bool {
        return hasPermission(userRole: userRole, permission: "edit_reputation")
    }
    
    static func canManageCurrency(userRole: String?) -> Bool {
        return hasPermission(userRole: userRole, permission: "manage_currency")
    }
    
    static func canManagePayments(userRole: String?) -> Bool {
        return hasPermission(userRole: userRole, permission: "manage_payments")
    }
    
    static func canCreateRaffles(userRole: String?) -> Bool {
        return hasPermission(userRole: userRole, permission: "create_raffles")
    }
    
    static func canCreateGiveaways(userRole: String?) -> Bool {
        return hasPermission(userRole: userRole, permission: "create_giveaways")
    }
    
    static func getPermissionMessage(userRole: String?, action: String) -> String {
        if !hasPermission(userRole: userRole, permission: action) {
            switch action {
            case "unban_members":
                return "Only community managers and admins can unban members"
            case "edit_reputation":
                return "Only community managers and admins can edit reputation scores"
            case "ban_members":
                return "You do not have permission to ban members"
            case "manage_currency":
                return "Only community managers and admins can manage currency settings"
            case "manage_payments":
                return "Only community managers and admins can manage payment settings"
            case "create_raffles":
                return "You do not have permission to create raffles"
            case "create_giveaways":
                return "You do not have permission to create giveaways"
            default:
                return "You do not have permission to perform this action"
            }
        }
        return ""
    }
}

// MARK: - Validation Utils
struct ValidationUtils {
    static func validateCurrencyAmount(_ amount: String) -> Bool {
        guard let numAmount = Double(amount) else { return false }
        return numAmount >= 0 && numAmount <= Double(CurrencyConfig.maxBalance)
    }
    
    static func validateCurrencyName(_ name: String) -> Bool {
        let trimmed = name.trimmingCharacters(in: .whitespacesAndNewlines)
        return !trimmed.isEmpty && trimmed.count <= 50
    }
    
    static func validateRewardAmount(_ amount: String, type: String) -> Bool {
        guard let numAmount = Double(amount) else { return false }
        
        switch type {
        case "chat":
            return numAmount >= Double(CurrencyConfig.minChatReward) && numAmount <= Double(CurrencyConfig.maxChatReward)
        case "event":
            return numAmount >= Double(CurrencyConfig.minEventReward) && numAmount <= Double(CurrencyConfig.maxEventReward)
        default:
            return true
        }
    }
    
    static func validatePaymentAmount(_ amount: String) -> Bool {
        guard let numAmount = Double(amount) else { return false }
        return numAmount >= PaymentConfig.minTransaction && numAmount <= PaymentConfig.maxTransaction
    }
    
    static func validateReputationThreshold(_ threshold: Int) -> Bool {
        return threshold >= ReputationConfig.minAutoBanThreshold && threshold <= ReputationConfig.maxAutoBanThreshold
    }
}