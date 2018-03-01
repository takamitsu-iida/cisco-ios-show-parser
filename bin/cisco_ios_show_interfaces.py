#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Catalystのshow interfacesコマンドの出力を整形します。

show interfacesコマンドを行に分解して、行単位で処理します。
切り取りたいところを正規表現で取り出していきます。

Examples:
  $ python -m doctest bin/cisco_ios_show_interfaces2.py
  $ python bin/cisco_ios_show_interfaces2.py testdata/show_interfaces.log

Note:
  結果は読み込んだデータと同じ場所に.csvで保存されます。
  別の場所に保存したい場合はコマンドの引数でファイル名を指定するか、スクリプトの改造が必要です。
"""

__author__ = 'Takamitsu IIDA'
__version__ = '0.1'
__date__ = "2016/01/11"  # 初版
__date__ = "2018/02/25"  # classを使うように書き換え

#
# 標準ライブラリのインポート
#
import re
from collections import OrderedDict

#
# クラス定義
#

class CiscoIosShowInterfacesParser(object):
  """Ciscoのshow interfaces表示を加工するためのクラスです。

  #
  # 想定しているコマンド出力
  #
  TenGigabitEthernet1/1/1 is administratively down, line protocol is down (disabled)
    Hardware is C6k 10000Mb 802.3, address is d072.dcc4.59d6 (bia d072.dcc4.59d6)
    MTU 1500 bytes, BW 1000000 Kbit, DLY 10 usec,
      reliability 255/255, txload 0/255, rxload 0/255
    Encapsulation ARPA, loopback not set
    Keepalive set (10 sec)
    Full-duplex, 1000Mb/s, media type is 1000BaseLH
    input flow-control is off, output flow-control is off
    Clock mode is auto
    ARP type: ARPA, ARP Timeout 04:00:00
    Last input never, output never, output hang never
    Last clearing of "show interface" counters 39w2d
    Input queue: 0/2000/0/0 (size/max/drops/flushes); Total output drops: 0
    Queueing strategy: fifo
    Output queue: 0/40 (size/max)
    5 minute input rate 0 bits/sec, 0 packets/sec
    5 minute output rate 0 bits/sec, 0 packets/sec
      15919273415 packets input, 3949235653296 bytes, 0 no buffer
      Received 238044 broadcasts (238044 multicasts)
      0 runts, 0 giants, 0 throttles
      0 input errors, 0 CRC, 0 frame, 0 overrun, 0 ignored
      0 watchdog, 0 multicast, 0 pause input
      0 input packets with dribble condition detected
      21323970279 packets output, 17076240928410 bytes, 0 underruns
      0 output errors, 0 collisions, 0 interface resets
      0 babbles, 0 late collision, 0 deferred
      0 lost carrier, 0 no carrier, 0 PAUSE output
      0 output buffer failures, 0 output buffers swapped out
  """

  #
  # クラス変数
  #

  token_dict = None
  """注目しているトークンをキーに、それを得るための正規表現を値にしたOrderedDict"""

  fieldnames = []
  """token_dictのキーの一覧。CSVに変換するときのヘッダになる"""

  #
  # メソッド
  #

  def __init__(self):
    """コンストラクタ

    注目しているトークンとそれを得るための正規表現を辞書型に格納し、クラス変数にします。
    画面表示やファイル保存時のカラムの順番は、ここで定義した順番になります。
    """
    self.token_dict = OrderedDict()
    self.token_dict["name"] = re.compile(r"^(\S+) is .*, line protocol is .*$")
    self.token_dict["status"] = re.compile(r"^\S+ is (.*), line protocol is .*$")
    self.token_dict["line protocol"] = re.compile(r"^\S+ is .*, line protocol is (.*)$")
    self.token_dict["Description"] = re.compile(r"^\s+Description: (.*)$")
    self.token_dict["duplex"] = re.compile(r"^\s+(.*), .*, media type is .*$")
    self.token_dict["speed"] = re.compile(r"^\s+\S+, (.*)b/s, media type is .*$")
    self.token_dict["media"] = re.compile(r"^\s+\S+, .*, media type is (.*)$")
    self.token_dict["output drops"] = re.compile(r"^\s+.* Total output drops: (\d+)")
    self.token_dict["5 minute input bps"] = re.compile(r"^\s+5 minute input rate (\d+) bits/sec.*$")
    self.token_dict["5 minute input pps"] = re.compile(r"^\s+5 minute input rate .* bits/sec, (\d+) packets/sec$")
    self.token_dict["5 minute output bps"] = re.compile(r"^\s+5 minute output rate (\d+) bits/sec.*$")
    self.token_dict["5 minute output pps"] = re.compile(r"^\s+5 minute output rate .* bits/sec, (\d+) packets/sec$")
    self.token_dict["input packets"] = re.compile(r"^\s+(\d+) packets input, .*$")
    self.token_dict["input bytes"] = re.compile(r"^\s+\d+ packets input, (\d+) bytes, .*$")
    self.token_dict["input errors"] = re.compile(r"^\s+(\d+) input errors, \d+ CRC, \d+ frame, \d+ overrun, \d+ ignored$")
    self.token_dict["crc"] = re.compile(r"^\s+\d+ input errors, (\d+) CRC, \d+ frame, \d+ overrun, \d+ ignored$")
    self.token_dict["output packets"] = re.compile(r"^\s+(\d+) packets output, .*$")
    self.token_dict["output bytes"] = re.compile(r"^\s+(\d+) packets output, (\d+) bytes, .*$")
    self.token_dict["output errors"] = re.compile(r"\s+(\d+) output errors, \d+ collisions, \d+ interface resets$")
    self.fieldnames = self.token_dict.keys()


  def parse(self, lines):
    """リストの各行を精査してインターフェースごとに分類してyieldします。

    インターフェースの区切りを検出したら処理を開始し、インタフェースのブロックを抜けたら辞書型をyieldします。

    Arguments:
      lines {list} -- show interfacesコマンド出力を行に分割した配列。

    Yields:
      {dict} -- インターフェースに関する情報を辞書型に変換したもの

    >>> lines = []
    >>> lines.append("TenGigabitEthernet1/1/1 is administratively down, line protocol is down (disabled)")
    >>> lines.append("  Full-duplex, 1000Mb/s, media type is 1000BaseLH")
    >>> lines.append("swith#")
    >>> parser = CiscoIosShowInterfacesParser()
    >>> results = [d for d in parser.parse(lines)]
    >>> results[0].get("name") == "TenGigabitEthernet1/1/1"
    True
    >>> results[0].get("status") == "administratively down"
    True
    >>> results[0].get("duplex") == "Full-duplex"
    True
    """

    # 処理中かどうか
    is_section = False

    # インタフェースの区切りを検出する正規表現
    # TenGigabitEthernet1/1/1 is administratively down, line protocol is down (disabled)
    # ここにも欲しい情報が含まれるので、この行を見つけても即座に次の行には移れない
    re_start = re.compile(r"^(\S+) is .*, line protocol is .*$")

    # ブロックの終わり
    re_end = re.compile(r"^(\S+)")

    # インタフェース情報を格納する辞書型
    d = OrderedDict()

    # 行単位で走査
    for line in lines:

      # 最初のインタフェースを見つけるまで無関係情報をスキップする
      if not is_section:
        # この行がインタフェースの区切りかどうかを判定
        match = re_start.match(line)
        if match:
          # 最初のインタフェースを見つけた
          is_section = True
          # 新しいインタフェース用に辞書型を新しくする
          d = OrderedDict()
          # この行にも関心のある情報が含まれている
          for k,v in self.token_dict.items():
            match = v.match(line)
            if match:
              d[k] = match.group(1)
        # 次の行へ
        continue

      # 処理中
      # 次のインタフェースかどうかを判定
      match = re_start.match(line)
      if match:
        # 一つ前のインタフェースの情報をyieldする
        yield d

        # 新しいインタフェース用に辞書型を新しくする
        d = OrderedDict()
        # この行にも関心のある情報が含まれている
        for k,v in self.token_dict.items():
          match = v.match(line)
          if match:
            d[k] = match.group(1)
        # この行の情報は取り込んだので次の行へ
        continue

      # ブロックが終わっていないかどうかを判定
      match = re_end.match(line)
      if match:
        is_section = False
        yield d
        continue

      # 関心のあるトークンを取り出す
      for k,v in self.token_dict.items():
        match = v.match(line)
        if match:
          d[k] = match.group(1)


  def filter_dict(self, key="", value_query=""):
    """辞書型のkeyバリューがqueryに合致すればそれを返却する関数を返却

    Arguments:
      key {str} -- 該当するキー
      value_query {str} -- 比較用の文字列

    Returns:
      function -- 辞書型オブジェクトを引数にとり、一致した場合にそれを返却する

    >>> lines = []
    >>> lines.append("TenGigabitEthernet1/1/1 is administratively down, line protocol is down (disabled)")
    >>> lines.append("  Full-duplex, 1000Mb/s, media type is 1000BaseLH")
    >>> lines.append("swith#")
    >>> parser = CiscoIosShowInterfacesParser()
    >>> results = [d for d in parser.parse(lines)]
    >>> d = results[0]
    >>> f = parser.filter_dict("name", "TenGigabitEthernet1/1/1")
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


  def dump(dicts, right_just=20, exclude_admindown=False, exclude_zero=False):
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
        # administratively downのものを省略する
        if exclude_admindown:
          if "administratively" in d.get("status", ""):
            continue

        # インタフェース名を先に表示
        name = d["name"]
        print("\n%s\n%s" % (name, '-' * len(name)))

        for k,v in d.items():
          # インタフェース名は既に表示したので省略
          if k == "name":
            continue

          if exclude_zero and v == "0":
            # 値が0になっている項目を省略する
            continue

          # キーとバリューのペアを表示
          print(k.rjust(RIGHT_JUST) + " : " + v)
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
    int_parser = CiscoIosShowInterfacesParser()

    # パーサーに全行を分析させて辞書型を得る
    results = []
    for d in int_parser.parse(lines):
      results.append(d)

    # 結果表示
    # dump(results, exclude_admindown=False, exclude_zero=False)

    if results:
      logger.info("Number of interfaces parsed = " + str(len(results)))
    else:
      logger.info("nothing detected")
      return 1

    # 結果をCSV形式でフィアルに書き込む
    fieldnames = int_parser.fieldnames
    save(results, fieldnames, output_filename)

    # "outpput drops"がゼロでないものだけを抽出して表示
    # 正規表現でゼロじゃないもの[^0]を指定する
    print("")
    print("outpput dropsがゼロでないものだけを抽出して表示します")
    f = int_parser.filter_dict(key="output drops", value_query="[^0]")
    filtered = [d for d in results if f(d)]
    dump(filtered)


  # 実行
  sys.exit(main())
