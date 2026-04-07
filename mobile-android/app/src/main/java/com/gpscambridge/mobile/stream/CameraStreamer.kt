package com.gpscambridge.mobile.stream

import android.content.Context
import com.gpscambridge.mobile.network.WebRtcAckPayload
import com.gpscambridge.mobile.network.WebRtcIcePayload
import com.gpscambridge.mobile.network.WebRtcOfferPayload
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow

class CameraStreamer(context: Context) {
    @Suppress("unused")
    private val appContext = context.applicationContext

    private val _state = MutableStateFlow("idle")
    val state: StateFlow<String> = _state.asStateFlow()

    fun start() {
        _state.value = "ready"
    }

    fun stop() {
        _state.value = "idle"
    }

    suspend fun handleOffer(offer: WebRtcOfferPayload): WebRtcOfferPayload {
        _state.value = "signaling"
        // Scaffold: full peer connection setup can be plugged in without API changes.
        val sanitizedSdp = if (offer.sdp.isNotBlank()) offer.sdp else "v=0\r\n"
        return WebRtcOfferPayload(type = "answer", sdp = sanitizedSdp)
    }

    suspend fun handleIce(candidate: WebRtcIcePayload): WebRtcAckPayload {
        _state.value = "connecting"
        val detail = if (candidate.candidate.isBlank()) "empty_candidate" else "candidate_received"
        return WebRtcAckPayload(ok = true, detail = detail)
    }
}
