# scrape_and_notify.py
import requests
from bs4 import BeautifulSoup
from datetime import datetime
import os
import json
import re
import urllib.parse
import subprocess
import gspread
from google.oauth2.service_account import Credentials

# ============================================================
# 環境変数から秘密情報を読み込む（GitHub Secretsから自動で入る）
# ============================================================
LINE_CHANNEL_ACCESS_TOKEN = os.environ["LINE_CHANNEL_ACCESS_TOKEN"]
GOOGLE_CREDENTIALS_JSON = os.environ["GOOGLE_CREDENTIALS"]

URL = "https://www.clover-estate.co.jp/"
NETLIFY_BASE_URL = "https://fastidious-biscochitos-991098.netlify.app"
GOOGLE_FORM_URL = "https://docs.google.com/forms/d/e/1FAIpQLSe1mfdDaB84CmATLQIHMc5-YRvF-tco7KqzvYl3W1Wxf_Sy7Q/viewform?usp=pp_url&entry.195312494="

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
                property_name = link_tag.get_text(strip=True) if link_tag else dd.get_text(strip=True)
                property_url = link_tag["href"] if link_tag else ""
                if property_url and not property_url.startswith("http"):
                    property_url = "https://www.clover-estate.co.jp" + property_url

                if not property_name or not property_url:
                    continue

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
# 4. 説明文から最寄駅・物件の特徴を抽出
# ----------------------------------------
def extract_station_and_feature(description):
    sentences = re.split(r'[！。\n]', description)
    sentences = [s.strip() for s in sentences if s.strip()]

    stations = [s for s in sentences if '駅' in s and '徒歩' in s]
    station_text = "・".join(stations) if stations else ""

    features = [s for s in sentences if '物件' in s]
    feature_text = features[-1] if features else ""

    return station_text, feature_text

