# morning_notify.py
# 翌日9時に送信するスクリプト
import os
import json
import requests
import gspread
from google.oauth2.service_account import Credentials

LINE_CHANNEL_ACCESS_TOKEN = os.environ["LINE_CHANNEL_ACCESS_TOKEN"]
GOOGLE_CREDENTIALS_JSON = os.environ["GOOGLE_CREDENTIALS"]

def get_spreadsheet():
    creds_dict = json.loads(GOOGLE_CREDENTIALS_JSON)
    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ]
    creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
    client = gspread.authorize(creds)
    return client.open("clover-スクレイピング")

def send_line_message(prop_name, page_url, station_text, feature_text, image_url):
    headers = {
        "Authorization": f"Bearer {LINE_CHANNEL_ACCESS_TOKEN}",
        "Content-Type": "application/json"
    }

    text = (
        f"🏠 新着物件のお知らせ\n"
        f"━━━━━━━━━━━━\n"
        f"🏢 {prop_name}\n"
    )
    if station_text:
        text += f"🚉 {station_text}\n"
    if feature_text:
        text += f"✨ {feature_text}\n"
    text += (
        f"━━━━━━━━━━━━\n"
        f"🔗 詳細はこちら\n{page_url}"
    )

    messages = [{"type": "text", "text": text}]
    if image_url:
        messages.append({
            "type": "image",
            "originalContentUrl": image_url,
            "previewImageUrl": image_url
        })

    response = requests.post(
        "https://api.line.me/v2/bot/message/broadcast",
        headers=headers,
        json={"messages": messages}
    )
    return response.status_code == 200

def main():
    print("翌日送信待ちを確認中...")
    spreadsheet = get_spreadsheet()

    try:
        pending_sheet = spreadsheet.worksheet("翌日送信待ち")
    except:
        print("翌日送信待ちシートが見つかりません。")
        return

    records = pending_sheet.get_all_records()
    if not records:
        print("送信待ちの物件はありません。")
        return

    sent_history_sheet = spreadsheet.worksheet("送信履歴")

    for i, r in enumerate(records):
        prop_name = r.get("物件名", "")
        date = r.get("日付", "")
        page_url = r.get("ページURL", "")
        station_text = r.get("駅情報", "")
        feature_text = r.get("特徴", "")
        image_url = r.get("画像URL", "")

        if not prop_name or not page_url:
            continue

        print(f"送信中: {prop_name}")
        success = send_line_message(prop_name, page_url, station_text, feature_text, image_url)

        if success:
            # 送信履歴に保存
            from datetime import datetime
            sent_history_sheet.append_row([
                prop_name,
                date,
                datetime.now().strftime("%Y/%m/%d %H:%M")
            ])
            print(f"  → LINE送信完了！")
        else:
            print(f"  → LINE送信失敗")

    # 翌日送信待ちシートをクリア
    pending_sheet.clear()
    pending_sheet.append_row(["物件名", "日付", "ページURL", "駅情報", "特徴", "画像URL"])
    print("\n✅ 完了！翌日送信待ちシートをクリアしました。")

if __name__ == "__main__":
    main()
