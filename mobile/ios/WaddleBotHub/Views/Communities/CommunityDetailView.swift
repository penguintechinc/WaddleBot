import SwiftUI

struct CommunityDetailView: View {
    let community: Community

    @Environment(\.colorScheme) var colorScheme
    @StateObject private var viewModel = CommunityDetailViewModel()

    var body: some View {
        ScrollView {
            VStack(spacing: Spacing.lg) {
                headerSection

                if viewModel.isLoading {
                    LoadingView(message: "Loading stats...")
                        .frame(height: 200)
                } else if let stats = viewModel.stats {
                    statsSection(stats: stats)
                }

                navigationSection
            }
            .padding(.horizontal, Spacing.md)
            .padding(.top, Spacing.md)
        }
        .background(Color.adaptiveBackground(colorScheme))
        .navigationTitle(community.name)
        .navigationBarTitleDisplayMode(.inline)
        .task {
            await viewModel.loadStats(communityId: community.id)
        }
        .refreshable {
            await viewModel.loadStats(communityId: community.id)
        }
    }

    private var headerSection: some View {
        VStack(spacing: Spacing.md) {
            communityIcon

            VStack(spacing: Spacing.xs) {
                Text(community.name)
                    .font(Typography.title2)
                    .foregroundColor(Color.adaptiveText(colorScheme))

                if let description = community.description, !description.isEmpty {
                    Text(description)
                        .font(Typography.body)
                        .foregroundColor(Color.adaptiveSecondaryText(colorScheme))
                        .multilineTextAlignment(.center)
                        .lineLimit(3)
                }

                platformBadge
            }
        }
        .padding(.vertical, Spacing.md)
    }

    private var communityIcon: some View {
        Group {
            if let iconUrl = community.iconUrl, let url = URL(string: iconUrl) {
                AsyncImage(url: url) { phase in
                    switch phase {
                    case .success(let image):
                        image
                            .resizable()
                            .aspectRatio(contentMode: .fill)
                    case .failure, .empty:
                        placeholderIcon
                    @unknown default:
                        placeholderIcon
                    }
                }
            } else {
                placeholderIcon
            }
        }
        .frame(width: 80, height: 80)
        .clipShape(RoundedRectangle(cornerRadius: 16))
    }

    private var placeholderIcon: some View {
        ZStack {
            Theme.platformColor(community.platform).opacity(0.2)

            Text(String(community.name.prefix(1)).uppercased())
                .font(.system(size: 32, weight: .bold))
                .foregroundColor(Theme.platformColor(community.platform))
        }
    }

    private var platformBadge: some View {
        HStack(spacing: 4) {
            Image(systemName: platformIcon)
                .font(.system(size: 12))

            Text(community.platform.capitalized)
                .font(Typography.subheadline)
        }
        .foregroundColor(Theme.platformColor(community.platform))
        .padding(.horizontal, 10)
        .padding(.vertical, 4)
        .background(Theme.platformColor(community.platform).opacity(0.15))
        .cornerRadius(6)
    }

    private var platformIcon: String {
        switch community.platform.lowercased() {
        case "twitch": return "tv"
        case "discord": return "message.fill"
        case "youtube": return "play.rectangle.fill"
        case "slack": return "number"
        default: return "link"
        }
    }

    private func statsSection(stats: CommunityStats) -> some View {
        LazyVGrid(columns: [GridItem(.flexible()), GridItem(.flexible())], spacing: Spacing.md) {
            StatCard(
                icon: "person.3.fill",
                title: "Total Members",
                value: "\(stats.totalMembers)",
                color: Theme.accent
            )

            StatCard(
                icon: "person.fill.checkmark",
                title: "Active Members",
                value: "\(stats.activeMembers)",
                color: Theme.success
            )

            StatCard(
                icon: "command",
                title: "Commands",
                value: "\(stats.totalCommands)",
                color: Theme.warning
            )

            StatCard(
                icon: "message.fill",
                title: "This Week",
                value: "\(stats.messagesThisWeek)",
                color: Theme.accentLight
            )
        }
    }

    private var navigationSection: some View {
        VStack(spacing: Spacing.sm) {
            NavigationLink(destination: MemberListView(communityId: community.id, communityName: community.name)) {
                NavigationRow(
                    icon: "person.2.fill",
                    title: "Members",
                    subtitle: "\(community.memberCount) members"
                )
            }

            NavigationRow(
                icon: "command",
                title: "Commands",
                subtitle: "Manage bot commands"
            )

            NavigationRow(
                icon: "gearshape.fill",
                title: "Settings",
                subtitle: "Community configuration"
            )
        }
        .padding(.top, Spacing.md)
    }
}

struct StatCard: View {
    let icon: String
    let title: String
    let value: String
    let color: Color

    @Environment(\.colorScheme) var colorScheme

    var body: some View {
        VStack(alignment: .leading, spacing: Spacing.sm) {
            HStack {
                Image(systemName: icon)
                    .font(.system(size: 16))
                    .foregroundColor(color)

                Spacer()
            }

            Text(value)
                .font(.system(size: 28, weight: .bold, design: .rounded))
                .foregroundColor(Color.adaptiveText(colorScheme))

            Text(title)
                .font(Typography.caption)
                .foregroundColor(Color.adaptiveSecondaryText(colorScheme))
        }
        .padding(Spacing.md)
        .frame(maxWidth: .infinity, alignment: .leading)
        .cardStyle()
    }
}

struct NavigationRow: View {
    let icon: String
    let title: String
    let subtitle: String

    @Environment(\.colorScheme) var colorScheme

    var body: some View {
        HStack(spacing: Spacing.md) {
            Image(systemName: icon)
                .font(.system(size: 20))
                .foregroundColor(Theme.accent)
                .frame(width: 32)

            VStack(alignment: .leading, spacing: 2) {
                Text(title)
                    .font(Typography.headline)
                    .foregroundColor(Color.adaptiveText(colorScheme))

                Text(subtitle)
                    .font(Typography.caption)
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

@MainActor
final class CommunityDetailViewModel: ObservableObject {
    @Published var stats: CommunityStats?
    @Published var isLoading = false
    @Published var error: String?

    func loadStats(communityId: String) async {
        isLoading = true
        error = nil

        do {
            stats = try await APIClient.shared.getCommunityStats(id: communityId)
        } catch let apiError as APIError {
            error = apiError.localizedDescription
        } catch {
            self.error = "Failed to load community stats"
        }

        isLoading = false
    }
}

#Preview {
    NavigationStack {
        CommunityDetailView(community: Community(
            id: "1",
            name: "Test Community",
            description: "A test community for development",
            iconUrl: nil,
            memberCount: 1234,
            platform: "twitch",
            createdAt: nil
        ))
    }
}
