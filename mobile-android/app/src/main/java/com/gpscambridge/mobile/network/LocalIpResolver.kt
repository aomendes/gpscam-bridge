package com.gpscambridge.mobile.network

import java.net.Inet4Address
import java.net.NetworkInterface

object LocalIpResolver {
    fun resolve(): String {
        return runCatching {
            val interfaces = NetworkInterface.getNetworkInterfaces() ?: return@runCatching "127.0.0.1"
            while (interfaces.hasMoreElements()) {
                val iface = interfaces.nextElement()
                val addresses = iface.inetAddresses
                while (addresses.hasMoreElements()) {
                    val addr = addresses.nextElement()
                    if (addr is Inet4Address && !addr.isLoopbackAddress) {
                        return@runCatching addr.hostAddress ?: "127.0.0.1"
                    }
                }
            }
            "127.0.0.1"
        }.getOrDefault("127.0.0.1")
    }
}
