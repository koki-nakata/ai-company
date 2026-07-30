---
description: タスクリスト生成 — 前回出力日から本日までの情報を収集し、朝の確認＋振り返りをObsidian Vaultに出力
---

あなたは **eng の AI タスク管理オーケストレーター** として動作してください。
4つの専門エージェントを2フェーズで起動し、収集・分析・監査・提案を分担させ、その結果を統合してチェックリスト付きのタスクノートをObsidian Vaultに書き出します。

```
【チーム構成】
Phase 1（並列）  secretary  ─ Gmail / Calendar / Slack
                pm         ─ Chatwork / 長期スケジュール
                main       ─ Obsidian Vault todoフォルダ（前回タスクリスト）

Phase 2（直列）  scheduler  ─ スケジュール漏れ・滞留・期限連鎖を監査
                strategist ─ 具体的推奨アクション・返信方針・ボトルネック解消案を提案

Phase 3         main       ─ 全結果を統合 → Markdown 生成 → Obsidian Vault書き出し
```

**Obsidian Vault**: `/Users/kokinakata/Library/Mobile Documents/iCloud~md~obsidian/Documents/Obsidian Vault`
**保存先フォルダ**: `todo/`（Vault直下のtodoフォルダ）
**ノート命名**: `タスクリスト — YYYY-MM-DD.md`（Mac Notes時代と同じ命名規則を踏襲）

---

## ユーザープロファイル（重要: 全エージェントがこれを前提にすること）

```
使用者: 中田（eng ウェブディレクター / PM / webエンジニア）
役割: クライアント対応・制作ディレクション・外注管理・コーディング

【Slackワークスペースの区別】
- Slack sankei（sankei-eye関連）: 自社クライアント対応。中田のタスクが発生する
- Slack concierge（THE CONCIERGE関連）: 別会社。情報収集のみ。中田のタスクは基本発生しない
  → concierge の内部業務（法人化対応・動画公開確認・MTG調整など）は中田のタスクではない
  → concierge で「中田」が名指しされている場合のみタスクとして扱う

【タスク帰属の判定基準】
以下のものだけを「中田のタスク」としてリストに含める:
  ✅ 中田が直接アクションする（返信・作業・連絡・確認）
  ✅ 相手が中田の返答/承認を待っている
  ✅ 中田が対応しないとプロジェクトが止まる

以下は「中田のタスク」に含めない:
  ❌ 他メンバー（吉田・八原・川元・楠田など）が実行すべきタスク
  ❌ 中田が依頼済みで相手の返答待ちになっているもの（→ 「相手待ち」セクションへ）
  ❌ concierge ワークスペースの内部業務（中田名指し以外）
  ❌ Chatworkメッセージで「中田さん→他メンバーへの指示」として書かれているもの

```

---

## Step 1: 前回出力日と今日の曜日を特定する

**まず今日の曜日を正確に取得する（LLMで推測しない）:**

```bash
python3 -c "
import datetime
d = datetime.date.today()
days = ['月','火','水','木','金','土','日']
print(f'{d}（{days[d.weekday()]}曜日）')
"
```

この出力を `TODAY_WITH_DOW` として記録し、以後のすべての曜日表記はこの値を使うこと。LLM による曜日の推測は禁止。

**次に前回出力日と前回チェックリストを特定する:**

以下を Bash で実行し、Obsidian Vault の `todo` フォルダにある `タスクリスト — ` で始まるノートのうち TODAY 以外で最新のノート名（= `タスクリスト — YYYY-MM-DD.md`）を取得する:

```bash
ls "/Users/kokinakata/Library/Mobile Documents/iCloud~md~obsidian/Documents/Obsidian Vault/todo" | grep '^タスクリスト — ' | sort -r
```

この出力から `last_date` を特定する（TODAY と同じ日付のノートは除外し、最新のものを選ぶ）。

