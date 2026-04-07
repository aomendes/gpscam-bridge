package com.gpscambridge.mobile.location

import android.Manifest
import android.annotation.SuppressLint
import android.content.Context
import android.content.pm.PackageManager
import android.location.Location
import android.os.Looper
import androidx.core.content.ContextCompat
import com.google.android.gms.location.FusedLocationProviderClient
import com.google.android.gms.location.LocationCallback
import com.google.android.gms.location.LocationRequest
import com.google.android.gms.location.LocationResult
import com.google.android.gms.location.LocationServices
import com.google.android.gms.location.Priority
import com.gpscambridge.mobile.network.GpsPayload
import kotlinx.coroutines.flow.MutableSharedFlow
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.SharedFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asSharedFlow
import kotlinx.coroutines.flow.asStateFlow

class GpsPublisher(context: Context) {
    private val appContext = context.applicationContext
    private val fusedClient: FusedLocationProviderClient =
        LocationServices.getFusedLocationProviderClient(appContext)

    private val _gpsFlow = MutableSharedFlow<GpsPayload>(replay = 1, extraBufferCapacity = 32)
    val gpsFlow: SharedFlow<GpsPayload> = _gpsFlow.asSharedFlow()

    private val _state = MutableStateFlow("idle")
    val state: StateFlow<String> = _state.asStateFlow()

    private val callback = object : LocationCallback() {
        override fun onLocationResult(result: LocationResult) {
            val location = result.lastLocation ?: return
            _state.value = "streaming"
            _gpsFlow.tryEmit(location.toPayload())
        }
    }

    fun hasPermissions(): Boolean {
        val fine = ContextCompat.checkSelfPermission(appContext, Manifest.permission.ACCESS_FINE_LOCATION)
        val coarse = ContextCompat.checkSelfPermission(appContext, Manifest.permission.ACCESS_COARSE_LOCATION)
        return fine == PackageManager.PERMISSION_GRANTED || coarse == PackageManager.PERMISSION_GRANTED
    }

    @SuppressLint("MissingPermission")
    fun start() {
        if (!hasPermissions()) {
            _state.value = "permission_required"
            return
        }

        val request =
            LocationRequest.Builder(Priority.PRIORITY_HIGH_ACCURACY, 1000L)
                .setMinUpdateIntervalMillis(500L)
                .build()

        _state.value = "starting"
        fusedClient.requestLocationUpdates(request, callback, Looper.getMainLooper())
    }

    fun stop() {
        fusedClient.removeLocationUpdates(callback)
        _state.value = "idle"
    }

    private fun Location.toPayload(): GpsPayload {
        return GpsPayload(
            latitude = latitude,
            longitude = longitude,
            accuracy_m = accuracy.toDouble(),
            heading_deg = if (hasBearing()) bearing.toDouble() else null,
            speed_mps = if (hasSpeed()) speed.toDouble() else null,
            timestamp_ms = time,
        )
    }
}
