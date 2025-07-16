import SwiftUI
import Combine

struct MemberListView: View {
    let communityId: String
    @EnvironmentObject var authManager: AuthenticationManager
    @StateObject private var viewModel = MemberListViewModel()
    @State private var searchText = ""
    @State private var selectedMember: Member?
    @State private var showingMemberActions = false
    @State private var showingAddMember = false
    
    var filteredMembers: [Member] {
        if searchText.isEmpty {
            return viewModel.members
        } else {
            return viewModel.members.filter { member in
                member.displayName.localizedCaseInsensitiveContains(searchText) ||
                member.username.localizedCaseInsensitiveContains(searchText) ||
                member.role.localizedCaseInsensitiveContains(searchText)
            }
        }
    }
    
    var body: some View {
        NavigationView {
            VStack {
                if viewModel.isLoading && viewModel.members.isEmpty {
                    LoadingView()
                } else if viewModel.members.isEmpty {
                    EmptyMembersView()
                } else {
                    memberList
                }
            }
            .navigationTitle("Members")
            .navigationBarTitleDisplayMode(.large)
            .searchable(text: $searchText, prompt: "Search members...")
            .toolbar {
                ToolbarItem(placement: .navigationBarTrailing) {
                    Button(action: {
                        showingAddMember = true
                    }) {
                        Image(systemName: "person.badge.plus")
                            .foregroundColor(AppColors.secondary)
                    }
                }
            }
            .refreshable {
                await viewModel.loadMembers(communityId: communityId)
            }
            .sheet(isPresented: $showingAddMember) {
                AddMemberView(communityId: communityId)
            }
            .sheet(item: $selectedMember) { member in
                MemberActionsSheet(member: member, communityId: communityId)
            }
            .onAppear {
                Task {
                    await viewModel.loadMembers(communityId: communityId)
                }
            }
        }
    }
    
    private var memberList: some View {
        List(filteredMembers) { member in
            MemberRow(member: member)
                .onTapGesture {
                    selectedMember = member
                    showingMemberActions = true
                }
                .listRowBackground(AppColors.cardBackground)
                .listRowSeparator(.hidden)
                .listRowInsets(EdgeInsets(top: 4, leading: 16, bottom: 4, trailing: 16))
        }
        .listStyle(PlainListStyle())
        .background(AppColors.background)
    }
}

struct MemberRow: View {
    let member: Member
    
    var body: some View {
        HStack(spacing: AppSpacing.medium) {
            // Avatar
            Circle()
                .fill(AppColors.secondary)
                .frame(width: 50, height: 50)
                .overlay(
                    Text(member.displayName.prefix(1).uppercased())
                        .font(AppFonts.title2)
                        .fontWeight(.bold)
                        .foregroundColor(AppColors.textPrimary)
                )
            
            // Member info
            VStack(alignment: .leading, spacing: AppSpacing.tiny) {
                Text(member.displayName)
                    .font(AppFonts.body)
                    .fontWeight(.semibold)
                    .foregroundColor(AppColors.textPrimary)
                    .lineLimit(1)
                
                Text("@\(member.username)")
                    .font(AppFonts.caption)
                    .foregroundColor(AppColors.textSecondary)
                
                Text("Joined \(member.joinDate.formatted())")
                    .font(AppFonts.caption2)
                    .foregroundColor(AppColors.textMuted)
            }
            
            Spacer()
            
            // Member metadata
            VStack(alignment: .trailing, spacing: AppSpacing.tiny) {
                // Role badge
                Text(member.role.capitalized)
                    .font(AppFonts.caption2)
                    .fontWeight(.medium)
                    .foregroundColor(AppColors.textLight)
                    .padding(.horizontal, AppSpacing.small)
                    .padding(.vertical, AppSpacing.tiny)
                    .background(Color(hex: UserRole(rawValue: member.role)?.color ?? "#757575"))
                    .cornerRadius(4)
                
                // Status badge
                Text(member.status.capitalized)
                    .font(AppFonts.caption2)
                    .fontWeight(.medium)
                    .foregroundColor(AppColors.textLight)
                    .padding(.horizontal, AppSpacing.small)
                    .padding(.vertical, AppSpacing.tiny)
                    .background(Color(hex: MemberStatus(rawValue: member.status)?.color ?? "#757575"))
                    .cornerRadius(4)
                
                // Reputation score
                HStack(spacing: 2) {
                    Text("\(member.reputationScore)")
                        .font(AppFonts.caption)
                        .fontWeight(.medium)
                        .foregroundColor(Color.reputationColor(for: member.reputationScore))
                    
                    Circle()
                        .fill(Color.reputationColor(for: member.reputationScore))
                        .frame(width: 6, height: 6)
                }
            }
        }
        .padding()
        .background(AppColors.cardBackground)
        .cornerRadius(AppSizes.cardCornerRadius)
        .applyShadow(AppShadows.light)
    }
}