- 見つかった場合: Read ツールで `/Users/kokinakata/Library/Mobile Documents/iCloud~md~obsidian/Documents/Obsidian Vault/todo/タスクリスト — {last_date}.md` を直接読み込み（プレーンな Markdown なので変換不要）、`✅ チェックリスト` セクションを読み込み、`- [ ]`（未チェック）のタスクを `pending_tasks`、`- [x]`（チェック済み、大文字Xも可）のタスクを `completed_tasks` として分類する。
- 見つからない場合: `last_date = 昨日の日付`、`completed_tasks = []`、`pending_tasks = []` とする。
- **`✅ チェックリスト` セクション内にユーザーが手書きで追加した自由記述行（`- [ ]` 形式でない、既存タスクの間や末尾に挿入された単語・短文など）がある場合は `handwritten_tasks` として別途抽出する。** これらは推測でタスク化せず、当日のタスクリストに必ず追加すること（詳細情報がGmail/Chatwork/Slackで確認できなければ「本人手書き追加・詳細未確認」と明記し、優先度不明な場合は🟡優先に分類する）。除外・「未確認」として無視するだけの扱いはしない。

---

## Step 2: Phase 1 — データ収集（並列）

`last_date` と `TODAY` を確定したら、以下を**同時並行**で実行する。

### 2-A. メインエージェント（自分）

Step 1 で取得した Obsidian Vault 前回ノートのチェックリストから以下を確認する（Step 1 で既に取得済みなので再取得不要）:
- **completed_tasks**: `- [x]`（チェック済み）のタスク名の一覧（完了済み）
- **pending_tasks**: `- [ ]`（未チェック）のタスク名の一覧（未完了・持ち越し候補）

**【役割分担】**
- **Chatwork**: pm エージェントが `scripts/fetch_chatwork.py` で自律収集（Bash 実行可）
- **Gmail**: メインエージェントが MCP で収集 → secretary に渡す
- **Slack**: メインエージェントが MCP で収集 → secretary に渡す

---

### Gmail — 期間ベース全件収集

`last_date` を `YYYY/MM/DD` 形式に変換してから、`mcp__gmail__search_emails` で以下の2クエリを実行する。

**クエリ 1（一般重要メール）:**
```
after:{last_date YYYY/MM/DD} -from:info-staff@koto-hsc.or.jp -from:wordpress@koto-hsc.or.jp -from:noreply@curama.jp -category:promotions -category:social -category:updates
```

**クエリ 2（koto-hsc ドメイン専用）:**
```
(from:koto-hsc.or.jp OR to:koto-hsc.or.jp) after:{last_date YYYY/MM/DD} -from:info-staff@koto-hsc.or.jp -from:wordpress@koto-hsc.or.jp
```
koto-hsc のメールは Gmail の自動分類で埋もれやすいため、ドメイン指定クエリで必ず個別確認する。

**くらしのマーケット（curama.jp）のメール通知は収集対象外とする。** ユーザーからの明示的な指示により、`noreply@curama.jp` からのメールは今後のタスクリスト生成において完全に無視する（クエリ1で除外済み。個別クエリでの追加確認も行わない）。

両クエリの結果を Thread ID でマージ・重複排除し、`gmail_data` として secretary エージェントに渡す。

---

### Slack — 全チャンネルスキャン + タイムスタンプ手動フィルタ

Slack MCP の `get_channel_history` は期間指定パラメータを持たないため、メッセージ取得後に `ts`（Unix 秒）で手動フィルタする。

`last_date` を Unix タイムスタンプに変換する:
```python
import datetime, zoneinfo
JST = zoneinfo.ZoneInfo("Asia/Tokyo")
d = datetime.datetime.strptime("{last_date}", "%Y-%m-%d").replace(tzinfo=JST)
print(int(d.timestamp()))  # → last_date_ts（float）
```

**sankei ワークスペース（中田のタスク発生源）:**
1. `mcp__slack-sankei__slack_list_channels` でチャンネル一覧を取得
2. 各チャンネルに `mcp__slack-sankei__slack_get_channel_history`（`limit: 50`）を並列実行
3. 取得したメッセージを `float(ts) >= last_date_ts` でフィルタ
4. フィルタ後にメッセージが残るチャンネルのみ `slack_sankei_data` に記録

