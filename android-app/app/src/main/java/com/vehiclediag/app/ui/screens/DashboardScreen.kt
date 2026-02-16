package com.vehiclediag.app.ui.screens

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.PlayArrow
import androidx.compose.material.icons.filled.Stop
import androidx.compose.material3.*
import androidx.compose.runtime.Composable
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.lifecycle.viewmodel.compose.viewModel
import com.vehiclediag.app.ui.components.BatteryIndicator
import com.vehiclediag.app.ui.components.DrivetrainPanel
import com.vehiclediag.app.ui.components.EVRangeCard
import com.vehiclediag.app.ui.components.SpeedGauge
import com.vehiclediag.app.ui.components.ThrottleBrakeBar
import com.vehiclediag.app.ui.components.TirePressureGrid
import com.vehiclediag.app.ui.theme.*
import com.vehiclediag.app.viewmodel.DashboardViewModel

/**
 * Dashboard Screen — Main vehicle health overview.
 * Shows speed gauge, battery indicator, tire pressure grid,
 * drivetrain controls, EV range, and simulation controls
 * with live 1-second refresh.
 */
@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun DashboardScreen(
    viewModel: DashboardViewModel = viewModel()
) {
    val telemetry by viewModel.telemetry.collectAsState()
    val isLoading by viewModel.isLoading.collectAsState()
    val error by viewModel.error.collectAsState()
    val simStatus by viewModel.simulationStatus.collectAsState()

    Column(
        modifier = Modifier
            .fillMaxSize()
            .background(DarkBackground)
            .verticalScroll(rememberScrollState())
            .padding(16.dp),
        horizontalAlignment = Alignment.CenterHorizontally
    ) {
        // ── Header ──────────────────────────────────────────────────
        Row(
            modifier = Modifier.fillMaxWidth(),
            horizontalArrangement = Arrangement.SpaceBetween,
            verticalAlignment = Alignment.CenterVertically
        ) {
            Column {
                Text(
                    text = "Vehicle Health Dashboard",
                    style = MaterialTheme.typography.headlineSmall,
                    fontWeight = FontWeight.Bold,
                    color = TextPrimary
                )
                Spacer(modifier = Modifier.height(4.dp))
                Text(
                    text = if (simStatus.running) "🟢 Live Data" else "⚪ Mock Data",
                    fontSize = 12.sp,
                    color = if (simStatus.running) AccentGreen else TextMuted
                )
            }

            // Vehicle variant badge
            Text(
                text = when (telemetry.vehicleVariant) {
                    "EV" -> "⚡ EV"
                    "Hybrid" -> "🔄 HEV"
                    else -> "🔥 ICE"
                },
                fontSize = 11.sp,
                fontWeight = FontWeight.Bold,
                color = AccentCyan,
                modifier = Modifier
                    .clip(RoundedCornerShape(6.dp))
                    .background(AccentCyan.copy(alpha = 0.12f))
                    .padding(horizontal = 10.dp, vertical = 4.dp)
            )
        }

        Spacer(modifier = Modifier.height(16.dp))

        // ── Error Banner ────────────────────────────────────────────
        error?.let { errorMsg ->
            Card(
                colors = CardDefaults.cardColors(containerColor = AccentRed.copy(alpha = 0.15f)),
                modifier = Modifier.fillMaxWidth()
            ) {
                Text(
                    text = "⚠️ $errorMsg",
                    color = AccentRed,
                    fontSize = 12.sp,
                    modifier = Modifier.padding(12.dp)
                )
            }
            Spacer(modifier = Modifier.height(12.dp))
        }

        // ── Simulation Controls ─────────────────────────────────────
        Row(
            modifier = Modifier
                .fillMaxWidth()
                .clip(RoundedCornerShape(12.dp))
                .background(DarkCard)
                .padding(12.dp),
            horizontalArrangement = Arrangement.SpaceBetween,
            verticalAlignment = Alignment.CenterVertically
        ) {
            Column {
                Text(
                    text = "Simulator",
                    fontSize = 14.sp,
                    fontWeight = FontWeight.SemiBold,
                    color = TextPrimary
                )
                Text(
                    text = if (simStatus.running) "Ticks: ${simStatus.tickCount}" else "Stopped",
                    fontSize = 11.sp,
                    color = TextMuted
                )
            }
            Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                FilledIconButton(
                    onClick = { viewModel.startSimulation() },
                    colors = IconButtonDefaults.filledIconButtonColors(
                        containerColor = AccentGreen.copy(alpha = 0.2f)
                    ),
                    modifier = Modifier.size(40.dp)
                ) {
                    Icon(
                        Icons.Default.PlayArrow,
                        contentDescription = "Start",
                        tint = AccentGreen
                    )
                }
                FilledIconButton(
                    onClick = { viewModel.stopSimulation() },
                    colors = IconButtonDefaults.filledIconButtonColors(
                        containerColor = AccentRed.copy(alpha = 0.2f)
                    ),
                    modifier = Modifier.size(40.dp)
                ) {
                    Icon(
                        Icons.Default.Stop,
                        contentDescription = "Stop",
                        tint = AccentRed
                    )
                }
            }
        }

        Spacer(modifier = Modifier.height(20.dp))

        // ── Loading ─────────────────────────────────────────────────
        if (isLoading) {
            CircularProgressIndicator(
                color = AccentCyan,
                modifier = Modifier.padding(32.dp)
            )
        } else {
            // ── Speed Gauge ─────────────────────────────────────────
            SpeedGauge(speed = telemetry.speed)

            Spacer(modifier = Modifier.height(20.dp))

            // ── Vehicle Info Bar ────────────────────────────────────
            Row(
                modifier = Modifier
                    .fillMaxWidth()
                    .clip(RoundedCornerShape(12.dp))
                    .background(DarkCard)
                    .padding(12.dp),
                horizontalArrangement = Arrangement.SpaceEvenly
            ) {
                InfoItem(label = "Odometer", value = "%.1f km".format(telemetry.odometer))
                InfoItem(label = "Engine", value = telemetry.engineStatus.uppercase())
                InfoItem(
                    label = "Time",
                    value = telemetry.timestamp.substringAfter("T").take(8)
                )
            }

            Spacer(modifier = Modifier.height(16.dp))

            // ── Battery ─────────────────────────────────────────────
            BatteryIndicator(
                soc = telemetry.battery.soc,
                voltage = telemetry.battery.voltage,
                temperature = telemetry.battery.temperature,
                healthStatus = telemetry.battery.healthStatus
            )

            Spacer(modifier = Modifier.height(16.dp))

            // ── EV Range ────────────────────────────────────────────
            if (telemetry.vehicleVariant != "ICE") {
                EVRangeCard(
                    evRange = telemetry.evStatus.evRange,
                    charging = telemetry.evStatus.charging,
                    regenBraking = telemetry.evStatus.regenBraking
                )

                Spacer(modifier = Modifier.height(16.dp))
            }

            // ── Throttle & Brake ────────────────────────────────────
            ThrottleBrakeBar(
                throttle = telemetry.drivetrain.throttlePosition,
                brake = telemetry.drivetrain.brakePosition
            )

            Spacer(modifier = Modifier.height(16.dp))

            // ── Drivetrain Panel (Gear, Steering, GPS) ──────────────
            DrivetrainPanel(
                gearPosition = telemetry.drivetrain.gearPosition,
                steeringAngle = telemetry.drivetrain.steeringAngle,
                latitude = telemetry.gps.latitude,
                longitude = telemetry.gps.longitude,
                vehicleVariant = telemetry.vehicleVariant
            )

            Spacer(modifier = Modifier.height(16.dp))

            // ── Tire Pressure Grid ──────────────────────────────────
            TirePressureGrid(
                frontLeft = telemetry.tires.frontLeft,
                frontRight = telemetry.tires.frontRight,
                rearLeft = telemetry.tires.rearLeft,
                rearRight = telemetry.tires.rearRight
            )

            Spacer(modifier = Modifier.height(24.dp))
        }
    }
}

@Composable
private fun InfoItem(label: String, value: String) {
    Column(horizontalAlignment = Alignment.CenterHorizontally) {
        Text(text = label, fontSize = 10.sp, color = TextMuted)
        Text(
            text = value,
            fontSize = 13.sp,
            fontWeight = FontWeight.Medium,
            color = TextSecondary
        )
    }
}