struct EmptyMembersView: View {
    var body: some View {
        VStack(spacing: AppSpacing.large) {
            Image(systemName: "person.3.fill")
                .font(.system(size: 60))
                .foregroundColor(AppColors.textMuted)
            
            VStack(spacing: AppSpacing.small) {
                Text("No Members Yet")
                    .font(AppFonts.title)
                    .fontWeight(.bold)
                    .foregroundColor(AppColors.textPrimary)
                
                Text("Invite members to your community to get started")
                    .font(AppFonts.body)
                    .foregroundColor(AppColors.textSecondary)
                    .multilineTextAlignment(.center)
                    .padding(.horizontal, AppSpacing.large)
            }
            
            Button("Invite Members") {
                // Handle invite action
            }
            .buttonStyle(WaddleBotPrimaryButtonStyle())
            .padding(.horizontal, AppSpacing.xlarge)
        }
        .frame(maxWidth: .infinity, maxHeight: .infinity)
        .background(AppColors.background)
    }
}

struct AddMemberView: View {
    let communityId: String
    @Environment(\.presentationMode) var presentationMode
    @State private var username = ""
    @State private var email = ""
    @State private var selectedRole = UserRole.member
    
    var body: some View {
        NavigationView {
            Form {
                Section(header: Text("Member Information")) {
                    TextField("Username", text: $username)
                    TextField("Email", text: $email)
                        .keyboardType(.emailAddress)
                        .autocapitalization(.none)
                }
                
                Section(header: Text("Role")) {
                    Picker("Role", selection: $selectedRole) {
                        ForEach(UserRole.allCases, id: \.self) { role in
                            Text(role.displayName).tag(role)
                        }
                    }
                    .pickerStyle(SegmentedPickerStyle())
                }
                
                Section(footer: Text("The member will receive an invitation email to join the community.")) {
                    EmptyView()
                }
            }
            .navigationTitle("Add Member")
            .navigationBarTitleDisplayMode(.inline)
            .navigationBarItems(
                leading: Button("Cancel") {
                    presentationMode.wrappedValue.dismiss()
                },
                trailing: Button("Send Invite") {
                    // Handle add member action
                    presentationMode.wrappedValue.dismiss()
                }
                .disabled(username.isEmpty || email.isEmpty)
            )
        }
    }
}

struct MemberActionsSheet: View {
    let member: Member
    let communityId: String
    @Environment(\.presentationMode) var presentationMode
    @EnvironmentObject var authManager: AuthenticationManager
    @State private var showingReputationEditor = false
    @State private var showingRemoveConfirmation = false
    
    var userRole: String {
        authManager.getUserRole(in: communityId) ?? "member"
    }
    
