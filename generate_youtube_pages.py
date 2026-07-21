"""
YouTube物件一覧ページ生成スクリプト
====================================
youtube_properties.csvを読み込んで
- youtube_index.html（物件一覧）
- youtube_property_〇〇.html（各物件詳細）
を生成してGitHubにコミットします。
"""

import csv
import os
import re
import subprocess
import urllib.parse

NETLIFY_BASE_URL = "https://officialyunox07-hub.github.io/clover-scraping"
GOOGLE_FORM_URL = "https://docs.google.com/forms/d/e/1FAIpQLSfNblUPGNXTNBISb3reb4QjEA5dgFLONxZIkRZVvW6-PAN78w/viewform?usp=pp_url&entry.195312494="
CSV_FILE = "youtube_properties.csv"

# ----------------------------------------
# 1. 動画IDを取得
# ----------------------------------------
def get_video_id(url):
    match = re.search(r'(?:v=|youtu\.be/)([a-zA-Z0-9_-]{11})', url)
    return match.group(1) if match else None

# ----------------------------------------
# 2. サムネイルURLを取得
# ----------------------------------------
def get_thumbnail_url(video_id):
    return f"https://img.youtube.com/vi/{video_id}/maxresdefault.jpg"

# ----------------------------------------
# 3. 各物件の詳細ページを生成
# ----------------------------------------
def generate_youtube_property_html(property_name, video_url, video_id):
    safe_name = re.sub(r'[\\/:*?"<>|\'「」『』【】]', '', property_name)
    filename = f"youtube_property_{safe_name}.html"
    page_url = f"{NETLIFY_BASE_URL}/{filename}"
    thumbnail_url = get_thumbnail_url(video_id)
    form_url = GOOGLE_FORM_URL + urllib.parse.quote(property_name)

    html = f'''<!DOCTYPE html>
<html lang="ja">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{property_name} | 理想のおうち案内所</title>
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
    header {{ background: var(--green); padding: 16px 24px; text-align: center; box-shadow: 0 2px 8px rgba(0,0,0,0.15); }}
    .logo {{ font-family: 'Shippori Mincho', serif; color: white; font-size: 20px; letter-spacing: 0.1em; }}
    .logo span {{ color: #a8d5b5; font-size: 13px; display: block; letter-spacing: 0.2em; }}
    .hero {{ background: linear-gradient(135deg, var(--green) 0%, var(--green-light) 100%); padding: 28px 24px; text-align: center; }}
    .hero-badge {{ display: inline-block; background: var(--gold); color: white; font-size: 12px; font-weight: 700; letter-spacing: 0.15em; padding: 4px 14px; border-radius: 20px; margin-bottom: 12px; }}
    .hero h1 {{ font-family: 'Shippori Mincho', serif; color: white; font-size: 24px; font-weight: 700; line-height: 1.4; }}
    .container {{ max-width: 680px; margin: 0 auto; padding: 24px 16px 48px; }}
    .property-card {{ background: white; border-radius: 12px; overflow: hidden; box-shadow: 0 2px 16px rgba(45,106,79,0.1); margin-bottom: 24px; }}
    .thumbnail {{ width: 100%; display: block; cursor: pointer; position: relative; }}
    .thumbnail img {{ width: 100%; height: 240px; object-fit: contain; background: #000; display: block; }}
    .play-btn {{ position: absolute; top: 50%; left: 50%; transform: translate(-50%, -50%); width: 64px; height: 64px; background: rgba(255,0,0,0.85); border-radius: 50%; display: flex; align-items: center; justify-content: center; }}
    .play-btn::after {{ content: ''; border-left: 24px solid white; border-top: 14px solid transparent; border-bottom: 14px solid transparent; margin-left: 4px; }}
    .sold-out-overlay {{ width: 100%; height: 240px; background: #ccc; display: none; flex-direction: column; align-items: center; justify-content: center; gap: 12px; border-radius: 0; }}
    .sold-out-badge {{ background: #888; color: white; font-size: 14px; font-weight: 700; padding: 6px 16px; border-radius: 20px; letter-spacing: 0.1em; }}
    .sold-out-msg {{ font-size: 13px; color: #666; }}
    .video-embed {{ display: none; width: 100%; aspect-ratio: 16/9; }}
    .video-embed iframe {{ width: 100%; height: 100%; border: none; }}
    .property-body {{ padding: 20px; }}
    .property-name {{ font-family: 'Shippori Mincho', serif; font-size: 22px; font-weight: 700; color: var(--green); margin-bottom: 16px; line-height: 1.4; }}
    .divider {{ border: none; border-top: 1px solid var(--border); margin: 16px 0; }}
    .youtube-link {{ display: flex; align-items: center; gap: 6px; font-size: 12px; color: #ff0000; text-decoration: none; }}
    .youtube-link:hover {{ text-decoration: underline; }}
    .cta-section {{ background: white; border-radius: 12px; padding: 24px 20px; box-shadow: 0 2px 16px rgba(45,106,79,0.1); text-align: center; }}
    .cta-title {{ font-family: 'Shippori Mincho', serif; font-size: 18px; color: var(--green); font-weight: 700; margin-bottom: 8px; }}
    .cta-sub {{ font-size: 12px; color: var(--gray-text); margin-bottom: 20px; line-height: 1.6; }}
    .btn-apply {{ display: block; width: 100%; background: linear-gradient(135deg, var(--green) 0%, var(--green-light) 100%); color: white; font-size: 16px; font-weight: 700; padding: 16px; border-radius: 50px; text-decoration: none; letter-spacing: 0.1em; box-shadow: 0 4px 14px rgba(45,106,79,0.35); }}
    .back-link {{ display: block; text-align: center; margin-top: 20px; font-size: 13px; color: var(--green-light); text-decoration: none; }}
    footer {{ background: var(--green); color: rgba(255,255,255,0.7); text-align: center; padding: 20px; font-size: 12px; margin-top: 32px; }}
    footer strong {{ color: white; display: block; font-size: 14px; margin-bottom: 4px; }}
  </style>
</head>
<body>
<header>
  <div class="logo">理想のおうち案内所<span>CLOVER ESTATE</span></div>
</header>
<div class="hero">
  <div class="hero-badge">🎬 YouTube紹介物件</div>
  <h1>{property_name}</h1>
</div>
<div class="container">
  <div class="property-card">
    <div class="thumbnail" id="thumbnail" onclick="playVideo()">
      <img src="{thumbnail_url}" alt="{property_name}" id="thumb-img">
      <div class="play-btn" id="play-btn"></div>
    </div>
    <div class="sold-out-overlay" id="sold-out-overlay">
      <span class="sold-out-badge">販売終了</span>
      <span class="sold-out-msg">現在この物件は販売終了しています</span>
    </div>
    <div class="video-embed" id="video-embed">
      <iframe id="yt-iframe" src="" allowfullscreen allow="autoplay"></iframe>
    </div>
    <div class="property-body">
      <h2 class="property-name">{property_name}</h2>
      <hr class="divider">
      <a class="youtube-link" href="{video_url}" target="_blank">▶ YouTubeで見る</a>
    </div>
  </div>
  <div class="cta-section">
    <p class="cta-title">この物件が気になる方へ</p>
    <p class="cta-sub">下のボタンからお気軽にお問い合わせください。<br>専門スタッフが丁寧にご対応いたします。</p>
    <a class="btn-apply" href="{form_url}" target="_blank">📩 この物件に問い合わせる</a>
  </div>
  <a class="back-link" href="{NETLIFY_BASE_URL}/youtube_index.html">← 紹介物件一覧に戻る</a>
</div>
<footer>
  <strong>株式会社クローバー</strong>
  東京都渋谷区神宮前４丁目１１-６　TEL: 03-6721-0818<br>
  営業時間：9:00〜22:00　定休日：水曜日
</footer>
<script>
  function playVideo() {{
    document.getElementById('thumbnail').style.display = 'none';
    var embed = document.getElementById('video-embed');
    embed.style.display = 'block';
    document.getElementById('yt-iframe').src = 'https://www.youtube.com/embed/{video_id}?autoplay=1';
  }}

  // サムネイル読み込み後に非公開かどうか判定
  // YouTubeの非公開動画は120x90の小さいデフォルト画像が返ってくる
  window.addEventListener('load', function() {{
    var img = document.getElementById('thumb-img');
    if (img.naturalWidth <= 120) {{
      showSoldOut();
    }}
  }});

  function showSoldOut() {{
    document.getElementById('thumbnail').style.display = 'none';
    document.getElementById('sold-out-overlay').style.display = 'flex';
    // 問い合わせセクションを非表示
    var cta = document.querySelector('.cta-section');
    if (cta) cta.style.display = 'none';
  }}
</script>
</body>
</html>'''

    return filename, html

