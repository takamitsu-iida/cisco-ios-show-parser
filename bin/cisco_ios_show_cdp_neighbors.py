#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Catalystのshow cdp neighborsコマンドの出力を整形します。

show cdp neighborsの出力は固定長の長さで整形されていますので、文字列の長さで情報を切り取ります。
辞書型に格納してから画面に表示したり、csv形式でファイルに保存します。

Examples:
  $ python -m doctest bin/cisco_ios_show_cdp_neighbors2.py
  $ python bin/cisco_ios_show_cdp_neighbors2.py testdata/show_cdp_neighbor.log

Note:
  結果は読み込んだデータと同じ場所に.csvで保存されます。
  別の場所に保存したい場合はコマンドの引数でファイル名を指定するか、スクリプトの改造が必要です。
"""

__author__ = 'Takamitsu IIDA <iida@jp.fujitsu.com>'
__version__ = '0.2'
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

class CiscoIosShowCdpNeghborsParser(object):
  """Ciscoのshow cdp neighbors表示を加工するためのクラスです。

  """

  # 辞書型のキーの一覧
  # CSV形式で保存する際のヘッダにもなる
  fieldnames = ["device_id", "local_interface", "holdtime", "capability", "platform", "port_id"]

  #
  # 想定しているコマンド出力
  #
  """
  Device ID        Local Intrfce     Holdtme    Capability  Platform  Port ID
  E-Cat3750X-41Stack
                  Ten 2/4/4         169            R T S I WS-C3750X Ten 2/1/2

            1         2          3        4         5         6         7
  012345678901234567890123456789012345678901234567890123456789012345678901234
  -----------------+-----------------+----------+-----------+---------+------
  Device ID        Local Intrfce     Holdtme    Capability  Platform  Port ID
  [0:17]           [17:35]           [35:46]    [46:58]     [58:68]   [68:]
  """

  def parse(self, lines):
    """リストの各行を精査してネイバー装置ごとに分類してyieldします。

    show cdp neighborsコマンドの出力はネイバーごとに1行or2行に分けて表示されます。
    ネイバーごとに区切ってから辞書型に変換し、それをyieldします。

    Arguments:
      lines {list} -- show cdp neighborsコマンド出力を行に分割した配列。

    Yields:
      {dict} -- ネイバーに関する情報を辞書型に変換したもの
    """

    # ネイバーごとにテキストを格納するリスト型をリスト型に格納します
    n = []

    # 処理中かどうか
    is_section = False

    # これを検出したらセクション開始
    start_str = "Device ID        Local Intrfce     Holdtme    Capability  Platform  Port ID"

    # これを含む行を検出したらそれ以降は無視。ホスト名に#が入っていると都合が悪い
    skipStr = "#"

    # 全行を走査
    for line in lines:

      # 改行コードを含む右端の余白を削除
      line = line.rstrip()

      if not line:
        # 空行はスキップ
        continue

      if line.find(skipStr) >= 0:
        is_section = False
        continue

      if line.find(start_str) >= 0:
        is_section = True
        continue  #この行そのものは不要

      if is_section == False:
        # 関心のある部分が始まるまでループを回す
        continue

      if len(line) < 68:
        # 行として短すぎる。ホスト名が長すぎて2行に分割されてるか、空白の行（ゴミ）の可能性もある
        # ゴミでなければホスト名だけを含む行なのでn配列に一時保管
        n.append(line)
        continue

      if line.startswith(' '):
        # 先頭が空白なら、分割された2行目と判断。
        n.append(line)
        yield self.make_dict_by_neighbor_lists(n)
        n = []
        continue

      # 通常の1行表示
      n.append(line)
      yield self.make_dict_by_neighbor_lists(n)
      n = []


  def make_dict_by_neighbor_lists(self, lines):
    """１行or２行の情報からネイバー情報を辞書型にして返却します

    Arguments:
      lines {list} -- 配列の配列。ネイバー装置ごとに1行or2行に分割されたshow cdp neighbors出力。

    Returns:
      list -- ネイバー情報が格納された辞書型の配列。

    >>> lines = []
    >>> lines.append("E-Cat3750X-41Stack")
    >>> lines.append("                 Ten 2/4/4         147            R T S I WS-C3750X Ten 2/1/2")
    >>> parser = CiscoIosShowCdpNeghborsParser()
    >>> d = parser.make_dict_by_neighbor_lists(lines)
    >>> d.get("device_id", "") == "E-Cat3750X-41Stack"
    True
    >>> d.get("local_interface", "") == "Ten 2/4/4"
    True
    >>> d.get("holdtime", "") == "147"
    True
    """

    # 空の辞書型を作って情報を格納し、返却する
    d = OrderedDict()

    # linesは1行の場合と、2行に分割されている場合がある
    line = lines[0]
    if len(lines) == 1 :
      # 1行の場合、17文字目までがdevice_id
      d["device_id"] = line[0:17].strip()
    else :
      # 2行に分割されている場合、1行目に格納されているのはdevice_idそのもの
      d["device_id"] = line.strip()
      line = lines[1]

    # 極力例外を出さないように行の文字数に気をつけながら、文字列を取り出す
    if len(line) >= 35 :
      d["local_interface"] = line[17:35].strip()

    if len(line) >= 46 :
      d["holdtime"] = line[35:46].strip()

    if len(line) >= 58 :
      d["capability"] = line[46:58].strip()

    if len(line) >= 68 :
      d["platform"] = line[58:68].strip()

    if len(line) > 68 :
      d["port_id"] = line[68:].strip()

    return d


  def filter_dict(self, key="", value_query=""):
    """辞書型のkeyバリューがqueryに合致すればそれを返却する関数を返却

    Arguments:
      key {str} -- 該当するキー
      value_query {str} -- 比較用の文字列

    Returns:
      function -- 辞書型オブジェクトを引数にとり、一致した場合にそれを返却する

    >>> lines = []
    >>> lines.append("E-Cat3750X-41Stack")
    >>> lines.append("                 Ten 2/4/4         147            R T S I WS-C3750X Ten 2/1/2")
    >>> parser = CiscoIosShowCdpNeghborsParser()
    >>> d = parser.make_dict_by_neighbor_lists(lines)
    >>> f = parser.filter_dict("device_id", "E-Cat3750X-41Stack")
    >>> f(d) is not None
    True
    >>> f = parser.filter_dict("local_interface", "Ten 2/4/4")
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


  def filter_device_id(self, d, query):
    """device_idキーのバリューをqueryで検索する関数を返却します

    Arguments:
      query {str} -- 比較用の文字列

    Returns:
      function -- 辞書型オブジェクトを引数にとり、一致した場合にそれを返却する
    """
    return self.filter_dict(key="device_id", value_query=query)


  def filter_local_interface(self, d, query):
    """local_interfaceキーのバリューをqueryで検索する関数を返却します

    Arguments:
      query {str} -- 比較用の文字列

    Returns:
      function -- 辞書型オブジェクトを引数にとり、一致した場合にそれを返却する
    """
    return self.filter_dict(key="local_interface", value_query=query)


  def get_filter_result(self, d, funcs):
    """オブジェクトとフィルタ関数の配列を受け取り、条件にあえばそのオブジェクトを返却する

    Arguments:
      d {dict} -- 辞書型オブジェクト
      funcs {list} -- 関数のリスト

    Returns:
      d -- フィルタ関数をすべて適用して残ったオブジェクト、一致しない場合はNoneを返す

    >>> lines = []
    >>> lines.append("E-Cat3750X-41Stack")
    >>> lines.append("                 Ten 2/4/4         147            R T S I WS-C3750X Ten 2/1/2")
    >>> parser = CiscoIosShowCdpNeghborsParser()
    >>> d = parser.make_dict_by_neighbor_lists(lines)
    >>> f1 = parser.filter_dict("device_id", "E-Cat3750X-41Stack")
    >>> f2 = parser.filter_dict("local_interface", "Ten 2/4/4")
    >>> parser.get_filter_result(d, [f1, f2]) is not None
    True
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
    cdp_parser = CiscoIosShowCdpNeghborsParser()

    # ネイバーごとに行を分割して、中身を辞書型に変換する
    results = []
    for d in cdp_parser.parse(lines):
      results.append(d)

    # 結果を画面に表示
    dump(results, right_just=RIGHT_JUST)

    logger.info("%s neighbors found", str(len(results)))

    # 結果をCSV形式で保存
    # 保存したいキー名を一覧にする
    # fieldnames = ["device_id", "local_interface", "holdtime", "capability", "platform", "port_id"]
    fieldnames = cdp_parser.fieldnames
    save(results, fieldnames, output_filename)

    return 0


  # 実行
  sys.exit(main())
