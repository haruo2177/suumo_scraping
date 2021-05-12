# suumo_scraping

## 概要

suumo の中古マンション購入ページをスクレイピングして
差分があれば LINE に通知する Python コードです。

個人用途以外で利用しないでください。

## 動作環境

Windows Pro 20H2, Python 3.9.1

まぁそんな変なもの使ってないのであまりバージョンは気にせずで大丈夫かと

## 事前準備

### 設定ファイルをコピー

```shell
cp config.json.example config.json
```

### LINE Notify のアクセストークンを取得

1. LINE 通知用のグループを作成して、LINE Notify アカウントを招待する
1. なんかググって LINE Notify トークンを取得する
1. 取得したトークンを config.json の"line_notify_api"に貼り付ける

### suuumo で中古マンションを検索

1. https://suumo.jp/kanto/ にアクセスする
1. 中古マンション買うボタンを押す
1. 「エリアから探す」で適当な地域とか条件とかで検索する
1. 検索結果の URL を config.json の"result_url"に貼り付ける

### パッケージインストール

```python
pip install -r requirements.txt
```

これで事前準備は終了です。

## python 実行

```python
python get_property.py
```

## 結果確認

property.csv が生成され、各物件の情報が記載されている。

2 回目以降の python 実行で、物件情報に以下の差分があれば LINE に通知される。

- 追加
- 削除
- 価格

※ 掲載されなくなった物件は CSV からも削除されるので注意してください。

## ToDo

1. コードをきれいにする
1. 収集データの分析コードを追加する
1. 機能ごとに関数を分割(取得、読込、比較、etc...)
1. 重複物件の削除処理
1. アットホーム、ホームズ取得処理
