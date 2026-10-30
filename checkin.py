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
  if TG_BOT_TOKEN and TG_CHAT_ID:
    try:
      tg_url = f"https://api.telegram.org/bot{TG_BOT_TOKEN}/sendMessage"
      payload = {
          "chat_id": TG_CHAT_ID,
          "text": f"*{title}*\n\n{content}",
          "parse_mode": "Markdown",
      }
      requests.post(tg_url, data=payload, timeout=10)
    except Exception as e:
      print(f"-> Telegram 推送异常: {e}")

  if WECHAT_API_URL:
    try:
      headers = (
          {"Authorization": f"Bearer {WECHAT_AUTH_TOKEN}"}
          if WECHAT_AUTH_TOKEN
          else {}
      )
      payload = {"title": title, "content": content}
      requests.post(WECHAT_API_URL, json=payload, headers=headers, timeout=10)
    except Exception as e:
      print(f"-> 微信推送异常: {e}")


def main():
  with sync_playwright() as p:
    browser = p.chromium.launch(
        headless=True,
        args=[
            "--disable-blink-features=AutomationControlled",
            "--no-sandbox",
            "--disable-setuid-sandbox",
            "--disable-infobars",
            "--window-size=1280,800",
        ],
    )
    context = browser.new_context(
        user_agent=(
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML,"
            " like Gecko) Chrome/122.0.0.0 Safari/537.36"
        ),
        viewport={"width": 1280, "height": 800},
    )
    page = context.new_page()

    try:
      print("[1/3] 正在访问后台登录页...")
      page.goto(f"{BASE_URL}/wp-login.php", timeout=60000, wait_until="networkidle")
      time.sleep(3)

      print(f"当前页面标题: {page.title()}")
      print(f"当前页面 URL: {page.url}")

      print("正在精准定位并填写账号密码...")
      # WordPress 默认后台专属 ID
      page.wait_for_selector("#user_login", timeout=15000)
      
      # 显式点击并填入账号密码
      page.click("#user_login")
      page.fill("#user_login", USERNAME)
      
      page.click("#user_pass")
      page.fill("#user_pass", PASSWORD)
      
      # 勾选“记住我”
      try:
        page.check("#rememberme")
      except:
        pass

      print("正在点击登录按钮...")
      # 点击登录，并等待页面跳转离开 wp-login.php
      with page.expect_navigation(timeout=30000):
        page.click("#wp-submit")

      print(f"登录跳转后的 URL: {page.url}")

      # 如果跳转后仍然包含 wp-login.php，说明登录被拒绝或账号密码未被接受
      if "wp-login.php" in page.url:
        page.screenshot(path="assets_page_debug.png", full_page=True)
        raise Exception("登录失败：提交后仍停留在登录页，请核对 Secrets 中的账号与密码是否正确。")

      print("[2/3] 正在进入 VIP 个人中心执行签到...")
      page.goto(f"{BASE_URL}/vip?pd=money", timeout=60000, wait_until="networkidle")
      time.sleep(5)  # 等待页面完全渲染

      # 📸 保存登录后的资产页截图
      page.screenshot(path="assets_page_debug.png", full_page=True)

      # 签到处理逻辑
      sign_status = "未知"
      try:
        # 定位右上角的签到按钮/状态标识 (a.usercheck)
        sign_btn = page.locator("a.usercheck").first
        if sign_btn.count() > 0:
          btn_text = sign_btn.inner_text().strip()
          print(f"检测到签到按钮文案: [{btn_text}]")

          if "已签到" in btn_text:
            print("今日已经完成签到。")
            sign_status = "今日已签到 (无需重复)"
          else:
            print("未签到，正在执行点击签到...")
            sign_btn.click()
            time.sleep(4)
            sign_status = "签到成功"
        else:
          if "已签到" in page.content():
            sign_status = "今日已签到"
          else:
            page.locator("text=签到").first.click()
            time.sleep(4)
            sign_status = "签到成功"
      except Exception as ex:
        print(f"签到步骤提示: {ex}")
        if "已签到" in page.content():
          sign_status = "今日已签到"
        else:
          sign_status = "签到状态未知"

      # 刷新页面以获取最新的金币资产
      page.reload(wait_until="networkidle")
      time.sleep(3)
      html_content = page.content()

      print("[3/3] 正在提取资产数据...")
      spent_match = re.search(r"消费金币[：:]\s*(\d+)", html_content)
      left_match = re.search(r"剩余金币[：:]\s*(\d+)", html_content)

      spent_coins = spent_match.group(1) if spent_match else "获取失败"
      left_coins = left_match.group(1) if left_match else "获取失败"

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
      try:
        page.screenshot(path="error_screenshot.png", full_page=True)
      except:
        pass
      error_msg = f"❌ 小兵下载站签到异常\n\n错误原因: {str(e)}"
      print(error_msg)
      send_notification("【异常】小兵下载站签到失败", error_msg)
      raise e
    finally:
      browser.close()


if __name__ == "__main__":
  main()
