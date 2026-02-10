import SwiftUI

struct MemberListView: View {
    let communityId: String
    let communityName: String

    @Environment(\.colorScheme) var colorScheme
    @StateObject private var viewModel = MemberListViewModel()
    @State private var searchText = ""

    var body: some View {
        Group {
            if viewModel.isLoading && viewModel.members.isEmpty {
                LoadingView(message: "Loading members...")
            } else if let error = viewModel.error, viewModel.members.isEmpty {
                ErrorView(message: error) {
                    Task { await viewModel.loadMembers(communityId: communityId) }
                }
            } else if viewModel.members.isEmpty {
                EmptyStateView(
                    icon: "person.3",
                    title: "No Members",
                    message: "This community doesn't have any members yet.",
                    actionTitle: nil,
                    action: nil
                )
            } else {
                memberList
            }
        }
        .navigationTitle("Members")
        .navigationBarTitleDisplayMode(.inline)
        .searchable(text: $searchText, prompt: "Search members")
        .onChange(of: searchText) { _, newValue in
            Task {
                await viewModel.searchMembers(communityId: communityId, query: newValue)
            }
        }
        .toolbar {
            ToolbarItem(placement: .navigationBarTrailing) {
                if viewModel.isLoading && !viewModel.members.isEmpty {
                    ProgressView()
                }
            }
        }
        .task {
            await viewModel.loadMembers(communityId: communityId)
        }
    }

    private var memberList: some View {
        List {
            ForEach(viewModel.members) { member in
                MemberRowView(member: member)
                    .listRowBackground(Color.adaptiveCardBackground(colorScheme))
            }
        }
        .listStyle(.insetGrouped)
        .refreshable {
            await viewModel.loadMembers(communityId: communityId, search: searchText)
        }
    }
}

struct MemberRowView: View {
    let member: Member

    @Environment(\.colorScheme) var colorScheme

    var body: some View {
        HStack(spacing: Spacing.md) {
            memberAvatar

            VStack(alignment: .leading, spacing: Spacing.xxs) {
                Text(member.displayNameOrUsername)
                    .font(Typography.headline)
                    .foregroundColor(Color.adaptiveText(colorScheme))

                HStack(spacing: Spacing.xs) {
                    roleBadge

                    if let lastSeen = member.lastSeen {
                        Text("Last seen \(lastSeen.timeAgoDisplay())")
                            .font(Typography.caption)
                            .foregroundColor(Color.adaptiveSecondaryText(colorScheme))
                    }
                }
            }

            Spacer()
        }
        .padding(.vertical, Spacing.xs)
    }

    private var memberAvatar: some View {
        Group {
            if let avatarUrl = member.avatarUrl, let url = URL(string: avatarUrl) {
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
        .frame(width: 44, height: 44)
        .clipShape(Circle())
    }

    private var placeholderAvatar: some View {
        ZStack {
            Theme.accent.opacity(0.2)

            Text(String(member.displayNameOrUsername.prefix(1)).uppercased())
                .font(Typography.headline)
                .foregroundColor(Theme.accent)
        }
    }

    private var roleBadge: some View {
        Text(member.role.capitalized)
            .font(Typography.caption)
            .foregroundColor(roleColor)
            .padding(.horizontal, 6)
            .padding(.vertical, 2)
            .background(roleColor.opacity(0.15))
            .cornerRadius(4)
    }

    private var roleColor: Color {
        switch member.role.lowercased() {
        case "admin": return Theme.error
        case "moderator": return Theme.warning
        case "vip": return Theme.accentLight
        default: return Color.adaptiveSecondaryText(colorScheme)
        }
    }
}

@MainActor
final class MemberListViewModel: ObservableObject {
    @Published var members: [Member] = []
    @Published var isLoading = false
    @Published var error: String?

    private var searchTask: Task<Void, Never>?

    func loadMembers(communityId: String, search: String? = nil) async {
        isLoading = true
        error = nil

        do {
            members = try await APIClient.shared.getMembers(communityId: communityId, search: search)
        } catch let apiError as APIError {
            error = apiError.localizedDescription
        } catch {
            self.error = "Failed to load members"
        }

        isLoading = false
    }

    func searchMembers(communityId: String, query: String) async {
        searchTask?.cancel()

        searchTask = Task {
            try? await Task.sleep(nanoseconds: 300_000_000)

            guard !Task.isCancelled else { return }

            await loadMembers(communityId: communityId, search: query.isEmpty ? nil : query)
        }
    }
}

extension Date {
    func timeAgoDisplay() -> String {
        let calendar = Calendar.current
        let now = Date()
        let components = calendar.dateComponents([.minute, .hour, .day, .weekOfYear], from: self, to: now)

        if let weeks = components.weekOfYear, weeks > 0 {
            return weeks == 1 ? "1 week ago" : "\(weeks) weeks ago"
        } else if let days = components.day, days > 0 {
            return days == 1 ? "1 day ago" : "\(days) days ago"
        } else if let hours = components.hour, hours > 0 {
            return hours == 1 ? "1 hour ago" : "\(hours) hours ago"
        } else if let minutes = components.minute, minutes > 0 {
            return minutes == 1 ? "1 min ago" : "\(minutes) mins ago"
        } else {
            return "Just now"
        }
    }
}

#Preview {
    NavigationStack {
        MemberListView(communityId: "1", communityName: "Test Community")
    }
}
