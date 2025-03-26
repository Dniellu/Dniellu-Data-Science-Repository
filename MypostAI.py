from playwright.sync_api import sync_playwright
import os
from dotenv import load_dotenv

# 讀取 .env 檔案
load_dotenv()
MOODLE_USERNAME = os.getenv("MOODLE_USERNAME")
MOODLE_PASSWORD = os.getenv("MOODLE_PASSWORD")

with sync_playwright() as p:
    browser = p.chromium.launch(headless=False)  # 顯示瀏覽器
    page = browser.new_page()

    print("啟動瀏覽器，開始登入 Moodle...")
    #HW3
    # 進入 Moodle 登入頁面
    page.goto("https://moodle3.ntnu.edu.tw/")
    page.wait_for_timeout(3000)

    # 使用 .env 讀取帳號密碼
    page.fill("#username", MOODLE_USERNAME)
    page.fill("#password", MOODLE_PASSWORD)

    # 按下登入按鈕
    page.locator('button:text("登入")').click()

    # 等待登入完成
    page.wait_for_timeout(5000)
    print("登入成功！")
    page.screenshot(path="debug_1_after_login.png")
    #HW3
    # 直接前往個人首頁
    page.goto("https://moodle3.ntnu.edu.tw/my/")
    page.wait_for_timeout(3000)
    print("進入個人首頁")
    page.screenshot(path="debug_2_after_profile.png")

    # 點擊「信箱郵件」按鈕（根據 Moodle UI 可能需要調整 selector）
    print("嘗試打開信箱...")
    page.locator('[aria-label="切換Moodle訊息選單"]').click()

    page.wait_for_timeout(3000)
    
    # 截圖確認信箱已開啟
    page.screenshot(path="debug_3_after_mailbox.png")
    print("信箱已開啟")

    # 點擊第一封信件（假設信件有標題 class "message"）
    print("點擊第一封信件...")
    page.locator(".message").first.click()
    page.wait_for_timeout(3000)

    # 截圖確認郵件內容
    page.screenshot(path="debug_4_after_email.png")
    print("信件內容已開啟")

    # 保持瀏覽器開啟，方便 Debug
    input("瀏覽器保持開啟，按 Enter 關閉...")

    # 關閉瀏覽器
    browser.close()
    print("瀏覽器已關閉")
