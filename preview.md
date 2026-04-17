# Prompt Preview

- Generated: 2026-04-18T02:19:32
- Sample data: `data/sample_packet.yml`
- Blocks: `prompts/*.jinja`

このファイルは `scripts/preview_prompt.py` により自動生成されます. 
プロンプトテンプレートやブロックを変更した後に再実行すると上書き更新されます.

---

## Mode: multi_turn

- Config: `config/config.multi_turn.jp.yml.example`
- LLM: type=`google` / separate_langchain=`False`

### `initialize`

- Length: 195 chars

```
あなたの名前: kanolab1
あなたの役職: SEER
あなたのプロフィール: 名前: 佐藤 / 年齢: 25 / 性別: 男性 / 論理的で慎重な性格。村の若手のまとめ役。

ゲーム開始リクエストです。以降のリクエストに対し日本語で適切に応答してください。

以降のリクエストには日本語で応答してください。レスポンスはそのままゲームに送信されるため, 不要な情報を含めないでください。
```

### `daily_initialize`

- Length: 330 chars

```
2日目が始まりました。

Day 1 (daily_finish)
  追放結果: kanolab3
  投票結果: [{'day': 1, 'agent': 'kanolab1', 'target': 'kanolab3'}, {'day': 1, 'agent': 'kanolab2', 'target': 'kanolab3'}, {'day': 1, 'agent': 'kanolab4', 'target': 'kanolab3'}]
Day 2 (daily_initialize)
  占い結果: {'day': 2, 'agent': 'kanolab1', 'target': 'kanolab4', 'result': 'HUMAN'}
```

### `daily_finish`

- Length: 411 chars

```
2日目が終了しました。

Day 1 (daily_finish)
  追放結果: kanolab3
  投票結果: [{'day': 1, 'agent': 'kanolab1', 'target': 'kanolab3'}, {'day': 1, 'agent': 'kanolab2', 'target': 'kanolab3'}, {'day': 1, 'agent': 'kanolab4', 'target': 'kanolab3'}]
Day 2 (daily_initialize)
  占い結果: {'day': 2, 'agent': 'kanolab1', 'target': 'kanolab4', 'result': 'HUMAN'}

kanolab4: 昨日の投票で kanolab3 が追放されましたね。次が肝心です。
kanolab5: 私は kanolab2 が少し不自然に感じました。
```

### `talk`

- Length: 222 chars

```
kanolab4: 昨日の投票で kanolab3 が追放されましたね。次が肝心です。
kanolab5: 私は kanolab2 が少し不自然に感じました。

現在 2日目のトークリクエストです。ゲーム内で発言すべき内容を出力してください。

1発言あたり最大 150 文字以内で出力してください。
発言内容のみを出力してください。説明やメタ情報、前置きは含めないでください。
これ以上発言することがない場合は「Over」と出力してください。
```

### `whisper`

- Length: 212 chars

```
kanolab1: 今日は kanolab3 を狙うのが安全そうだね。
kanolab4: 賛成。村側に疑われないよう表では別の話題を振ろう。

現在 2日目の囁きリクエストです。人狼仲間に対する囁きの内容を出力してください。

1発言あたり最大 100 文字以内で出力してください。
囁き内容のみを出力してください。説明やメタ情報、前置きは含めないでください。
これ以上囁くことがない場合は「Over」と出力してください。
```

### `divine`

- Length: 123 chars

```
占いリクエストです。占い対象のエージェント名のみを出力してください。

対象:
kanolab1
kanolab2
kanolab4
kanolab5

対象エージェント名のみを出力してください。説明・理由・記号・接頭辞は一切含めないでください。
```

### `guard`

- Length: 123 chars

```
護衛リクエストです。護衛対象のエージェント名のみを出力してください。

対象:
kanolab1
kanolab2
kanolab4
kanolab5

対象エージェント名のみを出力してください。説明・理由・記号・接頭辞は一切含めないでください。
```

### `vote`

- Length: 125 chars

```
投票リクエストです。追放投票の対象エージェント名のみを出力してください。

対象:
kanolab1
kanolab2
kanolab4
kanolab5

対象エージェント名のみを出力してください。説明・理由・記号・接頭辞は一切含めないでください。
```

