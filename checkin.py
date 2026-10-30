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

  if WECHAT_API_URL:
    try:
      headers = (
          {"Authorization": f"Bearer {WECHAT_AUTH_TOKEN}"}
          if WECHAT_AUTH_TOKEN
          else {}
      )
      payload = {"title": title, "content": content}
      requests.post(WECHAT_API_URL, json=payload, headers=headers, timeout=10)
      print("-> 微信通知已发送")
    except Exception as e:
      print(f"-> 微信推送异常: {e}")


def main():
  with sync_playwright() as p:
    # 启动浏览器，增加反检测参数
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
      # 因为小兵下载站是 WordPress，直接访问 wp-login.php 更精准
      page.goto(f"{BASE_URL}/wp-login.php", timeout=60000, wait_until="networkidle")
      
      # 额外给 5 秒让 Cloudflare 验证自动通过
      time.sleep(5)

      # 【修改处 1】修复：page.title() 加上了括号，page.url 是属性不加括号
      print(f"当前页面标题: {page.title()}")
      print(f"当前页面 URL: {page.url}")

      # 截图保存，方便在 Artifacts 中查看
      page.screenshot(path="debug_login.png")

      print("正在查找账号密码输入框...")
      # 【修改处 2】适配 WordPress 后台的默认表单 id (user_login / user_pass)
      username_selector = "#user_login, input[name='log'], input[name='username']"
      password_selector = "#user_pass, input[name='pwd'], input[name='password']"

      page.wait_for_selector(username_selector, timeout=15000)

      page.fill(username_selector, USERNAME)
      page.fill(password_selector, PASSWORD)

      print("正在点击登录按钮...")
      # 【修改处 3】适配 WordPress 的登录按钮 id (wp-submit)
      submit_selector = "#wp-submit, button[type='submit'], input[type='submit']"
      page.click(submit_selector)
      
      # 等待登录后跳转
      time.sleep(5)

      print("[2/3] 正在访问资产/个人中心页执行签到...")
      page.goto(f"{BASE_URL}/vip?pd=money", timeout=60000, wait_until="networkidle")
      time.sleep(3)

      # 检查签到按钮
      content = page.content()
      if "已签到" not in content:
        print("检测到未签到，尝试寻找签到按钮...")
        try:
          page.click("text=签到", timeout=5000)
          time.sleep(3)
        except:
          print("未直接找到‘签到’文字按钮，可能已由其他逻辑触发。")

      # 刷新页面获取最新资产数据
      page.reload(wait_until="networkidle")
      time.sleep(3)
      html_content = page.content()

      print("[3/3] 正在提取资产数据...")
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