# ----------------------------------------
# 4. 物件一覧ページを生成
# ----------------------------------------
def generate_youtube_index_html(properties):
    cards_html = ""
    for prop in properties:
        video_id = get_video_id(prop["url"])
        if not video_id:
            continue
        thumbnail_url = get_thumbnail_url(video_id)
        safe_name = re.sub(r'[\\/:*?"<>|\'「」『』【】]', '', prop["name"])
        page_url = f"{NETLIFY_BASE_URL}/youtube_property_{safe_name}.html"

        cards_html += f'''
    <a class="card" href="{page_url}" id="card-{video_id}">
      <div class="card-img">
        <img src="{thumbnail_url}" alt="{prop["name"]}"
             id="thumb-{video_id}"
             onload="checkSoldOut('{video_id}', this)">
        <div class="play-overlay" id="play-{video_id}">▶</div>
        <div class="sold-out-overlay" id="overlay-{video_id}" style="display:none">
          <span class="sold-out-badge">販売終了</span>
          <span class="sold-out-text">現在この物件は販売終了しています</span>
        </div>
      </div>
      <div class="card-body">
        <h2 class="card-title">{prop["name"]}</h2>
        <p class="card-sub" id="sub-{video_id}">動画で物件をチェック・お問い合わせはこちらから</p>
      </div>
    </a>'''

    html = f'''<!DOCTYPE html>
<html lang="ja">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>YouTube紹介物件一覧 | 理想のおうち案内所</title>
  <link href="https://fonts.googleapis.com/css2?family=Noto+Sans+JP:wght@400;500;700&family=Shippori+Mincho:wght@400;700&display=swap" rel="stylesheet">
  <style>
    :root {{
      --green: #2d6a4f;
      --green-light: #40916c;
      --green-pale: #d8f3dc;
      --gold: #b5883a;
      --gray-bg: #f7f9f7;
      --border: #d0e4d6;
    }}
    * {{ margin: 0; padding: 0; box-sizing: border-box; }}
    body {{ font-family: 'Noto Sans JP', sans-serif; background: var(--gray-bg); color: #333; }}
    header {{ background: var(--green); padding: 16px 24px; text-align: center; box-shadow: 0 2px 8px rgba(0,0,0,0.15); }}
    .logo {{ font-family: 'Shippori Mincho', serif; color: white; font-size: 20px; letter-spacing: 0.1em; }}
    .logo span {{ color: #a8d5b5; font-size: 13px; display: block; letter-spacing: 0.2em; }}
    .hero {{ background: linear-gradient(135deg, var(--green) 0%, var(--green-light) 100%); padding: 28px 24px; text-align: center; }}
    .hero h1 {{ font-family: 'Shippori Mincho', serif; color: white; font-size: 22px; font-weight: 700; margin-bottom: 6px; }}
    .hero p {{ color: rgba(255,255,255,0.8); font-size: 13px; }}
    .container {{ max-width: 680px; margin: 0 auto; padding: 24px 16px 48px; }}
    .count {{ font-size: 13px; color: #666; margin-bottom: 16px; }}
    .card {{ display: block; background: white; border-radius: 12px; overflow: hidden; box-shadow: 0 2px 16px rgba(45,106,79,0.1); margin-bottom: 16px; text-decoration: none; color: inherit; transition: transform 0.15s, box-shadow 0.15s; }}
    .card:hover {{ transform: translateY(-2px); box-shadow: 0 4px 20px rgba(45,106,79,0.18); }}
    .card-img {{ position: relative; }}
    .card-img img {{ width: 100%; height: 200px; object-fit: contain; background: #000; display: block; }}
    .sold-out-overlay {{ width: 100%; height: 200px; background: #ccc; display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 8px; }}
    .sold-out-badge {{ background: #888; color: white; font-size: 12px; font-weight: 700; padding: 4px 12px; border-radius: 20px; letter-spacing: 0.1em; }}
    .sold-out-text {{ font-size: 12px; color: #666; }}
    .card.sold-out .card-title {{ color: #999; }}
    .card.sold-out .card-sub {{ color: #bbb; }}
    .play-overlay {{ position: absolute; top: 50%; left: 50%; transform: translate(-50%, -50%); width: 48px; height: 48px; background: rgba(255,0,0,0.85); border-radius: 50%; display: flex; align-items: center; justify-content: center; color: white; font-size: 18px; padding-left: 4px; }}
    .card-body {{ padding: 16px; }}
    .card-title {{ font-family: 'Shippori Mincho', serif; font-size: 18px; font-weight: 700; color: var(--green); margin-bottom: 6px; line-height: 1.4; }}
    .card-sub {{ font-size: 12px; color: #888; }}
    footer {{ background: var(--green); color: rgba(255,255,255,0.7); text-align: center; padding: 20px; font-size: 12px; }}
    footer strong {{ color: white; display: block; font-size: 14px; margin-bottom: 4px; }}
  </style>
</head>
<body>
<header>
  <div class="logo">理想のおうち案内所<span>CLOVER ESTATE</span></div>
</header>
<div class="hero">
  <h1>🎬 YouTube紹介物件一覧</h1>
  <p>動画で紹介した物件をまとめています</p>
</div>
<div class="container">
  <p class="count">全{len(properties)}件</p>
  {cards_html}
</div>
<footer>
  <strong>株式会社クローバー</strong>
  東京都渋谷区神宮前４丁目１１-６　TEL: 03-6721-0818<br>
  営業時間：9:00〜22:00　定休日：水曜日
</footer>
<script>
  function checkSoldOut(videoId, img) {{
    if (img.naturalWidth <= 120) {{
      markSoldOut(videoId);
    }}
  }}
  function markSoldOut(videoId) {{
    var thumb = document.getElementById('thumb-' + videoId);
    var play = document.getElementById('play-' + videoId);
    var overlay = document.getElementById('overlay-' + videoId);
    var card = document.getElementById('card-' + videoId);
    var sub = document.getElementById('sub-' + videoId);
    if (thumb) thumb.style.display = 'none';
    if (play) play.style.display = 'none';
    if (overlay) overlay.style.display = 'flex';
    if (card) card.classList.add('sold-out');
    if (sub) sub.textContent = '販売終了';
  }}
</script>
</body>
</html>'''

    return html
