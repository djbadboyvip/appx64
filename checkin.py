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
      print("[1/3] 正在访问登录页...")
      page.goto(f"{BASE_URL}/wp-login.php", timeout=60000, wait_until="networkidle")
      time.sleep(3)

      print(f"当前页面标题: {page.title()}")
      print(f"当前页面 URL: {page.url}")

      print("正在查找账号密码输入框并登录...")
      username_selector = "#user_login, input[name='log'], input[name='username']"
      password_selector = "#user_pass, input[name='pwd'], input[name='password']"

      page.wait_for_selector(username_selector, timeout=15000)
      page.fill(username_selector, USERNAME)
      page.fill(password_selector, PASSWORD)

      submit_selector = "#wp-submit, button[type='submit'], input[type='submit']"
      page.click(submit_selector)
      
      # 等待登录成功跳转
      time.sleep(6)

      print("[2/3] 正在访问资产/个人中心页执行签到...")
      page.goto(f"{BASE_URL}/vip?pd=money", timeout=60000, wait_until="networkidle")
      time.sleep(3)

      # 精准通过签到按钮的专属类名（.usercheck）来检查和点击
      try:
        sign_element = page.locator("a.usercheck")
        if sign_element.count() > 0:
          btn_text = sign_element.inner_text().strip()
          print(f"检测到签到元素，当前状态文字为: [{btn_text}]")
          
          # 如果还没签到（通常文字包含“签到”且没有“已”字，或者根据实际调整）
          if "已签到" not in btn_text:
            print("正在执行点击签到...")
            sign_element.click()
            time.sleep(4)
          else:
            print("今日已经完成签到，无需重复点击。")
        else:
          print("未找到 class 为 usercheck 的签到元素。")
      except Exception as ex:
        print(f"处理签到动作时提示: {ex}")

      # 再次刷新页面以获取最新的金币数据
      page.reload(wait_until="networkidle")
      time.sleep(3)
      html_content = page.content()

      print("[3/3] 正在提取资产数据...")
      # 匹配消费金币与剩余金币（自动忽略中间的 &nbsp; 或空格）
      spent_match = re.search(r"消费金币[：:]\s*(\d+)", html_content)
      left_match = re.search(r"剩余金币[：:]\s*(\d+)", html_content)

      spent_coins = spent_match.group(1) if spent_match else "未知"
      left_coins = left_match.group(1) if left_match else "未知"

      # 检查最终状态
      is_signed = "已签到" in html_content
      sign_status = "签到成功 / 今日已完成" if is_signed else "签到状态未知"

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
        page.screenshot(path="error_screenshot.png")
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
