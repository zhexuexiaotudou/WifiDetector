# H10e-31 安全发现

公开资料不足以确认 H10e-31 的管理页面、API 或选择器，因此项目不包含猜测实现。

```powershell
py -m app.cli discover --room 2301
```

命令会先验证目标 Windows Wi‑Fi profile、SSID、可选 BSSID、DHCP 和默认网关，然后打开全新的可见 Edge context。用户完成授权登录和页面导航后，工具仅保存页面标题、经过 MAC/秘密脱敏的可见文字摘录，以及去除查询字符串的 XHR/fetch 方法、路径、状态码和内容类型。

工具明确不保存请求或响应正文、Cookie、浏览器存储、输入框值、原始 HAR 和截图。若页面存在验证码或人工认证，保持人工流程，不尝试绕过。
