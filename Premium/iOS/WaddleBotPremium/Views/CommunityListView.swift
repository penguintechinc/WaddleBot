import SwiftUI
import Combine

struct CommunityListView: View {
    @EnvironmentObject var authManager: AuthenticationManager
    @StateObject private var viewModel = CommunityListViewModel()
    @State private var showingAddCommunity = false
    @State private var searchText = ""
    
    var filteredCommunities: [Community] {
        if searchText.isEmpty {
            return viewModel.communities
        } else {
            return viewModel.communities.filter { community in
                community.name.localizedCaseInsensitiveContains(searchText) ||
                community.description.localizedCaseInsensitiveContains(searchText) ||
                community.platform.localizedCaseInsensitiveContains(searchText)
            }
        }
    }
    
    var body: some View {
        NavigationView {
            VStack {
                if viewModel.isLoading && viewModel.communities.isEmpty {
                    LoadingView()
                } else if viewModel.communities.isEmpty {
                    EmptyStateView()
                } else {
                    communityList
                }
            }
            .navigationTitle("Communities")
            .navigationBarTitleDisplayMode(.large)
            .searchable(text: $searchText, prompt: "Search communities...")
            .toolbar {
                ToolbarItem(placement: .navigationBarTrailing) {
                    Button(action: {
                        showingAddCommunity = true
                    }) {
                        Image(systemName: "plus")
                            .foregroundColor(AppColors.secondary)
                    }
                }
            }
            .refreshable {
                await viewModel.loadCommunities()
            }
            .sheet(isPresented: $showingAddCommunity) {
                AddCommunityView()
            }
            .onAppear {
                Task {
                    await viewModel.loadCommunities()
                }
            }
        }
    }
    
    private var communityList: some View {
        List(filteredCommunities) { community in
            NavigationLink(destination: CommunityDetailView(community: community)) {
                CommunityRow(community: community)
            }
            .listRowBackground(AppColors.cardBackground)
            .listRowSeparator(.hidden)
            .listRowInsets(EdgeInsets(top: 4, leading: 16, bottom: 4, trailing: 16))
        }
        .listStyle(PlainListStyle())
        .background(AppColors.background)
    }
}

struct CommunityRow: View {
    let community: Community
    
    var body: some View {
        HStack(spacing: AppSpacing.medium) {
            // Platform icon
            Circle()
                .fill(AppColors.secondary)
                .frame(width: 50, height: 50)
                .overlay(
                    Text(Platform(rawValue: community.platform)?.icon ?? "🏘️")
                        .font(.title2)
                )
            
            // Community info
            VStack(alignment: .leading, spacing: AppSpacing.tiny) {
                Text(community.name)
                    .font(AppFonts.body)
                    .fontWeight(.semibold)
                    .foregroundColor(AppColors.textPrimary)
                    .lineLimit(1)
                
                Text(community.description)
                    .font(AppFonts.caption)
                    .foregroundColor(AppColors.textSecondary)
                    .lineLimit(2)
                
                HStack(spacing: AppSpacing.small) {
                    // Platform badge
                    Text(Platform(rawValue: community.platform)?.displayName ?? community.platform)
                        .font(AppFonts.caption2)
                        .fontWeight(.medium)
                        .foregroundColor(AppColors.textLight)
                        .padding(.horizontal, AppSpacing.small)
                        .padding(.vertical, AppSpacing.tiny)
                        .background(AppColors.info)
                        .cornerRadius(4)
                    
                    // Member count
                    HStack(spacing: 2) {
                        Image(systemName: "person.2.fill")
                            .font(.caption2)
                        Text("\(community.memberCount)")
                            .font(AppFonts.caption2)
                    }
                    .foregroundColor(AppColors.textMuted)
                    
                    Spacer()
                    
                    // Status indicator
                    Circle()
                        .fill(community.isActive ? AppColors.success : AppColors.error)
                        .frame(width: 8, height: 8)
                }
            }
            
            Spacer()
            
            // Chevron
            Image(systemName: "chevron.right")
                .font(.caption)
                .foregroundColor(AppColors.textSecondary)
        }
        .padding()
        .background(AppColors.cardBackground)
        .cornerRadius(AppSizes.cardCornerRadius)
        .applyShadow(AppShadows.light)
    }
}

struct EmptyStateView: View {
    var body: some View {
        VStack(spacing: AppSpacing.large) {
            Image(systemName: "house.fill")
                .font(.system(size: 60))
                .foregroundColor(AppColors.textMuted)
            
            VStack(spacing: AppSpacing.small) {
                Text("No Communities Yet")
                    .font(AppFonts.title)
                    .fontWeight(.bold)
                    .foregroundColor(AppColors.textPrimary)
                
                Text("Create your first community to get started with WaddleBot Premium")
                    .font(AppFonts.body)
                    .foregroundColor(AppColors.textSecondary)
                    .multilineTextAlignment(.center)
                    .padding(.horizontal, AppSpacing.large)
            }
            
            Button("Create Community") {
                // Handle create community action
            }
            .buttonStyle(WaddleBotPrimaryButtonStyle())
            .padding(.horizontal, AppSpacing.xlarge)
        }
        .frame(maxWidth: .infinity, maxHeight: .infinity)
        .background(AppColors.background)
    }
}

