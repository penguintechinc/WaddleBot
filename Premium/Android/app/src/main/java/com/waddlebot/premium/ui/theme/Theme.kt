package com.waddlebot.premium.ui.theme

import androidx.compose.foundation.isSystemInDarkTheme
import androidx.compose.material3.*
import androidx.compose.runtime.Composable
import androidx.compose.ui.graphics.Color

// WaddleBot Premium Brand Colors (White, Yellow, Black)
private val WaddleBotYellow = Color(0xFFFFD700)
private val WaddleBotYellowVariant = Color(0xFFFFF4B8)
private val WaddleBotBlack = Color(0xFF000000)
private val WaddleBotWhite = Color(0xFFFFFFFF)
private val WaddleBotGray = Color(0xFF666666)
private val WaddleBotLightGray = Color(0xFFF5F5F5)

// Status Colors
private val WaddleBotSuccess = Color(0xFF4CAF50)
private val WaddleBotWarning = Color(0xFFFF9800)
private val WaddleBotError = Color(0xFFF44336)
private val WaddleBotInfo = Color(0xFF2196F3)

// Reputation Colors
private val ReputationExcellent = Color(0xFF4CAF50)
private val ReputationGood = Color(0xFF2196F3)
private val ReputationFair = Color(0xFFFF9800)
private val ReputationPoor = Color(0xFFF44336)
private val ReputationBanned = Color(0xFF757575)

private val LightColorScheme = lightColorScheme(
    primary = WaddleBotYellow,
    onPrimary = WaddleBotBlack,
    primaryContainer = WaddleBotYellowVariant,
    onPrimaryContainer = WaddleBotBlack,
    secondary = WaddleBotYellow,
    onSecondary = WaddleBotBlack,
    secondaryContainer = WaddleBotYellowVariant,
    onSecondaryContainer = WaddleBotBlack,
    tertiary = WaddleBotInfo,
    onTertiary = WaddleBotWhite,
    error = WaddleBotError,
    onError = WaddleBotWhite,
    errorContainer = Color(0xFFFFDAD6),
    onErrorContainer = Color(0xFF410002),
    background = WaddleBotWhite,
    onBackground = WaddleBotBlack,
    surface = WaddleBotWhite,
    onSurface = WaddleBotBlack,
    surfaceVariant = WaddleBotLightGray,
    onSurfaceVariant = WaddleBotGray,
    outline = Color(0xFF79747E),
    outlineVariant = Color(0xFFCAC4D0),
    scrim = WaddleBotBlack,
    inverseSurface = WaddleBotBlack,
    inverseOnSurface = WaddleBotWhite,
    inversePrimary = WaddleBotYellow,
    surfaceDim = Color(0xFFDDD8E1),
    surfaceBright = WaddleBotWhite,
    surfaceContainerLowest = WaddleBotWhite,
    surfaceContainerLow = Color(0xFFF7F2FA),
    surfaceContainer = WaddleBotLightGray,
    surfaceContainerHigh = Color(0xFFE6E0E9),
    surfaceContainerHighest = Color(0xFFE1D9E3)
)

private val DarkColorScheme = darkColorScheme(
    primary = WaddleBotYellow,
    onPrimary = WaddleBotBlack,
    primaryContainer = Color(0xFF332D00),
    onPrimaryContainer = WaddleBotYellowVariant,
    secondary = WaddleBotYellow,
    onSecondary = WaddleBotBlack,
    secondaryContainer = Color(0xFF332D00),
    onSecondaryContainer = WaddleBotYellowVariant,
    tertiary = Color(0xFF8EAADF),
    onTertiary = Color(0xFF003062),
    error = Color(0xFFFFB4AB),
    onError = Color(0xFF690005),
    errorContainer = Color(0xFF93000A),
    onErrorContainer = Color(0xFFFFDAD6),
    background = Color(0xFF121212),
    onBackground = Color(0xFFE8E0E8),
    surface = Color(0xFF121212),
    onSurface = Color(0xFFE8E0E8),
    surfaceVariant = Color(0xFF49454F),
    onSurfaceVariant = Color(0xFFCAC4D0),
    outline = Color(0xFF938F99),
    outlineVariant = Color(0xFF49454F),
    scrim = WaddleBotBlack,
    inverseSurface = Color(0xFFE8E0E8),
    inverseOnSurface = Color(0xFF1B1B1B),
    inversePrimary = WaddleBotYellow,
    surfaceDim = Color(0xFF121212),
    surfaceBright = Color(0xFF3B3B3B),
    surfaceContainerLowest = Color(0xFF0D0D0D),
    surfaceContainerLow = Color(0xFF1B1B1B),
    surfaceContainer = Color(0xFF1F1F1F),
    surfaceContainerHigh = Color(0xFF2A2A2A),
    surfaceContainerHighest = Color(0xFF353535)
)

@Composable
fun WaddleBotPremiumTheme(
    darkTheme: Boolean = isSystemInDarkTheme(),
    content: @Composable () -> Unit
) {
    val colorScheme = if (darkTheme) {
        DarkColorScheme
    } else {
        LightColorScheme
    }

    MaterialTheme(
        colorScheme = colorScheme,
        typography = Typography,
        content = content
    )
}

// Custom color extensions for specific use cases
object WaddleBotColors {
    val success = WaddleBotSuccess
    val warning = WaddleBotWarning
    val error = WaddleBotError
    val info = WaddleBotInfo
    
    // Reputation colors
    val reputationExcellent = ReputationExcellent
    val reputationGood = ReputationGood
    val reputationFair = ReputationFair
    val reputationPoor = ReputationPoor
    val reputationBanned = ReputationBanned
    
    // Role colors
    val roleOwner = WaddleBotError
    val roleAdmin = WaddleBotWarning
    val roleModerator = WaddleBotInfo
    val roleMember = Color(0xFF757575)
}

// Helper function to get reputation color
@Composable
fun getReputationColor(score: Int): Color {
    return when (score) {
        in 750..850 -> WaddleBotColors.reputationExcellent
        in 650..749 -> WaddleBotColors.reputationGood
        in 550..649 -> WaddleBotColors.reputationFair
        in 500..549 -> WaddleBotColors.reputationPoor
        else -> WaddleBotColors.reputationBanned
    }
}

// Helper function to get reputation label
fun getReputationLabel(score: Int): String {
    return when (score) {
        in 750..850 -> "Excellent"
        in 650..749 -> "Good"
        in 550..649 -> "Fair"
        in 500..549 -> "Poor"
        else -> "Banned"
    }
}

// Helper function to get role color
@Composable
fun getRoleColor(role: String): Color {
    return when (role.lowercase()) {
        "owner" -> WaddleBotColors.roleOwner
        "admin" -> WaddleBotColors.roleAdmin
        "moderator" -> WaddleBotColors.roleModerator
        else -> WaddleBotColors.roleMember
    }
}