package com.waddlebot.premium.presentation.license

import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Description
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.tooling.preview.Preview
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel
import com.waddlebot.premium.ui.theme.WaddleBotPremiumTheme
import kotlin.system.exitProcess

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun PremiumLicenseScreen(
    onLicenseAccepted: () -> Unit,
    viewModel: PremiumLicenseViewModel = hiltViewModel()
) {
    val context = LocalContext.current
    val scrollState = rememberScrollState()
    var hasScrolledToBottom by remember { mutableStateOf(false) }
    
    // Check if user has scrolled to bottom
    LaunchedEffect(scrollState.value, scrollState.maxValue) {
        hasScrolledToBottom = scrollState.value >= scrollState.maxValue - 100 || scrollState.maxValue == 0
    }
    
    Column(
        modifier = Modifier
            .fillMaxSize()
            .padding(16.dp),
        horizontalAlignment = Alignment.CenterHorizontally
    ) {
        // Header
        Column(
            horizontalAlignment = Alignment.CenterHorizontally,
            modifier = Modifier.padding(vertical = 24.dp)
        ) {
            Icon(
                imageVector = Icons.Default.Description,
                contentDescription = null,
                modifier = Modifier.size(60.dp),
                tint = MaterialTheme.colorScheme.primary
            )
            
            Spacer(modifier = Modifier.height(16.dp))
            
            Text(
                text = "Premium License Agreement",
                style = MaterialTheme.typography.headlineMedium,
                fontWeight = FontWeight.Bold,
                textAlign = TextAlign.Center
            )
            
            Text(
                text = "Terms of Service",
                style = MaterialTheme.typography.bodyMedium,
                color = MaterialTheme.colorScheme.onSurfaceVariant
            )
        }
        
        // License content
        Card(
            modifier = Modifier
                .weight(1f)
                .fillMaxWidth()
        ) {
            Column(
                modifier = Modifier
                    .verticalScroll(scrollState)
                    .padding(16.dp)
            ) {
                LicenseSection(
                    title = "PREMIUM SUBSCRIPTION REQUIRED",
                    content = """
                        This application is exclusively available to WaddleBot Premium subscribers. By using this application, you acknowledge that you have an active premium subscription and agree to comply with all premium service terms.
                    """.trimIndent()
                )
                
                LicenseSection(
                    title = "LICENSE GRANT",
                    content = """
                        Subject to your compliance with these terms and your active premium subscription, WaddleBot grants you a limited, non-exclusive, non-transferable license to use this application solely for managing your premium communities.
                    """.trimIndent()
                )
                
                LicenseSection(
                    title = "SUBSCRIPTION VERIFICATION",
                    content = """
                        The application will periodically verify your premium subscription status. If your subscription expires or is cancelled, your access to the application will be immediately revoked.
                    """.trimIndent()
                )
                
                LicenseSection(
                    title = "RESTRICTIONS",
                    content = """
                        You may not:
                        • Share your account credentials with non-premium users
                        • Use the application for commercial purposes beyond your premium subscription scope
                        • Reverse engineer, decompile, or disassemble the application
                        • Remove or modify any proprietary notices or labels
                    """.trimIndent()
                )
                
                LicenseSection(
                    title = "DATA AND PRIVACY",
                    content = """
                        The application collects and processes community data in accordance with WaddleBot's Privacy Policy. Premium subscribers have enhanced data protection and priority support.
                    """.trimIndent()
                )
                
                LicenseSection(
                    title = "PREMIUM FEATURES",
                    content = """
                        Premium features include:
                        • Advanced member management with reputation system
                        • Custom community currency and rewards
                        • Payment processing integration
                        • Raffle and giveaway systems
                        • Priority support and exclusive features
                    """.trimIndent()
                )
                
                LicenseSection(
                    title = "TERMINATION",
                    content = """
                        This license terminates automatically upon:
                        • Cancellation or expiration of your premium subscription
                        • Violation of these terms
                        • Termination of your WaddleBot account
                    """.trimIndent()
                )
                
                LicenseSection(
                    title = "DISCLAIMER",
                    content = """
                        THE APPLICATION IS PROVIDED "AS IS" WITHOUT WARRANTY OF ANY KIND. WADDLEBOT DISCLAIMS ALL WARRANTIES, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE, AND NON-INFRINGEMENT.
                    """.trimIndent()
                )
                
                LicenseSection(
                    title = "LIMITATION OF LIABILITY",
                    content = """
                        IN NO EVENT SHALL WADDLEBOT BE LIABLE FOR ANY INDIRECT, INCIDENTAL, SPECIAL, CONSEQUENTIAL, OR PUNITIVE DAMAGES ARISING OUT OF OR RELATING TO THE USE OF THIS APPLICATION.
                    """.trimIndent()
                )
                
                LicenseSection(
                    title = "GOVERNING LAW",
                    content = """
                        This agreement shall be governed by and construed in accordance with the laws of the jurisdiction where WaddleBot is incorporated.
                    """.trimIndent()
                )
                
                Card(
                    modifier = Modifier
                        .fillMaxWidth()
                        .padding(vertical = 16.dp),
                    colors = CardDefaults.cardColors(
                        containerColor = MaterialTheme.colorScheme.primaryContainer
                    )
                ) {
                    Text(
                        text = "By continuing to use this application, you acknowledge that you have read, understood, and agree to be bound by these terms and conditions.",
                        style = MaterialTheme.typography.bodyMedium,
                        fontWeight = FontWeight.SemiBold,
                        modifier = Modifier.padding(16.dp)
                    )
                }
            }
        }
        
        // Acceptance buttons
        Column(
            modifier = Modifier.padding(top = 16.dp),
            horizontalAlignment = Alignment.CenterHorizontally
        ) {
            Button(
                onClick = {
                    viewModel.acceptLicense()
                    onLicenseAccepted()
                },
                modifier = Modifier.fillMaxWidth(),
                enabled = hasScrolledToBottom
            ) {
                Text("I Accept the Terms and Conditions")
            }
            
            Spacer(modifier = Modifier.height(8.dp))
            
            TextButton(
                onClick = {
                    exitProcess(0)
                },
                modifier = Modifier.fillMaxWidth()
            ) {
                Text(
                    text = "I Do Not Accept",
                    color = MaterialTheme.colorScheme.error
                )
            }
            
            if (!hasScrolledToBottom) {
                Spacer(modifier = Modifier.height(8.dp))
                Text(
                    text = "Please scroll to the bottom to continue",
                    style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                    textAlign = TextAlign.Center
                )
            }
        }
    }
}

@Composable
private fun LicenseSection(
    title: String,
    content: String
) {
    Column(
        modifier = Modifier.padding(vertical = 8.dp)
    ) {
        Text(
            text = title,
            style = MaterialTheme.typography.titleMedium,
            fontWeight = FontWeight.Bold,
            modifier = Modifier.padding(bottom = 4.dp)
        )
        
        Text(
            text = content,
            style = MaterialTheme.typography.bodyMedium,
            color = MaterialTheme.colorScheme.onSurfaceVariant
        )
    }
}

@Preview(showBackground = true)
@Composable
fun PremiumLicenseScreenPreview() {
    WaddleBotPremiumTheme {
        PremiumLicenseScreen(
            onLicenseAccepted = {}
        )
    }
}