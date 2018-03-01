#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Cisco IOSのshow ip routeコマンドの表示をパースします。

Examples:
  $ python -m doctest bin/cisco_ios_show_logging.py
  $ python bin/cisco_ios_show_logging.py

"""

__author__ = 'Takamitsu IIDA'
__version__ = '0.1'
__date__ = '2016/01/11'  # 初版
__date__ = '2018/02/27'  # Python3用に書き換え

#
# 標準ライブラリのインポート
#

import re
from collections import OrderedDict


class CiscoIosShowLoggingParser(object):
  """Cisco IOSのshow loggingコマンドの表示を加工するためのクラスです。

  """

  #
  # クラス変数
  #

  token_dict = None
  """注目しているトークンをキーに、それを得るための正規表現を値にしたOrderedDict"""

  fieldnames = []
  """tokensのキーの一覧。CSVに変換するときのヘッダになる"""

  #
  # メソッド
  #

  def __init__(self):
    """コンストラクタ

    注目しているトークンとそれを得るための正規表現を辞書型に格納し、クラス変数にします。
    画面表示やファイル保存時のカラムの順番は、ここで定義した順番になります。
    """

    # 注目しているトークンとそれを得るための正規表現を定義して、辞書型に格納する
    # CSV保存するときのカラムの順番は、ここで定義した順番になる
    # ログのフォーマットは設定次第で変わってしまうため、環境に合わせてカスタマイズが必要かも。
    # Sep  5 22:56:48.497: %LINK-SW1-3-UPDOWN: Interface TenGigabitEthernet1/3/11, changed state to down

    self.token_dict = OrderedDict()
    self.token_dict["date"] = re.compile(r"^(\S.*): %.*-\d-.*: .*$")
    self.token_dict["facility"] = re.compile(r"^\S.*: %(\S+)-\d-.*: .*$")
    self.token_dict["severity"] = re.compile(r"^\S.*: %.*-(\d)-.*: .*$")
    self.token_dict["mnemonic"] = re.compile(r"^\S.*: %.*-\d-(\S+): .*$")
    self.token_dict["description"] = re.compile(r"^\S.*: %.*-\d-.*: (.*)$")

    self.fieldnames = self.token_dict.keys()


  def parse(self, lines):
    """リストの各行を精査してログ情報を辞書型にしたものをyieldします。

    インターフェースの区切りを検出したら処理を開始し、インタフェースのブロックを抜けたら辞書型をyieldします。

    Arguments:
      lines {list} -- show loggingコマンド出力を行に分割した配列。

    Yields:
      {dict} -- インターフェースに関する情報を辞書型に変換したもの

    >>> lines = []
    >>> lines.append("Sep  5 22:56:48.497: %LINK-SW1-3-UPDOWN: Interface TenGigabitEthernet1/3/11, changed state to down")
    >>> lines.append("Sep  5 22:56:48.485: %EC-SW2_STBY-5-UNBUNDLE: Interface TenGigabitEthernet1/3/11 left the port-channel Port-channel111")
    >>> parser = CiscoIosShowLoggingParser()
    >>> results = [d for d in parser.parse(lines)]
    >>> results[0].get("date") == "Sep  5 22:56:48.497"
    True
    >>> results[0].get("facility") == "LINK-SW1"
    True
    """

    # ログ表示かどうかを検出する正規表現
    rex_log = re.compile(r"^\S.*: (%.*-\d-.*): .*")

    # 行単位で走査
    for line in lines:
      # 改行コードを含む右端の余白を削除
      line = line.rstrip()

      # この行がログのフォーマットにあっているかどうかを判定
      match = rex_log.match(line)
      if match :
        yield self.make_dict_by_line(line)


  def make_dict_by_line(self, line):
    """１行の情報からログ情報を辞書型にして返却します"""

    # ログ情報格納用に辞書型を新しく作る
    d = OrderedDict()

    # 関心のあるトークンが含まれるかどうかを正規表現で判定
    for k,v in self.token_dict.items():
      match = v.match(line)
      if match:
        d[k] = match.group(1)

    return d


  def filter_dict(self, key="", value_query=""):
    """辞書型のkeyバリューがqueryに合致すればそれを返却する関数を返却

    Arguments:
      key {str} -- 該当するキー
      value_query {str} -- 比較用の文字列

    Returns:
      function -- 辞書型オブジェクトを引数にとり、一致した場合にそれを返却する
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


#
# ここからスクリプト
#
if __name__ == '__main__':

  import argparse
  import configparser  # python3 only
  import csv  # 結果をCSVで保存
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
  # 固有スクリプト
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
      with open(filename, mode="r", encoding="utf-8") as f:
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
      exclude_admindown {bool} -- administratively downの表示を省略する場合はTrue (default: {False})
      exclude_zero {bool} -- 値がゼロの項目の表示を省略する場合はTrue (default: {False})
    """
    try:
      for d in dicts:
        for k,v in d.items():
          # キーとバリューのペアを表示
          print(k.rjust(RIGHT_JUST) + " : " + v)
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

    # 指定がないなら入力ファイルと同じ場所に、拡張子を.csvにしたファイルを作成
    if not output_filename:
      # 入力ファイルのパスの拡張子だけを差し替える
      (name, _ext) = os.path.splitext(input_filename)
      # ファイル名だけを取り出して拡張子を差し替える
      # (name, _ext) = os.path.splitext(os.path.basename(input_filename))
      output_filename = name + ".csv"

    # 入力ファイルの各行を配列にする
    lines = get_lines(input_filename)
    if not lines:
      logger.error("input data not found.")
      return 1

    # パーサーをインスタンス化する
    logging_parser = CiscoIosShowLoggingParser()

    # パーサーに全行を分析させて辞書型を得る
    results = []
    for d in logging_parser.parse(lines):
      results.append(d)

    # 結果表示
    # dump(results, exclude_admindown=False, exclude_zero=False)

    if results:
      logger.info("Number of interfaces parsed = " + str(len(results)))
    else:
      logger.info("nothing detected")
      return 1

    # 結果をCSV形式でフィアルに書き込む
    fieldnames = logging_parser.fieldnames
    save(results, fieldnames, output_filename)

    #
    # フィルタ機能のテスト
    #

    # "severity"が"3"だけを抽出して表示
    print("")
    print("severityが3のものを抽出して表示します")
    f = logging_parser.filter_dict(key="severity", value_query="3")
    filtered = [d for d in results if f(d)]
    dump(filtered)


  # 実行
  sys.exit(main())
