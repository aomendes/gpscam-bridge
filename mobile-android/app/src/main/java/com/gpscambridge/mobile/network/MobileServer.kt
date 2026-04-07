package com.gpscambridge.mobile.network

import android.content.Context
import com.gpscambridge.mobile.stream.CameraStreamer
import io.ktor.http.ContentDisposition
import io.ktor.http.ContentType
import io.ktor.http.HttpHeaders
import io.ktor.serialization.kotlinx.json.json
import io.ktor.server.application.Application
import io.ktor.server.application.call
import io.ktor.server.engine.ApplicationEngine
import io.ktor.server.engine.embeddedServer
import io.ktor.server.plugins.contentnegotiation.ContentNegotiation
import io.ktor.server.request.receive
import io.ktor.server.response.header
import io.ktor.server.response.respond
import io.ktor.server.response.respondBytes
import io.ktor.server.response.respondRedirect
import io.ktor.server.response.respondText
import io.ktor.server.routing.get
import io.ktor.server.routing.post
import io.ktor.server.routing.routing
import io.ktor.server.websocket.WebSockets
import io.ktor.server.websocket.webSocket
import io.ktor.websocket.Frame
import io.ktor.websocket.close
import io.ktor.websocket.readText
import io.ktor.server.cio.CIO
import kotlinx.coroutines.flow.SharedFlow
import kotlinx.coroutines.flow.collectLatest
import kotlinx.coroutines.launch
import kotlinx.serialization.encodeToString
import kotlinx.serialization.json.Json
import java.net.BindException

class MobileServer(
    private val context: Context,
    private val cameraStreamer: CameraStreamer,
    private val gpsFlow: SharedFlow<GpsPayload>,
    private val stateProvider: () -> ServerState,
) {
    private var engine: ApplicationEngine? = null
    private val serializerJson = Json { ignoreUnknownKeys = true }

    fun start(): Int {
        if (engine != null) {
            return stateProvider().port
        }

        for (port in ServerConfig.DEFAULT_PORT..ServerConfig.MAX_PORT) {
            try {
                val created = embeddedServer(CIO, host = ServerConfig.SERVER_HOST, port = port) {
                    configureServer(port)
                }
                created.start(wait = false)
                engine = created
                return port
            } catch (ex: Exception) {
                if (ex is BindException || ex.cause is BindException) {
                    continue
                }
                throw ex
            }
        }

        error("No available port in range ${ServerConfig.DEFAULT_PORT}-${ServerConfig.MAX_PORT}")
    }

    fun stop() {
        engine?.stop(gracePeriodMillis = 500, timeoutMillis = 1_000)
        engine = null
    }

    private fun Application.configureServer(boundPort: Int) {
        install(ContentNegotiation) {
            json()
        }
        install(WebSockets)

        routing {
            get("/") {
                val state = stateProvider().copy(port = boundPort)
                call.respondText(homePage(state), ContentType.Text.Html)
            }

            get("/download/windows") {
                val assetPath = ServerConfig.WINDOWS_ASSET_PATH
                val bytes = runCatching {
                    context.assets.open(assetPath).use { it.readBytes() }
                }.getOrNull()

                if (bytes == null) {
                    call.respondRedirect(ServerConfig.RELEASE_ASSET_URL, permanent = false)
                    return@get
                }

                call.response.header(
                    HttpHeaders.ContentDisposition,
                    ContentDisposition.Attachment.withParameter(ContentDisposition.Parameters.FileName, "GpsCamBridgeDesktop.exe").toString(),
                )
                call.respondBytes(bytes, ContentType.Application.OctetStream)
            }

            get("/api/status") {
                val state = stateProvider().copy(port = boundPort)
                call.respond(
                    StatusPayload(
                        app_version = ServerConfig.APP_VERSION,
                        server_id = state.serverId,
                        ip = state.ip,
                        port = state.port,
                        camera_state = state.cameraState,
                        gps_state = state.gpsState,
                    )
                )
            }

            get("/api/health") {
                call.respond(HealthPayload(ok = true, timestamp_ms = System.currentTimeMillis()))
            }

            post("/api/webrtc/offer") {
                val offer = call.receive<WebRtcOfferPayload>()
                call.respond(cameraStreamer.handleOffer(offer))
            }

            post("/api/webrtc/ice") {
                val candidate = call.receive<WebRtcIcePayload>()
                call.respond(cameraStreamer.handleIce(candidate))
            }

            webSocket("/api/gps") {
                val senderJob = launch {
                    gpsFlow.collectLatest { payload ->
                        send(Frame.Text(serializerJson.encodeToString(payload)))
                    }
                }

                try {
                    for (frame in incoming) {
                        if (frame is Frame.Text && frame.readText() == "ping") {
                            send(Frame.Text("pong"))
                        }
                    }
                } finally {
                    senderJob.cancel()
                    close()
                }
            }
        }
    }

    private fun homePage(state: ServerState): String {
        val base = "http://${state.ip}:${state.port}"
        return """
            <!doctype html>
            <html lang="en">
            <head>
              <meta charset="utf-8" />
              <meta name="viewport" content="width=device-width, initial-scale=1" />
              <title>GpsCam Bridge Installer</title>
              <style>
                body { font-family: Segoe UI, sans-serif; margin: 24px; background: #f4f7fb; color: #1a2433; }
                .card { background: #fff; border-radius: 12px; padding: 20px; box-shadow: 0 6px 20px rgba(19,39,67,0.12); max-width: 720px; }
                .btn { display: inline-block; margin: 8px 8px 0 0; padding: 10px 14px; border-radius: 8px; text-decoration: none; color: #fff; background: #1266f1; }
                .btn.secondary { background: #0f8f5f; }
                code { background: #eef2f7; padding: 3px 6px; border-radius: 4px; }
              </style>
            </head>
            <body>
              <div class="card">
                <h1>GpsCam Bridge</h1>
                <p>Server active at <code>$base</code></p>
                <p>Use this page on Windows to install the desktop companion.</p>
                <a class="btn" href="/download/windows">Download Windows .exe (local)</a>
                <a class="btn secondary" href="${ServerConfig.RELEASE_ASSET_URL}">Download from GitHub Release (.exe)</a>
                <p><a href="${ServerConfig.REPOSITORY_URL}">Repository</a></p>
                <p>After install, open the desktop app and connect to <code>${state.ip}:${state.port}</code>.</p>
              </div>
            </body>
            </html>
        """.trimIndent()
    }
}
