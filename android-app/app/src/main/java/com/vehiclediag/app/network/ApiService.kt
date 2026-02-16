package com.vehiclediag.app.network

import com.vehiclediag.app.data.models.*
import retrofit2.http.Body
import retrofit2.http.GET
import retrofit2.http.POST
import retrofit2.http.Query

/**
 * Retrofit API service interface for the Vehicle Diagnostics backend.
 */
interface ApiService {

    // ── Vehicle Telemetry ───────────────────────────────────────────

    @GET("vehicle/speed")
    suspend fun getSpeed(): SpeedResponse

    @GET("vehicle/battery")
    suspend fun getBattery(): BatteryHealth

    @GET("vehicle/tire-pressure")
    suspend fun getTirePressure(): TireStatus

    @GET("vehicle/all")
    suspend fun getAllTelemetry(): VehicleTelemetry

    @GET("vehicle/alerts")
    suspend fun getAlerts(@Query("limit") limit: Int = 50): List<AlertModel>

    // ── Simulation Control ──────────────────────────────────────────

    @POST("vehicle/simulate/start")
    suspend fun startSimulation(): SimulationStatus

    @POST("vehicle/simulate/stop")
    suspend fun stopSimulation(): SimulationStatus

    @GET("vehicle/simulate/status")
    suspend fun getSimulationStatus(): SimulationStatus

    // ── Configuration ───────────────────────────────────────────────

    @GET("config/signals")
    suspend fun getSignalConfig(): SignalConfigResponse

    // ── Code Generation ─────────────────────────────────────────────

    @POST("codegen/generate")
    suspend fun generateCode(@Body request: CodeGenRequest): CodeGenResponse

    @GET("codegen/languages")
    suspend fun getLanguages(): LanguagesResponse
}
