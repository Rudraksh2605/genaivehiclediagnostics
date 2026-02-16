package com.vehiclediag.app.ui.screens

import androidx.compose.foundation.background
import androidx.compose.foundation.horizontalScroll
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.*
import androidx.compose.runtime.Composable
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.lifecycle.viewmodel.compose.viewModel
import com.vehiclediag.app.ui.theme.*
import com.vehiclediag.app.viewmodel.CodeGenViewModel

/**
 * Code Generator Screen — Input a natural-language requirement,
 * select a language, and view AI-generated service code.
 */
@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun CodeGeneratorScreen(
    viewModel: CodeGenViewModel = viewModel()
) {
    val requirement by viewModel.requirement.collectAsState()
    val selectedLanguage by viewModel.selectedLanguage.collectAsState()
    val result by viewModel.result.collectAsState()
    val isGenerating by viewModel.isGenerating.collectAsState()
    val error by viewModel.error.collectAsState()
    val languages by viewModel.languages.collectAsState()

    Column(
        modifier = Modifier
            .fillMaxSize()
            .background(DarkBackground)
            .verticalScroll(rememberScrollState())
            .padding(16.dp)
    ) {
        // ── Header ──────────────────────────────────────────────────
        Text(
            text = "🤖 GenAI Code Generator",
            style = MaterialTheme.typography.headlineSmall,
            fontWeight = FontWeight.Bold,
            color = TextPrimary
        )

        Spacer(modifier = Modifier.height(4.dp))

        Text(
            text = "Enter a vehicle diagnostics requirement to generate service code.",
            fontSize = 12.sp,
            color = TextMuted
        )

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

        // ── Requirement Input ───────────────────────────────────────
        Column(
            modifier = Modifier
                .fillMaxWidth()
                .clip(RoundedCornerShape(12.dp))
                .background(DarkCard)
                .padding(16.dp)
        ) {
            Text(
                text = "Requirement",
                fontSize = 11.sp,
                fontWeight = FontWeight.SemiBold,
                color = TextMuted,
                modifier = Modifier.padding(bottom = 8.dp)
            )

            OutlinedTextField(
                value = requirement,
                onValueChange = { viewModel.setRequirement(it) },
                placeholder = {
                    Text(
                        text = "e.g. Monitor speed, battery SoC, and tire pressure with alerts",
                        color = TextMuted,
                        fontSize = 13.sp
                    )
                },
                modifier = Modifier
                    .fillMaxWidth()
                    .heightIn(min = 80.dp),
                colors = OutlinedTextFieldDefaults.colors(
                    focusedBorderColor = AccentCyan,
                    unfocusedBorderColor = DarkSurfaceVariant,
                    focusedContainerColor = DarkSurface,
                    unfocusedContainerColor = DarkSurface,
                    focusedTextColor = TextPrimary,
                    unfocusedTextColor = TextPrimary,
                    cursorColor = AccentCyan
                ),
                shape = RoundedCornerShape(8.dp)
            )

            Spacer(modifier = Modifier.height(12.dp))

            // ── Language Selector ───────────────────────────────────
            Text(
                text = "Target Language",
                fontSize = 11.sp,
                fontWeight = FontWeight.SemiBold,
                color = TextMuted,
                modifier = Modifier.padding(bottom = 8.dp)
            )

            Row(
                horizontalArrangement = Arrangement.spacedBy(8.dp),
                modifier = Modifier.horizontalScroll(rememberScrollState())
            ) {
                languages.forEach { lang ->
                    val isSelected = lang == selectedLanguage
                    val displayName = when (lang) {
                        "python" -> "Python"
                        "cpp" -> "C++"
                        "kotlin" -> "Kotlin"
                        "rust" -> "Rust"
                        else -> lang
                    }

                    FilterChip(
                        selected = isSelected,
                        onClick = { viewModel.setLanguage(lang) },
                        label = {
                            Text(
                                text = displayName,
                                fontSize = 12.sp,
                                fontWeight = if (isSelected) FontWeight.Bold else FontWeight.Normal
                            )
                        },
                        colors = FilterChipDefaults.filterChipColors(
                            selectedContainerColor = AccentCyan.copy(alpha = 0.2f),
                            selectedLabelColor = AccentCyan,
                            containerColor = DarkSurfaceVariant,
                            labelColor = TextSecondary
                        )
                    )
                }
            }

            Spacer(modifier = Modifier.height(16.dp))

            // ── Generate Button ─────────────────────────────────────
            Button(
                onClick = { viewModel.generateCode() },
                enabled = !isGenerating,
                modifier = Modifier.fillMaxWidth(),
                colors = ButtonDefaults.buttonColors(
                    containerColor = AccentCyan,
                    contentColor = DarkBackground,
                    disabledContainerColor = AccentCyan.copy(alpha = 0.3f)
                ),
                shape = RoundedCornerShape(8.dp)
            ) {
                if (isGenerating) {
                    CircularProgressIndicator(
                        modifier = Modifier.size(18.dp),
                        color = DarkBackground,
                        strokeWidth = 2.dp
                    )
                    Spacer(modifier = Modifier.width(8.dp))
                    Text("Generating…")
                } else {
                    Text(
                        "⚡ Generate Code",
                        fontWeight = FontWeight.Bold
                    )
                }
            }
        }

        Spacer(modifier = Modifier.height(16.dp))

        // ── Generated Code Output ───────────────────────────────────
        result?.let { response ->
            Column(
                modifier = Modifier
                    .fillMaxWidth()
                    .clip(RoundedCornerShape(12.dp))
                    .background(DarkCard)
                    .padding(16.dp)
            ) {
                // Header
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.SpaceBetween,
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    Text(
                        text = "Generated: ${response.generatedCode.languageName}",
                        fontSize = 13.sp,
                        fontWeight = FontWeight.SemiBold,
                        color = TextPrimary
                    )
                    Text(
                        text = "${response.generatedCode.linesOfCode} lines",
                        fontSize = 11.sp,
                        color = AccentCyan,
                        modifier = Modifier
                            .clip(RoundedCornerShape(4.dp))
                            .background(AccentCyan.copy(alpha = 0.12f))
                            .padding(horizontal = 8.dp, vertical = 2.dp)
                    )
                }

                // Metadata
                Text(
                    text = "${response.generatedCode.generationMethod} · ${response.generatedCode.generationTimeMs}ms",
                    fontSize = 10.sp,
                    color = TextMuted,
                    modifier = Modifier.padding(top = 4.dp, bottom = 4.dp)
                )

                // Detected signals
                if (response.signalsDetected.isNotEmpty()) {
                    Text(
                        text = "Signals: ${response.signalsDetected.joinToString(", ")}",
                        fontSize = 10.sp,
                        color = TextSecondary,
                        modifier = Modifier.padding(bottom = 8.dp)
                    )
                }

                // Code block
                Box(
                    modifier = Modifier
                        .fillMaxWidth()
                        .heightIn(max = 400.dp)
                        .clip(RoundedCornerShape(8.dp))
                        .background(DarkSurface)
                        .verticalScroll(rememberScrollState())
                        .horizontalScroll(rememberScrollState())
                        .padding(12.dp)
                ) {
                    Text(
                        text = response.generatedCode.code,
                        fontSize = 11.sp,
                        fontFamily = FontFamily.Monospace,
                        color = AccentCyan,
                        lineHeight = 18.sp
                    )
                }
            }
        }

        Spacer(modifier = Modifier.height(24.dp))
    }
}
