# suumo_scraping

## 概要
suumoの中古マンション購入ページをスクレイピングして
差分があればLINEに通知するPythonコードです。

個人用途以外で利用しないでください。

## 動作環境
Windows Pro 20H2, Python 3.9.1

まぁそんな変なもの使ってないのであまりバージョンは気にせずで大丈夫かと

## 事前準備

### 設定ファイルをコピー
```shell
cp config.json.example config.json
```

### LINE Notifyのアクセストークンを取得
1. LINE通知用のグループを作成して、LINE Notifyアカウントを招待する
1. なんかググってLINE Notifyトークンを取得する
1. 取得したトークンをconfig.jsonの"line_notify_api"に貼り付ける

### suuumoで中古マンションを検索
1. https://suumo.jp/kanto/ にアクセスする
1. 中古マンション買うボタンを押す
1. 「エリアから探す」で適当な地域とか条件とかで検索する
1. 検索結果のURLをconfig.jsonの"result_url"に貼り付ける

### パッケージインストール
```python
pip install -r requirements.txt
```

これで事前準備は終了です。

## python実行
```python
python get_property.py
```

## 結果確認
property.csvが生成され、各物件の情報が記載されている。

2回目以降のpython実行で、物件情報に差分があればLINEに通知される。

※ 掲載されなくなった物件はCSVからも削除されるので注意してください。