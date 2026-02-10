import SwiftUI

struct SettingsView: View {
    @EnvironmentObject var authManager: AuthenticationManager
    @Environment(\.colorScheme) var colorScheme

    @StateObject private var viewModel = SettingsViewModel()
    @State private var showLogoutConfirmation = false

    var body: some View {
        NavigationStack {
            ScrollView {
                VStack(spacing: Spacing.lg) {
                    profileSection

                    linkedPlatformsSection

                    accountSection

                    appInfoSection
                }
                .padding(.horizontal, Spacing.md)
                .padding(.top, Spacing.md)
            }
            .background(Color.adaptiveBackground(colorScheme))
            .navigationTitle("Settings")
        }
        .task {
            await viewModel.loadLinkedPlatforms()
        }
        .alert("Sign Out", isPresented: $showLogoutConfirmation) {
            Button("Cancel", role: .cancel) {}
            Button("Sign Out", role: .destructive) {
                Task { await authManager.logout() }
            }
        } message: {
            Text("Are you sure you want to sign out?")
        }
    }

    private var profileSection: some View {
        VStack(spacing: Spacing.md) {
            sectionHeader("Profile")

            HStack(spacing: Spacing.md) {
                profileAvatar

                VStack(alignment: .leading, spacing: Spacing.xxs) {
                    Text(authManager.currentUser?.username ?? "User")
                        .font(Typography.headline)
                        .foregroundColor(Color.adaptiveText(colorScheme))

                    Text(authManager.currentUser?.email ?? "")
                        .font(Typography.subheadline)
                        .foregroundColor(Color.adaptiveSecondaryText(colorScheme))
                }

                Spacer()

                Image(systemName: "chevron.right")
                    .font(.system(size: 14, weight: .semibold))
                    .foregroundColor(Color.adaptiveSecondaryText(colorScheme).opacity(0.5))
            }
            .padding(Spacing.md)
            .cardStyle()
        }
    }

    private var profileAvatar: some View {
        Group {
            if let avatarUrl = authManager.currentUser?.avatarUrl, let url = URL(string: avatarUrl) {
                AsyncImage(url: url) { phase in
                    switch phase {
                    case .success(let image):
                        image
                            .resizable()
                            .aspectRatio(contentMode: .fill)
                    case .failure, .empty:
                        placeholderAvatar
                    @unknown default:
                        placeholderAvatar
                    }
                }
            } else {
                placeholderAvatar
            }
        }
        .frame(width: 56, height: 56)
        .clipShape(Circle())
    }

    private var placeholderAvatar: some View {
        ZStack {
            Theme.accent.opacity(0.2)

            Image(systemName: "person.fill")
                .font(.system(size: 24))
                .foregroundColor(Theme.accent)
        }
    }

    private var linkedPlatformsSection: some View {
        VStack(spacing: Spacing.md) {
            sectionHeader("Linked Platforms")

            if viewModel.isLoading {
                HStack {
                    Spacer()
                    ProgressView()
                    Spacer()
                }
                .padding(Spacing.lg)
                .cardStyle()
            } else if viewModel.linkedPlatforms.isEmpty {
                VStack(spacing: Spacing.sm) {
                    Image(systemName: "link")
                        .font(.system(size: 24))
                        .foregroundColor(Color.adaptiveSecondaryText(colorScheme))

                    Text("No linked platforms")
                        .font(Typography.subheadline)
                        .foregroundColor(Color.adaptiveSecondaryText(colorScheme))
                }
                .frame(maxWidth: .infinity)
                .padding(Spacing.lg)
                .cardStyle()
            } else {
                VStack(spacing: 0) {
                    ForEach(Array(viewModel.linkedPlatforms.enumerated()), id: \.element.id) { index, platform in
                        LinkedPlatformRow(platform: platform)

                        if index < viewModel.linkedPlatforms.count - 1 {
                            Divider()
                                .padding(.leading, 56)
                        }
                    }
                }
                .cardStyle()
            }
        }
    }

    private var accountSection: some View {
        VStack(spacing: Spacing.md) {
            sectionHeader("Account")

            VStack(spacing: 0) {
                SettingsRow(icon: "bell.fill", title: "Notifications", iconColor: Theme.warning)

                Divider()
                    .padding(.leading, 56)

                SettingsRow(icon: "lock.fill", title: "Privacy & Security", iconColor: Theme.success)

                Divider()
                    .padding(.leading, 56)

                SettingsRow(icon: "questionmark.circle.fill", title: "Help & Support", iconColor: Theme.accent)
            }
            .cardStyle()
        }
    }

