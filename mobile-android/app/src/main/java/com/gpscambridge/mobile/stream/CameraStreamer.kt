package com.gpscambridge.mobile.stream

import android.annotation.SuppressLint
import android.content.Context
import android.graphics.ImageFormat
import android.graphics.Rect
import android.graphics.YuvImage
import androidx.camera.core.CameraSelector
import androidx.camera.core.ImageAnalysis
import androidx.camera.core.ImageProxy
import androidx.camera.lifecycle.ProcessCameraProvider
import androidx.core.content.ContextCompat
import androidx.lifecycle.Lifecycle
import androidx.lifecycle.LifecycleOwner
import androidx.lifecycle.LifecycleRegistry
import com.gpscambridge.mobile.network.WebRtcAckPayload
import com.gpscambridge.mobile.network.WebRtcIcePayload
import com.gpscambridge.mobile.network.WebRtcOfferPayload
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import java.io.ByteArrayOutputStream
import java.util.concurrent.ExecutorService
import java.util.concurrent.Executors
import java.util.concurrent.atomic.AtomicLong
import java.util.concurrent.atomic.AtomicReference

class CameraStreamer(context: Context) {
    private val appContext = context.applicationContext

    private val _state = MutableStateFlow("idle")
    val state: StateFlow<String> = _state.asStateFlow()

    private val latestJpeg = AtomicReference<ByteArray?>(null)
    private val latestTimestampMs = AtomicLong(0L)
    private var cameraExecutor: ExecutorService? = null
    private var cameraProvider: ProcessCameraProvider? = null
    private var isStarted = false

    private val lifecycleOwner = object : LifecycleOwner {
        private val registry = LifecycleRegistry(this)

        init {
            registry.currentState = Lifecycle.State.CREATED
        }

        override val lifecycle: Lifecycle
            get() = registry

        fun start() {
            registry.currentState = Lifecycle.State.STARTED
        }

        fun stop() {
            registry.currentState = Lifecycle.State.CREATED
        }
    }

    @SuppressLint("MissingPermission")
    fun start(owner: LifecycleOwner? = null) {
        if (isStarted) {
            return
        }
        isStarted = true
        _state.value = "starting"
        lifecycleOwner.start()
        if (cameraExecutor == null || cameraExecutor?.isShutdown == true) {
            cameraExecutor = Executors.newSingleThreadExecutor()
        }

        val future = ProcessCameraProvider.getInstance(appContext)
        future.addListener(
            {
                try {
                    val provider = future.get()
                    cameraProvider = provider
                    provider.unbindAll()

                    val analysis = ImageAnalysis.Builder()
                        .setBackpressureStrategy(ImageAnalysis.STRATEGY_KEEP_ONLY_LATEST)
                        .build()

                    analysis.setAnalyzer(cameraExecutor ?: return@addListener) { image ->
                        analyzeFrame(image)
                    }

                    provider.bindToLifecycle(
                        owner ?: lifecycleOwner,
                        CameraSelector.DEFAULT_BACK_CAMERA,
                        analysis,
                    )
                    _state.value = "ready"
                } catch (error: Exception) {
                    _state.value = "error:${error.message ?: "camera_bind_failed"}"
                    isStarted = false
                }
            },
            ContextCompat.getMainExecutor(appContext),
        )
    }

    fun stop() {
        isStarted = false
        runCatching { cameraProvider?.unbindAll() }
        cameraProvider = null
        lifecycleOwner.stop()
        cameraExecutor?.shutdownNow()
        cameraExecutor = null
        latestJpeg.set(null)
        latestTimestampMs.set(0L)
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

    fun latestFrameJpeg(): ByteArray? = latestJpeg.get()

    fun latestFrameTimestampMs(): Long = latestTimestampMs.get()

    private fun analyzeFrame(image: ImageProxy) {
        try {
            val jpeg = imageToJpeg(image) ?: return
            latestJpeg.set(jpeg)
            latestTimestampMs.set(System.currentTimeMillis())
            _state.value = "streaming"
        } finally {
            image.close()
        }
    }

    private fun imageToJpeg(image: ImageProxy): ByteArray? {
        val width = image.width
        val height = image.height
        if (width <= 0 || height <= 0) {
            return null
        }

        val nv21 = yuv420ToNv21(image)
        val yuvImage = YuvImage(nv21, ImageFormat.NV21, width, height, null)
        val output = ByteArrayOutputStream()
        val compressed = yuvImage.compressToJpeg(Rect(0, 0, width, height), 70, output)
        if (!compressed) {
            return null
        }
        return output.toByteArray()
    }

    private fun yuv420ToNv21(image: ImageProxy): ByteArray {
        val width = image.width
        val height = image.height
        val ySize = width * height
        val uvSize = width * height / 2
        val nv21 = ByteArray(ySize + uvSize)

        val yPlane = image.planes[0]
        val uPlane = image.planes[1]
        val vPlane = image.planes[2]

        var outputOffset = 0
        val yBuffer = yPlane.buffer
        for (row in 0 until height) {
            val rowOffset = row * yPlane.rowStride
            for (col in 0 until width) {
                val index = rowOffset + (col * yPlane.pixelStride)
                nv21[outputOffset++] = yBuffer.get(index)
            }
        }

        val chromaHeight = height / 2
        val chromaWidth = width / 2
        val uBuffer = uPlane.buffer
        val vBuffer = vPlane.buffer

        for (row in 0 until chromaHeight) {
            val uRowOffset = row * uPlane.rowStride
            val vRowOffset = row * vPlane.rowStride
            for (col in 0 until chromaWidth) {
                val uIndex = uRowOffset + (col * uPlane.pixelStride)
                val vIndex = vRowOffset + (col * vPlane.pixelStride)
                nv21[outputOffset++] = vBuffer.get(vIndex)
                nv21[outputOffset++] = uBuffer.get(uIndex)
            }
        }

        return nv21
    }
}
