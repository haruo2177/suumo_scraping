# -*- coding: utf-8 -*-
import json

import logging
import logging.handlers

import os
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
    date_of_construction = dottable_lines[4].find_all('dd')[1].text
    # 管理会社
    company = ''
    if property_unit.find('div', {'class': 'shopmore-title'}) is not None:
        company = property_unit.find('div', {'class': 'shopmore-title'}).text.strip()

    return [property_id, name, url, price, location, station, area, floor_plan, balcony, date_of_construction, company]


def setup_logger(name, logfile=config['log']):
    """loggerの初期設定を行う

    Args:
        name (string): __name__
        logfile (string, optional): log file path. Defaults to config['log'].

    Returns:
        logging: set up logger
    """
    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)

    # create file handler which logs even DEBUG messages
    os.makedirs(os.path.dirname(config['log']), exist_ok=True)
    fh = logging.handlers.RotatingFileHandler(logfile, maxBytes=100000, backupCount=10)
    fh.setLevel(logging.DEBUG)
    fh_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(filename)s - %(name)s - %(funcName)s - %(message)s')
    fh.setFormatter(fh_formatter)

    # create console handler with a INFO log level
    ch = logging.StreamHandler()
    ch.setLevel(logging.INFO)
    ch_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s', '%Y-%m-%d %H:%M:%S')
    ch.setFormatter(ch_formatter)

    # add the handlers to the logger
    logger.addHandler(fh)
    logger.addHandler(ch)
    return logger


if __name__ == '__main__':
    # logger設定
    logger = setup_logger(__name__)

    # 検索結果ページのHTMLからbodyを抽出
    result = requests.get(config["result_url"])
    soup = BeautifulSoup(result.content, 'html5lib')
    body = soup.find('body')
    logger.info('get body of specified page.')

    # 検索結果のページ数を取得
    pagenation = body.find('div', {'class': 'pagination pagination_set-nav'})
    li = pagenation.find_all('li')[-1]
    page_num = int(li.find('a').text) if li.find('a') else 1
    logger.info(f'get number of pages, {page_num}.')

    # 検索結果1ページ目の物件データ収集
    # 1ページ目はURLにpnクエリが無いため
    properties = list()
    for property_unit in body.find_all('div', {'class': 'property_unit'}):
        properties.append(get_property_data(property_unit))
    logger.info(f'get {len(properties)} properties information from p.1.')

    # 2ページ目以降の各物件データ収集
    for i in range(2, page_num + 1):
        url = config["result_url"] + '&pn=' + str(i)
        result = requests.get(url)
        soup = BeautifulSoup(result.content, 'html5lib')
        body = soup.find('body')
        for property_unit in body.find_all('div', {'class': 'property_unit'}):
            properties.append(get_property_data(property_unit))
        logger.info(f'get {len(properties)} properties information from p.{i}.')

    # LINE通知設定
    is_line_notify = os.path.exists(config['data'])

    # 更新前の物件情報ファイルを読み込む
    if os.path.exists(f"{config['data']}"):
        df_old = pd.read_csv(f"{config['data']}")
    else:
        df_old = pd.DataFrame(data=list(), columns=config['header'])
    logger.info(f'read {len(df_old)} old-properties.')

    # 取得した物件情報をデータフレームに変換してCSVに出力
    df_new = pd.DataFrame(data=properties, columns=config['header'])
    df_new.to_csv(config['data'], index=False)
    logger.info(f'save {len(df_new)} new-properties to csv.')

    # 物件情報を確認して差分があればLINE通知
    if is_line_notify:
        list_old = df_old['id'].tolist()
        list_new = df_new['id'].tolist()

        # 追加物件
        added_properties = set(list_new) - set(list_old)
        if added_properties == set():
            logger.info('NOT added from last time.')
        else:
            logger.info('added from last time.')
            logger.info(added_properties)
            message = ''
            for added_property in added_properties:
                message += df_new.query('id == @added_property')['url'].values[0] + '\r\n'
            send_line_notify('次の物件が追加されました\r\n' + message)
            logger.info('send LINE Notify.')
            logger.info(message)

        # 削除物件
        reduced_properties = set(list_old) - set(list_new)
        if reduced_properties == set():
            logger.info('NOT reduced from last time.')
        else:
            logger.info('reduced from last time.')
            logger.info(reduced_properties)
            message = ''
            for reduced_property in reduced_properties:
                message += str(df_old.query('id == @reduced_property').loc[:, ['name', 'price', 'location']].values[0]) + '\r\n'
            send_line_notify('次の物件が削除されました\r\n' + message)
            logger.info('send LINE Notify.')
            logger.info(message)

        # 価格変動
        message_price = ''
        for item_new in list_new:
            item_old = df_old.query('id == @item_new')
            if len(item_old) == 0:
                continue
            name_and_price_new = df_new.query('id == @item_new').loc[:, ['name', 'url', 'price']].values[0]
            name_and_price_old = df_old.query('id == @item_new').loc[:, ['name', 'url', 'price']].values[0]
            if name_and_price_new[2] != name_and_price_old[2]:
                message_price += name_and_price_new[0] + ' '
                message_price += name_and_price_old[2] + ' => ' + name_and_price_new[2] + '\r\n'
                message_price += name_and_price_new[1] + '\r\n'
        if message_price != '':
            logger.info('fluctuated from last time.')
            send_line_notify('次の物件価格が変更されました\r\n' + message_price)
            logger.info('send LINE Notify.')
            logger.info(message_price)
        else:
            logger.info('NOT fluctuated from last time.')
