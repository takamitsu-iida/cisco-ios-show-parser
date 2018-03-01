#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Cisco IOSのshow ip routeコマンドの表示をパースします。

Examples:
  $ python -m doctest bin/cisco_ios_show_ip_route.py
  $ python bin/cisco_ios_show_ip_route.py

"""

__author__ = 'Takamitsu IIDA'
__version__ = '0.1'
__date__ = '2016/04/20'  # 初版
__date__ = '2018/02/22'  # Python3用に書き換え

#
# 標準ライブラリのインポート
#

import re


class IPv4RouteEntry(object):
  """IPv4の経路情報を格納

  show ip route表示に含まれる情報のうち、いくつかをアトリビュートとして保持します。
  メトリックやディスタンス、時間は省略しています。

  O    192.168.104.0/24 [110/3] via 192.168.13.3, 7w0d, Vlan13

  Attributes:
    proto (str): プロトコルを識別する文字
    addr (str): IPv4アドレスの文字列表現
    mask (int): マスク長をintで表現したもの
    gw (str): ゲートウエイアドレス
    interface (str): インタフェース
    addr32 (int): アドレスのint表現、主に大小比較のために利用
  """

  def __init__(self, proto, addr, mask, gw, interface):
    """コンストラクタ"""
    self.proto = proto
    self.addr = addr
    if isinstance(mask, str):
      self.mask = int(mask)
    self.gw = gw
    self.interface = interface
    cols = addr.split('.')
    self.addr32 = int(cols[0]) * 256 * 256 * 256 + int(cols[1]) * 256 * 256 + int(cols[2] * 256) + int(cols[3])

  def __eq__(self, other):
    """=="""
    return all([self.addr == other.addr, self.mask == other.mask, self.gw == other.gw])

  def __ne__(self, other):
    """!="""
    return not all([self.addr == other.addr, self.mask == other.mask, self.gw == other.gw])

  def __cmp__(self, other):
    """比較"""
    return self.addr32 - other.addr32

  def __lt__(self, other):
    """less than"""
    return self.addr32 < other.addr32

  def __gt__(self, other):
    """greater than"""
    return self.addr32 > other.addr32

  def __le__(self, other):
    """less or equal"""
    return self.addr32 <= other.addr32

  def __ge__(self, other):
    """greater or equal"""
    return self.addr32 >= other.addr32

  def __repr__(self):
    """print"""
    # return '{0} {1}/{2} via {3} {4}'.format(self.proto, self.addr, self.mask, self.gw, self.interface)
    return '{0},{1},{2},via,{3},{4}'.format(self.proto, self.addr, self.mask, self.gw, self.interface)


class CiscoIosShowIpRouteParser(object):
  """Ciscoのshow ip route表示を加工するためのクラスです。


  """

  #
  # クラス変数
  #

  # (?P<name>正規表現)　・・・シンボリックグループ名を使うと名前で該当部分を取り出すことができて便利（少々見づらくなるのが難点）
  # (?:正規表現)　・・・カッコで括った部分をグループ扱いしない（あとから取り出す必要がない）

  # 10.1.22.0
  re_ipv4_addr = re.compile(r'(?P<addr>(?:\d{1,3}\.){3}\d{1,3})')

  # 10.1.22.0/24
  re_ipv4_prefix = re.compile(r'(?P<addr>(?:\d{1,3}\.){3}\d{1,3})/(?P<mask>\d{1,2})')

  # 100.0.0.0/16 is subnetted, 63 subnets
  re_fixed_mask = re.compile(r'(?P<addr>(?:\d{1,3}\.){3}\d{1,3})/(?P<mask>\d{1,2}) is subnetted')

  # 110.0.0.0/8 is variably subnetted, 7 subnets, 2 masks
  re_variable_mask = re.compile(r'(?P<addr>(?:\d{1,3}\.){3}\d{1,3})/(?P<mask>\d{1,2}) is variably subnetted')

  # S        110.0.0.0/8 is directly connected, Null0
  re_directly_connected = re.compile(r'(?P<proto>.*) (?P<addr>(?:\d{1,3}\.){3}\d{1,3})/(?P<mask>\d{1,2}) is directly connected,(?P<interface>.*)')

  # O E1     100.3.0.0 [110/122] via 10.245.2.2, 7w0d, Vlan102
  re_ipv4_fixed_prefix = re.compile(r'(?P<proto>.*) (?P<addr>(?:\d{1,3}\.){3}\d{1,3}) \[\d+/\d+] via (?P<gw>(?:\d{1,3}\.){3}\d{1,3}),.*,(?P<interface>.*)')

  # O        10.244.1.0/24 [110/2] via 10.245.11.2, 7w0d, Vlan111
  re_ipv4_variable_prefix = re.compile(r'(?P<proto>.*) (?P<addr>(?:\d{1,3}\.){3}\d{1,3})/(?P<mask>\d{1,2}) \[\d+/\d+\] via (?P<gw>(?:\d{1,3}\.){3}\d{1,3}),.*,(?P<interface>.*)')

  # O    192.168.23.0/24 [110/2] via 192.168.13.3, 7w0d, Vlan13
  #                   [110/2] via 192.168.12.2, 7w0d, Vlan12
  re_ipv4_prefix_ecmp = re.compile(r'\s+\[\d+/\d+] via (?P<gw>(?:\d{1,3}\.){3}\d{1,3}),.*,(?P<interface>.*)')


  def parse_lines(self, lines):
    """行の配列linesを走査してIPv4RouteEntryオブジェクトをyieldする

    Arguments:
      lines {list}: 行のリスト

    Yields:
      {obj:`IPv4RouteEntry`} -- IPv4RouteEntryクラスのオブジェクト
    """

    current_proto = None
    current_mask = None
    current_addr = None

    for line in lines:

      #       106.0.0.0/16 is subnetted, 7 subnets
      # r'(?P<addr>(?:\d{1,3}\.){3}\d{1,3})/(?P<mask>\d{1,2}) is subnetted'
      match = re.search(self.re_fixed_mask, line)
      if match:
        current_addr = match.group('addr')
        current_mask = match.group('mask')
        continue

      #       110.0.0.0/8 is variably subnetted, 7 subnets, 2 masks
      # r'(?P<addr>(?:\d{1,3}\.){3}\d{1,3})/(?P<mask>\d{1,2}) is variably subnetted'
      match = re.search(self.re_variable_mask, line)
      if match:
        continue

      # S        110.0.0.0/8 is directly connected, Null0
      # r'(?P<proto>.*) (?P<addr>(?:\d{1,3}\.){3}\d{1,3})/(?P<mask>\d{1,2})is directly connected,(?P<interface>.*)'
      match = re.match(self.re_directly_connected, line)
      if match:
        p = match.group('proto').strip()
        a = match.group('addr')
        m = match.group('mask')
        g = ""
        i = match.group('interface')
        ipv4_route_entry = IPv4RouteEntry(p, a, m, g, i)
        yield ipv4_route_entry, line
        continue

      # O        10.244.1.0/24 [110/2] via 10.245.11.2, 7w0d, Vlan111
      # r'(?P<proto>.*) (?P<addr>(?:\d{1,3}\.){3}\d{1,3})/(?P<mask>\d{1,2}) \[\d+/\d+\] via (?P<gw>(?:\d{1,3}\.){3}\d{1,3}),.*,(?P<interface>.*)'
      match = re.match(self.re_ipv4_variable_prefix, line)
      if match:
        p = match.group('proto').strip()
        a = match.group('addr')
        m = match.group('mask')
        g = match.group('gw')
        i = match.group('interface')
        current_proto = p
        current_addr = a
        current_mask = m
        ipv4_route_entry = IPv4RouteEntry(p, a, m, g, i)
        yield ipv4_route_entry, line
        continue

      match = re.match(self.re_ipv4_fixed_prefix, line)
      if match:
        current_addr = match.group('addr')
        p = match.group('proto').strip()
        a = match.group('addr')
        m = current_mask
        g = match.group('gw')
        i = match.group('interface')
        current_proto = p
        current_addr = a
        ipv4_route_entry = IPv4RouteEntry(p, a, m, g, i)
        yield ipv4_route_entry, line
        continue

      match = re.match(self.re_ipv4_prefix_ecmp, line)
      if match:
        p = current_proto
        a = current_addr
        m = current_mask
        g = match.group('gw')
        i = match.group('interface')
        ipv4_route_entry = IPv4RouteEntry(p, a, m, g, i)
        yield ipv4_route_entry, line
        continue
    # end for
  #


  def filter_addr(self, query):
    """アドレスを文字列で比較して条件にあえばそのIPv4RouteEntryを返却する関数を返却

    Arguments:
      query {str} -- 比較用の文字列

    Returns:
      function -- IPv4RouteEntryを引数としてフィルタする関数

    >>> r = IPv4RouteEntry("O E1", "192.168.0.0", "24", "192.168.0.254", "Vlan100")
    >>> parser = CiscoIosShowIpRouteParser()
    >>> filter = parser.filter_addr("192.168.0.0")
    >>> filter(r) is not None
    True
    """
    r = re.compile(r"%s" % query)

    def _filter(ipv4_route_entry):
      ret = None
      if r.search(ipv4_route_entry.addr):
        ret = ipv4_route_entry
      return ret
    return _filter


  def filter_proto(self, query):
    """プロトコルを文字列で比較して条件にあえばそのIPv4RouteEntryを返却する関数を返却

    Arguments:
      query {str} -- 比較用の文字列

    Returns:
      function -- IPv4RouteEntryオブジェクトを引数にとり、一致した場合にそれを返却する

    >>> r = IPv4RouteEntry("O E1", "192.168.0.0", "24", "192.168.0.254", "Vlan100")
    >>> parser = CiscoIosShowIpRouteParser()
    >>> filter = parser.filter_proto("O E1")
    >>> filter(r) is not None
    True
    """
    r = re.compile(r"%s" % query, re.IGNORECASE)

    def _filter(ipv4_route_entry):
      ret = None
      if r.search(ipv4_route_entry.proto):
        ret = ipv4_route_entry
      return ret
    return _filter


  def filter_gw(self, query):
    """ゲートウェイを文字列で比較して条件にあえばそのIPv4RouteEntryを返却する関数を返却

    Arguments:
      query {str} -- 比較用の文字列

    Returns:
      function -- IPv4RouteEntryオブジェクトを引数にとり、一致した場合にそれを返却する

    >>> r = IPv4RouteEntry("O E1", "192.168.0.0", "24", "192.168.0.254", "Vlan100")
    >>> parser = CiscoIosShowIpRouteParser()
    >>> filter = parser.filter_gw("192.168.0.254")
    >>> filter(r) is not None
    True
    """
    r = re.compile(r"%s" % query)

    def _filter(ipv4_route_entry):
      ret = None
      if r.search(ipv4_route_entry.gw):
        ret = ipv4_route_entry
      return ret
    return _filter


  def filter_interface(self, query):
    """インタフェース名が条件にあえばそのIPv4RouteEntryを返却する関数を返却

    Arguments:
      query {str} -- 比較用の文字列

    Returns:
      function -- IPv4RouteEntryオブジェクトを引数にとり、一致した場合にそれを返却する

    >>> r = IPv4RouteEntry("O E1", "192.168.0.0", "24", "192.168.0.254", "Vlan100")
    >>> parser = CiscoIosShowIpRouteParser()
    >>> filter = parser.filter_interface("Vlan100")
    >>> filter(r) is not None
    True

    """
    r = re.compile(r"%s" % query, re.IGNORECASE)

    def _filter(ipv4_route_entry):
      ret = None
      if r.search(ipv4_route_entry.interface):
        ret = ipv4_route_entry
      return ret
    return _filter


  def filter_mask(self, masklen, *_ope):
    """マスク長が条件にあえばそのIPv4RouteEntryを返却する関数を返却

    Arguments:
      masklen {int} -- マスク長
      *_ope {str} -- 比較演算子、eq/lt/ge

    Returns:
      function -- IPv4RouteEntryオブジェクトを引数にとり、一致した場合にそれを返却する

    >>> r = IPv4RouteEntry("O E1", "192.168.0.0", "24", "192.168.0.254", "Vlan100")
    >>> parser = CiscoIosShowIpRouteParser()
    >>> filter = parser.filter_mask(24)
    >>> filter(r) is not None
    True
    """
    if _ope:
      ope = _ope[0]
    else:
      ope = 'eq'

    def _filter(ipv4_route_entry):
      ret = None
      if ope == 'le':
        if ipv4_route_entry.mask <= masklen:
          ret = ipv4_route_entry
      if ope == 'lt':
        if ipv4_route_entry.mask < masklen:
          ret = ipv4_route_entry
      if ope == 'ge':
        if ipv4_route_entry.mask >= masklen:
          ret = ipv4_route_entry
      if ope == 'gt':
        if ipv4_route_entry.mask > masklen:
          ret = ipv4_route_entry
      if ope == 'eq':
        if ipv4_route_entry.mask == masklen:
          ret = ipv4_route_entry
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
  testdata_dir = os.path.join(app_home, "testdata")

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


  def test_ecmp():
    """ECMPを含む経路をパースするテスト"""

    # ファイルを行配列にする
    lines = get_lines(os.path.join(testdata_dir, "show_ip_route3.log"))

    # パーサーをインスタンス化する
    parser = CiscoIosShowIpRouteParser()

    # リストに格納する
    route_entries = []
    for ipv4_route_entry, _line in parser.parse_lines(lines):
      route_entries.append(ipv4_route_entry)
    #
    for ipv4_route_entry in route_entries:
      print(ipv4_route_entry)


  def test_filter():
    """フィルタのテスト"""
    # ファイルを行配列にする
    filename1 = "testdata/show_ip_route1.log"
    lines1 = get_lines(filename1)
    # パーサーをインスタンス化する
    parser = CiscoIosShowIpRouteParser()
    # リストに格納する
    route_entries1 = []
    for ipv4_route_entry, _line in parser.parse_lines(lines1):
      route_entries1.append(ipv4_route_entry)
    #
    f1 = parser.filter_addr(r'^10\.')
    f2 = parser.filter_mask(24, 'ge')
    # f3 = parser.filter_proto('L')
    # f4 = parser.filter_gw('10.245.2.2')
    f5 = parser.filter_interface('vlan102')
    funcs = [f1, f2, f5]
    for ipv4_route_entry in route_entries1:
      result = parser.get_filter_result(ipv4_route_entry, funcs)
      if result:
        print(result)


  def test_diff():
    """差分を取るテスト"""
    # ファイルを行配列にする
    filename1 = "testdata/show_ip_route1.log"
    filename2 = "testdata/show_ip_route2.log"
    lines1 = get_lines(filename1)
    lines2 = get_lines(filename2)

    # パーサーをインスタンス化する
    parser = CiscoIosShowIpRouteParser()

    # リストに格納する
    route_entries1 = []
    for ipv4_route_entry, _line in parser.parse_lines(lines1):
      route_entries1.append(ipv4_route_entry)

    route_entries2 = []
    for ipv4_route_entry, _line in parser.parse_lines(lines2):
      route_entries2.append(ipv4_route_entry)

    # 共通の経路情報は数が多いので、表示しない
    common = [addr for addr in route_entries1 if addr in route_entries2]
    """
    for addr in common:
      print('= ' + str(addr))
    """

    minus = [addr for addr in route_entries1 if addr not in route_entries2]
    for addr in minus:
      print('- ' + str(addr))

    plus = [addr for addr in route_entries2 if addr not in route_entries1]
    for addr in plus:
      print('+ ' + str(addr))

    print('route_entries1 : {0}\nroute_entries2 : {1}'.format(str(len(route_entries1)), str(len(route_entries2))))
    print('= : {0}\n- : {1}\n+ : {2}'.format(str(len(common)), str(len(minus)), str(len(plus))))


  def test_print():
    filename = "testdata/show_ip_route1.log"
    lines = get_lines(filename)
    parser = CiscoIosShowIpRouteParser()
    route_entries = []
    for ipv4_route_entry, _line in parser.parse_lines(lines):
      route_entries.append(ipv4_route_entry)

    for ipv4_route_entry in route_entries:
      print(ipv4_route_entry)


  def main():
    """メイン関数"""
    #test_print()
    test_diff()
    #test_filter()
    #test_ecmp()
    return 0

  sys.exit(main())
