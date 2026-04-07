package com.gpscambridge.mobile

import android.Manifest
import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge
import androidx.activity.result.contract.ActivityResultContracts
import androidx.activity.viewModels
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import com.gpscambridge.mobile.ui.AppViewModel
import com.gpscambridge.mobile.ui.MainScreen

class MainActivity : ComponentActivity() {
    private val viewModel: AppViewModel by viewModels()

    private val permissionsLauncher =
        registerForActivityResult(ActivityResultContracts.RequestMultiplePermissions()) { result ->
            val hasLocation = result[Manifest.permission.ACCESS_FINE_LOCATION] == true ||
                result[Manifest.permission.ACCESS_COARSE_LOCATION] == true
            val hasCamera = result[Manifest.permission.CAMERA] == true
            if (hasLocation && hasCamera) {
                viewModel.onPermissionsReady()
            }
        }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        enableEdgeToEdge()

        permissionsLauncher.launch(
            arrayOf(
                Manifest.permission.CAMERA,
                Manifest.permission.ACCESS_FINE_LOCATION,
                Manifest.permission.ACCESS_COARSE_LOCATION,
            )
        )

        setContent {
            val state by viewModel.uiState.collectAsState()
            MainScreen(
                state = state,
                onStartClick = {
                    viewModel.startServer()
                    viewModel.onPermissionsReady()
                },
                onStopClick = {
                    viewModel.stopServer()
                }
            )
        }
    }
}
