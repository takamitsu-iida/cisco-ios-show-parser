#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Catalystのshow interfaces statusコマンドの出力を整形します。

show interfaces statusの出力は固定長の長さで整形されていますので、文字列の長さで情報を切り取ります。
辞書型に格納してから画面に表示したり、csv形式でファイルに保存します。

Examples:
  $ python -m doctest bin/cisco_ios_show_interfaces_status.py
  $ python bin/bin/cisco_ios_show_interfaces_status.py testdata/show_int_status.log

Note:
  結果は読み込んだデータと同じ場所に.csvで保存されます。
  別の場所に保存したい場合はコマンドの引数でファイル名を指定するか、スクリプトの改造が必要です。
"""

__author__ = 'Takamitsu IIDA <iida@jp.fujitsu.com>'
__version__ = '0.1'
__date__ = "2016/01/11"  # 初版
__date__ = "2018/02/25"  # classを使うように改造


#
# 標準ライブラリのインポート
#
import re
from collections import OrderedDict

#
# クラス定義
#

class CiscoIosShowInterfacesStatusParser(object):
  """Ciscoのshow interfaces status表示を加工するためのクラスです。

  """

  #
  # 想定しているコマンド出力
  #
  """
  想定しているコマンド出力
  E-Cat6880X-01#show int status
  Load for five secs: 7%/0%; one minute: 6%; five minutes: 6%
  Time source is NTP, 21:46:09.148 JST Sun Jan 10 2016

  Port          Name               Status       Vlan       Duplex  Speed Type
  Te1/1/1                          disabled     1            full   1000 1000BaseLH
  Te1/1/2                          disabled     1            full   1000 1000BaseLH

            1         2          3        4         5         6         7         8
  012345678901234567890123456789012345678901234567890123456789012345678901234567890
  --------------+------------------+------------+----------+-----+------+---------
  Port          Name               Status       Vlan       Duplex  Speed Type
  [0:14]        [14:33]            [33:46]      [46:57]    [57:63] [63:70][70:]
  """

  # 処理開始となる行
  start_string = "Port          Name               Status       Vlan       Duplex  Speed Type"

  # 1行における最小の文字数
  # これに満たない場合は次のコマンド表示に移っていると判断
  min_len = 70

  # 辞書型のデータを表示する際のキー一覧
  fieldnames = ["Port", "Name", "Status", "Vlan", "Duplex", "Speed", "Type"]


  def parse(self, lines):
    """リストの各行を精査してパラメータを辞書型にしたものをyieldします。

    一つのインタフェースに関する情報は１行に集約されていますので、各行から欲しい情報を切り取って辞書型に格納し、yieldします。

    Arguments:
      lines {list} -- show interfaces statusコマンド出力を行に分割した配列。

    Yields:
      {dict} -- インタフェース状態に関する情報を辞書型に変換したもの
    """

    # 処理中かどうか
    is_section = False

    # 行単位で走査
    for line in lines:
      # 改行コードを含む右端の余白を削除
      line = line.rstrip()

      # 処理開始を告げる行を発見
      if line == self.start_string:
        is_section = True
        # この行そのものに欲しい情報は含まれていない
        continue

      # 1行の長さが短い場合は、show int statusの表示から抜けたと見ていい
      if len(line) < self.min_len :
        is_section = False
        continue

      if not is_section :
        continue

      # その行から情報を抜き取って辞書型に変換してyield
      yield self.make_dict_by_line(line)


  def make_dict_by_line(self, line):
    """１行の情報からインタフェースの情報を辞書型にして返却します

    Arguments:
      line {str} -- show interfaces statusコマンド出力の1行

    Returns:
      dict -- インタフェース情報が格納された辞書型

    >>> line = "Te1/1/1                          disabled     1            full   1000 1000BaseLH"
    >>> parser = CiscoIosShowInterfacesStatusParser()
    >>> d = parser.make_dict_by_line(line)
    >>> d.get("Port", "") == "Te1/1/1"
    True
    >>> d.get("Status", "") == "disabled"
    True
    >>> d.get("Vlan", "") == "1"
    True
    """

    d = OrderedDict()

    d["Port"] = line[0:14].strip()
    d["Name"] = line[14:33].strip()
    d["Status"] = line[33:46].strip()
    d["Vlan"] = line[46:57].strip()
    d["Duplex"] = line[57:63].strip()
    d["Speed"] = line[63:70].strip()
    if (len(line) > self.min_len) :
      d["Type"] = line[70:].strip()
    else:
      d["Type"] = ""

    return d


  def filter_dict(self, key="", value_query=""):
    """辞書型のkeyバリューがqueryに合致すればそれを返却する関数を返却

    Arguments:
      key {str} -- 該当するキー
      value_query {str} -- 比較用の文字列

    Returns:
      function -- 辞書型オブジェクトを引数にとり、一致した場合にそれを返却する

    >>> line = "Te1/1/1                          disabled     1            full   1000 1000BaseLH"
    >>> parser = CiscoIosShowInterfacesStatusParser()
    >>> d = parser.make_dict_by_line(line)
    >>> f = parser.filter_dict("Status", "disabled")
    >>> f(d) is not None
    True
    """
    if not key:
      return None

    r = re.compile(r"%s" % value_query, re.IGNORECASE)

    def _filter(d):
      ret = None
      v = d.get(key, "")
      if r.search(v):
        ret = d
      return ret
    return _filter


  def filter_status(self, query):
    """Statusキーのバリューをqueryで検索する関数を返却します

    Arguments:
      query {str} -- 比較用の文字列

    Returns:
      function -- 辞書型オブジェクトを引数にとり、一致した場合にそれを返却する
    """
    return self.filter_dict(key="Status", value_query=query)


  def filter_vlan(self, query):
    """Vlanキーのバリューをqueryで検索する関数を返却します

    Arguments:
      query {str} -- 比較用の文字列

    Returns:
      function -- 辞書型オブジェクトを引数にとり、一致した場合にそれを返却する
    """
    return self.filter_dict(key="Vlan", value_query=query)


  def filter_speed(self, query):
    """Speedキーのバリューをqueryで検索する関数を返却します

    Arguments:
      query {str} -- 比較用の文字列

    Returns:
      function -- 辞書型オブジェクトを引数にとり、一致した場合にそれを返却する
    """
    return self.filter_dict(key="Speed", value_query=query)


  def get_filter_result(self, d, funcs):
    """オブジェクトとフィルタ関数の配列を受け取り、条件にあえばそのオブジェクトを返却する

    Arguments:
      d {dict} -- 辞書型オブジェクト
      funcs {list} -- 関数のリスト

    Returns:
      d -- フィルタ関数をすべて適用して残ったオブジェクト、一致しない場合はNoneを返す
    """
    func = funcs[0]
    result = func(d)
    if result and funcs[1:]:
      return self.get_filter_result(d, funcs[1:])
    return result


#
# ここからスクリプト
#
if __name__ == '__main__':

  import argparse
  import csv  # 結果をCSVで保存
  import configparser  # python3 only
  import logging
  import os
  import sys

  #
  # 共通スクリプト
  #

  def here(path=''):
    """相対パスを絶対パスに変換して返却します"""
    if getattr(sys, 'frozen', False):
      # cx_Freezeで固めた場合は実行ファイルからの相対パス
      return os.path.abspath(os.path.join(os.path.dirname(sys.executable), path))
    else:
      # 通常はこのファイルの場所からの相対パス
      return os.path.abspath(os.path.join(os.path.dirname(__file__), path))

  # ./libフォルダにおいたpythonスクリプトをインポートできるようにするための処理
  if not here("../lib") in sys.path:
    sys.path.append(here("../lib"))

  if not here("../lib/site-packages") in sys.path:
    sys.path.append(here("../lib/site-packages"))

  # アプリケーションのホームディレクトリは一つ上
  app_home = here("..")

  # 自身の名前から拡張子を除いてプログラム名を得る
  app_name = os.path.splitext(os.path.basename(__file__))[0]

  # ディレクトリ
  conf_dir = os.path.join(app_home, "conf")
  data_dir = os.path.join(app_home, "data")

  #
  # 設定ファイルを読む
  #

  # 設定ファイルのパス
  config_file = os.path.join(conf_dir, "config.ini")  # $app_home/conf/config.ini

  if not os.path.exists(config_file):
    logging.error("File not found %s : ", config_file)
    sys.exit(1)

  try:
    cp = configparser.SafeConfigParser()
    cp.read(config_file, encoding='utf8')

    # [default] セクション
    config = cp['default']

    # ログをファイルに残すか
    USE_FILE_HANDLER = config.getboolean('USE_FILE_HANDLER', False)

    # 辞書型のキーを表示するときの右寄せ幅
    RIGHT_JUST = config.getint('RIGHT_JUST', 20)

    # 標準入力から情報を得た場合の出力ファイル名
    DEFAULT_OUTPUT_FILENAME = config.get('DEFAULT_OUTPUT_FILENAME', "output.csv")

  except configparser.Error as e:
    logging.exception(e)
    sys.exit(1)

  #
  # ログ設定
  #

  # ログファイルの名前
  log_file = app_name + ".log"

  # ログファイルを置くディレクトリ
  log_dir = os.path.join(app_home, "log")
  try:
    if not os.path.isdir(log_dir):
      os.makedirs(log_dir)
  except OSError:
    pass

  # レベルはこの順で下にいくほど詳細になる
  #   logging.CRITICAL
  #   logging.ERROR
  #   logging.WARNING --- 初期値はこのレベル
  #   logging.INFO
  #   logging.DEBUG
  #
  # ログの出力方法
  # logger.debug("debugレベルのログメッセージ")
  # logger.info("infoレベルのログメッセージ")
  # logger.warning("warningレベルのログメッセージ")

  # ロガーを取得
  logger = logging.getLogger(app_name)  # __package__

  # ログレベル設定
  logger.setLevel(logging.INFO)

  # フォーマット
  formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')

  # 標準出力へのハンドラ
  stdout_handler = logging.StreamHandler(sys.stdout)
  stdout_handler.setFormatter(formatter)
  stdout_handler.setLevel(logging.INFO)
  logger.addHandler(stdout_handler)

  # ログファイルのハンドラ
  if USE_FILE_HANDLER:
    file_handler = logging.FileHandler(os.path.join(log_dir, log_file), 'a+')
    file_handler.setFormatter(formatter)
    file_handler.setLevel(logging.INFO)
    logger.addHandler(file_handler)

  #
  # スクリプト固有関数
  #

  def get_lines(filename):
    """filenameのファイルを読み込んで各行をリストに格納して返却します。

    Arguments:
      filename {string} -- ファイル名

    Returns:
      [list] -- 行配列。右端の改行コードと空白文字列は削除済み。
    """

    # ファイル名が-だった場合は標準入力から読み込む
    if not filename or filename == "-":
      # return sys.stdin.readlines()
      return [x.rstrip() for x in sys.stdin.readlines() ]

    # ファイルを読み込む
    try:
      with open(filename, mode='r', encoding='utf-8') as f:
        logger.info("open file %s", filename)
        # return f.readlines()
        return [x.rstrip() for x in f.readlines()]
    except IOError:
      logger.warn("failed to open %s", filename)
      return None


  def dump(dicts, right_just=20):
    """OrderedDictの配列を受け取って、内容を表示します。

    Arguments:
      dicts {list} -- OrderedDictの配列

    Keyword Arguments:
      right_just {int} -- 辞書型のキーの右寄せ幅 (default: {20})
    """
    try:
      for d in dicts:
        for k,v in d.items():
          print(k.rjust(right_just) + " : " + v)
        print("")
    except (BrokenPipeError, IOError):
      sys.stderr.close()


  def save(dicts, fieldnames, output_filename):
    """OrderedDictの配列を受け取って、CSV形式で保存します。

    Arguments:
      dicts {list} -- OrderedDictの配列
      fieldnames {list} -- 保存対象とする辞書型のキーの一覧
      output_filename {str} -- 保存するファイル名
    """
    try:
      with open(output_filename, mode='w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(dicts)
        logger.info("saved to %s", output_filename)
    except IOError:
      logger.warn("failed to open %s", output_filename)
    except csv.Error as e:
      logger.warn("csv error")
      logger.exception(e)


  def main():
    """メイン関数

    Returns:
      int -- 正常終了は0、異常時はそれ以外を返却
    """

    # 引数処理
    parser = argparse.ArgumentParser(description='main script.')
    parser.add_argument('-o', '--output', dest='output_filename', metavar='output_file', help='Output filename')
    parser.add_argument('input_filename', help='Filename to be parsed')  # , default='-'
    args = parser.parse_args()

    input_filename = args.input_filename
    output_filename = args.output_filename

    if input_filename == "-" and not output_filename:
      output_filename = DEFAULT_OUTPUT_FILENAME

    # 保存するファイル名が未定の場合、入力ファイルのパスの拡張子だけを差し替える
    if not output_filename:
      (name, _ext) = os.path.splitext(input_filename)
      # ファイル名だけを取り出して拡張子を差し替える
      # (name, _ext) = os.path.splitext(os.path.basename(input_filename))
      output_filename = name + ".csv"

    # 入力ファイルの各行を配列にする
    lines = get_lines(input_filename)
    if lines:
      logger.info("found %s lines", str(len(lines)))
    else:
      logger.error("input data not found.")
      return 1

    # パーサーをインスタンス化する
    status_parser = CiscoIosShowInterfacesStatusParser()

    # ネイバーごとに行を分割して、中身を辞書型に変換する
    results = []
    for d in status_parser.parse(lines):
      results.append(d)

    logger.info("%s interfaces found", str(len(results)))

    # 結果を画面に表示
    # dump(results, right_just=RIGHT_JUST)

    print("ステータスがconnectedかつスピードが10Gのものだけを表示します")
    f1 = status_parser.filter_speed("10G")
    f2 = status_parser.filter_status("connected")
    filtered = [d for d in results if status_parser.get_filter_result(d, [f1, f2])]
    dump(filtered, right_just=RIGHT_JUST)

    # 結果をCSV形式で保存
    # 保存したいキー名を一覧にする
    fieldnames = status_parser.fieldnames
    save(results, fieldnames, output_filename)

    return 0


  # 実行
  sys.exit(main())
