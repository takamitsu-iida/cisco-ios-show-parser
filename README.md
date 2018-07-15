# Cisco IOS showコマンド出力をスクレイピングする例

Cisco IOS装置のshowコマンドの結果をスクレイピングして欲しい情報を取り出す例です。

TextFSMで取り出しづらい場面ではスクリプトを書いてしまった方が楽かもしれません。

## ディレクトリ構造

```tree
├── README.md
├── bin
│   ├── cisco_ios_show_cdp_neighbors.py
│   ├── cisco_ios_show_interfaces.py
│   ├── cisco_ios_show_interfaces_status.py
│   ├── cisco_ios_show_ip_route.py
│   └── cisco_ios_show_logging.py
├── conf
│   └── config.ini
├── lib
│   └── site-packages
├── log
├── requirements.txt
└── testdata
    ├── show_cdp_neighbor.log
    ├── show_int_status.log
    ├── show_interfaces.log
    ├── show_ip_route.log
    ├── show_ip_route1.log
    ├── show_ip_route2.log
    ├── show_ip_route3.log
    └── show_logging.log
```

binフォルダにスクリプト本体があります。

confフォルダには設定パラメータが書かれています。

testdataフォルダには動作確認用のログサンプルがあります。

# 文字列を固定長の長さで取り出す場合の例・その１

一番簡単な例です。
必要な情報が1行にきれいに収まっている場合が一番簡単です。

## スクリプト

bin/show_int_interfaces_status.py

## スクレイピング対象

```none
Port          Name               Status       Vlan       Duplex  Speed Type
Te1/1/1                          disabled     1            full   1000 1000BaseLH
Te1/1/2                          disabled     1            full   1000 1000BaseLH
```

## 実行例

```bash
$ python bin/cisco_ios_show_interfaces_status.py testdata/show_int_status.log
2018-02-28 17:08:55,076 - INFO - open file testdata/show_int_status.log
2018-02-28 17:08:55,077 - INFO - found 186 lines
2018-02-28 17:08:55,078 - INFO - 177 interfaces found
ステータスがconnectedかつスピードが10Gのものだけを表示します
                Port : Te1/2/1
                Name : 4500X-09 Te1/1/3
              Status : connected
                Vlan : trunk
              Duplex : full
               Speed : 10G
                Type : 10Gbase-SR

                Port : Te1/2/2
                Name : 4500X-09 Te2/1/3
              Status : connected
                Vlan : trunk
              Duplex : full
               Speed : 10G
                Type : 10Gbase-SR

(省略)

                Port : Po405
                Name : 3750X-23 Po1
              Status : connected
                Vlan : trunk
              Duplex : a-full
               Speed : 10G
                Type :

2018-02-28 17:08:55,081 - INFO - saved to testdata/show_int_status.csv
$
```

# 文字列を固定長の長さで取り出す場合の例・その２

固定長の幅で表示されるものの、ときどき２行に分割されて表示されたりする場合があります。
このようなときは、意味のある塊に分割してから処理しないといけません。

## スクリプト

bin/cisco_ios_show_cdp_neighbors.py

## スクレイピング対象

```none
Capability Codes: R - Router, T - Trans Bridge, B - Source Route Bridge
                  S - Switch, H - Host, I - IGMP, r - Repeater, P - Phone,
                  D - Remote, C - CVTA, M - Two-port Mac Relay

Device ID        Local Intrfce     Holdtme    Capability  Platform  Port ID
E-Cat3750X-41Stack
                 Ten 2/4/4         147            R T S I WS-C3750X Ten 2/1/2
```

## 実行例

