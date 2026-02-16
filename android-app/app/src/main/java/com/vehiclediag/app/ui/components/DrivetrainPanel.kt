package com.vehiclediag.app.ui.components

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.vehiclediag.app.ui.theme.*

/**
 * DrivetrainPanel — Compact 2×2 grid displaying gear, steering angle,
 * GPS coordinates, and vehicle variant.
 */
@Composable
fun DrivetrainPanel(
    gearPosition: String,
    steeringAngle: Double,
    latitude: Double,
    longitude: Double,
    vehicleVariant: String,
    modifier: Modifier = Modifier
) {
    Column(
        modifier = modifier
            .fillMaxWidth()
            .clip(RoundedCornerShape(12.dp))
            .background(DarkCard)
            .padding(16.dp)
    ) {
        Row(
            modifier = Modifier.fillMaxWidth(),
            horizontalArrangement = Arrangement.SpaceBetween,
            verticalAlignment = Alignment.CenterVertically
        ) {
            Text(
                text = "Vehicle Status",
                fontSize = 11.sp,
                fontWeight = FontWeight.SemiBold,
                color = TextMuted
            )
            // Vehicle variant badge
            Text(
                text = when (vehicleVariant) {
                    "EV" -> "⚡ EV"
                    "Hybrid" -> "🔄 HEV"
                    else -> "🔥 ICE"
                },
                fontSize = 10.sp,
                fontWeight = FontWeight.SemiBold,
                color = AccentCyan,
                modifier = Modifier
                    .clip(RoundedCornerShape(4.dp))
                    .background(AccentCyan.copy(alpha = 0.12f))
                    .padding(horizontal = 8.dp, vertical = 2.dp)
            )
        }

        Spacer(modifier = Modifier.height(12.dp))

        // 2×2 Grid
        Row(
            modifier = Modifier.fillMaxWidth(),
            horizontalArrangement = Arrangement.spacedBy(8.dp)
        ) {
            // Gear
            InfoCell(
                label = "Gear",
                value = gearPosition,
                valueSize = 28,
                valueColor = AccentCyan,
                modifier = Modifier.weight(1f)
            )

            // Steering
            InfoCell(
                label = "Steering",
                value = "%.0f°".format(steeringAngle),
                valueSize = 20,
                valueColor = TextPrimary,
                modifier = Modifier.weight(1f)
            )
        }

        Spacer(modifier = Modifier.height(8.dp))

        Row(
            modifier = Modifier.fillMaxWidth(),
            horizontalArrangement = Arrangement.spacedBy(8.dp)
        ) {
            // GPS Lat
            InfoCell(
                label = "Latitude",
                value = "%.5f".format(latitude),
                valueSize = 13,
                valueColor = AccentCyan,
                modifier = Modifier.weight(1f)
            )

            // GPS Lon
            InfoCell(
                label = "Longitude",
                value = "%.5f".format(longitude),
                valueSize = 13,
                valueColor = AccentCyan,
                modifier = Modifier.weight(1f)
            )
        }
    }
}

@Composable
private fun InfoCell(
    label: String,
    value: String,
    valueSize: Int,
    valueColor: androidx.compose.ui.graphics.Color,
    modifier: Modifier = Modifier
) {
    Column(
        horizontalAlignment = Alignment.CenterHorizontally,
        modifier = modifier
            .clip(RoundedCornerShape(8.dp))
            .background(DarkSurfaceVariant)
            .padding(vertical = 10.dp, horizontal = 8.dp)
    ) {
        Text(
            text = label,
            fontSize = 10.sp,
            color = TextMuted,
            textAlign = TextAlign.Center
        )
        Spacer(modifier = Modifier.height(4.dp))
        Text(
            text = value,
            fontSize = valueSize.sp,
            fontWeight = FontWeight.Bold,
            color = valueColor,
            textAlign = TextAlign.Center
        )
    }
}
