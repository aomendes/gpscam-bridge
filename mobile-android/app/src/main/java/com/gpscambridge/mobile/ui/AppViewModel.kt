package com.gpscambridge.mobile.ui

import android.app.Application
import androidx.lifecycle.LifecycleOwner
import androidx.lifecycle.AndroidViewModel
import androidx.lifecycle.viewModelScope
import com.gpscambridge.mobile.location.GpsPublisher
import com.gpscambridge.mobile.network.LocalIpResolver
import com.gpscambridge.mobile.network.MobileServer
import com.gpscambridge.mobile.network.ServerConfig
import com.gpscambridge.mobile.network.ServerState
import com.gpscambridge.mobile.stream.CameraStreamer
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import java.util.UUID

data class AppUiState(
    val running: Boolean = false,
    val serverId: String = "",
    val ip: String = "0.0.0.0",
    val port: Int = ServerConfig.DEFAULT_PORT,
    val cameraState: String = "idle",
    val gpsState: String = "idle",
    val lastGpsLine: String = "No GPS sample",
    val log: String = "Ready",
)

class AppViewModel(application: Application) : AndroidViewModel(application) {
    private val gpsPublisher = GpsPublisher(application.applicationContext)
    private val cameraStreamer = CameraStreamer(application.applicationContext)

    private val serverId = UUID.randomUUID().toString()

    private val _uiState = MutableStateFlow(
        AppUiState(
            serverId = serverId,
            ip = LocalIpResolver.resolve(),
        )
    )
    val uiState: StateFlow<AppUiState> = _uiState.asStateFlow()

    private val mobileServer = MobileServer(
        context = application.applicationContext,
        cameraStreamer = cameraStreamer,
        gpsFlow = gpsPublisher.gpsFlow,
        stateProvider = {
            val state = _uiState.value
            ServerState(
                isRunning = state.running,
                ip = state.ip,
                port = state.port,
                serverId = state.serverId,
                cameraState = state.cameraState,
                gpsState = state.gpsState,
            )
        },
    )

    init {
        viewModelScope.launch {
            gpsPublisher.state.collect { state ->
                _uiState.value = _uiState.value.copy(gpsState = state)
            }
        }

        viewModelScope.launch {
            gpsPublisher.gpsFlow.collect { payload ->
                _uiState.value = _uiState.value.copy(
                    lastGpsLine = "lat=%.6f lon=%.6f acc=%.1fm".format(
                        payload.latitude,
                        payload.longitude,
                        payload.accuracy_m,
                    )
                )
            }
        }

        viewModelScope.launch {
            cameraStreamer.state.collect { state ->
                _uiState.value = _uiState.value.copy(cameraState = state)
            }
        }
    }

    fun startServer(lifecycleOwner: LifecycleOwner) {
        val ip = LocalIpResolver.resolve()
        _uiState.value = _uiState.value.copy(ip = ip, log = "Starting local server...")

        runCatching {
            cameraStreamer.start(lifecycleOwner)
            val boundPort = mobileServer.start()
            _uiState.value = _uiState.value.copy(
                running = true,
                ip = ip,
                port = boundPort,
                log = "Server running at http://$ip:$boundPort",
            )
        }.onFailure { error ->
            _uiState.value = _uiState.value.copy(log = "Server start failed: ${error.message}")
        }
    }

    fun stopServer() {
        mobileServer.stop()
        cameraStreamer.stop()
        gpsPublisher.stop()
        _uiState.value = _uiState.value.copy(running = false, log = "Server stopped")
    }

    fun onPermissionsReady() {
        gpsPublisher.start()
    }

    override fun onCleared() {
        stopServer()
        super.onCleared()
    }
}
