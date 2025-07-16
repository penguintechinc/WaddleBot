import SwiftUI

struct LoginView: View {
    @EnvironmentObject var authManager: AuthenticationManager
    @State private var email = ""
    @State private var password = ""
    @State private var showingPassword = false
    @State private var showingPremiumGate = false
    
    var body: some View {
        NavigationView {
            VStack(spacing: AppSpacing.large) {
                // Logo and header
                VStack(spacing: AppSpacing.medium) {
                    Image(systemName: "crown.fill")
                        .font(.system(size: 60))
                        .foregroundColor(AppColors.secondary)
                    
                    Text(AppConfig.appName)
                        .font(AppFonts.largeTitle)
                        .foregroundColor(AppColors.textPrimary)
                        .fontWeight(.bold)
                    
                    Text("Premium Community Management")
                        .font(AppFonts.callout)
                        .foregroundColor(AppColors.textSecondary)
                        .multilineTextAlignment(.center)
                }
                .padding(.top, AppSpacing.xxlarge)
                
                Spacer()
                
                // Premium gate notice
                if AppConfig.premiumRequired {
                    VStack(spacing: AppSpacing.small) {
                        HStack {
                            Image(systemName: "star.fill")
                                .foregroundColor(AppColors.secondary)
                            Text("Premium Only")
                                .font(AppFonts.callout)
                                .fontWeight(.semibold)
                                .foregroundColor(AppColors.textPrimary)
                        }
                        
                        Text("This app is exclusively for WaddleBot Premium subscribers")
                            .font(AppFonts.caption)
                            .foregroundColor(AppColors.textSecondary)
                            .multilineTextAlignment(.center)
                            .padding(.horizontal)
                    }
                    .padding()
                    .background(AppColors.accent.opacity(0.3))
                    .cornerRadius(AppSizes.cardCornerRadius)
                }
                
                // Login form
                VStack(spacing: AppSpacing.medium) {
                    VStack(spacing: AppSpacing.small) {
                        HStack {
                            Text("Email")
                                .font(AppFonts.callout)
                                .foregroundColor(AppColors.textPrimary)
                            Spacer()
                        }
                        
                        TextField("Enter your email", text: $email)
                            .textFieldStyle(WaddleBotTextFieldStyle())
                            .keyboardType(.emailAddress)
                            .autocapitalization(.none)
                            .disableAutocorrection(true)
                    }
                    
                    VStack(spacing: AppSpacing.small) {
                        HStack {
                            Text("Password")
                                .font(AppFonts.callout)
                                .foregroundColor(AppColors.textPrimary)
                            Spacer()
                        }
                        
                        HStack {
                            if showingPassword {
                                TextField("Enter your password", text: $password)
                                    .textFieldStyle(WaddleBotTextFieldStyle())
                            } else {
                                SecureField("Enter your password", text: $password)
                                    .textFieldStyle(WaddleBotTextFieldStyle())
                            }
                            
                            Button(action: {
                                showingPassword.toggle()
                            }) {
                                Image(systemName: showingPassword ? "eye.slash" : "eye")
                                    .foregroundColor(AppColors.textSecondary)
                            }
                            .padding(.trailing, AppSpacing.small)
                        }
                        .overlay(
                            RoundedRectangle(cornerRadius: AppSizes.buttonCornerRadius)
                                .stroke(AppColors.inputBorder, lineWidth: 1)
                        )
                    }
                    
                    if let errorMessage = authManager.errorMessage {
                        Text(errorMessage)
                            .font(AppFonts.caption)
                            .foregroundColor(AppColors.error)
                            .padding(.horizontal)
                    }
                }
                
                // Login button
                Button(action: {
                    Task {
                        await authManager.login(email: email, password: password)
                    }
                }) {
                    if authManager.isLoading {
                        ProgressView()
                            .progressViewStyle(CircularProgressViewStyle(tint: AppColors.textPrimary))
                            .frame(maxWidth: .infinity, minHeight: AppSizes.buttonHeight)
                    } else {
                        Text("Sign In")
                            .font(AppFonts.body)
                            .fontWeight(.semibold)
                            .foregroundColor(AppColors.textPrimary)
                            .frame(maxWidth: .infinity, minHeight: AppSizes.buttonHeight)
                    }
                }
                .disabled(authManager.isLoading || email.isEmpty || password.isEmpty)
                .buttonStyle(WaddleBotPrimaryButtonStyle())
                
                Spacer()
                
                // Footer
                VStack(spacing: AppSpacing.small) {
                    Text("Don't have a premium account?")
                        .font(AppFonts.caption)
                        .foregroundColor(AppColors.textSecondary)
                    
                    Button("Learn More About Premium") {
                        showingPremiumGate = true
                    }
                    .font(AppFonts.caption)
                    .foregroundColor(AppColors.secondary)
                }
                .padding(.bottom, AppSpacing.large)
            }
            .padding(.horizontal, AppSpacing.medium)
            .background(AppColors.background)
            .onTapGesture {
                hideKeyboard()
            }
        }
        .sheet(isPresented: $showingPremiumGate) {
            PremiumGateView()
        }
    }
}