### `attack`

- Length: 123 chars

```
襲撃リクエストです。襲撃対象のエージェント名のみを出力してください。

対象:
kanolab1
kanolab2
kanolab4
kanolab5

対象エージェント名のみを出力してください。説明・理由・記号・接頭辞は一切含めないでください。
```

---

## Mode: single_turn

- Config: `config/config.single_turn.jp.yml.example`
- LLM: type=`google` / separate_langchain=`False`

### `talk`

- Length: 715 chars

```
あなたの名前: kanolab1
あなたの役職: SEER
あなたのプロフィール: 名前: 佐藤 / 年齢: 25 / 性別: 男性 / 論理的で慎重な性格。村の若手のまとめ役。


# 日次イベント
Day 1 (daily_finish)
  追放結果: kanolab3
  投票結果: [{'day': 1, 'agent': 'kanolab1', 'target': 'kanolab3'}, {'day': 1, 'agent': 'kanolab2', 'target': 'kanolab3'}, {'day': 1, 'agent': 'kanolab4', 'target': 'kanolab3'}]
Day 2 (daily_initialize)
  占い結果: {'day': 2, 'agent': 'kanolab1', 'target': 'kanolab4', 'result': 'HUMAN'}


# トーク履歴
kanolab1: おはよう。まずは自己紹介から始めませんか。
kanolab2: いいですね。僕は静かに見守るタイプです。
kanolab4: 昨日の投票で kanolab3 が追放されましたね。次が肝心です。
kanolab5: 私は kanolab2 が少し不自然に感じました。


現在 2日目のトークリクエストです。ゲーム内で発言すべき内容を出力してください。

1発言あたり最大 150 文字以内で出力してください。
発言内容のみを出力してください。説明やメタ情報、前置きは含めないでください。
これ以上発言することがない場合は「Over」と出力してください。
```

### `whisper`

- Length: 641 chars

```
あなたの名前: kanolab1
あなたの役職: SEER
あなたのプロフィール: 名前: 佐藤 / 年齢: 25 / 性別: 男性 / 論理的で慎重な性格。村の若手のまとめ役。


# 日次イベント
Day 1 (daily_finish)
  追放結果: kanolab3
  投票結果: [{'day': 1, 'agent': 'kanolab1', 'target': 'kanolab3'}, {'day': 1, 'agent': 'kanolab2', 'target': 'kanolab3'}, {'day': 1, 'agent': 'kanolab4', 'target': 'kanolab3'}]
Day 2 (daily_initialize)
  占い結果: {'day': 2, 'agent': 'kanolab1', 'target': 'kanolab4', 'result': 'HUMAN'}


# 囁き履歴
kanolab1: 今日は kanolab3 を狙うのが安全そうだね。
kanolab4: 賛成。村側に疑われないよう表では別の話題を振ろう。


現在 2日目の囁きリクエストです。人狼仲間に対する囁きの内容を出力してください。

1発言あたり最大 100 文字以内で出力してください。
囁き内容のみを出力してください。説明やメタ情報、前置きは含めないでください。
これ以上囁くことがない場合は「Over」と出力してください。
```

### `divine`

- Length: 697 chars

```
あなたの名前: kanolab1
あなたの役職: SEER
あなたのプロフィール: 名前: 佐藤 / 年齢: 25 / 性別: 男性 / 論理的で慎重な性格。村の若手のまとめ役。


# 日次イベント
Day 1 (daily_finish)
  追放結果: kanolab3
  投票結果: [{'day': 1, 'agent': 'kanolab1', 'target': 'kanolab3'}, {'day': 1, 'agent': 'kanolab2', 'target': 'kanolab3'}, {'day': 1, 'agent': 'kanolab4', 'target': 'kanolab3'}]
Day 2 (daily_initialize)
  占い結果: {'day': 2, 'agent': 'kanolab1', 'target': 'kanolab4', 'result': 'HUMAN'}


# トーク履歴
kanolab1: おはよう。まずは自己紹介から始めませんか。
kanolab2: いいですね。僕は静かに見守るタイプです。
kanolab4: 昨日の投票で kanolab3 が追放されましたね。次が肝心です。
kanolab5: 私は kanolab2 が少し不自然に感じました。


占いリクエストです。占い対象のエージェント名のみを出力してください。

対象:
kanolab1
kanolab2
kanolab4
kanolab5

対象エージェント名のみを出力してください。説明・理由・記号・接頭辞は一切含めないでください。
```

