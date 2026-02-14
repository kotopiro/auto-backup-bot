# 🔧 セットアップガイド

## 📋 前提条件

- Python 3.11以上
- Discord アカウント
- Cloudflare アカウント（Turnstile用）
- InfinityFree アカウント（ホスティング用）
- Koyeb アカウント（Bot/Webホスティング用）

---

## ステップ1: Discord Bot設定

### 1. Discord Developer Portalへアクセス
https://discord.com/developers/applications

### 2. 新しいアプリケーション作成
- 「New Application」をクリック
- 名前を入力（例: Auto Backup Bot）
- 「Create」をクリック

### 3. Bot作成
- 左メニューから「Bot」を選択
- 「Add Bot」をクリック
- 「Reset Token」をクリックしてトークンをコピー
  → これが `BOT_TOKEN` になります

### 4. Bot権限設定
以下の権限をONにする：
- `Presence Intent`
- `Server Members Intent`
- `Message Content Intent`

### 5. OAuth2設定
左メニューから「OAuth2」→「General」を選択

**Redirects** に以下を追加：
```
https://school-rekisi.kesug.com/callback
```

**Client ID** と **Client Secret** をコピー：
- Client ID → `DISCORD_CLIENT_ID`
- Client Secret → `DISCORD_CLIENT_SECRET`

### 6. OAuth2 URL Generator
左メニューから「OAuth2」→「URL Generator」を選択

**SCOPES** で以下を選択：
- `identify`
- `guilds.join`

**SELECT REDIRECT URL** で先ほど追加したURLを選択

生成されたURLをコピー（認証ページで使用）

---

## ステップ2: Cloudflare Turnstile設定

### 1. Cloudflare Dashboardへアクセス
https://dash.cloudflare.com

### 2. Turnstileページへ移動
左メニューから「Turnstile」を選択

### 3. 新しいサイト作成
- 「Add Site」をクリック
- **Site name**: Auto Backup Bot
- **Domain**: `school-rekisi.kesug.com`
- **Widget Type**: Managed（推奨）
- 「Create」をクリック

### 4. キーをコピー
- **Site Key** → `TURNSTILE_SITE_KEY`
- **Secret Key** → `TURNSTILE_SECRET_KEY`

---

## ステップ3: InfinityFree設定

### 1. アカウント作成
https://infinityfree.net

### 2. 新しいアカウント作成
- 「Create Account」をクリック
- サブドメイン: `school-rekisi`
- ドメイン選択: `kesug.com`

### 3. FTPでファイルアップロード
以下のファイルをアップロード：
```
/htdocs/
  ├── web/
  │   ├── templates/
  │   ├── static/
  │   └── app.py
  └── .htaccess
```

### 4. .htaccess 設定
```apache
RewriteEngine On
RewriteCond %{REQUEST_FILENAME} !-f
RewriteRule ^(.*)$ https://your-koyeb-app.koyeb.app/$1 [P,L]
```

または、直接Koyebで全てホストする場合はスキップ可能

---

## ステップ4: ローカルセットアップ

### 1. リポジトリのクローン
```bash
git clone <your-repo-url>
cd auto-backup-bot
```

### 2. Python仮想環境作成
```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
# または
venv\Scripts\activate  # Windows
```

### 3. 依存パッケージインストール
```bash
pip install -r requirements.txt
```

### 4. 環境変数設定
```bash
cp .env.example .env
```

`.env` ファイルを編集：
```env
# Discord Bot Configuration
BOT_TOKEN=YOUR_BOT_TOKEN_HERE
PREFIX=!

# OAuth2 Configuration
DISCORD_CLIENT_ID=YOUR_CLIENT_ID_HERE
DISCORD_CLIENT_SECRET=YOUR_CLIENT_SECRET_HERE
DISCORD_REDIRECT_URI=https://school-rekisi.kesug.com/callback

# Web Configuration
WEB_URL=https://school-rekisi.kesug.com
FLASK_SECRET_KEY=ランダムな文字列を生成
WEBHOOK_SECRET=ランダムな文字列を生成
BOT_WEBHOOK_URL=https://school-rekisi.kesug.com/api/webhook

# Cloudflare Turnstile
TURNSTILE_SITE_KEY=YOUR_SITE_KEY_HERE
TURNSTILE_SECRET_KEY=YOUR_SECRET_KEY_HERE

# Database
DATABASE_URL=sqlite:///data/backup_bot.db

# Admin Users (カンマ区切りのDiscord ID)
ADMIN_IDS=YOUR_DISCORD_ID_HERE

# Logging
LOG_LEVEL=INFO
```

