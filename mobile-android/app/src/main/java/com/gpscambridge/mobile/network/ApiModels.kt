package com.gpscambridge.mobile.network

import kotlinx.serialization.Serializable

@Serializable
data class StatusPayload(
    val app_version: String,
    val server_id: String,
    val ip: String,
    val port: Int,
    val camera_state: String,
    val gps_state: String,
)

@Serializable
data class HealthPayload(
    val ok: Boolean,
    val timestamp_ms: Long,
)

@Serializable
data class GpsPayload(
    val latitude: Double,
    val longitude: Double,
    val accuracy_m: Double,
    val heading_deg: Double? = null,
    val speed_mps: Double? = null,
    val timestamp_ms: Long,
)

@Serializable
data class WebRtcOfferPayload(
    val type: String,
    val sdp: String,
)

@Serializable
data class WebRtcIcePayload(
    val sdpMid: String? = null,
    val sdpMLineIndex: Int? = null,
    val candidate: String,
)

@Serializable
data class WebRtcAckPayload(
    val ok: Boolean,
    val detail: String,
)
