# Chunk Reset CLI

Minecraft **統合版（Bedrock Edition）** および Java 版のワールドについて、指定した矩形範囲内のチャンクを削除し、次回ゲーム内訪問時に再生成されるようにする CLI ツールです。

主な利用想定は **Windows + PowerShell 上の統合版** です。[Amulet Core](https://github.com/Amulet-Team/Amulet-Core) を利用しており、Amulet Map Editor 本体への依存はありません。

> 英語版: [README.md](README.md)

---

## 目次

1. [依存ライブラリに関する注意](#依存ライブラリに関する注意)
2. [ライセンス](#ライセンス)
3. [セットアップ（PowerShell）](#セットアップpowershell)
4. [基本的な使い方](#基本的な使い方)
5. [ワールドフォルダの場所（Windows 統合版）](#ワールドフォルダの場所windows-統合版)
6. [座標の指定方法](#座標の指定方法)
7. [固定チャンクと `reset-all`](#固定チャンクと-reset-all)
8. [オプション一覧](#オプション一覧)

---

## 依存ライブラリに関する注意

このプロジェクトは **Amulet-Core** に依存しています。

**本プロジェクトでは、Amulet-Core のソースコードは一切再配布していません。** Amulet-Core は pip 経由でインストールされる外部依存としてのみ利用されます。

**本ソフトウェアの利用者は、Amulet-Core を使用するための有効なライセンスを保有している必要があります。** Amulet-Core は有償ライセンスが必要なソフトウェアです。詳細については以下を参照してください。

https://www.amuletmc.com/legal

### MIT ライセンスでの公開について

**本プロジェクト**のソースコードは [MIT ライセンス](LICENSE) のもとで公開しています。公開前に、Discord 上で Amulet 開発者の **gentlegiantJGC** 氏に確認を取り、以下を条件として許可を得ています。

- Amulet-Core のコードを再配布しないこと
- 利用者に有効な Amulet ライセンスが必要であることを周知すること

---

## ライセンス

本プロジェクトのソースコードは MIT ライセンスの下で提供されます。全文は [LICENSE](LICENSE) を参照してください。

Amulet-Core 自体は別途 Amulet のライセンス条項が適用されます。本 CLI の利用は、お持ちの Amulet ライセンスの範囲内でのみ Amulet-Core を利用する権利を付与するものではありません。

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

> **注意:** `pip install` により Amulet-Core が依存関係としてダウンロードされます。Amulet-Core を合法的に利用するには、有効な Amulet ライセンスが必要です。

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

| プレースホルダー | 意味 | 形式の目安 |
|-----------------|------|-----------|
| `<ユーザーID>` | Microsoft アカウントごとのフォルダ名 | 数字のみの長い文字列 |
| `<ワールドID>` | `minecraftWorlds` 直下のワールドフォルダ名 | 英数字（末尾に `=` があることもある） |

```powershell
# ご自身の環境の値に置き換える
$userId = "<ユーザーID>"
$worldId = "<ワールドID>"
$worldPath = "$env:APPDATA\Minecraft Bedrock\Users\$userId\games\com.mojang\minecraftWorlds\$worldId"
```

#### ② dry-run で確認

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

## 固定チャンクと `reset-all`

固定チャンクは、`reset-all` が **絶対に削除しない** チャンクです。**ディレクトリ** の中にディメンションごとの JSON ファイルとして保存し、`chunk-reset pin` で管理します。pin コマンドはそれらのファイルを編集するだけで、ワールドを開いたり変更したりしません。

`reset-all` は、指定したディメンションの **固定チャンク以外の既存チャンクをすべて削除** します。矩形リセットよりはるかに破壊的なので、必ずバックアップを取り、本実行の前に `--dry-run` で確認してください。

### 固定ディレクトリとファイル名

`--pins` / `pin` にはディレクトリを渡します。対象ディメンションのファイルが、名前の規則で自動的に選ばれます。

| ディメンション（`--dimension`） | 固定ディレクトリ内のファイル |
|-------------------------------|---------------------------|
| `overworld`（既定） | `pin_overworld.json` |
| `nether` | `pin_nether.json` |
| `end` | `pin_end.json` |

```
pins/
  pin_overworld.json
  pin_nether.json
  pin_end.json
```

読み込まれるのは、リセット対象のディメンションのファイルだけです。そのファイルが存在しない場合はエラーになります。

### 安全のための制約

次の条件を満たさない場合、`reset-all` は何も変更せずに終了します。

- 対象ディメンションの固定ファイルがあり、内容が正しく、**固定が 1 つ以上** 定義されている
- 固定チャンクのうち **少なくとも 1 つが実際にワールドに存在する**（ディメンションや座標の指定ミスによる全削除を防ぐ）

これらのチェックは `-y` を付けても有効です。対象は `--dimension` で指定した 1 ディメンションのみで、他のディメンションには触れません。各ファイルは自身の `dimension` を記録しており、使われ方と一致しないファイル（たとえば `pin_overworld.json` をコピーして `pin_end.json` にリネームしたもの）は拒否されます。

### 固定チャンクの管理

固定は **チャンク座標** の矩形として保存されます。`--from` / `--to` の指定方法は矩形リセットと同じです（既定はブロック座標、`--chunk-coords` でチャンク座標。[座標の指定方法](#座標の指定方法) を参照）。`--dimension` の既定は `overworld` です。

```powershell
# 追加（ディレクトリとファイルがなければ新規作成）
chunk-reset pin add pins --from 0,0 --to 100,100 --label base
chunk-reset pin add pins --from=-352,736 --to=-100,800 --label farm
chunk-reset pin add pins --from 0,0 --to 3,3 --chunk-coords --dimension nether

# 一覧（チャンク座標）。全ファイル、またはディメンション指定
chunk-reset pin list pins
chunk-reset pin list pins --dimension nether

# ラベル、または完全に同じ範囲を指定して削除
chunk-reset pin remove pins --label farm
chunk-reset pin remove pins --from 0,0 --to 100,100
```

ラベルは任意ですが、同じディメンション内で重複できません。範囲指定での削除は、チャンクにスナップした後の範囲が **完全に一致** する固定だけが対象です。`pin list` で確認してください。

ファイル形式（`pin_overworld.json`）:

```json
{
  "version": 1,
  "dimension": "minecraft:overworld",
  "pins": [
    {"from": [0, 0], "to": [6, 6], "label": "base"}
  ]
}
```

### `reset-all` の実行

```powershell
# 1. 残るチャンクと削除されるチャンクを確認
chunk-reset reset-all $worldPath --pins pins --dry-run

# 2. 本実行（確認プロンプトあり。-y でスキップ）
chunk-reset reset-all $worldPath --pins pins

# 他のディメンションはそれぞれのファイル（pin_nether.json）を使う
chunk-reset reset-all $worldPath --pins pins --dimension nether --dry-run
```

存在するチャンク数、残る固定チャンク数、削除するチャンク数が表示されます。固定範囲の隣のチャンクはゲームが再生成するため、固定範囲の境界に地形の継ぎ目が出ることがあります。

### 矩形リセットでの固定チャンクの保護

通常の矩形リセットでも固定を使えます。`--pins` にディレクトリを渡すと、範囲内の、対象ディメンションの固定チャンクは削除されません。

```powershell
chunk-reset $worldPath --from 0,0 --to 300,300 --pins pins --dry-run
```

出力に `Chunks skipped (pinned, exist): N` が表示されます。`--pins` を付けない場合は、これまでどおり範囲内をすべて削除します。そのディメンションの固定ファイルは存在する必要がありますが、固定が 0 件でも実行できます（矩形削除は範囲が限定されるためです）。

---

## オプション一覧

| オプション | 説明 |
|-----------|------|
| `world` | ワールドフォルダへのパス（`level.dat` があるフォルダ） |
| `--from X,Z` | 範囲の一端（必須）。マイナス値は `--from=-352,736` 形式を推奨 |
| `--to X,Z` | 範囲の反対側（必須）。マイナス値は `--to=-100,800` 形式を推奨 |
| `--dimension`, `-d` | `overworld`（既定）, `nether`, `end` または `minecraft:overworld` 形式 |
| `--chunk-coords` | 座標をチャンク座標として解釈 |
| `--pins DIR` | 固定チャンクを削除しない（DIR 内の `pin_<dimension>.json` を読み込む） |
| `--dry-run` | 対象チャンクを表示するだけで変更しない |
| `-y`, `--yes` | 確認プロンプトをスキップ |
