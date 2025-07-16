import SwiftUI

struct PremiumLicenseView: View {
    @Binding var isAccepted: Bool
    @State private var hasScrolledToBottom = false
    @State private var scrollViewHeight: CGFloat = 0
    @State private var contentHeight: CGFloat = 0
    
    var body: some View {
        VStack(spacing: AppSpacing.large) {
            // Header
            VStack(spacing: AppSpacing.medium) {
                Image(systemName: "doc.text.fill")
                    .font(.system(size: 60))
                    .foregroundColor(AppColors.secondary)
                
                Text("Premium License Agreement")
                    .font(AppFonts.largeTitle)
                    .fontWeight(.bold)
                    .foregroundColor(AppColors.textPrimary)
                    .multilineTextAlignment(.center)
                
                Text("Terms of Service")
                    .font(AppFonts.body)
                    .foregroundColor(AppColors.textSecondary)
            }
            .padding(.top, AppSpacing.large)
            
            // License content
            ScrollView {
                VStack(alignment: .leading, spacing: AppSpacing.medium) {
                    LicenseSection(
                        title: "PREMIUM SUBSCRIPTION REQUIRED",
                        content: """
                        This application is exclusively available to WaddleBot Premium subscribers. By using this application, you acknowledge that you have an active premium subscription and agree to comply with all premium service terms.
                        """
                    )
                    
                    LicenseSection(
                        title: "LICENSE GRANT",
                        content: """
                        Subject to your compliance with these terms and your active premium subscription, WaddleBot grants you a limited, non-exclusive, non-transferable license to use this application solely for managing your premium communities.
                        """
                    )
                    
                    LicenseSection(
                        title: "SUBSCRIPTION VERIFICATION",
                        content: """
                        The application will periodically verify your premium subscription status. If your subscription expires or is cancelled, your access to the application will be immediately revoked.
                        """
                    )
                    
                    LicenseSection(
                        title: "RESTRICTIONS",
                        content: """
                        You may not:
                        • Share your account credentials with non-premium users
                        • Use the application for commercial purposes beyond your premium subscription scope
                        • Reverse engineer, decompile, or disassemble the application
                        • Remove or modify any proprietary notices or labels
                        """
                    )
                    
                    LicenseSection(
                        title: "DATA AND PRIVACY",
                        content: """
                        The application collects and processes community data in accordance with WaddleBot's Privacy Policy. Premium subscribers have enhanced data protection and priority support.
                        """
                    )
                    
                    LicenseSection(
                        title: "PREMIUM FEATURES",
                        content: """
                        Premium features include:
                        • Advanced member management with reputation system
                        • Custom community currency and rewards
                        • Payment processing integration
                        • Raffle and giveaway systems
                        • Priority support and exclusive features
                        """
                    )
                    
                    LicenseSection(
                        title: "TERMINATION",
                        content: """
                        This license terminates automatically upon:
                        • Cancellation or expiration of your premium subscription
                        • Violation of these terms
                        • Termination of your WaddleBot account
                        """
                    )
                    
                    LicenseSection(
                        title: "DISCLAIMER",
                        content: """
                        THE APPLICATION IS PROVIDED "AS IS" WITHOUT WARRANTY OF ANY KIND. WADDLEBOT DISCLAIMS ALL WARRANTIES, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE, AND NON-INFRINGEMENT.
                        """
                    )
                    
                    LicenseSection(
                        title: "LIMITATION OF LIABILITY",
                        content: """
                        IN NO EVENT SHALL WADDLEBOT BE LIABLE FOR ANY INDIRECT, INCIDENTAL, SPECIAL, CONSEQUENTIAL, OR PUNITIVE DAMAGES ARISING OUT OF OR RELATING TO THE USE OF THIS APPLICATION.
                        """
                    )
                    
                    LicenseSection(
                        title: "GOVERNING LAW",
                        content: """
                        This agreement shall be governed by and construed in accordance with the laws of the jurisdiction where WaddleBot is incorporated.
                        """
                    )
                    
                    Text("By continuing to use this application, you acknowledge that you have read, understood, and agree to be bound by these terms and conditions.")
                        .font(AppFonts.body)
                        .foregroundColor(AppColors.textPrimary)
                        .fontWeight(.semibold)
                        .padding()
                        .background(AppColors.accent.opacity(0.3))
                        .cornerRadius(AppSizes.cardCornerRadius)
                        .padding(.top, AppSpacing.medium)
                }
                .padding(.horizontal, AppSpacing.medium)
                .background(
                    GeometryReader { geometry in
                        Color.clear.onAppear {
                            contentHeight = geometry.size.height
                        }
                    }
                )
            }
            .background(
                GeometryReader { geometry in
                    Color.clear.onAppear {
                        scrollViewHeight = geometry.size.height
                    }
                }
            )
            .onAppear {
                // Auto-scroll detection for small screens
                DispatchQueue.main.asyncAfter(deadline: .now() + 0.5) {
                    hasScrolledToBottom = contentHeight <= scrollViewHeight
                }
            }
            
            // Acceptance buttons
            VStack(spacing: AppSpacing.medium) {
                Button(action: {
                    UserDefaults.standard.set(true, forKey: "license_accepted")
                    isAccepted = true
                }) {
                    Text("I Accept the Terms and Conditions")
                        .font(AppFonts.body)
                        .fontWeight(.semibold)
                        .foregroundColor(AppColors.textPrimary)
                        .frame(maxWidth: .infinity, minHeight: AppSizes.buttonHeight)
                }
                .buttonStyle(WaddleBotPrimaryButtonStyle())
                .disabled(!hasScrolledToBottom)
                .opacity(hasScrolledToBottom ? 1.0 : 0.5)
                
                Button(action: {
                    // Exit the app
                    exit(0)
                }) {
                    Text("I Do Not Accept")
                        .font(AppFonts.body)
                        .foregroundColor(AppColors.error)
                        .frame(maxWidth: .infinity, minHeight: AppSizes.buttonHeight)
                }
                .buttonStyle(PlainButtonStyle())
                
                if !hasScrolledToBottom {
                    Text("Please scroll to the bottom to continue")
                        .font(AppFonts.caption)
                        .foregroundColor(AppColors.textSecondary)
                        .multilineTextAlignment(.center)
                }
            }
            .padding(.horizontal, AppSpacing.medium)
            .padding(.bottom, AppSpacing.large)
        }
        .background(AppColors.background)
    }
}

struct LicenseSection: View {
    let title: String
    let content: String
    
    var body: some View {
        VStack(alignment: .leading, spacing: AppSpacing.small) {
            Text(title)
                .font(AppFonts.title2)
                .fontWeight(.bold)
                .foregroundColor(AppColors.textPrimary)
            
            Text(content)
                .font(AppFonts.body)
                .foregroundColor(AppColors.textSecondary)
                .fixedSize(horizontal: false, vertical: true)
        }
    }
}

#Preview {
    PremiumLicenseView(isAccepted: .constant(false))
}