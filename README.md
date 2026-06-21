# Chunk Reset CLI

Minecraft **統合版（Bedrock Edition）** および Java 版のワールドについて、指定した矩形範囲内のチャンクを削除し、次回ゲーム内訪問時に再生成されるようにする CLI ツールです。

主な利用想定は **Windows + PowerShell 上の統合版** です。[Amulet Core](https://github.com/Amulet-Team/Amulet-Core) を利用しており、Amulet Map Editor 本体への依存はありません。

---

## 目次

1. [セットアップ（PowerShell）](#セットアップpowershell)
2. [基本的な使い方](#基本的な使い方)
3. [ワールドフォルダの場所（Windows 統合版）](#ワールドフォルダの場所windows-統合版)
4. [座標の指定方法](#座標の指定方法)
5. [オプション一覧](#オプション一覧)

---

## セットアップ（PowerShell）

Python **3.11 以上** が必要です（[python.org](https://www.python.org/downloads/) からインストール）。

リポジトリを clone したら、プロジェクトのルートディレクトリで次を実行します。

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e .
```

インストール後、`chunk-reset --help` でヘルプが表示されれば OK です。

> `Activate.ps1` の実行が拒否される場合は、管理者 PowerShell で  
> `Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser` を一度実行してください。

---

## 基本的な使い方

### 事前準備（必須）

1. **ワールドのバックアップ** を取る
2. **Minecraft を完全終了** する（LevelDB がロックされていると失敗します）

### 実行の流れ

```
① ワールドフォルダのパスを特定する
        ↓
② --dry-run で対象チャンクを確認する（パスが正しいかもここで確認）
        ↓
③ 問題なければ本実行する
```

#### ① ワールドパスを特定

[ワールドフォルダの場所](#ワールドフォルダの場所windows-統合版) を参照し、`level.dat` と `db` フォルダがある **個別ワールドフォルダ** のパスを控えます。

以降のコマンド例では、次のプレースホルダーを PowerShell 変数に置き換えて使います。

| プレースホルダー | 意味 | 例（あくまで参考） |
|-----------------|------|-------------------|
| `<ユーザーID>` | Microsoft アカウントごとのフォルダ名 | `907912747214718426` |
| `<ワールドID>` | `minecraftWorlds` 直下のワールドフォルダ名 | `f2Tvgy1XaCQ=` |

```powershell
# ご自身の環境の値に置き換える
$userId = "<ユーザーID>"
$worldId = "<ワールドID>"
$worldPath = "$env:APPDATA\Minecraft Bedrock\Users\$userId\games\com.mojang\minecraftWorlds\$worldId"
```

サインアウト時など **`Shared` 配下** の場合:

```powershell
$worldId = "<ワールドID>"
$worldPath = "$env:APPDATA\Minecraft Bedrock\Users\Shared\games\com.mojang\minecraftWorlds\$worldId"
```

#### ② dry-run で確認

Microsoft アカウントでサインインしている場合、ワールドは **`Users\Shared` ではなく `<ユーザーID>` フォルダ** 配下にあることが多いです。

```powershell
chunk-reset $worldPath --from 0,0 --to 100,100 --dry-run
```

- `World: ...` と表示されれば **パスは正しい**
- `Chunks to delete (exist): N` で削除対象数を確認
- 各チャンク座標 `(cx, cz)` が一覧表示される

#### ③ 本実行

```powershell
chunk-reset $worldPath --from 0,0 --to 100,100
```

確認プロンプトが表示されます。スキップする場合は `-y` を付けます。

```powershell
chunk-reset $worldPath --from 100,300 --to 200,400 -y
```

### その他の例

```powershell
# チャンク座標で指定
chunk-reset $worldPath --from 6,18 --to 12,25 --chunk-coords --dry-run

# ネザー / エンド
chunk-reset $worldPath --from 0,0 --to 100,100 --dimension nether --dry-run
```

> **パスの書き方:** `Minecraft Bedrock` にスペースが含まれるため、パスは **`"..."` で囲む** 必要があります。`<ワールドID>` の末尾に **`=`** が付くことがあります。環境変数は PowerShell では **`$env:APPDATA`** の形式を使います（`%APPDATA%` は cmd 用で、PowerShell では展開されません）。

---

## ワールドフォルダの場所（Windows 統合版）

### 指定するパス

`chunk-reset` の第 1 引数 `world` に渡すのは **個々のワールドフォルダ** です。

```powershell
# PowerShell でパスを組み立てる例（<ユーザーID> / <ワールドID> は環境ごとに異なる）
$userId = "<ユーザーID>"
$worldId = "<ワールドID>"
"$env:APPDATA\Minecraft Bedrock\Users\$userId\games\com.mojang\minecraftWorlds\$worldId"
```

**指定してはいけない例:**

| パス | 理由 |
|------|------|
| `...\Minecraft Bedrock\Users` | ワールド本体ではなくユーザー一覧 |
| `...\minecraftWorlds` | 複数ワールドの親フォルダ |
| ゲーム内のワールド名だけ | フォルダ名は `<ワールドID>`（内部 ID）のため一致しない |

### フォルダ構造（GDK 版 / 1.21.120 以降）

```
C:\Users\<Windowsユーザー名>\AppData\Roaming\Minecraft Bedrock\
└── Users\
    ├── <ユーザーID>\games\com.mojang\minecraftWorlds\   ← ★ サインイン時（よくある）
    │   └── <ワールドID>\                               ← ★ world 引数（level.dat があるフォルダ）
    └── Shared\games\com.mojang\minecraftWorlds\         ← サインアウト時・共有
        └── <ワールドID>\
```

PowerShell では `$env:APPDATA` が上記の `...\AppData\Roaming\` に相当します。

### ワールドフォルダの探し方

1. `Win + R` を押し、`%appdata%\Minecraft Bedrock\Users` と入力して Enter（※ Run ダイアログでは `%appdata%` が使えます）
2. **`<ユーザーID>`**（数字だけの長いフォルダ名）を開く  
   - サインイン中の Microsoft アカウント用（**最も一般的**）  
   - 見当たらない場合は **`Shared`**（サインアウト状態・共有プロファイル）
3. `games` → `com.mojang` → `minecraftWorlds` と進む
4. 中の **`<ワールドID>` フォルダ** が 1 ワールド分  
   - 英数字に加え、末尾に **`=`** が付くことがある  
   - `level.dat` と `db` フォルダ（LevelDB）があることを確認
   - ゲーム内表示名は `levelname.txt` に書かれていることが多い

PowerShell で `Users` 配下のワールドを一覧する例:

```powershell
Get-ChildItem "$env:APPDATA\Minecraft Bedrock\Users\*\games\com.mojang\minecraftWorlds\*" -Directory |
  ForEach-Object {
    $name = Get-Content (Join-Path $_.FullName 'levelname.txt') -ErrorAction SilentlyContinue
    "$($_.Name)  $name  $($_.FullName)"
  }
```

### 旧 UWP 版（1.21.120 より前）

GDK 移行後は空のことが多いですが、古いインストールでは次の場所にあります。

```powershell
"$env:LOCALAPPDATA\Packages\Microsoft.MinecraftUWP_8wekyb3d8bbwe\LocalState\games\com.mojang\minecraftWorlds\<ワールドID>"
```

### うまく開けないとき

- Minecraft を完全終了してから再実行
- パス先に `level.dat` があるか確認
- `--dry-run` で `World: ...` が表示されればパスは正しい
- ゲーム内でワールドを `.mcworld` にエクスポートし、解凍したフォルダを指定する（バックアップ兼テスト向き）

---

## 座標の指定方法

`--from` と `--to` には **X,Z の 2 値**（カンマ区切り）を指定します。Y 座標は不要で、**ワールドの高さ全体** が対象になります。

### 共通ルール

- `--from` / `--to` の **順序は問いません**（自動で min/max に並べ替え）
- 両端とも **inclusive**（指定した座標を含む）
- 削除単位は **チャンク（16×16 ブロック）**。範囲に触れたチャンクは **チャンク全体** が削除される
- **マイナス座標も指定可能**（原点より西・北側のエリアなど）

### マイナス座標を指定するとき

座標計算自体はマイナス値に対応しています（例: `--from=-352,736`）。  
ただし PowerShell から **スペース区切り** で渡すと、`-352,736` が別オプションと誤解釈され **エラー** になることがあります。

```powershell
# NG: スペース区切り（マイナス値がオプション扱いになりやすい）
chunk-reset $worldPath --from -352,736 --to -100,800 --dry-run

# OK: = 形式（推奨）
chunk-reset $worldPath --from=-352,736 --to=-100,800 --dry-run

# OK: ダブルクォート
chunk-reset $worldPath --from "-352,736" --to "-100,800" --dry-run
```

正の座標（例: `--from 100,200`）はスペース区切りのままで問題ありません。

### ブロック座標（既定）

ゲーム内座標（統合版の座標表示など）を **ブロック座標** として解釈します。指定範囲は **16 ブロック単位のチャンク境界にスナップ** されます（Amulet Map Editor の Chunk ツールと同じ）。

```
チャンク (0,0) = ブロック x: 0〜15,  z: 0〜15
チャンク (1,0) = ブロック x: 16〜31, z: 0〜15
チャンク (0,1) = ブロック x: 0〜15,  z: 16〜31
```

#### 例: ごく小さな範囲（`--from 1,5 --to 2,10`）

| 項目 | 値 |
|------|-----|
| 指定範囲（ブロック） | x: 1〜2, z: 5〜10 |
| スナップ後 | x: 0〜15, z: 0〜15 |
| 削除されるチャンク | **`(0, 0)` の 1 チャンクのみ** |

4 ブロック分だけではなく、範囲がかかるチャンク `(0,0)` 全体（**16×16 ブロック**）が対象になります。

#### 例: 複数チャンク（`--from 0,0 --to 31,31`）

| 項目 | 値 |
|------|-----|
| 指定範囲（ブロック） | x: 0〜31, z: 0〜31 |
| 削除されるチャンク | `(0,0)`, `(1,0)`, `(0,1)`, `(1,1)` の **4 チャンク** |

#### 例: 広い範囲（`--from 100,300 --to 200,400`）

ブロック x: 100〜200, z: 300〜400 を含むすべてのチャンクが対象（スナップ後は x: 96〜207, z: 288〜415 相当）。

### チャンク座標（`--chunk-coords`）

チャンク番号で直接指定します（統合版の座標表示と対応）。

```powershell
# チャンク (0,0) の 1 個だけ
chunk-reset $worldPath --from 0,0 --to 0,0 --chunk-coords --dry-run

# チャンク x: 6〜12, z: 18〜25（最大 7×8 = 56 チャンク）
chunk-reset $worldPath --from 6,18 --to 12,25 --chunk-coords --dry-run
```

### どちらを使うべきか

| 目的 | おすすめ |
|------|---------|
| ゲーム内座標付近をリセットしたい | ブロック座標（既定） |
| チャンク番号が分かっている | `--chunk-coords` |
| 削除対象を正確に確認したい | 必ず `--dry-run` を先に実行 |

---

## オプション一覧

| オプション | 説明 |
|-----------|------|
| `world` | ワールドフォルダへのパス（`level.dat` があるフォルダ） |
| `--from X,Z` | 範囲の一端（必須）。マイナス値は `--from=-352,736` 形式を推奨 |
| `--to X,Z` | 範囲の反対側（必須）。マイナス値は `--to=-100,800` 形式を推奨 |
| `--dimension`, `-d` | `overworld`（既定）, `nether`, `end` または `minecraft:overworld` 形式 |
| `--chunk-coords` | 座標をチャンク座標として解釈 |
| `--dry-run` | 対象チャンクを表示するだけで変更しない |
| `-y`, `--yes` | 確認プロンプトをスキップ |