struct PremiumGateView: View {
    @Environment(\.presentationMode) var presentationMode
    
    var body: some View {
        NavigationView {
            VStack(spacing: AppSpacing.large) {
                // Header
                VStack(spacing: AppSpacing.medium) {
                    Image(systemName: "star.circle.fill")
                        .font(.system(size: 80))
                        .foregroundColor(AppColors.secondary)
                    
                    Text("WaddleBot Premium")
                        .font(AppFonts.largeTitle)
                        .fontWeight(.bold)
                        .foregroundColor(AppColors.textPrimary)
                    
                    Text("Unlock advanced community management features")
                        .font(AppFonts.body)
                        .foregroundColor(AppColors.textSecondary)
                        .multilineTextAlignment(.center)
                }
                .padding(.top, AppSpacing.large)
                
                // Features list
                VStack(spacing: AppSpacing.medium) {
                    FeatureRow(icon: "person.3.fill", title: "Advanced Member Management", description: "Reputation system, bulk operations, and detailed analytics")
                    FeatureRow(icon: "dollarsign.circle.fill", title: "Currency System", description: "Custom community currency with rewards and transactions")
                    FeatureRow(icon: "creditcard.fill", title: "Payment Integration", description: "Accept payments with PayPal and Stripe")
                    FeatureRow(icon: "gift.fill", title: "Raffles & Giveaways", description: "Engage your community with contests and prizes")
                    FeatureRow(icon: "chart.bar.fill", title: "Advanced Analytics", description: "Detailed insights and reporting dashboard")
                    FeatureRow(icon: "gear.2", title: "Premium Support", description: "Priority support and exclusive features")
                }
                .padding(.horizontal)
                
                Spacer()
                
                // CTA buttons
                VStack(spacing: AppSpacing.medium) {
                    Button("Subscribe to Premium") {
                        // Open subscription flow
                        if let url = URL(string: "https://waddlebot.com/premium") {
                            UIApplication.shared.open(url)
                        }
                    }
                    .buttonStyle(WaddleBotPrimaryButtonStyle())
                    
                    Button("I'm Already a Premium Member") {
                        presentationMode.wrappedValue.dismiss()
                    }
                    .font(AppFonts.callout)
                    .foregroundColor(AppColors.secondary)
                }
                .padding(.horizontal)
                .padding(.bottom, AppSpacing.large)
            }
            .background(AppColors.background)
            .navigationBarTitleDisplayMode(.inline)
            .navigationBarItems(trailing: Button("Close") {
                presentationMode.wrappedValue.dismiss()
            })
        }
    }
}

struct FeatureRow: View {
    let icon: String
    let title: String
    let description: String
    
    var body: some View {
        HStack(spacing: AppSpacing.medium) {
            Image(systemName: icon)
                .font(.title2)
                .foregroundColor(AppColors.secondary)
                .frame(width: 30)
            
            VStack(alignment: .leading, spacing: AppSpacing.tiny) {
                Text(title)
                    .font(AppFonts.callout)
                    .fontWeight(.semibold)
                    .foregroundColor(AppColors.textPrimary)
                
                Text(description)
                    .font(AppFonts.caption)
                    .foregroundColor(AppColors.textSecondary)
            }
            
            Spacer()
        }
        .padding()
        .background(AppColors.cardBackground)
        .cornerRadius(AppSizes.cardCornerRadius)
    }
}

// MARK: - Custom Styles
struct WaddleBotTextFieldStyle: TextFieldStyle {
    func _body(configuration: TextField<Self._Label>) -> some View {
        configuration
            .padding()
            .background(AppColors.inputBackground)
            .cornerRadius(AppSizes.buttonCornerRadius)
            .overlay(
                RoundedRectangle(cornerRadius: AppSizes.buttonCornerRadius)
                    .stroke(AppColors.inputBorder, lineWidth: 1)
            )
    }
}

struct WaddleBotPrimaryButtonStyle: ButtonStyle {
    func makeBody(configuration: Configuration) -> some View {
        configuration.label
            .background(AppColors.secondary)
            .foregroundColor(AppColors.textPrimary)
            .cornerRadius(AppSizes.buttonCornerRadius)
            .scaleEffect(configuration.isPressed ? 0.95 : 1.0)
            .animation(.easeInOut(duration: 0.1), value: configuration.isPressed)
    }
}

#Preview {
    LoginView()
        .environmentObject(AuthenticationManager())
}