struct AddCommunityView: View {
    @Environment(\.presentationMode) var presentationMode
    @State private var name = ""
    @State private var description = ""
    @State private var selectedPlatform = Platform.discord
    @State private var serverId = ""
    @State private var channelId = ""
    @State private var isPublic = true
    
    var body: some View {
        NavigationView {
            Form {
                Section(header: Text("Basic Information")) {
                    TextField("Community Name", text: $name)
                    TextField("Description", text: $description, axis: .vertical)
                        .lineLimit(3...6)
                    
                    Toggle("Public Community", isOn: $isPublic)
                }
                
                Section(header: Text("Platform Settings")) {
                    Picker("Platform", selection: $selectedPlatform) {
                        ForEach(Platform.allCases, id: \.self) { platform in
                            HStack {
                                Text(platform.icon)
                                Text(platform.displayName)
                            }
                            .tag(platform)
                        }
                    }
                    .pickerStyle(SegmentedPickerStyle())
                    
                    TextField("Server ID", text: $serverId)
                    TextField("Channel ID (Optional)", text: $channelId)
                }
                
                Section(footer: Text("You can configure additional settings after creating the community.")) {
                    EmptyView()
                }
            }
            .navigationTitle("New Community")
            .navigationBarTitleDisplayMode(.inline)
            .navigationBarItems(
                leading: Button("Cancel") {
                    presentationMode.wrappedValue.dismiss()
                },
                trailing: Button("Create") {
                    // Handle create action
                    presentationMode.wrappedValue.dismiss()
                }
                .disabled(name.isEmpty || serverId.isEmpty)
            )
        }
    }
}

// MARK: - View Model
class CommunityListViewModel: ObservableObject {
    @Published var communities: [Community] = []
    @Published var isLoading = false
    @Published var errorMessage: String? = nil
    
    private var cancellables = Set<AnyCancellable>()
    private let apiClient = APIClient.shared
    
    @MainActor
    func loadCommunities() async {
        isLoading = true
        errorMessage = nil
        
        apiClient.getUserCommunities()
            .receive(on: DispatchQueue.main)
            .sink(
                receiveCompletion: { [weak self] completion in
                    self?.isLoading = false
                    if case .failure(let error) = completion {
                        self?.errorMessage = "Failed to load communities"
                        print("Error loading communities: \(error)")
                    }
                },
                receiveValue: { [weak self] communities in
                    self?.communities = communities
                }
            )
            .store(in: &cancellables)
    }
}

// MARK: - Community Detail View
struct CommunityDetailView: View {
    let community: Community
    @State private var selectedTab = 0
    
    var body: some View {
        TabView(selection: $selectedTab) {
            MemberListView(communityId: community.id)
                .tabItem {
                    Image(systemName: "person.3.fill")
                    Text("Members")
                }
                .tag(0)
            
            CurrencyManagementView(communityId: community.id)
                .tabItem {
                    Image(systemName: "dollarsign.circle.fill")
                    Text("Currency")
                }
                .tag(1)
            
            RaffleListView(communityId: community.id)
                .tabItem {
                    Image(systemName: "gift.fill")
                    Text("Raffles")
                }
                .tag(2)
            
            CommunitySettingsView(community: community)
                .tabItem {
                    Image(systemName: "gear")
                    Text("Settings")
                }
                .tag(3)
        }
        .navigationTitle(community.name)
        .navigationBarTitleDisplayMode(.inline)
    }
}

struct RaffleListView: View {
    let communityId: String
    
    var body: some View {
        NavigationView {
            VStack {
                Text("Raffles & Giveaways")
                    .font(AppFonts.largeTitle)
                    .padding()
                
                Text("Raffle management coming soon...")
                    .font(AppFonts.body)
                    .foregroundColor(AppColors.textSecondary)
                
                Spacer()
            }
            .navigationBarTitleDisplayMode(.inline)
            .background(AppColors.background)
        }
    }
}

struct CommunitySettingsView: View {
    let community: Community
    
    var body: some View {
        NavigationView {
            VStack {
                Text("Community Settings")
                    .font(AppFonts.largeTitle)
                    .padding()
                
                Text("Settings panel coming soon...")
                    .font(AppFonts.body)
                    .foregroundColor(AppColors.textSecondary)
                
                Spacer()
            }
            .navigationBarTitleDisplayMode(.inline)
            .background(AppColors.background)
        }
    }
}

#Preview {
    CommunityListView()
        .environmentObject(AuthenticationManager())
}