### `guard`

- Length: 697 chars

```
あなたの名前: kanolab1
あなたの役職: SEER
あなたのプロフィール: 名前: 佐藤 / 年齢: 25 / 性別: 男性 / 論理的で慎重な性格。村の若手のまとめ役。


# 日次イベント
Day 1 (daily_finish)
  追放結果: kanolab3
  投票結果: [{'day': 1, 'agent': 'kanolab1', 'target': 'kanolab3'}, {'day': 1, 'agent': 'kanolab2', 'target': 'kanolab3'}, {'day': 1, 'agent': 'kanolab4', 'target': 'kanolab3'}]
Day 2 (daily_initialize)
  占い結果: {'day': 2, 'agent': 'kanolab1', 'target': 'kanolab4', 'result': 'HUMAN'}


# トーク履歴
kanolab1: おはよう。まずは自己紹介から始めませんか。
kanolab2: いいですね。僕は静かに見守るタイプです。
kanolab4: 昨日の投票で kanolab3 が追放されましたね。次が肝心です。
kanolab5: 私は kanolab2 が少し不自然に感じました。


護衛リクエストです。護衛対象のエージェント名のみを出力してください。

対象:
kanolab1
kanolab2
kanolab4
kanolab5

対象エージェント名のみを出力してください。説明・理由・記号・接頭辞は一切含めないでください。
```

### `vote`

- Length: 699 chars

```
あなたの名前: kanolab1
あなたの役職: SEER
あなたのプロフィール: 名前: 佐藤 / 年齢: 25 / 性別: 男性 / 論理的で慎重な性格。村の若手のまとめ役。


# 日次イベント
Day 1 (daily_finish)
  追放結果: kanolab3
  投票結果: [{'day': 1, 'agent': 'kanolab1', 'target': 'kanolab3'}, {'day': 1, 'agent': 'kanolab2', 'target': 'kanolab3'}, {'day': 1, 'agent': 'kanolab4', 'target': 'kanolab3'}]
Day 2 (daily_initialize)
  占い結果: {'day': 2, 'agent': 'kanolab1', 'target': 'kanolab4', 'result': 'HUMAN'}


# トーク履歴
kanolab1: おはよう。まずは自己紹介から始めませんか。
kanolab2: いいですね。僕は静かに見守るタイプです。
kanolab4: 昨日の投票で kanolab3 が追放されましたね。次が肝心です。
kanolab5: 私は kanolab2 が少し不自然に感じました。


投票リクエストです。追放投票の対象エージェント名のみを出力してください。

対象:
kanolab1
kanolab2
kanolab4
kanolab5

対象エージェント名のみを出力してください。説明・理由・記号・接頭辞は一切含めないでください。
```

### `attack`

- Length: 625 chars

```
あなたの名前: kanolab1
あなたの役職: SEER
あなたのプロフィール: 名前: 佐藤 / 年齢: 25 / 性別: 男性 / 論理的で慎重な性格。村の若手のまとめ役。


# 日次イベント
Day 1 (daily_finish)
  追放結果: kanolab3
  投票結果: [{'day': 1, 'agent': 'kanolab1', 'target': 'kanolab3'}, {'day': 1, 'agent': 'kanolab2', 'target': 'kanolab3'}, {'day': 1, 'agent': 'kanolab4', 'target': 'kanolab3'}]
Day 2 (daily_initialize)
  占い結果: {'day': 2, 'agent': 'kanolab1', 'target': 'kanolab4', 'result': 'HUMAN'}


# 囁き履歴
kanolab1: 今日は kanolab3 を狙うのが安全そうだね。
kanolab4: 賛成。村側に疑われないよう表では別の話題を振ろう。


襲撃リクエストです。襲撃対象のエージェント名のみを出力してください。

対象:
kanolab1
kanolab2
kanolab4
kanolab5

対象エージェント名のみを出力してください。説明・理由・記号・接頭辞は一切含めないでください。
```

---
