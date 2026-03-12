# scrape_and_notify.py
import requests
from bs4 import BeautifulSoup
from datetime import datetime
import os
import json
import gspread
from google.oauth2.service_account import Credentials

# ============================================================
# 環境変数から秘密情報を読み込む（GitHub Secretsから自動で入る）
# ============================================================
LINE_CHANNEL_ACCESS_TOKEN = os.environ["LINE_CHANNEL_ACCESS_TOKEN"]
LINE_CHANNEL_ID = os.environ["LINE_CHANNEL_ID"]
GOOGLE_CREDENTIALS_JSON = os.environ["GOOGLE_CREDENTIALS"]

URL = "https://www.clover-estate.co.jp/"
HISTORY_FILE = "sent_properties.json"

# ----------------------------------------
# 1. サイトから最新物件を取得
# ----------------------------------------
def scrape_latest_properties():
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
    response = requests.get(URL, headers=headers, timeout=60)
    response.encoding = "utf-8"
    soup = BeautifulSoup(response.text, "html.parser")

    section_title = None
    for h2 in soup.find_all("h2"):
        if "本日の最新物件" in h2.get_text():
            section_title = h2
            break

    if not section_title:
        return []

    dl = section_title.find_next("dl")
    properties = []

    if dl:
        items = dl.find_all("dt")
        descriptions = dl.find_all("dd")

        for i, dt in enumerate(items):
            date = dt.get_text(strip=True)
            if i < len(descriptions):
                dd = descriptions[i]
                link_tag = dd.find("a")
                property_name = link_tag.get_text(strip=True) if link_tag else ""
                property_url = link_tag["href"] if link_tag else ""
                if property_url and not property_url.startswith("http"):
                    property_url = "https://www.clover-estate.co.jp" + property_url

                # 物件ページから画像URLを取得
                image_url = get_property_image(property_url)

                properties.append({
                    "date": date,
                    "name": property_name,
                    "url": property_url,
                    "image_url": image_url,
                    "description": dd.get_text(separator=" ", strip=True)
                })

    return properties

# ----------------------------------------
# 2. 物件ページから画像URLを取得
# ----------------------------------------
def get_property_image(property_url):
    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        res = requests.get(property_url, headers=headers, timeout=10)
        res.encoding = "utf-8"
        soup = BeautifulSoup(res.text, "html.parser")
        img = soup.find("img", {"src": lambda s: s and "img-asp.jp" in s})
        if img:
            return img["src"]
    except:
        pass
    return None

# ----------------------------------------
# 3. 送信済み物件の履歴をGoogleスプレッドシートで管理
# ----------------------------------------
def get_spreadsheet():
    creds_dict = json.loads(GOOGLE_CREDENTIALS_JSON)
    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ]
    creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
    client = gspread.authorize(creds)
    spreadsheet = client.open("clover-スクレイピング")
    return spreadsheet

def get_sent_history(spreadsheet):
    try:
        sheet = spreadsheet.worksheet("送信履歴")
    except:
        sheet = spreadsheet.add_worksheet(title="送信履歴", rows=1000, cols=3)
        sheet.append_row(["物件名", "日付", "送信日時"])
    records = sheet.get_all_records()
    return set(f"{r['物件名']}_{r['日付']}" for r in records)

def save_sent_history(spreadsheet, property_name, date):
    sheet = spreadsheet.worksheet("送信履歴")
    sheet.append_row([property_name, date, datetime.now().strftime("%Y/%m/%d %H:%M")])

# ----------------------------------------
# 4. LINEに画像つきメッセージを送信
# ----------------------------------------
def send_line_message(prop):
    headers = {
        "Authorization": f"Bearer {LINE_CHANNEL_ACCESS_TOKEN}",
        "Content-Type": "application/json"
    }

    # メッセージ内容を組み立て
    messages = []

    # 画像があれば画像メッセージを追加
    if prop["image_url"]:
        messages.append({
            "type": "image",
            "originalContentUrl": prop["image_url"],
            "previewImageUrl": prop["image_url"]
        })

    # テキストメッセージ
    text = (
        f"🏠 新着物件のお知らせ\n"
        f"━━━━━━━━━━━━\n"
        f"📅 {prop['date']}\n"
        f"🏢 {prop['name']}\n"
        f"━━━━━━━━━━━━\n"
        f"🔗 詳細はこちら\n{prop['url']}"
    )
    messages.append({"type": "text", "text": text})

    payload = {
        "to": LINE_CHANNEL_ID,
        "messages": messages
    }

    response = requests.post(
        "https://api.line.me/v2/bot/message/multicast",
        headers=headers,
        json={"to": [LINE_CHANNEL_ID], "messages": messages}
    )

    # 友だち全員への一斉送信
    broadcast_response = requests.post(
        "https://api.line.me/v2/bot/message/broadcast",
        headers=headers,
        json={"messages": messages}
    )

    return broadcast_response.status_code == 200

# ----------------------------------------
# 5. メイン処理
# ----------------------------------------
def main():
    print("サイトをチェック中...")
    properties = scrape_latest_properties()

    if not properties:
        print("物件情報が取得できませんでした。")
        return

    spreadsheet = get_spreadsheet()
    sent_history = get_sent_history(spreadsheet)

    new_count = 0
    for prop in properties:
        key = f"{prop['name']}_{prop['date']}"
        if key not in sent_history:
            print(f"新物件を検知: {prop['name']}")
            success = send_line_message(prop)
            if success:
                save_sent_history(spreadsheet, prop["name"], prop["date"])
                new_count += 1
                print(f"  → LINE送信完了！")
            else:
                print(f"  → LINE送信失敗")
        else:
            print(f"送信済みのためスキップ: {prop['name']}")

    if new_count == 0:
        print("新しい物件はありませんでした。")
    else:
        print(f"\n✅ 完了！{new_count}件の新物件をLINEで送信しました。")

if __name__ == "__main__":
    main()
