# 我的 Python 小游戏合集

用 Python + pygame 写的几个小游戏，在 Windows 上装好 Python 就能直接跑，也可以打包成 exe 双击玩。

| 项目 | 主文件 | 说明 |
|---|---|---|
| 🀄 **中国象棋** | `xiangqi.py` | 完整规则 + 中文记谱 + 内置 AI 对手，全屏大字体界面，带棋谱记录和存读棋局。[详细说明](docs/xiangqi.md) |
| 🐍 **贪吃蛇** | `snake.py` | 经典贪吃蛇，方向键控制，吃一个变长一点。 |
| 🏓 **弹球** | `ball.py` | 挡板接球，碰到边缘反弹，计分。 |
| 🏹 **射箭** | `Arrow.py` | 鼠标控制弓箭手瞄准，空格键射箭射靶。 |
| 🔢 **猜数字** | `1.py` | 控制台版猜数字游戏，1~100，十次机会。 |

## 运行

先装好 Python 3.10 以上，再装依赖：

```bash
pip install pygame-ce
```

然后运行任意一个：

```bash
python xiangqi.py     # 中国象棋
python snake.py        # 贪吃蛇
python ball.py         # 弹球
python Arrow.py        # 射箭
python 1.py            # 猜数字（控制台，不需要 pygame）
```

## 打包成 exe

每个项目都带一个 `.spec` 打包配置，用 PyInstaller 一条命令生成独立 exe：

```bash
pip install pyinstaller
python -m PyInstaller --noconfirm --clean xiangqi.spec
```

生成的 exe 在 `dist/` 目录下，可以直接拷到别的电脑上双击运行，不用装 Python。

> `ball.spec` 和 `xiangqi.spec` 用到微软雅黑字体（`msyh.ttc`、`msyhbd.ttc`）。这两个文件没有放进仓库（太大，而且系统自带），需要打包前从 `C:\Windows\Fonts\` 复制到本目录。程序运行时优先调用系统字体，所以直接玩是不受影响的。

## 目录说明

```
Python/
├── xiangqi.py            中国象棋主程序
├── xiangqi_rules.py      象棋规则引擎 + AI 搜索（纯 Python，不依赖 pygame）
├── xiangqi_full.py       象棋旧版界面（带右侧栏和走法记录）
├── test_xiangqi_rules.py 象棋规则引擎测试（72 项）
├── test_xiangqi_ui.py    象棋界面交互测试（79 项）
├── snake.py / ball.py / Arrow.py / 1.py    其它小游戏
├── *.spec                PyInstaller 打包配置
└── docs/xiangqi.md       象棋详细说明
```

## 测试

```bash
python test_xiangqi_rules.py   # 规则引擎测试
python test_xiangqi_ui.py       # 界面交互测试（自动使用无头显示驱动）
```

## 运行环境

- Python 3.10+（开发环境为 3.15）
- pygame-ce 2.5.8
- Windows 10 / 11
