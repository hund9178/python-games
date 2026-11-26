# 我的 Python 小游戏合集

[![版本](https://img.shields.io/github/v/release/hund9178/python-games?label=%E7%89%88%E6%9C%AC&color=blue)](https://github.com/hund9178/python-games/releases)
[![许可证](https://img.shields.io/github/license/hund9178/python-games)](https://github.com/hund9178/python-games/blob/main/fonts/LICENSE.txt)
[![python](https://img.shields.io/badge/python-3.10%2B-blue)](https://www.python.org/)
[![pygame](https://img.shields.io/badge/pygame--ce-2.5.8-green)](https://pyga.me/)

用 Python + pygame 写的几个小游戏，在 Windows 上装好 Python 就能直接跑，也可以打包成 exe 双击玩。

**当前版本 v1.1.0** — 版本号写在 `version.py` 里，各游戏的窗口标题都会显示。

| 项目 | 主文件 | 说明 |
|---|---|---|
| 🀄 **中国象棋** | `xiangqi.py` | 完整规则 + 中文记谱 + 内置 AI 对手，全屏大字体界面，棋盘占满画面，所有按钮收在「暂停」菜单里，带棋谱记录和存读棋局。[详细说明](docs/xiangqi.md) |
| 🐍 **贪吃蛇** | `snake.py` | 经典贪吃蛇，方向键控制，吃一个变长一点。 |
| 🏓 **弹球** | `ball.py` | 滚球物理模拟：地面摩擦、落地反弹、撞墙减速，速度箭头标出方向和快慢。 |
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

> 字体已经打包进去了：程序自带 `fonts/` 下的 Noto Sans SC 子集字体（SIL OFL 协议，可自由分发），
> 所以换台没装黑体的电脑也不会出现满屏方框。打包前不需要再手工复制任何字体文件。
>
> 象棋的 exe 自带图标（红边「帅」棋子），快捷方式显示的就是这个图标。
> 改了图标后重新生成：`python tools/build_icon.py`，再重新打包即可。

## 中文字体

程序通过 `uifont.py` 找中文字体，顺序是：

1. 程序自带的 `fonts/NotoSansSC.ttf`（粗体用 `NotoSansSC-Bold.ttf`）
2. 系统里装的中文字体（微软雅黑、黑体、Noto Sans SC 等）
3. 系统字体目录里直接按文件名找

每个候选都会**实际渲染几个汉字来验证**，只有真能画出字形的才会被采用。
早期版本用 `pygame.font.SysFont()`，它在找不到字体时不会报错，而是悄悄用英文字体顶替，
导致中文全变成方框；那段「读本地字体文件」的兜底逻辑也因此永远执行不到。

想重新生成字体子集（改了界面文字后）：

```bash
pip install fonttools
python tools/build_font.py
```

脚本从系统的 Noto Sans SC 切出只含游戏用到的字符的新字体，输出约 150KB。

## 目录说明

```
Python/
├── version.py            版本号（各游戏共用，改这里就行）
├── xiangqi.py            中国象棋主程序
├── xiangqi_rules.py      象棋规则引擎 + AI 搜索（纯 Python，不依赖 pygame）
├── xiangqi_full.py       象棋旧版界面（带右侧栏和走法记录）
├── uifont.py             中文字体解析（各游戏共用）
├── fonts/                随包携带的中文字体子集（Noto Sans SC，OFL 协议）
├── tools/build_font.py   重新生成字体子集的脚本
├── tools/build_icon.py   重新生成 exe 图标（xiangqi.ico）的脚本
├── test_xiangqi_rules.py 象棋规则引擎测试（72 项）
├── test_xiangqi_ui.py    象棋界面交互测试（79 项）
├── test_uifont.py        中文字体测试（模拟缺字体电脑）
├── test_ball.py          弹球物理与速度箭头测试
├── snake.py / ball.py / Arrow.py / 1.py    其它小游戏
├── *.spec                PyInstaller 打包配置
└── docs/xiangqi.md       象棋详细说明
```

## 发一个新版本

版本号在 `version.py` 里。改完版本号后：

```bash
# 提交改动
git add -A
git commit -m "版本号升到 v1.1.0"

# 打标签并推到 GitHub
git tag -a v1.1.0 -m "v1.1.0"
git push origin main --tags

# 生成 Release 页面（可选，带打包好的 exe）
python -m PyInstaller --noconfirm --clean xiangqi.spec
gh release create v1.1.0 dist/*.exe --title "v1.1.0" --generate-notes
```

GitHub 仓库首页的版本徽章会自动跟着 `latest` release 更新。

## 测试

```bash
python test_xiangqi_rules.py   # 规则引擎测试
python test_xiangqi_ui.py       # 界面交互测试（自动使用无头显示驱动）
python test_uifont.py           # 中文字体测试
python test_ball.py             # 弹球物理与速度箭头测试
```

## 运行环境

- Python 3.10+（开发环境为 3.15）
- pygame-ce 2.5.8
- Windows 10 / 11