```bash
$ python bin/cisco_ios_show_cdp_neighbors.py testdata/show_cdp_neighbor.log
2018-02-28 17:18:59,200 - INFO - open file testdata/show_cdp_neighbor.log
2018-02-28 17:18:59,201 - INFO - found 93 lines
           device_id : E-Cat3750X-41Stack
     local_interface : Ten 2/4/4
            holdtime : 147
          capability : R T S I
            platform : WS-C3750X
             port_id : Ten 2/1/2

           device_id : E-Cat3750X-41Stack
     local_interface : Ten 2/4/3
            holdtime : 175
          capability : R T S I
            platform : WS-C3750X
             port_id : Ten 1/1/2

(省略)

           device_id : E-Cat3850-01Stack
     local_interface : Ten 1/4/9
            holdtime : 151
          capability : R S I
            platform : WS-C3850-
             port_id : Gig 1/0/1

2018-02-28 17:18:59,204 - INFO - 51 neighbors found
2018-02-28 17:18:59,204 - INFO - saved to testdata/show_cdp_neighbor.csv
$
```

# 正規表現で欲しい情報を取り出す例・その１

決まった長さでは切り取れない場合は正規表現で取り出します。
行単位で処理できるなら簡単です。

## スクリプト対象

bin/cisco_ios_show_logging.py

## スクレイピング対象がこのような形式の場合、

```none
Sep  5 22:56:48.497: %LINK-SW1-3-UPDOWN: Interface TenGigabitEthernet1/3/11, changed state to down
Sep  5 22:56:48.485: %EC-SW2_STBY-5-UNBUNDLE: Interface TenGigabitEthernet1/3/11 left the port-channel Port-channel111
Sep  5 22:57:01.686: %EC-SW1-5-UNBUNDLE: Interface TenGigabitEthernet2/3/11 left the port-channel Port-channel111
```

日付部分は `r"^(\S.*): %.*-\d-.*: .*$"` という正規表現で取り出せます。

ファシリティは `r"^\S.*: %(\S+)-\d-.*: .*$"` で取り出せます。

sererityは `r"^\S.*: %.*-(\d)-.*: .*$"` で取り出せます。

ニモニックは `r"^\S.*: %.*-\d-(\S+): .*$"` で取り出せます。

## 実行例

```bash
$ python bin/cisco_ios_show_logging.py testdata/show_logging.log
2018-02-28 18:08:17,901 - INFO - open file testdata/show_logging.log
2018-02-28 18:08:17,908 - INFO - Number of interfaces parsed = 599
2018-02-28 18:08:17,913 - INFO - saved to testdata/show_logging.csv

severityが6のものを抽出して表示します
                date : Sep  5 22:57:15.455
            facility : SPANTREE-SW1
            severity : 6
            mnemonic : PORT_STATE
         description : Port Po111 instance 104 moving from forwarding to disabled

                date : Sep  5 22:57:15.455
            facility : SPANTREE-SW1
            severity : 6
            mnemonic : PORT_STATE
         description : Port Po111 instance 254 moving from forwarding to disabled
```

# 正規表現で欲しい情報を取り出す例・その２

インタフェース情報のように一連の情報がブロックになっている場合、ブロック単位で処理しなければいけません。

## スクリプト

bin/cisco_ios_show_interfaces.py

## スクレイピング対象

```none
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
```

## 実行例

```bash
$ python bin/cisco_ios_show_interfaces.py testdata/show_interfaces.log
2018-02-28 18:13:12,490 - INFO - open file testdata/show_interfaces.log
2018-02-28 18:13:12,558 - INFO - Number of interfaces parsed = 196
2018-02-28 18:13:12,560 - INFO - saved to testdata/show_interfaces.csv

outpput dropsがゼロでないものだけを抽出して表示します

mgmt0
-----
              status : up
       line protocol : up (connected)
              duplex : Half-duplex
               speed : 10M
               media : 10/100/1000BaseT
        output drops : 440523
  5 minute input bps : 0
  5 minute input pps : 0
 5 minute output bps : 0
 5 minute output pps : 0
       input packets : 0
         input bytes : 0
        input errors : 0
                 crc : 0
      output packets : 0
        output bytes : 0
       output errors : 0
$
```

# 正規表現で欲しい情報を取り出す例・その３

正規表現で情報を抽出した後そのままCSVに変換するだけならよいのですが、
ある程度情報を加工して保存したいのであれば、辞書型よりも独自のクラスを定義した方が便利です。

## スクリプト

bin/cisco_show_ip_route.py

## スクレイピング対象

