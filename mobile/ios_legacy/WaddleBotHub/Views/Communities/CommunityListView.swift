import SwiftUI

struct CommunityListView: View {
    @Environment(\.colorScheme) var colorScheme
    @StateObject private var viewModel = CommunityListViewModel()

    var body: some View {
        NavigationStack {
            Group {
                if viewModel.isLoading && viewModel.communities.isEmpty {
                    LoadingView(message: "Loading communities...")
                } else if let error = viewModel.error, viewModel.communities.isEmpty {
                    ErrorView(message: error) {
                        Task { await viewModel.loadCommunities() }
                    }
                } else if viewModel.communities.isEmpty {
                    EmptyStateView(
                        icon: "person.3",
                        title: "No Communities",
                        message: "You haven't joined any communities yet. Join a community to get started.",
                        actionTitle: nil,
                        action: nil
                    )
                } else {
                    communityList
                }
            }
            .navigationTitle("Communities")
            .toolbar {
                ToolbarItem(placement: .navigationBarTrailing) {
                    if viewModel.isLoading && !viewModel.communities.isEmpty {
                        ProgressView()
                    }
                }
            }
        }
        .task {
            await viewModel.loadCommunities()
        }
    }

    private var communityList: some View {
        List {
            ForEach(viewModel.communities) { community in
                NavigationLink(destination: CommunityDetailView(community: community)) {
                    CommunityRowView(community: community)
                }
                .listRowBackground(Color.adaptiveCardBackground(colorScheme))
            }
        }
        .listStyle(.insetGrouped)
        .refreshable {
            await viewModel.loadCommunities()
        }
    }
}

struct CommunityRowView: View {
    let community: Community
    @Environment(\.colorScheme) var colorScheme

    var body: some View {
        HStack(spacing: Spacing.md) {
            communityIcon

            VStack(alignment: .leading, spacing: Spacing.xxs) {
                Text(community.name)
                    .font(Typography.headline)
                    .foregroundColor(Color.adaptiveText(colorScheme))

                HStack(spacing: Spacing.xs) {
                    platformBadge

                    Text("\(community.memberCount) members")
                        .font(Typography.caption)
                        .foregroundColor(Color.adaptiveSecondaryText(colorScheme))
                }
            }

            Spacer()

            Image(systemName: "chevron.right")
                .font(.system(size: 14, weight: .semibold))
                .foregroundColor(Color.adaptiveSecondaryText(colorScheme).opacity(0.5))
        }
        .padding(.vertical, Spacing.xs)
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
                    case .failure:
                        placeholderIcon
                    case .empty:
                        ProgressView()
                    @unknown default:
                        placeholderIcon
                    }
                }
            } else {
                placeholderIcon
            }
        }
        .frame(width: 48, height: 48)
        .clipShape(RoundedRectangle(cornerRadius: 10))
    }

    private var placeholderIcon: some View {
        ZStack {
            Theme.platformColor(community.platform).opacity(0.2)

            Text(String(community.name.prefix(1)).uppercased())
                .font(Typography.title2)
                .foregroundColor(Theme.platformColor(community.platform))
        }
    }

    private var platformBadge: some View {
        HStack(spacing: 2) {
            Image(systemName: platformIcon)
                .font(.system(size: 10))

            Text(community.platform.capitalized)
                .font(Typography.caption)
        }
        .foregroundColor(Theme.platformColor(community.platform))
        .padding(.horizontal, 6)
        .padding(.vertical, 2)
        .background(Theme.platformColor(community.platform).opacity(0.15))
        .cornerRadius(4)
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
}

@MainActor
final class CommunityListViewModel: ObservableObject {
    @Published var communities: [Community] = []
    @Published var isLoading = false
    @Published var error: String?

    func loadCommunities() async {
        isLoading = true
        error = nil

        do {
            communities = try await APIClient.shared.getCommunities()
        } catch let apiError as APIError {
            error = apiError.localizedDescription
        } catch {
            self.error = "Failed to load communities"
        }

        isLoading = false
    }
}

#Preview {
    CommunityListView()
        .environmentObject(AuthenticationManager())
}