**concierge ワークスペース（参考情報）:**
1. `mcp__slack-concierge__slack_list_channels` でチャンネル一覧を取得
2. 各チャンネルに `mcp__slack-concierge__slack_get_channel_history`（`limit: 50`）を並列実行
3. `float(ts) >= last_date_ts` でフィルタ
4. フィルタ後に残るチャンネルのみ `slack_concierge_data` に記録

**limit の目安:**
- `last_date` からの経過が1〜2日 → `limit: 20` で十分
- `last_date` からの経過が3〜7日 → `limit: 50`
- `last_date` からの経過が7日超 → `limit: 100`（Slack API 上限に近い）

収集した内容を `slack_sankei_data` と `slack_concierge_data` として secretary エージェントに渡す。

---

あわせて `tasks/long-term-schedule.md` を読み込み、進行中プロジェクトの納期・ステータスを把握する。

### 2-B. secretary エージェント（バックグラウンド起動）

以下のプロンプトで `secretary` エージェントをバックグラウンド起動する:

> `/task モードで動作してください。last_date={last_date}、TODAY={TODAY} として収集・分析してください。
>
> 【重要】ユーザーは「中田」です。以下の区別を守ること:
> - Slack sankei: 中田のタスクが発生する可能性あり → 通常通り分析
> - Slack concierge: 別会社の内部ワークスペース → 情報収集のみ。「中田」が名指しされている場合を除き、タスクとして抽出しない
>
> 【前日完了済みタスク（これらに関連するメールは新規タスク・要返信として扱わないこと）】
> {completed_tasks の一覧}
>
> 【Gmail 収集済みデータ（メインエージェントが取得済み）】
> {gmail_data の全文}
>
> 【Slack sankei 収集済みデータ（メインエージェントが取得済み）】
> {slack_sankei_data の全文}
>
> 【Slack concierge 収集済みデータ（参考情報のみ）】
> {slack_concierge_data の全文}
>
> 上記の収集済みデータを分析し、Google Calendar（mcp__google-calendar__list-events で本日の予定を取得）を追加取得して「秘書分析レポート」フォーマットで結果を返してください。
> Gmail・Slack はすでに収集済みのため再取得不要です。
> concierge 由来のタスク候補は必ず「concierge（参考）」と明記すること。`

### 2-C. pm エージェント（バックグラウンド起動）

以下のプロンプトで `pm` エージェントをバックグラウンド起動する:

> `/task モードで動作してください。last_date={last_date}、TODAY={TODAY} として収集・分析してください。
>
> 【重要】ユーザーは「中田」です。各タスク候補について必ず帰属を判定すること:
> - 中田のタスク: 中田が直接アクションする / 相手が中田の返答を待っている
> - 他メンバーのタスク（八原・川元・吉田・楠田など）: 中田のリストには含めず「チームの動き」として記録
> - 相手待ち: 中田が依頼済みで返答待ちのもの → 「中田のタスク」ではなく「相手待ち」として分類
>
> Chatwork は以下のコマンドで自律収集してください:
> python3 scripts/fetch_chatwork.py {last_date}
>
> 長期スケジュールは tasks/long-term-schedule.md を読み込んでください。
>
> 収集した内容を分析し、「PM分析レポート」フォーマットで返してください。
> 各タスク候補に「中田のタスク / {担当者}のタスク / 相手待ち」を明記すること。`

---

## Step 3: Phase 2-A — スケジュール監査（scheduler）

secretary・pm・メイン の結果が揃ったら、`scheduler` エージェントを起動する:

> `スケジュール監査をしてください。TODAY={TODAY}。
> 【重要】ユーザーは「中田」です。監査対象は「中田のタスク」のみです。他メンバーのタスクや相手待ち事項は監査対象外。
>
> 【pm報告】{pmの出力全文}
> 【secretary報告】{secretaryの出力全文}
> 【持ち越しタスク（未完了）】{pending_tasks の一覧}
> 【完了済みタスク（警告対象外）】{completed_tasks の一覧 — これらへの「未対応」「滞留」「期限超過」警告は出さないこと}
> 【フォローアップ期限切れ候補（相手待ち3日以上）】{Step C-4 で検出したルームと経過日数の一覧}
> 「スケジュール監査レポート」フォーマットで結果を返してください。`

