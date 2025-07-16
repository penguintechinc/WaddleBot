import SwiftUI

struct ContentView: View {
    @EnvironmentObject var authManager: AuthenticationManager
    @State private var isLoading = true
    @State private var hasAcceptedLicense = false
    
    var body: some View {
        Group {
            if !hasAcceptedLicense {
                PremiumLicenseView(isAccepted: $hasAcceptedLicense)
            } else if isLoading {
                LoadingView()
            } else if authManager.isAuthenticated {
                DashboardView()
            } else {
                LoginView()
            }
        }
        .onAppear {
            checkLicenseAcceptance()
        }
        .onChange(of: hasAcceptedLicense) { accepted in
            if accepted {
                checkAuthenticationStatus()
            }
        }
    }
    
    private func checkLicenseAcceptance() {
        hasAcceptedLicense = UserDefaults.standard.bool(forKey: "license_accepted")
        if hasAcceptedLicense {
            checkAuthenticationStatus()
        }
    }
    
    private func checkAuthenticationStatus() {
        Task {
            await authManager.checkAuthenticationStatus()
            isLoading = false
        }
    }
}

struct LoadingView: View {
    var body: some View {
        VStack {
            ProgressView()
                .progressViewStyle(CircularProgressViewStyle(tint: AppColors.secondary))
                .scaleEffect(1.5)
            
            Text("Loading...")
                .font(.headline)
                .foregroundColor(AppColors.textSecondary)
                .padding(.top, 20)
        }
        .frame(maxWidth: .infinity, maxHeight: .infinity)
        .background(AppColors.background)
    }
}

#Preview {
    ContentView()
        .environmentObject(AuthenticationManager())
}