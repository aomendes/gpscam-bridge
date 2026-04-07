package com.gpscambridge.mobile.ui

import android.graphics.Bitmap
import androidx.compose.foundation.Image
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.Button
import androidx.compose.material3.Card
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.remember
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.asImageBitmap
import androidx.compose.ui.unit.dp
import com.google.zxing.BarcodeFormat
import com.google.zxing.qrcode.QRCodeWriter
import com.gpscambridge.mobile.network.ServerConfig

@Composable
fun MainScreen(
    state: AppUiState,
    onStartClick: () -> Unit,
    onStopClick: () -> Unit,
) {
    val serverUrl = "http://${state.ip}:${state.port}"
    val qrBitmap = remember(serverUrl) { createQrBitmap(serverUrl) }

    Column(
        modifier = Modifier
            .fillMaxSize()
            .background(Color(0xFFF3F7FC))
            .padding(16.dp)
            .verticalScroll(rememberScrollState()),
        verticalArrangement = Arrangement.spacedBy(12.dp),
    ) {
        Text("GpsCam Bridge", style = MaterialTheme.typography.headlineMedium)
        Text("Server local para Windows baixar .exe e conectar camera + GPS")

        Card(modifier = Modifier.fillMaxWidth(), shape = RoundedCornerShape(16.dp)) {
            Column(modifier = Modifier.padding(14.dp), verticalArrangement = Arrangement.spacedBy(6.dp)) {
                Text("Servidor")
                Text("Status: ${if (state.running) "ONLINE" else "OFFLINE"}")
                Text("URL: $serverUrl")
                Text("Server ID: ${state.serverId}")
                Text("Camera: ${state.cameraState}")
                Text("GPS: ${state.gpsState}")
                Text("Ultimo GPS: ${state.lastGpsLine}")
                Text("Log: ${state.log}")
            }
        }

        Card(modifier = Modifier.fillMaxWidth(), shape = RoundedCornerShape(16.dp)) {
            Column(
                modifier = Modifier.fillMaxWidth().padding(14.dp),
                horizontalAlignment = Alignment.CenterHorizontally,
            ) {
                Text("QR para abrir no PC")
                Spacer(modifier = Modifier.height(8.dp))
                Image(bitmap = qrBitmap.asImageBitmap(), contentDescription = "Server QR", modifier = Modifier.size(220.dp))
            }
        }

        Card(modifier = Modifier.fillMaxWidth(), shape = RoundedCornerShape(16.dp)) {
            Column(modifier = Modifier.padding(14.dp), verticalArrangement = Arrangement.spacedBy(6.dp)) {
                Text("A pagina em $serverUrl contem:")
                Text("- Download local: /download/windows")
                Text("- GitHub Releases: ${ServerConfig.RELEASES_URL}")
                Text("- Repositorio: ${ServerConfig.REPOSITORY_URL}")
            }
        }

        Row(horizontalArrangement = Arrangement.spacedBy(12.dp)) {
            Button(onClick = onStartClick, enabled = !state.running) {
                Text("Iniciar servidor")
            }
            Button(onClick = onStopClick, enabled = state.running) {
                Text("Parar")
            }
        }
    }
}

private fun createQrBitmap(text: String, size: Int = 768): Bitmap {
    val bits = QRCodeWriter().encode(text, BarcodeFormat.QR_CODE, size, size)
    val bitmap = Bitmap.createBitmap(size, size, Bitmap.Config.RGB_565)
    for (x in 0 until size) {
        for (y in 0 until size) {
            bitmap.setPixel(x, y, if (bits[x, y]) android.graphics.Color.BLACK else android.graphics.Color.WHITE)
        }
    }
    return bitmap
}