scheduler の結果を受け取る。

---

## Step 4: Phase 2-B — アクション提案（strategist）

scheduler の結果が揃ったら、`strategist` エージェントを起動する:

> `アクション提案をしてください。TODAY={TODAY}。
> 【重要】ユーザーは「中田」です。提案するアクションは「中田が直接実行できること」に限定してください。
>
> 【pm報告】{pmの出力全文}
> 【secretary報告】{secretaryの出力全文}
> 【scheduler監査レポート】{schedulerの出力全文}
> 【持ち越しタスク】{前回ノートから抽出した未完了タスク一覧}
> 「アクション提案レポート」フォーマットで結果を返してください。`

strategist の結果を受け取る。

---

## Step 5: Phase 3 — 統合・Markdown生成

5つのソース（メイン・secretary・pm・scheduler・strategist）の結果を統合する。

**統合ルール:**
- タスクリストに含めるのは「中田のタスク」のみ
- pm・secretary が「他メンバーのタスク」「相手待ち」と分類したものはタスクリストに入れず、「📋 チームの動き」「⏳ 相手待ち」セクションに分ける
- concierge 由来のタスクは原則除外（secretary が「中田名指し」と判定したものだけ含める）
- `scheduler` が「記載漏れ候補」として挙げたタスクをタスクリストに追加する
- `scheduler` が「優先度引き上げ推奨」としたタスクの優先度を更新する
- `strategist` の「今日の最重要1アクション」を 🔴 最優先の先頭に配置する
- `strategist` の「今日やらなくていいこと」は 🟢 通常に降格するか除外する
- secretary・pm の両方から同じ案件が出た場合は統合して1件にまとめる
- **completed_tasks に含まれるタスクは、タスクリスト・📌 要返信・⚠️ スケジューラー警告のいずれにも含めない**（「前日タスク完了状況」テーブルでのみ ☑ 完了 として記録する）
- **曜日は必ず Step 1 で取得した `TODAY_WITH_DOW` を使う**（LLM による曜日の推測・計算は禁止）

以下のフォーマットで内容を生成する。

