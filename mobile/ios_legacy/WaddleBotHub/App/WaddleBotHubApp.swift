import SwiftUI

@main
struct WaddleBotHubApp: App {
    @StateObject private var authManager = AuthenticationManager()

    var body: some Scene {
        WindowGroup {
            ContentView()
                .environmentObject(authManager)
                .tint(Theme.accent)
        }
    }
}
