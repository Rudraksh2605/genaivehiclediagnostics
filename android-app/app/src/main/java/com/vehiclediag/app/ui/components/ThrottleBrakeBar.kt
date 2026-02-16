package com.vehiclediag.app.ui.components

import androidx.compose.animation.core.animateFloatAsState
import androidx.compose.animation.core.tween
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.vehiclediag.app.ui.theme.*

/**
 * ThrottleBrakeBar — Dual horizontal bars showing throttle and brake positions.
 * Throttle: green → cyan gradient, Brake: amber → red gradient.
 */
@Composable
fun ThrottleBrakeBar(
    throttle: Double,
    brake: Double,
    modifier: Modifier = Modifier
) {
    Column(
        modifier = modifier
            .fillMaxWidth()
            .clip(RoundedCornerShape(12.dp))
            .background(DarkCard)
            .padding(16.dp)
    ) {
        Text(
            text = "Drivetrain Controls",
            fontSize = 11.sp,
            fontWeight = FontWeight.SemiBold,
            color = TextMuted,
            modifier = Modifier.padding(bottom = 12.dp)
        )

        // Throttle bar
        ProgressBar(
            label = "Throttle",
            value = throttle,
            color = AccentGreen,
            modifier = Modifier.padding(bottom = 10.dp)
        )

        // Brake bar
        ProgressBar(
            label = "Brake",
            value = brake,
            color = AccentRed
        )
    }
}

@Composable
private fun ProgressBar(
    label: String,
    value: Double,
    color: androidx.compose.ui.graphics.Color,
    modifier: Modifier = Modifier
) {
    val animatedWidth by animateFloatAsState(
        targetValue = (value / 100.0).toFloat().coerceIn(0f, 1f),
        animationSpec = tween(400),
        label = "${label}_anim"
    )

    Column(modifier = modifier) {
        Row(
            modifier = Modifier.fillMaxWidth(),
            horizontalArrangement = Arrangement.SpaceBetween
        ) {
            Text(
                text = label,
                fontSize = 12.sp,
                color = TextSecondary
            )
            Text(
                text = "%.0f%%".format(value),
                fontSize = 12.sp,
                fontWeight = FontWeight.SemiBold,
                color = TextPrimary
            )
        }

        Spacer(modifier = Modifier.height(4.dp))

        Box(
            modifier = Modifier
                .fillMaxWidth()
                .height(8.dp)
                .clip(RoundedCornerShape(4.dp))
                .background(DarkSurfaceVariant)
        ) {
            Box(
                modifier = Modifier
                    .fillMaxHeight()
                    .fillMaxWidth(animatedWidth)
                    .clip(RoundedCornerShape(4.dp))
                    .background(color)
            )
        }
    }
}
