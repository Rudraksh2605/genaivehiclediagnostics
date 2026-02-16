package com.vehiclediag.app

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.padding
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Code
import androidx.compose.material.icons.filled.Dashboard
import androidx.compose.material.icons.filled.Warning
import androidx.compose.material3.*
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.text.font.FontWeight
import androidx.navigation.NavDestination.Companion.hierarchy
import androidx.navigation.NavGraph.Companion.findStartDestination
import androidx.navigation.compose.NavHost
import androidx.navigation.compose.composable
import androidx.navigation.compose.currentBackStackEntryAsState
import androidx.navigation.compose.rememberNavController
import com.vehiclediag.app.ui.screens.AlertsScreen
import com.vehiclediag.app.ui.screens.CodeGeneratorScreen
import com.vehiclediag.app.ui.screens.DashboardScreen
import com.vehiclediag.app.ui.theme.DarkBackground
import com.vehiclediag.app.ui.theme.DarkSurface
import com.vehiclediag.app.ui.theme.TextPrimary
import com.vehiclediag.app.ui.theme.TextMuted
import com.vehiclediag.app.ui.theme.AccentCyan
import com.vehiclediag.app.ui.theme.VehicleDiagnosticsTheme

/**
 * MainActivity — Entry point for the Vehicle Diagnostics Android app.
 * Sets up bottom navigation between Dashboard, Code Generator, and Alerts screens.
 */
class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContent {
            VehicleDiagnosticsTheme {
                MainScreen()
            }
        }
    }
}

/**
 * Bottom navigation destinations.
 */
sealed class Screen(val route: String, val title: String, val icon: ImageVector) {
    data object Dashboard : Screen("dashboard", "Dashboard", Icons.Default.Dashboard)
    data object CodeGen : Screen("codegen", "CodeGen", Icons.Default.Code)
    data object Alerts : Screen("alerts", "Alerts", Icons.Default.Warning)
}

val bottomNavItems = listOf(Screen.Dashboard, Screen.CodeGen, Screen.Alerts)

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun MainScreen() {
    val navController = rememberNavController()

    Scaffold(
        bottomBar = {
            NavigationBar(
                containerColor = DarkSurface,
                contentColor = TextPrimary
            ) {
                val navBackStackEntry by navController.currentBackStackEntryAsState()
                val currentDestination = navBackStackEntry?.destination

                bottomNavItems.forEach { screen ->
                    val isSelected = currentDestination?.hierarchy?.any {
                        it.route == screen.route
                    } == true

                    NavigationBarItem(
                        icon = {
                            Icon(
                                screen.icon,
                                contentDescription = screen.title
                            )
                        },
                        label = {
                            Text(
                                text = screen.title,
                                fontWeight = if (isSelected) FontWeight.Bold else FontWeight.Normal
                            )
                        },
                        selected = isSelected,
                        onClick = {
                            navController.navigate(screen.route) {
                                popUpTo(navController.graph.findStartDestination().id) {
                                    saveState = true
                                }
                                launchSingleTop = true
                                restoreState = true
                            }
                        },
                        colors = NavigationBarItemDefaults.colors(
                            selectedIconColor = AccentCyan,
                            selectedTextColor = AccentCyan,
                            indicatorColor = AccentCyan.copy(alpha = 0.15f),
                            unselectedIconColor = TextMuted,
                            unselectedTextColor = TextMuted
                        )
                    )
                }
            }
        }
    ) { innerPadding ->
        NavHost(
            navController = navController,
            startDestination = Screen.Dashboard.route,
            modifier = Modifier
                .padding(innerPadding)
                .background(DarkBackground)
        ) {
            composable(Screen.Dashboard.route) { DashboardScreen() }
            composable(Screen.CodeGen.route) { CodeGeneratorScreen() }
            composable(Screen.Alerts.route) { AlertsScreen() }
        }
    }
}
