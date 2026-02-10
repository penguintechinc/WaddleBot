import SwiftUI

struct LoginView: View {
    @EnvironmentObject var authManager: AuthenticationManager
    @Environment(\.colorScheme) var colorScheme

    @State private var email = ""
    @State private var password = ""
    @FocusState private var focusedField: Field?

    private enum Field {
        case email, password
    }

    private var isFormValid: Bool {
        !email.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty &&
        !password.isEmpty &&
        email.contains("@")
    }

    var body: some View {
        ZStack {
            Color.adaptiveBackground(colorScheme)
                .ignoresSafeArea()

            ScrollView {
                VStack(spacing: Spacing.xl) {
                    headerSection

                    formSection

                    loginButton

                    forgotPasswordLink
                }
                .padding(.horizontal, Spacing.lg)
                .padding(.top, Spacing.xxl)
            }

            LoadingOverlay(isLoading: authManager.isLoading, message: "Signing in...")
        }
        .alert("Login Failed", isPresented: .constant(authManager.error != nil)) {
            Button("OK") {
                authManager.clearError()
            }
        } message: {
            Text(authManager.error ?? "An error occurred")
        }
    }

    private var headerSection: some View {
        VStack(spacing: Spacing.sm) {
            Image(systemName: "bubble.left.and.bubble.right.fill")
                .font(.system(size: 60))
                .foregroundColor(Theme.accent)
                .padding(.bottom, Spacing.sm)

            Text("WaddleBot")
                .font(Typography.title)
                .foregroundColor(Color.adaptiveText(colorScheme))

            Text("Manage your communities")
                .font(Typography.body)
                .foregroundColor(Color.adaptiveSecondaryText(colorScheme))
        }
        .padding(.bottom, Spacing.lg)
    }

    private var formSection: some View {
        VStack(spacing: Spacing.md) {
            VStack(alignment: .leading, spacing: Spacing.xs) {
                Text("Email")
                    .font(Typography.subheadline)
                    .foregroundColor(Color.adaptiveSecondaryText(colorScheme))

                TextField("you@example.com", text: $email)
                    .textFieldStyle(CustomTextFieldStyle())
                    .textContentType(.emailAddress)
                    .keyboardType(.emailAddress)
                    .autocapitalization(.none)
                    .autocorrectionDisabled()
                    .focused($focusedField, equals: .email)
                    .submitLabel(.next)
                    .onSubmit {
                        focusedField = .password
                    }
            }

            VStack(alignment: .leading, spacing: Spacing.xs) {
                Text("Password")
                    .font(Typography.subheadline)
                    .foregroundColor(Color.adaptiveSecondaryText(colorScheme))

                SecureField("Enter your password", text: $password)
                    .textFieldStyle(CustomTextFieldStyle())
                    .textContentType(.password)
                    .focused($focusedField, equals: .password)
                    .submitLabel(.go)
                    .onSubmit {
                        if isFormValid {
                            performLogin()
                        }
                    }
            }
        }
    }

    private var loginButton: some View {
        Button(action: performLogin) {
            Text("Sign In")
        }
        .primaryButton()
        .disabled(!isFormValid || authManager.isLoading)
        .padding(.top, Spacing.sm)
    }

    private var forgotPasswordLink: some View {
        Button(action: {
            // Future: Implement forgot password flow
        }) {
            Text("Forgot password?")
                .font(Typography.subheadline)
                .foregroundColor(Theme.accent)
        }
        .padding(.top, Spacing.xs)
    }

    private func performLogin() {
        focusedField = nil
        Task {
            await authManager.login(
                email: email.trimmingCharacters(in: .whitespacesAndNewlines),
                password: password
            )
        }
    }
}

struct CustomTextFieldStyle: TextFieldStyle {
    @Environment(\.colorScheme) var colorScheme

    func _body(configuration: TextField<Self._Label>) -> some View {
        configuration
            .padding(.horizontal, Spacing.md)
            .padding(.vertical, Spacing.sm)
            .background(Color.adaptiveCardBackground(colorScheme))
            .cornerRadius(10)
            .overlay(
                RoundedRectangle(cornerRadius: 10)
                    .stroke(Color.gray.opacity(0.3), lineWidth: 1)
            )
    }
}

#Preview {
    LoginView()
        .environmentObject(AuthenticationManager())
}