# ----------------------------------------
# 5. 物件ページのHTMLを生成
# ----------------------------------------
def generate_property_html(prop, station_text, feature_text):
    safe_name = re.sub(r'[\\/:*?"<>|\'「」『』【】]', '', prop["name"])
    filename = f"property_{safe_name}.html"
    page_url = f"{NETLIFY_BASE_URL}/{filename}"
    form_url = GOOGLE_FORM_URL + urllib.parse.quote(prop["name"])

    image_tag = ""
    if prop["image_url"]:
        image_tag = f'<img class="property-image" src="{prop["image_url"]}" alt="{prop["name"]}" onerror="this.style.display=\'none\'">'
    else:
        image_tag = '<div class="property-image-placeholder">🏢</div>'

    station_html = ""
    if station_text:
        station_html = f'''
        <div class="station-info">
          <span class="station-icon">🚉</span>
          <span class="station-text">{station_text}</span>
        </div>'''

    feature_html = ""
    if feature_text:
        feature_html = f'<p class="feature-text">{feature_text}</p>'

    html = f'''<!DOCTYPE html>
<html lang="ja">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{prop["name"]} | クローバー不動産</title>
  <link href="https://fonts.googleapis.com/css2?family=Noto+Sans+JP:wght@400;500;700&family=Shippori+Mincho:wght@400;700&display=swap" rel="stylesheet">
  <style>
    :root {{
      --green: #2d6a4f;
      --green-light: #40916c;
      --green-pale: #d8f3dc;
      --gold: #b5883a;
      --white: #ffffff;
      --gray-bg: #f7f9f7;
      --gray-text: #555;
      --border: #d0e4d6;
    }}
    * {{ margin: 0; padding: 0; box-sizing: border-box; }}
    body {{ font-family: 'Noto Sans JP', sans-serif; background: var(--gray-bg); color: #333; }}
    header {{ background: var(--green); padding: 16px 24px; display: flex; align-items: center; justify-content: space-between; box-shadow: 0 2px 8px rgba(0,0,0,0.15); }}
    .logo {{ font-family: 'Shippori Mincho', serif; color: var(--white); font-size: 20px; letter-spacing: 0.1em; }}
    .logo span {{ color: #a8d5b5; font-size: 13px; display: block; letter-spacing: 0.2em; }}
    header .tel {{ color: #a8d5b5; font-size: 13px; text-align: right; }}
    header .tel strong {{ color: white; font-size: 18px; display: block; }}
    .hero {{ background: linear-gradient(135deg, var(--green) 0%, var(--green-light) 100%); padding: 32px 24px; text-align: center; }}
    .hero-badge {{ display: inline-block; background: var(--gold); color: white; font-size: 12px; font-weight: 700; letter-spacing: 0.15em; padding: 4px 14px; border-radius: 20px; margin-bottom: 12px; }}
    .hero h1 {{ font-family: 'Shippori Mincho', serif; color: white; font-size: 24px; font-weight: 700; line-height: 1.4; }}
    .container {{ max-width: 680px; margin: 0 auto; padding: 24px 16px 48px; }}
    .property-card {{ background: white; border-radius: 12px; overflow: hidden; box-shadow: 0 2px 16px rgba(45,106,79,0.1); margin-bottom: 24px; }}
    .property-image {{ width: 100%; height: 240px; object-fit: cover; display: block; }}
    .property-image-placeholder {{ width: 100%; height: 240px; background: var(--green-pale); display: flex; align-items: center; justify-content: center; font-size: 40px; }}
    .property-body {{ padding: 20px; }}
    .property-name {{ font-family: 'Shippori Mincho', serif; font-size: 22px; font-weight: 700; color: var(--green); margin-bottom: 16px; line-height: 1.4; }}
    .station-info {{ display: flex; align-items: flex-start; gap: 10px; background: var(--green-pale); border-radius: 8px; padding: 12px 14px; margin-bottom: 14px; }}
    .station-icon {{ font-size: 18px; flex-shrink: 0; }}
    .station-text {{ font-size: 13px; color: var(--green); line-height: 1.6; font-weight: 500; }}
    .feature-text {{ font-size: 13px; color: var(--gray-text); line-height: 1.8; border-left: 3px solid var(--green-light); padding-left: 12px; margin-bottom: 16px; }}
    .divider {{ border: none; border-top: 1px solid var(--border); margin: 16px 0; }}
    .original-link {{ display: flex; align-items: center; gap: 6px; font-size: 12px; color: var(--green-light); text-decoration: none; }}
    .original-link:hover {{ text-decoration: underline; }}
    .cta-section {{ background: white; border-radius: 12px; padding: 24px 20px; box-shadow: 0 2px 16px rgba(45,106,79,0.1); text-align: center; margin-bottom: 24px; }}
    .cta-title {{ font-family: 'Shippori Mincho', serif; font-size: 18px; color: var(--green); font-weight: 700; margin-bottom: 8px; }}
    .cta-sub {{ font-size: 12px; color: var(--gray-text); margin-bottom: 20px; line-height: 1.6; }}
    .btn-apply {{ display: block; width: 100%; background: linear-gradient(135deg, var(--green) 0%, var(--green-light) 100%); color: white; font-size: 16px; font-weight: 700; padding: 16px; border-radius: 50px; text-decoration: none; letter-spacing: 0.1em; box-shadow: 0 4px 14px rgba(45,106,79,0.35); margin-bottom: 12px; }}
    .btn-tel {{ display: block; width: 100%; background: white; color: var(--green); font-size: 15px; font-weight: 700; padding: 14px; border-radius: 50px; border: 2px solid var(--green); text-decoration: none; }}
    .form-section {{ background: white; border-radius: 12px; overflow: hidden; box-shadow: 0 2px 16px rgba(45,106,79,0.1); }}
    .form-title {{ font-family: 'Shippori Mincho', serif; font-size: 18px; color: var(--green); font-weight: 700; padding: 20px; border-bottom: 2px solid var(--green-pale); }}
    .form-iframe {{ width: 100%; height: 900px; border: none; display: block; }}
    footer {{ background: var(--green); color: rgba(255,255,255,0.7); text-align: center; padding: 20px; font-size: 12px; }}
    footer strong {{ color: white; display: block; font-size: 14px; margin-bottom: 4px; }}
  </style>
</head>
<body>
<header>
  <div class="logo">株式会社クローバー<span>CLOVER ESTATE</span></div>
  <div class="tel">お問い合わせ<strong>03-6721-0818</strong></div>
</header>
<div class="hero">
  <div class="hero-badge">🏠 新着物件のお知らせ</div>
  <h1>{prop["name"]}</h1>
</div>
<div class="container">
  <div class="property-card">
    {image_tag}
    <div class="property-body">
      <h2 class="property-name">{prop["name"]}</h2>
      {station_html}
      {feature_html}
      <hr class="divider">
      <a class="original-link" href="{prop["url"]}" target="_blank">🔗 クローバー公式サイトで詳細を見る</a>
    </div>
  </div>
  <div class="cta-section">
    <p class="cta-title">この物件が気になる方へ</p>
    <p class="cta-sub">下のボタンからお気軽にお問い合わせください。<br>専門スタッフが丁寧にご対応いたします。</p>
    <a class="btn-apply" href="#inquiry">📩 この物件に問い合わせる</a>
    <a class="btn-tel" href="tel:0367210818">📞 電話で問い合わせる</a>
  </div>
  <div class="form-section" id="inquiry">
    <p class="form-title">📋 お問い合わせフォーム</p>
    <iframe class="form-iframe" src="{form_url}"></iframe>
  </div>
</div>
<footer>
  <strong>株式会社クローバー</strong>
  東京都渋谷区神宮前４丁目１１-６　TEL: 03-6721-0818<br>
  営業時間：9:00〜22:00　定休日：水曜日
</footer>
</body>
</html>'''

    return filename, page_url, html