    var body: some View {
        NavigationView {
            VStack(spacing: 0) {
                // Member header
                VStack(spacing: AppSpacing.medium) {
                    Circle()
                        .fill(AppColors.secondary)
                        .frame(width: 80, height: 80)
                        .overlay(
                            Text(member.displayName.prefix(1).uppercased())
                                .font(AppFonts.largeTitle)
                                .fontWeight(.bold)
                                .foregroundColor(AppColors.textPrimary)
                        )
                    
                    VStack(spacing: AppSpacing.small) {
                        Text(member.displayName)
                            .font(AppFonts.title)
                            .fontWeight(.bold)
                            .foregroundColor(AppColors.textPrimary)
                        
                        Text("@\(member.username)")
                            .font(AppFonts.body)
                            .foregroundColor(AppColors.textSecondary)
                        
                        HStack(spacing: AppSpacing.medium) {
                            Text(member.role.capitalized)
                                .font(AppFonts.caption)
                                .fontWeight(.medium)
                                .foregroundColor(AppColors.textLight)
                                .padding(.horizontal, AppSpacing.small)
                                .padding(.vertical, AppSpacing.tiny)
                                .background(Color(hex: UserRole(rawValue: member.role)?.color ?? "#757575"))
                                .cornerRadius(4)
                            
                            Text("\(member.reputationScore) pts")
                                .font(AppFonts.caption)
                                .fontWeight(.medium)
                                .foregroundColor(Color.reputationColor(for: member.reputationScore))
                        }
                    }
                }
                .padding(.top, AppSpacing.large)
                .padding(.bottom, AppSpacing.large)
                
                // Action buttons
                VStack(spacing: 0) {
                    if member.role != "owner" {
                        ActionButton(
                            icon: "person.crop.circle.badge.plus",
                            title: "Change Role",
                            action: { /* Handle role change */ }
                        )
                        
                        if PermissionUtils.canEditReputation(userRole: userRole) {
                            ActionButton(
                                icon: "chart.bar.fill",
                                title: "Edit Reputation",
                                action: { showingReputationEditor = true }
                            )
                        }
                        
                        if member.status == "banned" {
                            if PermissionUtils.canUnbanMembers(userRole: userRole) {
                                ActionButton(
                                    icon: "checkmark.circle.fill",
                                    title: "Unban Member",
                                    color: AppColors.success,
                                    action: { /* Handle unban */ }
                                )
                            }
                        } else {
                            if PermissionUtils.canBanMembers(userRole: userRole) {
                                ActionButton(
                                    icon: "xmark.circle.fill",
                                    title: "Ban Member",
                                    color: AppColors.error,
                                    action: { /* Handle ban */ }
                                )
                            }
                        }
                        
                        ActionButton(
                            icon: "person.badge.minus",
                            title: "Remove Member",
                            color: AppColors.error,
                            action: { showingRemoveConfirmation = true }
                        )
                    }
                }
                .background(AppColors.cardBackground)
                .cornerRadius(AppSizes.cardCornerRadius)
                
                Spacer()
            }
            .padding(.horizontal, AppSpacing.medium)
            .background(AppColors.background)
            .navigationBarTitleDisplayMode(.inline)
            .navigationBarItems(trailing: Button("Done") {
                presentationMode.wrappedValue.dismiss()
            })
        }
        .sheet(isPresented: $showingReputationEditor) {
            ReputationEditorView(member: member, communityId: communityId)
        }
        .alert("Remove Member", isPresented: $showingRemoveConfirmation) {
            Button("Cancel", role: .cancel) { }
            Button("Remove", role: .destructive) {
                // Handle remove member
            }
        } message: {
            Text("Are you sure you want to remove \(member.displayName) from the community?")
        }
    }
}

struct ActionButton: View {
    let icon: String
    let title: String
    let color: Color
    let action: () -> Void
    
    init(icon: String, title: String, color: Color = AppColors.textPrimary, action: @escaping () -> Void) {
        self.icon = icon
        self.title = title
        self.color = color
        self.action = action
    }
    
    var body: some View {
        Button(action: action) {
            HStack(spacing: AppSpacing.medium) {
                Image(systemName: icon)
                    .font(.title3)
                    .foregroundColor(color)
                    .frame(width: 24)
                
                Text(title)
                    .font(AppFonts.body)
                    .foregroundColor(color)
                
                Spacer()
            }
            .padding()
            .background(AppColors.cardBackground)
        }
        .buttonStyle(PlainButtonStyle())
    }
}

