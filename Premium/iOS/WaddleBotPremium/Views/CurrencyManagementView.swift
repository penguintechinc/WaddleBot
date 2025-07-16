import SwiftUI
import Combine

struct CurrencyManagementView: View {
    let communityId: String
    @EnvironmentObject var authManager: AuthenticationManager
    @StateObject private var viewModel = CurrencyManagementViewModel()
    @State private var showingAdjustmentModal = false
    @State private var selectedMember: Member?
    
    var userRole: String {
        authManager.getUserRole(in: communityId) ?? "member"
    }
    
    var body: some View {
        NavigationView {
            ScrollView {
                VStack(spacing: AppSpacing.large) {
                    if !PermissionUtils.canManageCurrency(userRole: userRole) {
                        PermissionDeniedView()
                    } else if viewModel.isLoading {
                        LoadingView()
                    } else {
                        currencyContent
                    }
                }
                .padding(.horizontal, AppSpacing.medium)
            }
            .background(AppColors.background)
            .navigationTitle("Currency Management")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .navigationBarTrailing) {
                    Button("Settings") {
                        // Navigate to currency settings
                    }
                    .foregroundColor(AppColors.secondary)
                }
            }
            .refreshable {
                await viewModel.loadCurrencyData(communityId: communityId)
            }
            .onAppear {
                Task {
                    await viewModel.loadCurrencyData(communityId: communityId)
                }
            }
        }
        .sheet(item: $selectedMember) { member in
            CurrencyAdjustmentSheet(member: member, communityId: communityId)
        }
    }
    
    private var currencyContent: some View {
        VStack(spacing: AppSpacing.large) {
            // Statistics Cards
            statisticsSection
            
            // Top Members Leaderboard
            leaderboardSection
            
            // Recent Transactions
            transactionsSection
        }
    }
    
    private var statisticsSection: some View {
        VStack(spacing: AppSpacing.medium) {
            HStack {
                Text("Statistics")
                    .font(AppFonts.headline)
                    .fontWeight(.bold)
                    .foregroundColor(AppColors.textPrimary)
                Spacer()
            }
            
            LazyVGrid(columns: [
                GridItem(.flexible()),
                GridItem(.flexible())
            ], spacing: AppSpacing.medium) {
                StatCard(
                    title: "Total Currency",
                    value: viewModel.statistics.totalCurrency.formatCurrencyShort(),
                    subtitle: "In circulation",
                    color: AppColors.primary
                )
                
                StatCard(
                    title: "Active Members",
                    value: "\(viewModel.statistics.activeMembers)",
                    subtitle: "With currency",
                    color: AppColors.success
                )
                
                StatCard(
                    title: "Transactions",
                    value: "\(viewModel.statistics.totalTransactions)",
                    subtitle: "This month",
                    color: AppColors.info
                )
                
                StatCard(
                    title: "Average Balance",
                    value: viewModel.statistics.averageBalance.formatCurrencyShort(),
                    subtitle: "Per member",
                    color: AppColors.warning
                )
            }
        }
    }
    
    private var leaderboardSection: some View {
        VStack(spacing: AppSpacing.medium) {
            HStack {
                Text("Top Members")
                    .font(AppFonts.headline)
                    .fontWeight(.bold)
                    .foregroundColor(AppColors.textPrimary)
                Spacer()
            }
            
            VStack(spacing: 0) {
                ForEach(Array(viewModel.leaderboard.enumerated()), id: \.element.id) { index, member in
                    LeaderboardRow(member: member, rank: index + 1)
                        .onTapGesture {
                            selectedMember = member
                        }
                    
                    if index < viewModel.leaderboard.count - 1 {
                        Divider()
                            .background(AppColors.border)
                    }
                }
            }
            .background(AppColors.cardBackground)
            .cornerRadius(AppSizes.cardCornerRadius)
            .applyShadow(AppShadows.light)
        }
    }
    
    private var transactionsSection: some View {
        VStack(spacing: AppSpacing.medium) {
            HStack {
                Text("Recent Transactions")
                    .font(AppFonts.headline)
                    .fontWeight(.bold)
                    .foregroundColor(AppColors.textPrimary)
                Spacer()
            }
            
            VStack(spacing: 0) {
                ForEach(viewModel.transactions) { transaction in
                    TransactionRow(transaction: transaction)
                    
                    if transaction.id != viewModel.transactions.last?.id {
                        Divider()
                            .background(AppColors.border)
                    }
                }
            }
            .background(AppColors.cardBackground)
            .cornerRadius(AppSizes.cardCornerRadius)
            .applyShadow(AppShadows.light)
        }
    }
}