# ----------------------------------------
# 6. HTMLファイルをGitHubにコミット
# ----------------------------------------
def commit_html_to_github(filename, html_content):
    try:
        filepath = filename
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(html_content)

        subprocess.run(["git", "config", "user.email", "action@github.com"], check=True)
        subprocess.run(["git", "config", "user.name", "GitHub Actions"], check=True)
        subprocess.run(["git", "add", filepath], check=True)
        subprocess.run(["git", "commit", "-m", f"Add property page: {filename}"], check=True)
        subprocess.run(["git", "push"], check=True)
        print(f"  → GitHubにHTMLをコミット完了: {filename}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"  → GitHubコミット失敗: {e}")
        return False

# ----------------------------------------
# 7. LINEにメッセージを送信
# ----------------------------------------
def send_line_message(prop, page_url, station_text, feature_text):
    headers = {
        "Authorization": f"Bearer {LINE_CHANNEL_ACCESS_TOKEN}",
        "Content-Type": "application/json"
    }

    text = (
        f"🏠 新着物件のお知らせ\n"
        f"━━━━━━━━━━━━\n"
        f"🏢 {prop['name']}\n"
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

    if prop["image_url"]:
        messages.append({
            "type": "image",
            "originalContentUrl": prop["image_url"],
            "previewImageUrl": prop["image_url"]
        })

    broadcast_response = requests.post(
        "https://api.line.me/v2/bot/message/broadcast",
        headers=headers,
        json={"messages": messages}
    )

    return broadcast_response.status_code == 200

# ----------------------------------------
# 8. メイン処理
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

            station_text, feature_text = extract_station_and_feature(prop["description"])
            filename, page_url, html_content = generate_property_html(prop, station_text, feature_text)

            # HTMLをGitHubにコミット→Netlifyが自動公開
            commit_html_to_github(filename, html_content)

            # LINEに送信
            success = send_line_message(prop, page_url, station_text, feature_text)
            if success:
                save_sent_history(spreadsheet, prop["name"], prop["date"])
                new_count += 1
                print(f"  → LINE送信完了！")
                print(f"  → 物件ページURL: {page_url}")
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
