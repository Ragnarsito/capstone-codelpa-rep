package com.simple.qrscanner

import android.util.Log
import okhttp3.*
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.RequestBody.Companion.toRequestBody
import org.json.JSONObject
import java.io.IOException
import java.util.concurrent.TimeUnit

class NetworkService {
    
    companion object {
        private const val TAG = "NetworkService"
        
        // Configurable server settings - inspired by spy repository's approach
        private const val SERVER_IP = "192.168.1.86"   // la IP que te muestra Flask en "Running on"
        private const val SERVER_PORT = "5000"
        private const val ENDPOINT = "scan"
        private const val BASE_URL = "http://$SERVER_IP:$SERVER_PORT"
        
        // Connection timeouts
        private const val CONNECT_TIMEOUT = 30L
        private const val READ_TIMEOUT = 30L
        private const val WRITE_TIMEOUT = 30L
    }
    
    private val httpClient = OkHttpClient.Builder()
        .connectTimeout(CONNECT_TIMEOUT, TimeUnit.SECONDS)
        .readTimeout(READ_TIMEOUT, TimeUnit.SECONDS)
        .writeTimeout(WRITE_TIMEOUT, TimeUnit.SECONDS)
        .retryOnConnectionFailure(true)
        .build()
    
    interface NetworkCallback {
        fun onSuccess(response: String)
        fun onError(error: String, errorCode: Int = -1)
    }
    
    /**
     * Send QR data to REP server
     * Inspired by spy repository's PostData class architecture
     */
    fun sendQRData(
        qrCode: String,
        userName: String,
        callback: NetworkCallback
    ) {
        Thread {
            try {
                val jsonPayload = createQRPayload(qrCode, userName)
                val request = buildRequest(jsonPayload)
                
                Log.d(TAG, "Sending QR data to server: $BASE_URL/$ENDPOINT")
                Log.d(TAG, "Payload: $jsonPayload")
                
                httpClient.newCall(request).execute().use { response ->
                    handleResponse(response, callback)
                }
                
            } catch (e: IOException) {
                Log.e(TAG, "Network error occurred", e)
                callback.onError("Network error: ${e.message}")
            } catch (e: Exception) {
                Log.e(TAG, "Unexpected error occurred", e)
                callback.onError("Unexpected error: ${e.message}")
            }
        }.start()
    }
    
    /**
     * Create JSON payload for QR data
     * Following REP server expected format
     */
    private fun createQRPayload(qrCode: String, userName: String): JSONObject {
        return JSONObject().apply {
            put("qr_code", qrCode)
            put("user_name", userName)
        }
    }
    
    /**
     * Build HTTP request with proper headers
     */
    private fun buildRequest(jsonPayload: JSONObject): Request {
        val mediaType = "application/json; charset=utf-8".toMediaType()
        val requestBody = jsonPayload.toString().toRequestBody(mediaType)
        
        return Request.Builder()
            .url("$BASE_URL/$ENDPOINT")
            .post(requestBody)
            .addHeader("Content-Type", "application/json")
            .addHeader("User-Agent", "QRScanner-Android/1.0")
            .addHeader("Accept", "application/json")
            .build()
    }
    
    /**
     * Handle server response with detailed error reporting
     * Inspired by spy repository's robust error handling
     */
    private fun handleResponse(response: Response, callback: NetworkCallback) {
        val responseCode = response.code
        val responseBody = response.body?.string() ?: ""
        
        Log.d(TAG, "Server response code: $responseCode")
        Log.d(TAG, "Server response body: $responseBody")
        
        when {
            response.isSuccessful -> {
                Log.i(TAG, "QR data successfully sent to server")
                callback.onSuccess(responseBody)
            }
            responseCode == 400 -> {
                Log.w(TAG, "Bad request - Invalid QR data format")
                callback.onError("Invalid QR data format", responseCode)
            }
            responseCode == 403 -> {
                Log.w(TAG, "QR not authorized - Only Desktop App generated QRs allowed")
                callback.onError("QR NO AUTORIZADO: Solo se permiten códigos QR generados por Desktop App", responseCode)
            }
            responseCode == 404 -> {
                Log.w(TAG, "Endpoint not found")
                callback.onError("Server endpoint not found", responseCode)
            }
            responseCode == 500 -> {
                Log.e(TAG, "Internal server error")
                callback.onError("Server internal error", responseCode)
            }
            responseCode in 500..599 -> {
                Log.e(TAG, "Server error: $responseCode")
                callback.onError("Server error occurred", responseCode)
            }
            else -> {
                Log.e(TAG, "Unexpected response code: $responseCode")
                callback.onError("Server returned error: $responseCode", responseCode)
            }
        }
    }
    
    /**
     * Test server connectivity
     * Useful for debugging network issues
     */
    fun testConnection(callback: NetworkCallback) {
        Thread {
            try {
                val request = Request.Builder()
                    .url(BASE_URL)
                    .head()
                    .build()
                
                Log.d(TAG, "Testing connection to: $BASE_URL")
                
                httpClient.newCall(request).execute().use { response ->
                    if (response.isSuccessful) {
                        Log.i(TAG, "Server connection successful")
                        callback.onSuccess("Connection OK")
                    } else {
                        Log.w(TAG, "Server responded with code: ${response.code}")
                        callback.onError("Server unavailable", response.code)
                    }
                }
                
            } catch (e: IOException) {
                Log.e(TAG, "Connection test failed", e)
                callback.onError("Cannot reach server: ${e.message}")
            } catch (e: Exception) {
                Log.e(TAG, "Connection test error", e)
                callback.onError("Connection test failed: ${e.message}")
            }
        }.start()
    }
    
    /**
     * Get server configuration info
     * Useful for debugging and configuration
     */
    fun getServerInfo(): String {
        return "Server: $BASE_URL/$ENDPOINT\n" +
                "Timeout: ${CONNECT_TIMEOUT}s\n" +
                "Retry: Enabled"
    }
}