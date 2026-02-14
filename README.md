# 🔒 Auto Backup Bot

高性能なDiscordサーバーメンバーバックアップ＆復元システム

## ✨ 特徴

- 🚀 **高速・安全** - 非同期処理とレート制限対応
- 🔐 **完全認証** - Cloudflare Turnstile + Discord OAuth2
- 💾 **自動バックアップ** - スケジューラー機能搭載
- 📊 **詳細統計** - リアルタイム分析とランキング
- 🎨 **モダンUI** - レスポンシブWebインターフェース
- ⚡ **バッチ処理** - 一括メンバー追加対応

## 🏗️ アーキテクチャ

```
├── AJS/              # コアライブラリ（OAuth2 & API）
├── bot/              # Discord Bot本体
│   ├── cogs/         # コマンド群
│   ├── database.py   # データベース管理
│   └── config.py     # 設定
├── web/              # 認証Webサイト
│   ├── templates/    # HTML
│   └── static/       # CSS/JS
└── Dockerfile        # Koyebデプロイ用
```

## 🚀 セットアップ

### 1. Discord Developer Portal設定

1. [Discord Developer Portal](https://discord.com/developers/applications) でアプリケーション作成
2. Bot作成してトークン取得
3. OAuth2設定：
   - Redirect URI: `https://school-rekisi.kesug.com/callback`
   - Scopes: `identify`, `guilds.join`

### 2. Cloudflare Turnstile設定

1. [Cloudflare Turnstile](https://dash.cloudflare.com/?to=/:account/turnstile) でサイト作成
2. サイトキーとシークレットキーを取得

### 3. 環境変数設定

`.env.example` をコピーして `.env` を作成：

```bash
cp .env.example .env
```

必要な値を入力：
```env
BOT_TOKEN=your_bot_token
DISCORD_CLIENT_ID=your_client_id
DISCORD_CLIENT_SECRET=your_client_secret
TURNSTILE_SITE_KEY=your_site_key
TURNSTILE_SECRET_KEY=your_secret_key
```

### 4. ローカル実行

```bash
# 依存パッケージインストール
pip install -r requirements.txt

# Botを起動
python -m bot.main

# Webサーバーを別ターミナルで起動
python -m web.app
```

### 5. Koyebデプロイ

1. GitHubにプッシュ
2. Koyebで新しいアプリ作成
3. GitHub連携
4. 環境変数を設定
5. デプロイ

## 📝 コマンド一覧

### 🔐 認証コマンド

| コマンド | 説明 |
|---------|------|
| `/button [title] [description]` | 認証用ボタンを表示 |
| `/check [user]` | ユーザーの登録状況確認 |
| `/datacheck` | 登録ユーザー数確認 |

### 💾 バックアップコマンド

| コマンド | 説明 |
|---------|------|
| `/backup` | サーバーをバックアップ |
| `/listbackups [limit]` | バックアップ一覧表示 |

### ♻️ 復元コマンド

| コマンド | 説明 |
|---------|------|
| `/restore [backup_id]` | バックアップから復元 |
| `/call` | 全登録ユーザーを追加 |
| `/request <user_id>` | 特定ユーザーを追加 |

### 📊 統計コマンド

| コマンド | 説明 |
|---------|------|
| `/stats [days]` | 統計情報表示 |
| `/leaderboard [metric] [limit]` | サーバーランキング |
| `/activity [limit]` | 最近のアクティビティ |
| `/userinfo <user>` | ユーザー詳細情報 |

### ⚙️ 管理コマンド（管理者限定）

| コマンド | 説明 |
|---------|------|
| `/delkey <user_id>` | ユーザー削除 |
| `/purge` | 期限切れトークン削除 |
| `/refresh <user_id>` | トークンリフレッシュ |
| `/setup` | 初期設定 |
| `/help` | ヘルプ表示 |

## 🔧 AJSライブラリ使用例

```python
from AJS import AJS

async def main():
    async with AJS(
        bot_token="your_token",
        client_id="your_id",
        client_secret="your_secret",
        redirect_uri="your_uri"
    ) as ajs:
        # トークン交換
        tokens = await ajs.exchange_code("auth_code")
        
        # ユーザー情報取得
        user = await ajs.get_user_info(tokens['access_token'])
        
        # メンバー追加
        result = await ajs.add_guild_member(
            access_token=tokens['access_token'],
            guild_id="123456789",
            user_id=user['id']
        )
        
        # バッチ追加
        members = [
            {'access_token': 'token1', 'user_id': 'id1'},
            {'access_token': 'token2', 'user_id': 'id2'},
        ]
        results = await ajs.batch_add_members(
            members_data=members,
            guild_id="123456789"
        )
        
        print(f"成功: {results['success']}, 失敗: {results['failed']}")
```

## 🛡️ セキュリティ

- ✅ Cloudflare Turnstileによるボット対策
- ✅ OAuth2標準認証
- ✅ トークン暗号化保存
- ✅ レート制限自動処理
- ✅ CSRF対策

## 📊 データベーススキーマ

### users テーブル
```sql
user_id TEXT PRIMARY KEY
username TEXT
discriminator TEXT
avatar TEXT
access_token TEXT
refresh_token TEXT
expires_at INTEGER
created_at INTEGER
updated_at INTEGER
```

### backups テーブル
```sql
backup_id TEXT PRIMARY KEY
guild_id TEXT
guild_name TEXT
created_by TEXT
created_at INTEGER
member_count INTEGER
status TEXT
```

### statistics テーブル
```sql
id INTEGER PRIMARY KEY
event_type TEXT
guild_id TEXT
user_id TEXT
data_json TEXT
timestamp INTEGER
```

## 🤝 貢献

プルリクエスト歓迎！

## 📄 ライセンス

MIT License

## 💬 サポート

質問や問題があれば、Issueを作成してください。

---

**Powered by AJS Library** 🚀
