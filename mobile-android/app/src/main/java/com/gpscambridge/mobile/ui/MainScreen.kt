package com.gpscambridge.mobile.ui

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.navigationBarsPadding
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.statusBarsPadding
import androidx.compose.foundation.layout.widthIn
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.Button
import androidx.compose.material3.Card
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.unit.dp
import com.gpscambridge.mobile.network.ServerConfig

@Composable
fun MainScreen(
    state: AppUiState,
    onStartClick: () -> Unit,
    onStopClick: () -> Unit,
) {
    val serverUrl = "http://${state.ip}:${state.port}"
    Scaffold(
        containerColor = Color(0xFFF3F7FC),
        bottomBar = {
            Surface(shadowElevation = 4.dp) {
                Row(
                    modifier = Modifier
                        .fillMaxWidth()
                        .navigationBarsPadding()
                        .padding(horizontal = 16.dp, vertical = 12.dp),
                    horizontalArrangement = Arrangement.spacedBy(12.dp),
                ) {
                    Button(
                        onClick = onStartClick,
                        enabled = !state.running,
                        modifier = Modifier.weight(1f),
                    ) {
                        Text("Iniciar servidor")
                    }
                    Button(
                        onClick = onStopClick,
                        enabled = state.running,
                        modifier = Modifier.weight(1f),
                    ) {
                        Text("Parar servidor")
                    }
                }
            }
        },
    ) { innerPadding ->
        Column(
            modifier = Modifier
                .fillMaxSize()
                .padding(innerPadding)
                .statusBarsPadding()
                .padding(horizontal = 16.dp)
                .verticalScroll(rememberScrollState()),
            verticalArrangement = Arrangement.spacedBy(12.dp),
            horizontalAlignment = Alignment.CenterHorizontally,
        ) {
            Text(
                text = "GpsCam Bridge",
                style = MaterialTheme.typography.headlineMedium,
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(top = 6.dp),
            )

            Card(
                modifier = Modifier
                    .fillMaxWidth()
                    .widthIn(max = 700.dp),
                shape = RoundedCornerShape(16.dp),
            ) {
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

            Card(
                modifier = Modifier
                    .fillMaxWidth()
                    .widthIn(max = 700.dp),
                shape = RoundedCornerShape(16.dp),
            ) {
                Column(modifier = Modifier.padding(14.dp), verticalArrangement = Arrangement.spacedBy(6.dp)) {
                    Text("Instalacao no PC")
                    Text("No Windows, abra no navegador: $serverUrl")
                    Text("- Download local: /download/windows")
                    Text("- GitHub Releases: ${ServerConfig.RELEASES_URL}")
                    Text("- Repositorio: ${ServerConfig.REPOSITORY_URL}")
                }
            }
        }
    }
}