struct StatCard: View {
    let title: String
    let value: String
    let subtitle: String
    let color: Color
    
    var body: some View {
        VStack(alignment: .leading, spacing: AppSpacing.small) {
            Text(title)
                .font(AppFonts.caption)
                .foregroundColor(AppColors.textSecondary)
            
            Text(value)
                .font(AppFonts.title)
                .fontWeight(.bold)
                .foregroundColor(AppColors.textPrimary)
            
            Text(subtitle)
                .font(AppFonts.caption2)
                .foregroundColor(AppColors.textMuted)
        }
        .frame(maxWidth: .infinity, alignment: .leading)
        .padding()
        .background(AppColors.cardBackground)
        .cornerRadius(AppSizes.cardCornerRadius)
        .overlay(
            RoundedRectangle(cornerRadius: AppSizes.cardCornerRadius)
                .stroke(color, lineWidth: 2)
                .frame(width: 4)
                .offset(x: -AppSizes.cardCornerRadius + 2),
            alignment: .leading
        )
        .applyShadow(AppShadows.light)
    }
}

struct LeaderboardRow: View {
    let member: Member
    let rank: Int
    
    var body: some View {
        HStack(spacing: AppSpacing.medium) {
            // Rank badge
            Circle()
                .fill(AppColors.secondary)
                .frame(width: 30, height: 30)
                .overlay(
                    Text("#\(rank)")
                        .font(AppFonts.caption)
                        .fontWeight(.bold)
                        .foregroundColor(AppColors.textPrimary)
                )
            
            // Member info
            VStack(alignment: .leading, spacing: AppSpacing.tiny) {
                Text(member.displayName)
                    .font(AppFonts.body)
                    .fontWeight(.semibold)
                    .foregroundColor(AppColors.textPrimary)
                
                Text("@\(member.username)")
                    .font(AppFonts.caption)
                    .foregroundColor(AppColors.textSecondary)
            }
            
            Spacer()
            
            // Balance
            VStack(alignment: .trailing, spacing: AppSpacing.tiny) {
                Text(member.currencyBalance.formatCurrencyShort())
                    .font(AppFonts.body)
                    .fontWeight(.bold)
                    .foregroundColor(AppColors.success)
                
                Text(viewModel.currencySettings.name)
                    .font(AppFonts.caption2)
                    .foregroundColor(AppColors.textMuted)
            }
        }
        .padding()
    }
}

struct TransactionRow: View {
    let transaction: CurrencyTransaction
    
    var body: some View {
        HStack(spacing: AppSpacing.medium) {
            // Transaction icon
            Circle()
                .fill(AppColors.inputBackground)
                .frame(width: 30, height: 30)
                .overlay(
                    Text(getTransactionIcon(transaction.type))
                        .font(AppFonts.body)
                )
            
            // Transaction info
            VStack(alignment: .leading, spacing: AppSpacing.tiny) {
                Text(transaction.memberName)
                    .font(AppFonts.body)
                    .fontWeight(.semibold)
                    .foregroundColor(AppColors.textPrimary)
                
                Text(transaction.reason)
                    .font(AppFonts.caption)
                    .foregroundColor(AppColors.textSecondary)
                
                Text(transaction.timestamp.formatted())
                    .font(AppFonts.caption2)
                    .foregroundColor(AppColors.textMuted)
            }
            
            Spacer()
            
            // Amount
            Text("\(transaction.amount > 0 ? "+" : "")\(transaction.amount)")
                .font(AppFonts.body)
                .fontWeight(.bold)
                .foregroundColor(transaction.amount > 0 ? AppColors.success : AppColors.error)
        }
        .padding()
    }
    
    private func getTransactionIcon(_ type: String) -> String {
        switch type {
        case "earned": return "💰"
        case "spent": return "💸"
        case "bonus": return "🎁"
        case "penalty": return "⚠️"
        case "refund": return "↩️"
        case "transfer": return "🔄"
        case "manual": return "⚙️"
        default: return "📝"
        }
    }
}

struct CurrencyAdjustmentSheet: View {
    let member: Member
    let communityId: String
    @Environment(\.presentationMode) var presentationMode
    @State private var adjustmentType = "bonus"
    @State private var amount = ""
    @State private var reason = ""
    
