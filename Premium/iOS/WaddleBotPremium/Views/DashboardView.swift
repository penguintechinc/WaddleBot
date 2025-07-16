import SwiftUI

struct DashboardView: View {
    @EnvironmentObject var authManager: AuthenticationManager
    @State private var selectedTab = 0
    
    var body: some View {
        TabView(selection: $selectedTab) {
            CommunityListView()
                .tabItem {
                    Image(systemName: "house.fill")
                    Text("Communities")
                }
                .tag(0)
            
            ModulesView()
                .tabItem {
                    Image(systemName: "cube.box.fill")
                    Text("Modules")
                }
                .tag(1)
            
            AnalyticsView()
                .tabItem {
                    Image(systemName: "chart.bar.fill")
                    Text("Analytics")
                }
                .tag(2)
            
            ProfileView()
                .tabItem {
                    Image(systemName: "person.fill")
                    Text("Profile")
                }
                .tag(3)
        }
        .accentColor(AppColors.secondary)
        .onAppear {
            configureTabBar()
        }
    }
    
    private func configureTabBar() {
        let appearance = UITabBarAppearance()
        appearance.configureWithOpaqueBackground()
        appearance.backgroundColor = UIColor(AppColors.cardBackground)
        
        UITabBar.appearance().standardAppearance = appearance
        UITabBar.appearance().scrollEdgeAppearance = appearance
    }
}

struct ModulesView: View {
    var body: some View {
        NavigationView {
            VStack {
                Text("Modules")
                    .font(AppFonts.largeTitle)
                    .padding()
                
                Text("Module marketplace coming soon...")
                    .font(AppFonts.body)
                    .foregroundColor(AppColors.textSecondary)
                
                Spacer()
            }
            .navigationBarTitleDisplayMode(.inline)
            .background(AppColors.background)
        }
    }
}

struct AnalyticsView: View {
    var body: some View {
        NavigationView {
            VStack {
                Text("Analytics")
                    .font(AppFonts.largeTitle)
                    .padding()
                
                Text("Analytics dashboard coming soon...")
                    .font(AppFonts.body)
                    .foregroundColor(AppColors.textSecondary)
                
                Spacer()
            }
            .navigationBarTitleDisplayMode(.inline)
            .background(AppColors.background)
        }
    }
}

struct ProfileView: View {
    @EnvironmentObject var authManager: AuthenticationManager
    
    var body: some View {
        NavigationView {
            VStack(spacing: AppSpacing.large) {
                // Profile header
                VStack(spacing: AppSpacing.medium) {
                    Circle()
                        .fill(AppColors.secondary)
                        .frame(width: 80, height: 80)
                        .overlay(
                            Text(authManager.currentUser?.displayName.prefix(1).uppercased() ?? "U")
                                .font(AppFonts.largeTitle)
                                .fontWeight(.bold)
                                .foregroundColor(AppColors.textPrimary)
                        )
                    
                    VStack(spacing: AppSpacing.small) {
                        Text(authManager.currentUser?.displayName ?? "Unknown User")
                            .font(AppFonts.title)
                            .fontWeight(.bold)
                            .foregroundColor(AppColors.textPrimary)
                        
                        Text("@\(authManager.currentUser?.username ?? "unknown")")
                            .font(AppFonts.callout)
                            .foregroundColor(AppColors.textSecondary)
                        
                        if authManager.currentUser?.isPremium == true {
                            HStack {
                                Image(systemName: "star.fill")
                                    .foregroundColor(AppColors.secondary)
                                Text("Premium Member")
                                    .font(AppFonts.caption)
                                    .fontWeight(.semibold)
                                    .foregroundColor(AppColors.textPrimary)
                            }
                            .padding(.horizontal, AppSpacing.small)
                            .padding(.vertical, AppSpacing.tiny)
                            .background(AppColors.accent.opacity(0.3))
                            .cornerRadius(AppSizes.buttonCornerRadius)
                        }
                    }
                }
                .padding(.top, AppSpacing.large)
                
                // Settings list
                VStack(spacing: 0) {
                    ProfileMenuItem(icon: "person.circle", title: "Account Settings", action: {})
                    ProfileMenuItem(icon: "bell", title: "Notifications", action: {})
                    ProfileMenuItem(icon: "lock", title: "Privacy & Security", action: {})
                    ProfileMenuItem(icon: "questionmark.circle", title: "Help & Support", action: {})
                    ProfileMenuItem(icon: "info.circle", title: "About", action: {})
                }
                .background(AppColors.cardBackground)
                .cornerRadius(AppSizes.cardCornerRadius)
                
                Spacer()
                
                // Logout button
                Button(action: {
                    Task {
                        await authManager.logout()
                    }
                }) {
                    if authManager.isLoading {
                        ProgressView()
                            .progressViewStyle(CircularProgressViewStyle(tint: AppColors.textLight))
                            .frame(maxWidth: .infinity, minHeight: AppSizes.buttonHeight)
                    } else {
                        Text("Sign Out")
                            .font(AppFonts.body)
                            .fontWeight(.semibold)
                            .foregroundColor(AppColors.textLight)
                            .frame(maxWidth: .infinity, minHeight: AppSizes.buttonHeight)
                    }
                }
                .background(AppColors.error)
                .cornerRadius(AppSizes.buttonCornerRadius)
                .disabled(authManager.isLoading)
                
                // App version
                Text("Version \(AppConfig.appVersion)")
                    .font(AppFonts.caption)
                    .foregroundColor(AppColors.textMuted)
                    .padding(.bottom, AppSpacing.large)
            }
            .padding(.horizontal, AppSpacing.medium)
            .background(AppColors.background)
            .navigationTitle("Profile")
            .navigationBarTitleDisplayMode(.inline)
        }
    }
}

struct ProfileMenuItem: View {
    let icon: String
    let title: String
    let action: () -> Void
    
    var body: some View {
        Button(action: action) {
            HStack(spacing: AppSpacing.medium) {
                Image(systemName: icon)
                    .font(.title3)
                    .foregroundColor(AppColors.secondary)
                    .frame(width: 24)
                
                Text(title)
                    .font(AppFonts.body)
                    .foregroundColor(AppColors.textPrimary)
                
                Spacer()
                
                Image(systemName: "chevron.right")
                    .font(.caption)
                    .foregroundColor(AppColors.textSecondary)
            }
            .padding()
            .background(AppColors.cardBackground)
        }
        .buttonStyle(PlainButtonStyle())
    }
}

#Preview {
    DashboardView()
        .environmentObject(AuthenticationManager())
}