package io.waddlebot.hub.presentation.navigation

import androidx.compose.runtime.Composable
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.ui.Modifier
import androidx.hilt.navigation.compose.hiltViewModel
import androidx.navigation.NavHostController
import androidx.navigation.NavType
import androidx.navigation.compose.NavHost
import androidx.navigation.compose.composable
import androidx.navigation.compose.rememberNavController
import androidx.navigation.navArgument
import io.waddlebot.hub.presentation.auth.AuthViewModel
import io.waddlebot.hub.presentation.auth.LoginScreen
import io.waddlebot.hub.presentation.communities.CommunityDetailScreen
import io.waddlebot.hub.presentation.communities.CommunityListScreen
import io.waddlebot.hub.presentation.members.MemberListScreen
import io.waddlebot.hub.presentation.settings.SettingsScreen

object NavRoutes {
    const val LOGIN = "login"
    const val COMMUNITIES = "communities"
    const val COMMUNITY_DETAIL = "community/{communityId}"
    const val COMMUNITY_MEMBERS = "community/{communityId}/members"
    const val SETTINGS = "settings"

    fun communityDetail(communityId: String) = "community/$communityId"
    fun communityMembers(communityId: String) = "community/$communityId/members"
}

@Composable
fun HubNavGraph(
    modifier: Modifier = Modifier,
    navController: NavHostController = rememberNavController(),
    authViewModel: AuthViewModel = hiltViewModel()
) {
    val authState by authViewModel.state.collectAsState()

    val startDestination = when {
        authState.isCheckingAuth -> NavRoutes.LOGIN
        authState.isLoggedIn -> NavRoutes.COMMUNITIES
        else -> NavRoutes.LOGIN
    }

    NavHost(
        navController = navController,
        startDestination = startDestination,
        modifier = modifier
    ) {
        composable(NavRoutes.LOGIN) {
            LoginScreen(
                onLoginSuccess = {
                    navController.navigate(NavRoutes.COMMUNITIES) {
                        popUpTo(NavRoutes.LOGIN) { inclusive = true }
                    }
                },
                viewModel = authViewModel
            )
        }

        composable(NavRoutes.COMMUNITIES) {
            CommunityListScreen(
                onCommunityClick = { communityId ->
                    navController.navigate(NavRoutes.communityDetail(communityId))
                },
                onSettingsClick = {
                    navController.navigate(NavRoutes.SETTINGS)
                }
            )
        }

        composable(
            route = NavRoutes.COMMUNITY_DETAIL,
            arguments = listOf(
                navArgument("communityId") { type = NavType.StringType }
            )
        ) { backStackEntry ->
            val communityId = backStackEntry.arguments?.getString("communityId") ?: ""
            CommunityDetailScreen(
                communityId = communityId,
                onBackClick = { navController.popBackStack() },
                onMembersClick = {
                    navController.navigate(NavRoutes.communityMembers(communityId))
                }
            )
        }

        composable(
            route = NavRoutes.COMMUNITY_MEMBERS,
            arguments = listOf(
                navArgument("communityId") { type = NavType.StringType }
            )
        ) {
            MemberListScreen(
                onBackClick = { navController.popBackStack() }
            )
        }

        composable(NavRoutes.SETTINGS) {
            SettingsScreen(
                onBackClick = { navController.popBackStack() },
                onLogout = {
                    authViewModel.logout()
                    navController.navigate(NavRoutes.LOGIN) {
                        popUpTo(0) { inclusive = true }
                    }
                }
            )
        }
    }
}
