# appx64
### 🔑 GitHub 密钥 (Secrets) 配置步骤

请进入您的 GitHub 仓库，依次点击 **Settings** -> **Secrets and variables** -> **Actions**，然后点击 **New repository secret** 分别添加以下变量：

| Secret 名称 | 对应内容说明 |
| :--- | :--- |
| `APP_USERNAME` | 您的网站登录用户名或注册邮箱 |
| `APP_PASSWORD` | 您的网站登录密码 |
| `TG_BOT_TOKEN` | （可选）Telegram Bot Token |
| `TG_CHAT_ID` | （可选）Telegram 接收通知的 Chat ID |
| `WECHAT_API_URL` | （可选）微信推送 API 地址（例如 `https://wx.djcf.pp.ua/wxsend`） |
| `WECHAT_AUTH_TOKEN` | （可选）微信推送的 Bearer Token |

## 功能特点

智能签到处理：自动检查个人中心右上角状态，未签到时自动点击，已签到时安全跳过。

资产精准监控：自动抓取个人中心的“消费金币”与“剩余金币”数据并在通知中展示。

环境缓存优化：利用 actions/cache 对 Playwright 浏览器内核进行缓存，避免每次重复下载，极大提升运行速度。

完善的异常捕获：如遇登录失败或未知异常，会自动生成全屏错误截图并发送带直达日志链接的告警通知。
