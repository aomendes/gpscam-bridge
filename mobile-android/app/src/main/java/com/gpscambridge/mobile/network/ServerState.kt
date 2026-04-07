package com.gpscambridge.mobile.network

data class ServerState(
    val isRunning: Boolean = false,
    val ip: String = "0.0.0.0",
    val port: Int = ServerConfig.DEFAULT_PORT,
    val serverId: String = "",
    val cameraState: String = "idle",
    val gpsState: String = "idle",
)