### 5. ローカル起動
```bash
./start.sh
```

または個別に起動：
```bash
# ターミナル1: Webサーバー
python -m web.app

# ターミナル2: Discord Bot
python -m bot.main
```

---

## ステップ5: Koyebデプロイ

### 1. GitHubにプッシュ
```bash
git init
git add .
git commit -m "Initial commit"
git remote add origin <your-github-repo>
git push -u origin main
```

### 2. Koyebアカウント作成
https://www.koyeb.com/

### 3. 新しいアプリ作成
- 「Create App」をクリック
- 「GitHub」を選択
- リポジトリを選択

### 4. ビルド設定
- **Builder**: Dockerfile
- **Dockerfile path**: `Dockerfile`
- **Port**: `5000`

### 5. 環境変数設定
Koyebの「Environment」タブで以下を設定：

```
BOT_TOKEN = <your_bot_token>
DISCORD_CLIENT_ID = <your_client_id>
DISCORD_CLIENT_SECRET = <your_client_secret>
DISCORD_REDIRECT_URI = https://<your-app>.koyeb.app/callback
WEB_URL = https://<your-app>.koyeb.app
FLASK_SECRET_KEY = <random_string>
WEBHOOK_SECRET = <random_string>
TURNSTILE_SITE_KEY = <your_site_key>
TURNSTILE_SECRET_KEY = <your_secret_key>
ADMIN_IDS = <your_discord_id>
DATABASE_URL = sqlite:///data/backup_bot.db
```

### 6. デプロイ
- 「Deploy」をクリック
- デプロイ完了まで待機（3-5分）

### 7. URLの確認
デプロイ完了後、`https://<your-app>.koyeb.app` にアクセス

---

## ステップ6: Botをサーバーに招待

### 1. Bot招待URL生成
Discord Developer Portalで以下の権限を選択：
- `Administrator`（または必要な権限のみ）

### 2. URLをコピーしてブラウザで開く
Botをテストサーバーに招待

### 3. 動作確認
サーバーで `/help` コマンドを実行

---

## 🎯 初回セットアップ完了チェックリスト

- [ ] Discord Botが起動している
- [ ] Webサーバーが起動している
- [ ] `/help` コマンドが動作する
- [ ] `/button` コマンドで認証ボタンが表示される
- [ ] 認証ページにアクセスできる
- [ ] Turnstileチャレンジが表示される
- [ ] OAuth2認証が完了する
- [ ] `/check` でユーザーが登録済みと表示される
- [ ] `/backup` でバックアップが作成される

---

## 🐛 トラブルシューティング

### Botが起動しない
- `.env` ファイルが正しく設定されているか確認
- `BOT_TOKEN` が正しいか確認
- Python 3.11以上がインストールされているか確認

### 認証ページにアクセスできない
- Webサーバーが起動しているか確認
- ポート5000が開いているか確認
- Cloudflare設定を確認

### OAuth2エラー
- `DISCORD_CLIENT_ID` と `DISCORD_CLIENT_SECRET` を確認
- Redirect URIが正しく設定されているか確認
- Discord Developer Portalで「guilds.join」スコープが有効か確認

### メンバー追加に失敗
- Botがサーバーに参加しているか確認
- Bot権限を確認（Administrator推奨）
- ユーザーがOAuth2認証を完了しているか確認
- トークンが期限切れでないか確認（`/check` で確認可能）

---

## 📞 サポート

問題が解決しない場合は、Issueを作成してください。
