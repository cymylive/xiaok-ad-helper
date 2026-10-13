package com.xiaok.adhelper

import android.app.Notification
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.PendingIntent
import android.app.Service
import android.content.Intent
import android.os.Build
import android.os.IBinder
import com.chaquo.python.Python
import com.chaquo.python.android.AndroidPlatform
import java.io.File

class ServerService : Service() {

    override fun onBind(intent: Intent?): IBinder? = null

    override fun onCreate() {
        super.onCreate()
        startForegroundNotice()
        Thread {
            if (!Python.isStarted()) {
                Python.start(AndroidPlatform(this))
            }
            // 把 app 私有可写目录传给 Python（存 presets）
            val filesDir = File(filesDir, "").absolutePath
            val py = Python.getInstance()
            py.getModule("main").callAttr("start_server", filesDir)
        }.start()
    }

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        return START_STICKY
    }

    private fun startForegroundNotice() {
        val channelId = "xiaok_scroll"
        val nm = getSystemService(NOTIFICATION_SERVICE) as NotificationManager
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            val ch = NotificationChannel(
                channelId, "投屏服务", NotificationManager.IMPORTANCE_LOW
            )
            ch.description = "文本投屏 HTTP 服务常驻通知"
            nm.createNotificationChannel(ch)
        }

        val intent = Intent(this, MainActivity::class.java)
        val pi = PendingIntent.getActivity(
            this, 0, intent,
            PendingIntent.FLAG_IMMUTABLE or PendingIntent.FLAG_UPDATE_CURRENT
        )

        val builder: Notification.Builder =
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O)
                Notification.Builder(this, channelId)
            else
                Notification.Builder(this)

        val notif = builder
            .setContentTitle("小K投屏")
            .setContentText("文本投屏服务运行中 · 点开查看连接地址")
            .setSmallIcon(android.R.drawable.ic_menu_upload)
            .setContentIntent(pi)
            .setOngoing(true)
            .build()

        startForeground(1, notif)
    }
}
