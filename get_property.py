# -*- coding: utf-8 -*-
import json
import os
import csv
import logging
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
        property_unit (string): <div class='property_unit'>を抽出したテキスト

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
    # ロギング設定
    logging.basicConfig(filename='log', encoding='utf-8', level=logging.DEBUG)

    # 物件情報ファイルを読み込む、無ければ作りLINE通知はしない
    line_notify = True
    if not os.path.exists(config['data']):
        line_notify = False
        with open(config['data'], 'w') as f:
            logging.info('make file: ' + config['data'])
            writer = csv.writer(f)
            writer.writerow(config['header'])
    df_old = pd.read_csv(config['data'])
    logging.info('read property data.')
    logging.info(len(df_old))

    # 検索結果ページのHTMLからbodyを抽出
    result = requests.get(config["result_url"])
    soup = BeautifulSoup(result.content, 'html5lib')
    body = soup.find('body')
    # logging.info(body)

    # 検索結果のページ数を取得
    pagenation = body.find('div', {'class': 'pagination pagination_set-nav'})
    li = pagenation.find_all('li')[-1]
    page_num = int(li.find('a').text)
    logging.info('get number of pages.')
    logging.info(page_num)

    # 1ページ目の物件データ収集
    propertyies = list()
    for property_unit in body.find_all('div', {'class': 'property_unit'}):
        propertyies.append(get_property_data(property_unit))
    logging.info('get property information from p.1.')
    logging.info(len(propertyies))

    # 2ページ名以降の各物件データ収集
    for i in range(2, page_num + 1):
        url = config["result_url"] + '&pn=' + str(i)
        result = requests.get(url)
        soup = BeautifulSoup(result.content, 'html5lib')
        body = soup.find('body')
        for property_unit in body.find_all('div', {'class': 'property_unit'}):
            propertyies.append(get_property_data(property_unit))
        logging.info('get property information from p.{}.'.format(i))
        logging.info(len(propertyies))

    # 取得した物件情報をデータフレームに変換してCSVに出力
    df_new = pd.DataFrame(
        data=propertyies,
        columns=config['header']
    )
    df_new.to_csv(config['data'], index=False)
    logging.info('save property data to csv.')
    logging.info(len(df_new))

    # 物件情報を確認して差分があればLINE通知
    if line_notify:
        list_old = df_old['id'].tolist()
        list_new = df_new['id'].tolist()

        # 追加物件
        added_properties = set(list_new) - set(list_old)
        if added_properties == set():
            logging.info('NOT addedd from last time.')
        else:
            logging.info('addedd from last time.')
            logging.info(added_properties)
            message = ''
            for added_property in added_properties:
                message += df_new.query('id == @added_property')['url'].values[0] + '\r\n'
            send_line_notify('次の物件が追加されました\r\n' + message)
            logging.info('send LINE Notify.')
            logging.info(message)

        # 削除物件
        reduced_properties = set(list_old) - set(list_new)
        if reduced_properties == set():
            logging.info('NOT reduced from last time.')
        else:
            logging.info('reduced from last time.')
            logging.info(reduced_properties)
            message = ''
            for reduced_property in reduced_properties:
                message += str(df_old.query('id == @reduced_property').loc[:, ['name', 'price', 'location']].values[0]) + '\r\n'
            send_line_notify('次の物件が削除されました\r\n' + message)
            logging.info('send LINE Notify.')
            logging.info(message)
