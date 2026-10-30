import os
import re
import time
from playwright.sync_api import sync_playwright
import requests

# ==================== 配置 (通过环境变量读取) ====================
USERNAME = os.getenv("APP_USERNAME")
PASSWORD = os.getenv("APP_PASSWORD")

TG_BOT_TOKEN = os.getenv("TG_BOT_TOKEN", "")
TG_CHAT_ID = os.getenv("TG_CHAT_ID", "")

WECHAT_API_URL = os.getenv("WECHAT_API_URL", "https://wx.djcf.pp.ua/wxsend")
WECHAT_AUTH_TOKEN = os.getenv("WECHAT_AUTH_TOKEN", "")
# ===============================================================

BASE_URL = "https://www.appx64.com"


def send_notification(title, content):
  """发送通知到 Telegram 和 自建微信 API"""
  # 1. 发送 Telegram 消息
  if TG_BOT_TOKEN and TG_CHAT_ID:
    try:
      tg_url = f"https://api.telegram.org/bot{TG_BOT_TOKEN}/sendMessage"
      payload = {
          "chat_id": TG_CHAT_ID,
          "text": f"*{title}*\n\n{content}",
          "parse_mode": "Markdown",
      }
      requests.post(tg_url, data=payload, timeout=10)
      print("-> Telegram 通知已发送")
    except Exception as e:
      print(f"-> Telegram 推送异常: {e}")

  # 2. 发送自建微信消息
  if WECHAT_API_URL:
    try:
      headers = {"Authorization": f"Bearer {WECHAT_AUTH_TOKEN}"} if WECHAT_AUTH_TOKEN else {}
      payload = {"title": title, "content": content}
      requests.post(WECHAT_API_URL, json=payload, headers=headers, timeout=10)
      print("-> 微信通知已发送")
    except Exception as e:
      print(f"-> 微信推送异常: {e}")


def main():
  with sync_playwright() as p:
    # 启动 Chromium 浏览器 (headless=True 在云端运行)
    browser = p.chromium.launch(
        headless=True,
        args=[
            "--disable-blink-features=AutomationControlled",
            "--no-sandbox",
            "--disable-setuid-sandbox",
        ],
    )
    context = browser.new_context(
        user_agent=(
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML,"
            " like Gecko) Chrome/120.0.0.0 Safari/537.36"
        ),
        viewport={"width": 1280, "height": 800},
    )
    page = context.new_page()

    try:
      print("[1/3] 正在访问登录页...")
      page.goto(f"{BASE_URL}/login", timeout=60000)
      time.sleep(3)  # 等待 Cloudflare 验证加载/通过

      # 检查是否需要手动输入或填写表单
      # 请根据实际网站的输入框选择器调整 (比如 input[name='username'] 等)
      print("正在输入账号密码...")
      page.fill("input[name='username']", USERNAME)
      page.fill("input[name='password']", PASSWORD)

      # 点击登录按钮
      page.click("button[type='submit']")
      time.sleep(5)  # 等待登录跳转

      print("[2/3] 正在访问资产/个人中心页执行签到...")
      page.goto(f"{BASE_URL}/vip?pd=money", timeout=60000)
      time.sleep(3)

      # 检查页面中是否有签到按钮并点击（如果未签到的话）
      # 从页面结构看，如果显示“已签到”说明完成了，否则寻找签到按钮
      content = page.content()
      if "已签到" not in content:
        print("检测到未签到，尝试寻找签到按钮...")
        # 尝试点击页面上的签到元素（根据实际网页调整选择器）
        try:
          page.click("text=签到", timeout=5000)
          time.sleep(3)
        except:
          print("未直接找到‘签到’文字按钮，可能已由其他逻辑触发或需手动确认。")

      # 刷新页面获取最新资产数据
      page.reload()
      time.sleep(3)
      html_content = page.content()

      print("[3/3] 正在提取资产数据...")
      # 使用正则匹配消费金币与剩余金币
      spent_match = re.search(r"消费金币[：:]\s*(\d+)", html_content)
      left_match = re.search(r"剩余金币[：:]\s*(\d+)", html_content)

      spent_coins = spent_match.group(1) if spent_match else "未知"
      left_coins = left_match.group(1) if left_match else "未知"

      is_signed = "已签到" in html_content
      sign_status = "签到成功 / 今日已完成" if is_signed else "状态未知/请检查"

      msg_title = "【小兵下载站】自动签到通知"
      msg_content = (
          f"状态: {sign_status}\n\n"
          f"• 消费金币: {spent_coins}\n"
          f"• 剩余金币: {left_coins}\n"
          f"• 执行平台: GitHub Actions"
      )

      print(msg_content)
      send_notification(msg_title, msg_content)

    except Exception as e:
      error_msg = f"❌ 小兵下载站签到异常\n\n错误原因: {str(e)}"
      print(error_msg)
      send_notification("【异常】小兵下载站签到失败", error_msg)
      raise e
    finally:
      browser.close()


if __name__ == "__main__":
  main()
