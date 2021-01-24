# -*- coding: utf-8 -*-
import json
import os
import csv
import pandas as pd

import requests
from bs4 import BeautifulSoup

# configファイルを読み込む
json_file = open('config.json', 'r')
config = json.load(json_file)


def send_line_notify(notification_message):
    """ 受け取った文字列をLINEに通知する

    Args:
        notification_message (string): 送信するメッセージ内容
    """
    headers = {'Authorization': f'Bearer {config["line_notify_token"]}'}
    data = {'message': f'{notification_message}'}
    requests.post(config["line_notify_api"], headers=headers, data=data)


def get_property_data(property_unit):
    """ 一覧ページから各物件のデータを取得する

    Args:
        property_unit (string): [description]

    Return:
        (list): 物件の各情報
    """
    dottable_lines = property_unit.find_all('div', {'class': 'dottable-line'})
    # id, url
    link = property_unit.find('a').get('href')
    property_id = link.split('/')[-2]
    url = config['suumo_url'] + link
    # 物件名
    name = dottable_lines[0].find('dd').text
    # 販売価格
    price = dottable_lines[1].find('span').text
    # 所在地、沿線・駅
    location = dottable_lines[2].find_all('dd')[0].text
    station = dottable_lines[2].find_all('dd')[1].text
    # 専有面積、間取り
    area = dottable_lines[3].find_all('dd')[0].text
    floor_plan = dottable_lines[3].find_all('dd')[1].text
    # バルコニー、築年月
    balcony = dottable_lines[4].find_all('dd')[0].text
    data_of_construction = dottable_lines[4].find_all('dd')[1].text
    # 管理会社
    company = ''
    if property_unit.find('div', {'class': 'shopmore-title'}) is not None:
        company = property_unit.find('div', {'class': 'shopmore-title'}).text.strip()

    return [property_id, name, url, price, location, station, area, floor_plan, balcony, data_of_construction, company]


if __name__ == '__main__':
    # 物件情報ファイルを読み込む、無ければ作りLINE通知はしない
    line_notify = True
    if not os.path.exists(config['data']):
        line_notify = False
        with open(config['data'], 'w') as f:
            print('make file: ' + config['data'])
            writer = csv.writer(f)
            writer.writerow(config['header'])
    df_old = pd.read_csv(config['data'])
    print('[INFO] read property data.')
    print(len(df_old))

    # 検索結果ページのHTMLからbodyを抜き出す
    result = requests.get(config["result_url"])
    soup = BeautifulSoup(result.content, 'html5lib')
    body = soup.find('body')
    # print(body)

    # 検索結果のページ数を取得
    pagenation = body.find('div', {'class': 'pagination pagination_set-nav'})
    li = pagenation.find_all('li')[-1]
    page_num = int(li.find('a').text)
    print('[INFO] get number of pages.')
    print(page_num)

    # 1ページ目の物件データ収集してCSVに出力
    propertyies = list()
    for property_unit in body.find_all('div', {'class': 'property_unit'}):
        propertyies.append(get_property_data(property_unit))
    print('[INFO] get property information from p.1.')
    print(len(propertyies))

    # 2ページ名以降の各物件データ収集してCSVに出力
    for i in range(2, page_num + 1):
        url = config["result_url"] + '&pn=' + str(i)
        result = requests.get(url)
        soup = BeautifulSoup(result.content, 'html5lib')
        body = soup.find('body')
        for property_unit in body.find_all('div', {'class': 'property_unit'}):
            propertyies.append(get_property_data(property_unit))
        print('[INFO] get property information from p.{}.'.format(i))
        print(len(propertyies))

    # 取得した物件情報をデータフレームに変換
    df_new = pd.DataFrame(
        data=propertyies,
        columns=config['header']
    )
    df_new.to_csv(config['data'], index=False)
    print('[INFO] save property data to csv.')
    print(len(df_new))

    # 物件情報を確認して差分があればLINE通知
    list_old = df_old['id'].tolist()
    list_new = df_new['id'].tolist()

    # 追加物件
    added_properties = set(list_new) - set(list_old)
    if added_properties == set():
        print('[INFO] NOT addedd from last time.')
    else:
        print('[INFO] addedd from last time and notify to LINE.')
        print(added_properties)
        if line_notify:
            send_line_notify('次の物件が追加されました\r\n' + repr(added_properties))

    # 削除物件
    reduced_properties = set(list_old) - set(list_new)
    if reduced_properties == set():
        print('[INFO] NOT reduced from last time.')
    else:
        print('[INFO] reduced from last time and notify to LINE.')
        print(reduced_properties)
        if line_notify:
            send_line_notify('次の物件が削除されました\r\n' + repr(reduced_properties))
