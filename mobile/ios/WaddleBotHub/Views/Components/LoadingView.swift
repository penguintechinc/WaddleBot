import SwiftUI

struct LoadingView: View {
    var message: String = "Loading..."
    @Environment(\.colorScheme) var colorScheme

    var body: some View {
        VStack(spacing: Spacing.md) {
            ProgressView()
                .progressViewStyle(CircularProgressViewStyle(tint: Theme.accent))
                .scaleEffect(1.2)

            Text(message)
                .font(Typography.subheadline)
                .foregroundColor(Color.adaptiveSecondaryText(colorScheme))
        }
        .frame(maxWidth: .infinity, maxHeight: .infinity)
        .background(Color.adaptiveBackground(colorScheme).opacity(0.8))
    }
}

struct LoadingOverlay: View {
    var isLoading: Bool
    var message: String = "Loading..."

    var body: some View {
        ZStack {
            if isLoading {
                Color.black.opacity(0.3)
                    .ignoresSafeArea()

                VStack(spacing: Spacing.md) {
                    ProgressView()
                        .progressViewStyle(CircularProgressViewStyle(tint: .white))
                        .scaleEffect(1.5)

                    Text(message)
                        .font(Typography.subheadline)
                        .foregroundColor(.white)
                }
                .padding(Spacing.lg)
                .background(Color.black.opacity(0.7))
                .cornerRadius(12)
            }
        }
        .animation(.easeInOut(duration: 0.2), value: isLoading)
    }
}

struct InlineLoadingView: View {
    var body: some View {
        HStack(spacing: Spacing.xs) {
            ProgressView()
                .progressViewStyle(CircularProgressViewStyle(tint: Theme.accent))

            Text("Loading...")
                .font(Typography.footnote)
                .foregroundColor(.secondary)
        }
    }
}

struct EmptyStateView: View {
    var icon: String
    var title: String
    var message: String
    var actionTitle: String?
    var action: (() -> Void)?

    @Environment(\.colorScheme) var colorScheme

    var body: some View {
        VStack(spacing: Spacing.md) {
            Image(systemName: icon)
                .font(.system(size: 48))
                .foregroundColor(Theme.accent.opacity(0.6))

            Text(title)
                .font(Typography.title3)
                .foregroundColor(Color.adaptiveText(colorScheme))

            Text(message)
                .font(Typography.body)
                .foregroundColor(Color.adaptiveSecondaryText(colorScheme))
                .multilineTextAlignment(.center)
                .padding(.horizontal, Spacing.xl)

            if let actionTitle = actionTitle, let action = action {
                Button(action: action) {
                    Text(actionTitle)
                }
                .primaryButton()
                .padding(.horizontal, Spacing.xxl)
                .padding(.top, Spacing.sm)
            }
        }
        .frame(maxWidth: .infinity, maxHeight: .infinity)
    }
}

struct ErrorView: View {
    var message: String
    var retryAction: (() -> Void)?

    @Environment(\.colorScheme) var colorScheme

    var body: some View {
        VStack(spacing: Spacing.md) {
            Image(systemName: "exclamationmark.triangle.fill")
                .font(.system(size: 48))
                .foregroundColor(Theme.error)

            Text("Something went wrong")
                .font(Typography.title3)
                .foregroundColor(Color.adaptiveText(colorScheme))

            Text(message)
                .font(Typography.body)
                .foregroundColor(Color.adaptiveSecondaryText(colorScheme))
                .multilineTextAlignment(.center)
                .padding(.horizontal, Spacing.xl)

            if let retryAction = retryAction {
                Button(action: retryAction) {
                    Text("Try Again")
                }
                .primaryButton()
                .padding(.horizontal, Spacing.xxl)
                .padding(.top, Spacing.sm)
            }
        }
        .frame(maxWidth: .infinity, maxHeight: .infinity)
    }
}

#Preview("Loading View") {
    LoadingView(message: "Fetching data...")
}

#Preview("Empty State") {
    EmptyStateView(
        icon: "person.3",
        title: "No Communities",
        message: "You haven't joined any communities yet.",
        actionTitle: "Explore",
        action: {}
    )
}

#Preview("Error View") {
    ErrorView(
        message: "Unable to connect to the server.",
        retryAction: {}
    )
}