struct ReputationEditorView: View {
    let member: Member
    let communityId: String
    @Environment(\.presentationMode) var presentationMode
    @State private var reputationScore = ""
    @State private var reason = ""
    
    var body: some View {
        NavigationView {
            Form {
                Section(header: Text("Current Reputation")) {
                    HStack {
                        Text("Current Score:")
                        Spacer()
                        Text("\(member.reputationScore)")
                            .fontWeight(.bold)
                            .foregroundColor(Color.reputationColor(for: member.reputationScore))
                    }
                    
                    HStack {
                        Text("Status:")
                        Spacer()
                        Text(Color.reputationLabel(for: member.reputationScore))
                            .fontWeight(.medium)
                            .foregroundColor(Color.reputationColor(for: member.reputationScore))
                    }
                }
                
                Section(header: Text("New Reputation")) {
                    TextField("New Score (\(ReputationConfig.minScore)-\(ReputationConfig.maxScore))", text: $reputationScore)
                        .keyboardType(.numberPad)
                    
                    TextField("Reason for change", text: $reason, axis: .vertical)
                        .lineLimit(3...6)
                }
                
                Section(footer: Text("Reputation scores range from \(ReputationConfig.minScore) to \(ReputationConfig.maxScore). Users with scores below \(ReputationConfig.minAutoBanThreshold) may be automatically banned.")) {
                    EmptyView()
                }
            }
            .navigationTitle("Edit Reputation")
            .navigationBarTitleDisplayMode(.inline)
            .navigationBarItems(
                leading: Button("Cancel") {
                    presentationMode.wrappedValue.dismiss()
                },
                trailing: Button("Save") {
                    // Handle save reputation
                    presentationMode.wrappedValue.dismiss()
                }
                .disabled(reputationScore.isEmpty || reason.isEmpty)
            )
        }
    }
}

// MARK: - View Model
class MemberListViewModel: ObservableObject {
    @Published var members: [Member] = []
    @Published var isLoading = false
    @Published var errorMessage: String? = nil
    
    private var cancellables = Set<AnyCancellable>()
    private let apiClient = APIClient.shared
    
    @MainActor
    func loadMembers(communityId: String) async {
        isLoading = true
        errorMessage = nil
        
        apiClient.getCommunityMembers(communityId: communityId)
            .receive(on: DispatchQueue.main)
            .sink(
                receiveCompletion: { [weak self] completion in
                    self?.isLoading = false
                    if case .failure(let error) = completion {
                        self?.errorMessage = "Failed to load members"
                        print("Error loading members: \(error)")
                    }
                },
                receiveValue: { [weak self] response in
                    self?.members = response.data
                }
            )
            .store(in: &cancellables)
    }
}

// MARK: - Color Extension
extension Color {
    init(hex: String) {
        let hex = hex.trimmingCharacters(in: CharacterSet.alphanumerics.inverted)
        var int: UInt64 = 0
        Scanner(string: hex).scanHexInt64(&int)
        let a, r, g, b: UInt64
        switch hex.count {
        case 3: // RGB (12-bit)
            (a, r, g, b) = (255, (int >> 8) * 17, (int >> 4 & 0xF) * 17, (int & 0xF) * 17)
        case 6: // RGB (24-bit)
            (a, r, g, b) = (255, int >> 16, int >> 8 & 0xFF, int & 0xFF)
        case 8: // ARGB (32-bit)
            (a, r, g, b) = (int >> 24, int >> 16 & 0xFF, int >> 8 & 0xFF, int & 0xFF)
        default:
            (a, r, g, b) = (1, 1, 1, 0)
        }
        
        self.init(
            .sRGB,
            red: Double(r) / 255,
            green: Double(g) / 255,
            blue:  Double(b) / 255,
            opacity: Double(a) / 255
        )
    }
}

#Preview {
    MemberListView(communityId: "test-community")
        .environmentObject(AuthenticationManager())
}