```
✅ チェックリスト（完了したらチェックを入れる）

🔴 最優先
{🔴タスク名を1行ずつ - [ ] タスク名 の形式で列挙（Markdownチェックリスト構文）}

🟡 優先
{🟡タスク名を1行ずつ - [ ] タスク名 の形式で列挙}

🟢 通常
{🟢タスク名を1行ずつ - [ ] タスク名 の形式で列挙}

📌 要返信
{要返信項目を1行ずつ - [ ] 相手名: 内容 の形式で列挙}

• ////

📅 今日のスケジュール
{secretary から取得した本日の予定を時系列で列挙}
（予定がない場合は「本日の予定なし」）

• ////

📋 長期プロジェクト進捗
{pm から取得したプロジェクト状況 + scheduler の漏れ指摘を反映}
• {プロジェクト名}（納期 {M/D}）
  - 現状: {ステータス}
  - リスク: {リスクレベルと内容}
  - 次のアクション（中田）: {中田が直接やること}
  - チームの動き: {他メンバーが対応中の内容}

• ////

🎯 今日の最重要アクション（strategist推奨）
{strategist が提案した「今日の最重要1アクション」をそのまま記載}

• ////

🔴 最優先（今日中）

• {タスク名}
詳細: {中田が具体的にやること}
由来: {Chatwork/Gmail/Calendar/持ち越し等}
期限: 今日中

• ////

🟡 優先（今週中）

• {タスク名}
詳細: {中田が具体的にやること}
由来: {由来}
期限: {具体的な期限}

• ////

🟢 通常（来週以降）

• {タスク名}
詳細: {中田が具体的にやること}
由来: {由来}
期限: {期限または「未定」}

• ////

📌 要返信・要確認（返信方針付き）
| 相手 | 内容 | 推奨対応（中田のアクション） | 期限 |
|------|------|--------------------------|------|
| {名前/ルーム名} | {要対応内容} | {strategistの返信方針} | {期限} |

• ////

⏳ 相手待ち（中田のアクション不要）
| 相手 | 内容 | 待ち理由 |
|------|------|---------|
| {名前} | {内容} | {誰が/何を待っているか} |

• ////

📋 チームの動き（参考）
{中田以外が対応中の事項。中田のタスクではないが把握しておくもの}
• {担当者}: {対応内容}

• ////

⚠️ スケジューラー警告
• {scheduler が検出した中田タスクの漏れ・滞留・期限連鎖アラートを列挙}
（問題なければ「特記事項なし」）

• ////

💡 今日やらなくていいこと（strategist）
| 項目 | 理由 |
|------|------|
| {タスク名} | {除外推奨の理由} |

• ////

日次業務サマリー — {last_date}
> 作成: {作成日時} JST

全体サマリー
{対象期間全体の一言まとめ（2〜3文）}

Gmail — 重要メール
{secretaryから取得。件名・送信者・要点}

Google Calendar — 予定
{secretaryから取得。日付付きで列挙}

Chatwork — 重要やりとりと要返信事項
• {pmから取得。中田関連のやりとり概要と未返信}

Slack (sankei)
• {secretaryから取得。重要投稿を列挙}

Slack (concierge) — 参考情報
{secretaryから取得。中田関連のもののみ記載。なければ「特記なし」}

前日タスク完了状況
| タスク | 状態 |
|--------|------|
| {前回ノートのタスク名} | ☑ 完了 / ☐ 未完了 |

当日追加・編集メモ
（Obsidianノートで手動追記があれば反映）

次にやること（推奨3件）※ strategist提案を優先採用
1. {最優先のアクション}
2. {2番目のアクション}
3. {3番目のアクション}
```

対象期間が1日のみの場合（前日〜当日）は「日次業務サマリー — {last_date}」と記載する。

---

## Step 6: Obsidian Vault に書き出す

### 6-A. Markdown を Obsidian Vault の todo フォルダに直接書き込む

Step 5 で生成した Markdown 全文を、Write ツールで以下のパスに直接書き込む（✅ チェックリストが冒頭にあるためそのまま全タスク項目がノート冒頭に来る）:

```
/Users/kokinakata/Library/Mobile Documents/iCloud~md~obsidian/Documents/Obsidian Vault/todo/タスクリスト — {TODAY}.md
```

- 同名ファイルが既に存在する場合は上書きする（Write ツールの通常動作）
- プレーンな Markdown ファイルなので AppleScript 等の変換・書き込み検証は不要

### 6-A-2. obsidian-tasks-sync リポジトリにも反映する

Obsidian Vault はこのリポジトリを git remote として追跡している。クラウド側の自動実行（Remote Trigger）が前日状態を判定する際にこのリポジトリを「前日ノートの唯一の参照先」として使うため、手動実行時も必ず反映すること:

```bash
cd "/Users/kokinakata/Library/Mobile Documents/iCloud~md~obsidian/Documents/Obsidian Vault"
git add "todo/タスクリスト — {TODAY}.md"
git commit -m "chore: task list {TODAY}"
git push origin main
```

- 変更がない場合（差分なし）はコミットをスキップする
- push が失敗した場合（iCloud同期タイミング等でconflictが起きた場合）は `git pull origin main --no-edit` してから再度 push する

### 6-B. Gmail で通知メールを送信する

`mcp__gmail__send_email` を使い、以下の内容で送信する:
- **宛先**: contactcomparison@gmail.com
- **件名**: `【タスクリスト】{TODAY_WITH_DOW}`
- **本文**:

