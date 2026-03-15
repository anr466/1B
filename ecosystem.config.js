module.exports = {
  apps: [
    {
      name: "trading-api",
      script: "start_server.py",
      interpreter: "python3",
      cwd: "/Users/anr/Desktop/trading_ai_bot-1",
      autorestart: true,
      max_restarts: 10,
      min_uptime: "20s",
      restart_delay: 5000,
      watch: false,
      env: {
        ENVIRONMENT: "production",
        SERVER_PORT: "3002"
      }
    },
    {
      name: "external-watchdog",
      script: "bin/telegram_external_watchdog.py",
      interpreter: "python3",
      cwd: "/Users/anr/Desktop/trading_ai_bot-1",
      autorestart: true,
      max_restarts: 50,
      min_uptime: "10s",
      restart_delay: 3000,
      watch: false,
      env: {
        WATCHDOG_HEALTH_URL: "http://127.0.0.1:3002/health",
        WATCHDOG_INTERVAL_SECONDS: "30",
        WATCHDOG_FAILURE_THRESHOLD: "3",
        WATCHDOG_RECOVERY_THRESHOLD: "1",
        WATCHDOG_ALERT_COOLDOWN_SECONDS: "300",
        WATCHDOG_REQUEST_TIMEOUT_SECONDS: "8"
      }
    }
  ]
};