    private var appInfoSection: some View {
        VStack(spacing: Spacing.md) {
            sectionHeader("App")

            VStack(spacing: 0) {
                SettingsRow(icon: "doc.text.fill", title: "Terms of Service", iconColor: Color.adaptiveSecondaryText(colorScheme))

                Divider()
                    .padding(.leading, 56)

                SettingsRow(icon: "hand.raised.fill", title: "Privacy Policy", iconColor: Color.adaptiveSecondaryText(colorScheme))

                Divider()
                    .padding(.leading, 56)

                HStack(spacing: Spacing.md) {
                    Image(systemName: "info.circle.fill")
                        .font(.system(size: 20))
                        .foregroundColor(Color.adaptiveSecondaryText(colorScheme))
                        .frame(width: 32)

                    Text("Version")
                        .font(Typography.body)
                        .foregroundColor(Color.adaptiveText(colorScheme))

                    Spacer()

                    Text(appVersion)
                        .font(Typography.body)
                        .foregroundColor(Color.adaptiveSecondaryText(colorScheme))
                }
                .padding(Spacing.md)
            }
            .cardStyle()

            Button(action: { showLogoutConfirmation = true }) {
                HStack {
                    Spacer()
                    Text("Sign Out")
                        .font(Typography.headline)
                        .foregroundColor(Theme.error)
                    Spacer()
                }
                .padding(Spacing.md)
                .cardStyle()
            }
            .padding(.top, Spacing.sm)
        }
    }

    private func sectionHeader(_ title: String) -> some View {
        HStack {
            Text(title)
                .font(Typography.subheadline)
                .foregroundColor(Color.adaptiveSecondaryText(colorScheme))
                .textCase(.uppercase)

            Spacer()
        }
        .padding(.horizontal, Spacing.xxs)
    }

    private var appVersion: String {
        let version = Bundle.main.infoDictionary?["CFBundleShortVersionString"] as? String ?? "1.0"
        let build = Bundle.main.infoDictionary?["CFBundleVersion"] as? String ?? "1"
        return "\(version) (\(build))"
    }
}

struct LinkedPlatformRow: View {
    let platform: LinkedPlatform

    @Environment(\.colorScheme) var colorScheme

    var body: some View {
        HStack(spacing: Spacing.md) {
            Image(systemName: platform.platformIcon)
                .font(.system(size: 20))
                .foregroundColor(Theme.platformColor(platform.platform))
                .frame(width: 32)

            VStack(alignment: .leading, spacing: 2) {
                Text(platform.platform.capitalized)
                    .font(Typography.headline)
                    .foregroundColor(Color.adaptiveText(colorScheme))

                Text(platform.username)
                    .font(Typography.caption)
                    .foregroundColor(Color.adaptiveSecondaryText(colorScheme))
            }

            Spacer()

            Image(systemName: "checkmark.circle.fill")
                .font(.system(size: 20))
                .foregroundColor(Theme.success)
        }
        .padding(Spacing.md)
    }
}

struct SettingsRow: View {
    let icon: String
    let title: String
    let iconColor: Color

    @Environment(\.colorScheme) var colorScheme

    var body: some View {
        HStack(spacing: Spacing.md) {
            Image(systemName: icon)
                .font(.system(size: 20))
                .foregroundColor(iconColor)
                .frame(width: 32)

            Text(title)
                .font(Typography.body)
                .foregroundColor(Color.adaptiveText(colorScheme))

            Spacer()

            Image(systemName: "chevron.right")
                .font(.system(size: 14, weight: .semibold))
                .foregroundColor(Color.adaptiveSecondaryText(colorScheme).opacity(0.5))
        }
        .padding(Spacing.md)
    }
}

@MainActor
final class SettingsViewModel: ObservableObject {
    @Published var linkedPlatforms: [LinkedPlatform] = []
    @Published var isLoading = false
    @Published var error: String?

    func loadLinkedPlatforms() async {
        isLoading = true
        error = nil

        do {
            linkedPlatforms = try await APIClient.shared.getLinkedPlatforms()
        } catch let apiError as APIError {
            error = apiError.localizedDescription
        } catch {
            self.error = "Failed to load linked platforms"
        }

        isLoading = false
    }
}

#Preview {
    SettingsView()
        .environmentObject(AuthenticationManager())
}