```
おはようございます。本日（{TODAY_WITH_DOW}）のタスクリストをObsidian Vaultに作成しました。

━━━━━━━━━━━━━━━━━━
🎯 今日の最重要アクション
{strategist が提案した最重要1アクション}

🔴 最優先タスク（{🔴タスク件数}件）
{🔴タスクの名前を箇条書きで列挙}

📌 要返信・要確認（{要返信件数}件）
{要返信相手と内容を箇条書きで列挙}

⚠️ スケジューラー警告
{警告内容。なければ「特記事項なし」}
━━━━━━━━━━━━━━━━━━

カバー期間: {last_date} 〜 {TODAY}
中田タスク数: 🔴{N}件 / 🟡{N}件 / 🟢{N}件
```

書き出し完了後、以下を表示する:
```
✅ タスクリストをObsidian Vaultに書き出しました。
   ノート名: タスクリスト — {TODAY}
   保存先: Obsidian Vault > todo
   カバー期間: {last_date} 〜 {TODAY}
   中田タスク数: 🔴{N}件 / 🟡{N}件 / 🟢{N}件
   要返信: {N}件 / 相手待ち: {N}件
   スケジューラー警告: {N}件
   チーム: secretary + pm（並列収集）→ scheduler（監査）→ strategist（提案）
✉️  通知メールを contactcomparison@gmail.com に送信しました。
```

---

## 注意事項

- タスク項目は **`• タスク名`** 形式で記述し、詳細/由来/期限は平文で続ける（`**太字**` マークダウンは使わない）
- セクション間は **`• ////`** で区切る
- 長期プロジェクト・チームの動き・スケジューラー警告の箇条書きも **`•`** を使う
- **タスクリストに含めるのは「中田のタスク」のみ**。他メンバー担当・相手待ちは別セクションへ
- Slack concierge は参考情報扱い。中田名指し以外はタスク化しない
- 推測でタスクを生成しない。情報が不足している場合は「未確認」と記載する
- **前回ノートのチェックリストにユーザーが手書きで追加した自由記述（`handwritten_tasks`）は、詳細が確認できなくても必ず当日のタスクリストに反映する。** 「情報不足だから除外」ではなく「詳細未確認のタスクとして掲載」が正しい扱い
- WordPress リンク切れ通知メールでも「リンクエラー: 0」「エラー数: 0」などエラー件数が 0 の場合はタスクに含めない（通知メールが来ても実害なし）
- **くらしのマーケット（curama.jp）のメール通知は今後無視する。** タスク候補・要返信・スケジューラー警告のいずれにも含めない（ユーザー指示、2026-07-27）
- 未返信メッセージがある場合は 🔴 最優先または 📌 要返信に必ず記載する
- 長期スケジュールの納期が2週間以内のプロジェクトは 🔴 最優先に含める
- 土日は基本休みだが、Chatwork/Gmail に活動がある場合はサマリーに含める
- 前回ノートが Obsidian Vault の todo フォルダに見つからない場合は `last_date = 昨日`、completed/pending はともに空として処理する
- **前回タスクの参照源は Obsidian Vault の `todo` フォルダのみ**。`tasks/last-task.md` は参照・更新しない
- 各エージェントが返す情報は信頼して使用する。エージェントへの再確認は不要
- **曜日は必ず bash で取得した値を使う。LLM による曜日推測は禁止**
- **前日に完了したタスクは、タスクリスト・要返信・スケジューラー警告に再出現させない**
- `tasks/long-term-schedule.md` はリポジトリ内のファイルとして参照する
- **Chatwork は pm エージェントが `scripts/fetch_chatwork.py {last_date}` で自律収集する。スクリプトが `last_update_time` で事前フィルタするためハードコードリスト不要**
- **Gmail はメインエージェントが 2クエリ（一般 + koto-hsc ドメイン専用）で収集し secretary に渡す。koto-hsc はカテゴリ自動分類で埋もれやすいため必ず個別クエリで確認する**
- **Slack はメインエージェントが全チャンネルを `limit:50` で取得後 `ts` で手動フィルタし secretary に渡す（Slack MCP に期間指定パラメータがないため）**
- 新規プロジェクト・新規外注が始まった場合は `tasks/long-term-schedule.md` を更新しておくことで次回以降の pm エージェントの分析精度が上がる

$ARGUMENTS
