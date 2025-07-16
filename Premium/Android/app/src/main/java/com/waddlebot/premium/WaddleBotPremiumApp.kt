package com.waddlebot.premium

import androidx.compose.runtime.Composable
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.hilt.navigation.compose.hiltViewModel
import androidx.navigation.compose.NavHost
import androidx.navigation.compose.composable
import androidx.navigation.compose.rememberNavController
import com.waddlebot.premium.presentation.auth.AuthViewModel
import com.waddlebot.premium.presentation.auth.LoginScreen
import com.waddlebot.premium.presentation.auth.PremiumGateScreen
import com.waddlebot.premium.presentation.communities.CommunityListScreen
import com.waddlebot.premium.presentation.communities.CommunityDetailScreen
import com.waddlebot.premium.presentation.dashboard.DashboardScreen
import com.waddlebot.premium.presentation.members.MemberListScreen
import com.waddlebot.premium.presentation.currency.CurrencyManagementScreen
import com.waddlebot.premium.presentation.profile.ProfileScreen
import com.waddlebot.premium.presentation.common.LoadingScreen
import com.waddlebot.premium.presentation.license.PremiumLicenseScreen
import com.waddlebot.premium.presentation.license.PremiumLicenseViewModel

@Composable
fun WaddleBotPremiumApp(
    authViewModel: AuthViewModel = hiltViewModel(),
    licenseViewModel: PremiumLicenseViewModel = hiltViewModel()
) {
    val navController = rememberNavController()
    val authState by authViewModel.authState.collectAsState()
    val isLoading by authViewModel.isLoading.collectAsState()
    val hasAcceptedLicense = licenseViewModel.isLicenseAccepted()
    
    if (!hasAcceptedLicense) {
        PremiumLicenseScreen(
            onLicenseAccepted = {
                // License is automatically saved in the view model
            }
        )
    } else if (isLoading) {
        LoadingScreen()
    } else {
        NavHost(
            navController = navController,
            startDestination = if (authState.isAuthenticated) "dashboard" else "login"
        ) {
            // Authentication
            composable("login") {
                LoginScreen(
                    onNavigateToSplash = { navController.navigate("dashboard") },
                    onNavigateToPremiumGate = { navController.navigate("premium_gate") }
                )
            }
            
            composable("premium_gate") {
                PremiumGateScreen(
                    onNavigateBack = { navController.popBackStack() }
                )
            }
            
            // Main App
            composable("dashboard") {
                DashboardScreen(navController = navController)
            }
            
            composable("communities") {
                CommunityListScreen(
                    onNavigateToDetail = { communityId ->
                        navController.navigate("community_detail/$communityId")
                    }
                )
            }
            
            composable("community_detail/{communityId}") { backStackEntry ->
                val communityId = backStackEntry.arguments?.getString("communityId") ?: ""
                CommunityDetailScreen(
                    communityId = communityId,
                    onNavigateToMembers = { navController.navigate("members/$communityId") },
                    onNavigateToCurrency = { navController.navigate("currency/$communityId") }
                )
            }
            
            composable("members/{communityId}") { backStackEntry ->
                val communityId = backStackEntry.arguments?.getString("communityId") ?: ""
                MemberListScreen(
                    communityId = communityId,
                    onNavigateBack = { navController.popBackStack() }
                )
            }
            
            composable("currency/{communityId}") { backStackEntry ->
                val communityId = backStackEntry.arguments?.getString("communityId") ?: ""
                CurrencyManagementScreen(
                    communityId = communityId,
                    onNavigateBack = { navController.popBackStack() }
                )
            }
            
            composable("profile") {
                ProfileScreen(
                    onNavigateToLogin = { 
                        navController.navigate("login") {
                            popUpTo("dashboard") { inclusive = true }
                        }
                    }
                )
            }
        }
    }
}