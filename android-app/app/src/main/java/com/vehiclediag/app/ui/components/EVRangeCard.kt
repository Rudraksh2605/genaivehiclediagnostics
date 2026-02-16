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
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.vehiclediag.app.ui.theme.*

/**
 * EVRangeCard — Displays EV range, charging, and regen braking status.
 * Color changes dynamically when range is low.
 */
@Composable
fun EVRangeCard(
    evRange: Double,
    charging: Boolean,
    regenBraking: Boolean,
    modifier: Modifier = Modifier
) {
    val rangeColor = when {
        evRange < 30 -> AccentRed
        evRange < 80 -> AccentOrange
        else -> AccentGreen
    }

    Column(
        modifier = modifier
            .fillMaxWidth()
            .clip(RoundedCornerShape(12.dp))
            .background(DarkCard)
            .padding(16.dp),
        horizontalAlignment = Alignment.CenterHorizontally
    ) {
        Text(
            text = "EV Range",
            fontSize = 11.sp,
            fontWeight = FontWeight.SemiBold,
            color = TextMuted
        )

        Spacer(modifier = Modifier.height(8.dp))

        // Big range number
        Row(
            verticalAlignment = Alignment.Bottom
        ) {
            Text(
                text = "%.0f".format(evRange),
                fontSize = 42.sp,
                fontWeight = FontWeight.Bold,
                color = rangeColor
            )
            Text(
                text = " km",
                fontSize = 16.sp,
                color = TextSecondary,
                modifier = Modifier.padding(bottom = 6.dp)
            )
        }

        Spacer(modifier = Modifier.height(8.dp))

        // Status row
        Row(
            modifier = Modifier.fillMaxWidth(),
            horizontalArrangement = Arrangement.SpaceEvenly
        ) {
            StatusChip(
                label = if (charging) "⚡ Charging" else "🔋 Not Charging",
                isActive = charging
            )
            StatusChip(
                label = if (regenBraking) "♻️ Regen Active" else "♻️ Regen Off",
                isActive = regenBraking
            )
        }
    }
}

@Composable
private fun StatusChip(
    label: String,
    isActive: Boolean
) {
    Text(
        text = label,
        fontSize = 11.sp,
        fontWeight = if (isActive) FontWeight.SemiBold else FontWeight.Normal,
        color = if (isActive) AccentCyan else TextMuted,
        modifier = Modifier
            .clip(RoundedCornerShape(6.dp))
            .background(if (isActive) AccentCyan.copy(alpha = 0.12f) else DarkSurfaceVariant)
            .padding(horizontal = 10.dp, vertical = 4.dp)
    )
}