# ----------------------------------------
def commit_to_github(files):
    try:
        subprocess.run(["git", "config", "user.email", "action@github.com"], check=True)
        subprocess.run(["git", "config", "user.name", "GitHub Actions"], check=True)
        for f in files:
            subprocess.run(["git", "add", f], check=True)
        result = subprocess.run(["git", "diff", "--cached", "--quiet"])
        if result.returncode != 0:
            subprocess.run(["git", "commit", "-m", "Update YouTube property pages"], check=True)
            subprocess.run(["git", "push"], check=True)
            print("  → GitHubにコミット完了")
        else:
            print("  → 変更なし、コミットスキップ")
        return True
    except subprocess.CalledProcessError as e:
        print(f"  → コミット失敗: {e}")
        return False

# ----------------------------------------
# 6. メイン処理
# ----------------------------------------
def main():
    print("CSVを読み込み中...")

    if not os.path.exists(CSV_FILE):
        print(f"エラー: {CSV_FILE} が見つかりません")
        return

    properties = []
    with open(CSV_FILE, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            url = row.get("動画URL", "").strip()
            name = row.get("物件名", "").strip()
            if url and name:
                properties.append({"url": url, "name": name})

    if not properties:
        print("物件情報が見つかりませんでした")
        return

    print(f"{len(properties)}件の物件を取得しました")

    files_to_commit = []

    # 各物件の詳細ページを生成
    for prop in properties:
        video_id = get_video_id(prop["url"])
        if not video_id:
            print(f"  → 動画IDが取得できませんでした: {prop['url']}")
            continue
        filename, html = generate_youtube_property_html(prop["name"], prop["url"], video_id)
        with open(filename, "w", encoding="utf-8") as f:
            f.write(html)
        files_to_commit.append(filename)
        print(f"  → {filename} 生成完了")

    # 一覧ページを生成（CSVの逆順＝新しい順）
    index_html = generate_youtube_index_html(list(reversed(properties)))
    with open("youtube_index.html", "w", encoding="utf-8") as f:
        f.write(index_html)
    files_to_commit.append("youtube_index.html")
    print("  → youtube_index.html 生成完了")

    # GitHubにコミット
    commit_to_github(files_to_commit)
    print(f"\n✅ 完了！")
    print(f"   一覧ページ: {NETLIFY_BASE_URL}/youtube_index.html")

if __name__ == "__main__":
    main()
