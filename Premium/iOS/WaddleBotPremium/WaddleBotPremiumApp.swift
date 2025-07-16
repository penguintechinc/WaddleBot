import SwiftUI

@main
struct WaddleBotPremiumApp: App {
    @StateObject private var authManager = AuthenticationManager()
    
    var body: some Scene {
        WindowGroup {
            ContentView()
                .environmentObject(authManager)
                .onAppear {
                    ThemeManager.shared.applyTheme()
                }
        }
    }
}