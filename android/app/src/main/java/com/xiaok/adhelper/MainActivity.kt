package com.xiaok.adhelper

import android.annotation.SuppressLint
import android.content.Intent
import android.os.Build
import android.os.Bundle
import android.util.Log
import android.view.WindowManager
import android.webkit.JavascriptInterface
import android.webkit.WebView
import android.webkit.WebViewClient
import android.widget.Toast
import androidx.appcompat.app.AppCompatActivity
import java.io.File
import java.io.PrintWriter
import java.io.StringWriter
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale

class MainActivity : AppCompatActivity() {

    private lateinit var webView: WebView
    private var keepOn = true

    /** 暴露给网页 JS 的桥接：控制屏幕常亮 */
    inner class Bridge {
        @JavascriptInterface
        fun setKeepScreenOn(on: Boolean) {
            keepOn = on
            runOnUiThread { applyKeepScreenOn(on) }
        }

        @JavascriptInterface
        fun getKeepScreenOn(): Boolean = keepOn
    }

    private fun applyKeepScreenOn(on: Boolean) {
        if (on) {
            window.addFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON)
        } else {
            window.clearFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON)
        }
    }

    @SuppressLint("SetJavaScriptEnabled", "AddJavascriptInterface")
    override fun onCreate(savedInstanceState: Bundle?) {
        installCrashHandler()
        super.onCreate(savedInstanceState)

        // 默认屏幕常亮：防止 1 分钟自动息屏（用户按电源键仍可主动息屏）
        applyKeepScreenOn(true)

        webView = WebView(this)
        webView.settings.javaScriptEnabled = true
        webView.settings.domStorageEnabled = true
        webView.settings.loadWithOverviewMode = true
        webView.settings.useWideViewPort = true
        webView.webViewClient = WebViewClient()
        webView.addJavascriptInterface(Bridge(), "AndroidBridge")
        setContentView(webView)

        try {
            val intent = Intent(this, ServerService::class.java)
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
                startForegroundService(intent)
            } else {
                startService(intent)
            }
        } catch (e: Throwable) {
            Log.e("XiaokAd", "启动服务失败", e)
            Toast.makeText(this, "服务启动失败: " + e.message, Toast.LENGTH_LONG).show()
        }

        webView.postDelayed({
            webView.loadUrl("http://127.0.0.1:8080/m")
        }, 1800)
    }

    private fun installCrashHandler() {
        val prev = Thread.getDefaultUncaughtExceptionHandler()
        Thread.setDefaultUncaughtExceptionHandler { t, e ->
            try {
                val sw = StringWriter()
                e.printStackTrace(PrintWriter(sw))
                val ts = SimpleDateFormat("yyyy-MM-dd HH:mm:ss", Locale.US).format(Date())
                val logFile = File(filesDir, "crash.log")
                logFile.appendText("\n[$ts] thread=" + t.name + "\n" + sw.toString() + "\n")
                Log.e("XiaokAd", "崩溃: " + sw.toString())
            } catch (_: Throwable) {
            }
            prev?.uncaughtException(t, e)
        }
    }

    override fun onDestroy() {
        if (this::webView.isInitialized) {
            webView.destroy()
        }
        super.onDestroy()
    }
}