```none
Gateway of last resort is 10.245.2.2 to network 0.0.0.0

S*    0.0.0.0/0 [252/0] via 10.245.2.2, Vlan102
      10.0.0.0/8 is variably subnetted, 469 subnets, 10 masks
O E1     10.1.22.0/24 [110/134] via 10.245.2.2, 7w0d, Vlan102
O E1     10.1.24.0/24 [110/134] via 10.245.2.2, 7w0d, Vlan102
O E1     10.2.68.0/24 [110/134] via 10.245.2.2, 7w0d, Vlan102
O        10.2.100.0/24 [110/195] via 10.245.2.2, 7w0d, Vlan102
O        10.2.150.0/24 [110/195] via 10.245.2.2, 7w0d, Vlan102
O E1     10.3.50.0/24 [110/134] via 10.245.2.2, 6w5d, Vlan102
O E1     10.3.53.0/24 [110/134] via 10.245.2.2, 6w5d, Vlan102
```

## 実行例

差分だけを表示する例です。

```bash
$ python bin/cisco_ios_show_ip_route.py
2018-03-01 09:14:58,169 - INFO - open file testdata/show_ip_route1.log
2018-03-01 09:14:58,172 - INFO - open file testdata/show_ip_route2.log
- O E1,10.2.10.0,24,via,10.245.2.2, Vlan102
- O E1,10.8.8.0,24,via,10.245.2.2, Vlan102
- O E1,10.114.0.0,16,via,10.245.2.2, Vlan102
- O E1,10.129.68.0,22,via,10.245.2.2, Vlan102
- O E1,10.129.248.0,22,via,10.245.2.2, Vlan102
- O E1,10.131.76.0,22,via,10.245.2.2, Vlan102
- O E1,10.132.28.0,22,via,10.245.2.2, Vlan102
- O E1,10.133.128.0,22,via,10.245.2.2, Vlan102
- O E1,10.137.84.0,22,via,10.245.2.2, Vlan102
- O E1,10.141.52.0,22,via,10.245.2.2, Vlan102
- O E1,10.145.20.0,22,via,10.245.2.2, Vlan102
- O E1,10.148.252.0,22,via,10.245.2.2, Vlan102
- O,10.241.8.0,24,via,10.245.2.2, Vlan102
- L,10.245.11.1,32,via,, Vlan111
- O E1,100.64.0.0,16,via,10.245.2.2, Vlan102
- O,100.242.0.0,16,via,10.245.2.2, Vlan102
- O E1,172.21.39.0,24,via,10.245.2.2, Vlan102
- O E1,192.18.79.0,24,via,10.245.2.2, Vlan102
- O,192.168.137.20,30,via,10.245.2.2, Vlan102
+ O E1,10.5.3.0,24,via,10.245.2.2, Vlan102
+ O E1,10.112.0.0,15,via,10.245.2.2, Vlan102
+ O E1,10.129.236.0,22,via,10.245.2.2, Vlan102
+ O E1,10.131.68.0,22,via,10.245.2.2, Vlan102
+ O E1,10.132.12.0,22,via,10.245.2.2, Vlan102
+ O E1,10.133.116.0,22,via,10.245.2.2, Vlan102
+ O E1,10.137.76.0,22,via,10.245.2.2, Vlan102
+ O E1,10.141.44.0,22,via,10.245.2.2, Vlan102
+ O E1,10.145.12.0,22,via,10.245.2.2, Vlan102
+ O E1,10.148.244.0,22,via,10.245.2.2, Vlan102
+ O,10.241.3.0,24,via,10.245.2.2, Vlan102
+ L,10.245.9.1,32,via,, Vlan109
+ O E1,100.60.0.0,16,via,10.245.2.2, Vlan102
+ O,100.240.0.0,16,via,10.245.2.2, Vlan102
+ O E1,104.84.0.0,16,via,10.245.2.2, Vlan102
+ O E1,172.21.30.0,24,via,10.245.2.2, Vlan102
+ O E1,192.18.74.0,24,via,10.245.2.2, Vlan102
route_entries1 : 653
route_entries2 : 651
= : 634
- : 19
+ : 17
```
