package com.vehiclediag.app.viewmodel

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.vehiclediag.app.data.models.CodeGenRequest
import com.vehiclediag.app.data.models.CodeGenResponse
import com.vehiclediag.app.network.RetrofitClient
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch

/**
 * ViewModel for the Code Generator screen.
 * Manages code generation requests and responses.
 */
class CodeGenViewModel : ViewModel() {

    private val api = RetrofitClient.apiService

    // ── State ───────────────────────────────────────────────────────

    private val _requirement = MutableStateFlow("")
    val requirement: StateFlow<String> = _requirement.asStateFlow()

    private val _selectedLanguage = MutableStateFlow("python")
    val selectedLanguage: StateFlow<String> = _selectedLanguage.asStateFlow()

    private val _result = MutableStateFlow<CodeGenResponse?>(null)
    val result: StateFlow<CodeGenResponse?> = _result.asStateFlow()

    private val _isGenerating = MutableStateFlow(false)
    val isGenerating: StateFlow<Boolean> = _isGenerating.asStateFlow()

    private val _error = MutableStateFlow<String?>(null)
    val error: StateFlow<String?> = _error.asStateFlow()

    private val _languages = MutableStateFlow(
        listOf("python", "cpp", "kotlin", "rust")
    )
    val languages: StateFlow<List<String>> = _languages.asStateFlow()

    // ── Lifecycle ───────────────────────────────────────────────────

    init {
        fetchLanguages()
    }

    // ── Actions ─────────────────────────────────────────────────────

    fun setRequirement(text: String) {
        _requirement.value = text
    }

    fun setLanguage(language: String) {
        _selectedLanguage.value = language
    }

    fun generateCode() {
        val req = _requirement.value.trim()
        if (req.isEmpty()) {
            _error.value = "Enter a requirement first"
            return
        }

        _isGenerating.value = true
        _error.value = null

        viewModelScope.launch {
            try {
                val response = api.generateCode(
                    CodeGenRequest(
                        requirement = req,
                        language = _selectedLanguage.value
                    )
                )
                _result.value = response
            } catch (e: Exception) {
                _error.value = "Generation failed: ${e.localizedMessage}"
            } finally {
                _isGenerating.value = false
            }
        }
    }

    fun clearError() {
        _error.value = null
    }

    private fun fetchLanguages() {
        viewModelScope.launch {
            try {
                val resp = api.getLanguages()
                if (resp.languages.isNotEmpty()) {
                    _languages.value = resp.languages
                }
            } catch (_: Exception) {
                // Keep defaults
            }
        }
    }
}