    var body: some View {
        NavigationView {
            Form {
                Section(header: Text("Member")) {
                    HStack {
                        Circle()
                            .fill(AppColors.secondary)
                            .frame(width: 40, height: 40)
                            .overlay(
                                Text(member.displayName.prefix(1).uppercased())
                                    .font(AppFonts.body)
                                    .fontWeight(.bold)
                                    .foregroundColor(AppColors.textPrimary)
                            )
                        
                        VStack(alignment: .leading) {
                            Text(member.displayName)
                                .font(AppFonts.body)
                                .fontWeight(.semibold)
                            
                            Text("Current Balance: \(member.currencyBalance.formatCurrency())")
                                .font(AppFonts.caption)
                                .foregroundColor(AppColors.textSecondary)
                        }
                        
                        Spacer()
                    }
                }
                
                Section(header: Text("Adjustment Type")) {
                    Picker("Type", selection: $adjustmentType) {
                        Text("Bonus (+)").tag("bonus")
                        Text("Penalty (-)").tag("penalty")
                    }
                    .pickerStyle(SegmentedPickerStyle())
                }
                
                Section(header: Text("Amount")) {
                    TextField("Enter amount", text: $amount)
                        .keyboardType(.numberPad)
                }
                
                Section(header: Text("Reason")) {
                    TextField("Enter reason for adjustment", text: $reason, axis: .vertical)
                        .lineLimit(3...6)
                }
            }
            .navigationTitle("Adjust Currency")
            .navigationBarTitleDisplayMode(.inline)
            .navigationBarItems(
                leading: Button("Cancel") {
                    presentationMode.wrappedValue.dismiss()
                },
                trailing: Button(adjustmentType == "bonus" ? "Add Bonus" : "Apply Penalty") {
                    // Handle currency adjustment
                    presentationMode.wrappedValue.dismiss()
                }
                .disabled(amount.isEmpty || reason.isEmpty)
            )
        }
    }
}

struct PermissionDeniedView: View {
    var body: some View {
        VStack(spacing: AppSpacing.large) {
            Image(systemName: "lock.fill")
                .font(.system(size: 60))
                .foregroundColor(AppColors.error)
            
            VStack(spacing: AppSpacing.small) {
                Text("Permission Denied")
                    .font(AppFonts.title)
                    .fontWeight(.bold)
                    .foregroundColor(AppColors.textPrimary)
                
                Text("You don't have permission to manage currency settings")
                    .font(AppFonts.body)
                    .foregroundColor(AppColors.textSecondary)
                    .multilineTextAlignment(.center)
            }
        }
        .frame(maxWidth: .infinity, maxHeight: .infinity)
        .background(AppColors.background)
    }
}

// MARK: - View Model
class CurrencyManagementViewModel: ObservableObject {
    @Published var statistics = CurrencyStatistics(
        totalCurrency: 0,
        activeMembers: 0,
        totalTransactions: 0,
        averageBalance: 0.0,
        topEarners: []
    )
    @Published var leaderboard: [Member] = []
    @Published var transactions: [CurrencyTransaction] = []
    @Published var currencySettings = CurrencySettings(
        communityId: "",
        enabled: true,
        name: CurrencyConfig.defaultName,
        chatMessageReward: CurrencyConfig.defaultChatReward,
        eventReward: CurrencyConfig.defaultEventReward
    )
    @Published var isLoading = false
    @Published var errorMessage: String? = nil
    
    private var cancellables = Set<AnyCancellable>()
    private let apiClient = APIClient.shared
    
    @MainActor
    func loadCurrencyData(communityId: String) async {
        isLoading = true
        errorMessage = nil
        
        // Load statistics
        apiClient.getCurrencyStatistics(communityId: communityId)
            .receive(on: DispatchQueue.main)
            .sink(
                receiveCompletion: { completion in
                    if case .failure(let error) = completion {
                        print("Error loading currency statistics: \(error)")
                    }
                },
                receiveValue: { [weak self] stats in
                    self?.statistics = stats
                    self?.leaderboard = stats.topEarners
                }
            )
            .store(in: &cancellables)
        
        // Load transactions
        apiClient.getCurrencyTransactions(communityId: communityId)
            .receive(on: DispatchQueue.main)
            .sink(
                receiveCompletion: { [weak self] completion in
                    self?.isLoading = false
                    if case .failure(let error) = completion {
                        self?.errorMessage = "Failed to load currency data"
                        print("Error loading currency transactions: \(error)")
                    }
                },
                receiveValue: { [weak self] response in
                    self?.transactions = response.data
                }
            )
            .store(in: &cancellables)
        
        // Load currency settings
        apiClient.getCurrencySettings(communityId: communityId)
            .receive(on: DispatchQueue.main)
            .sink(
                receiveCompletion: { completion in
                    if case .failure(let error) = completion {
                        print("Error loading currency settings: \(error)")
                    }
                },
                receiveValue: { [weak self] settings in
                    self?.currencySettings = settings
                }
            )
            .store(in: &cancellables)
    }
}

#Preview {
    CurrencyManagementView(communityId: "test-community")
        .environmentObject(AuthenticationManager())
}