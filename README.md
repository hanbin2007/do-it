# Do-It 运动计数器

基于 **OpenCV + MediaPipe + CustomTkinter** 的实时运动计数工具。

## ✨ 功能

- 🏋️ 深蹲 / 半俯卧撑 实时计数
- 🎥 摄像头实时画面 + 骨架叠加
- 🎛️ 现代深色 UI，所有参数运行中实时可调
- ⏸️ 暂停 / 继续（按钮或空格键）
- 🔊 可选语音播报（每 N 次播报一次）
- 🖥️ 支持 GUI 模式和命令行模式

## 📦 安装

```bash
pip install -r requirements.txt
```

## 🚀 启动

### GUI 模式（推荐）

```bash
python run.py
```

或双击 `start.bat`（Windows，无黑窗口）。

### 命令行模式

```bash
python run.py --no-gui --camera 0 --exercise squat
python run.py --no-gui --camera 1 --exercise half_pushup --voice-every 5
```

### 创建桌面快捷方式

```bash
python create_shortcut.py
```

运行后桌面出现「Do-It 运动计数器」图标，双击直接启动。

## ⌨️ 快捷键

| 按键 | 功能 |
|------|------|
| `Space` | 暂停 / 继续 |
| `Esc` | 退出 |

CLI 模式下：`q` 退出，`r` 重置计数。

## 🗂️ 项目结构

```
do-it/
├── app/
│   ├── main.py      # 入口（参数解析 + 模式选择）
│   ├── config.py    # 配置和常量
│   ├── camera.py    # 摄像头工具
│   ├── pose.py      # 姿态角度计算
│   ├── counter.py   # 计数状态机
│   ├── voice.py     # 语音播报
│   ├── engine.py    # 视频处理引擎（后台线程）
│   └── ui.py        # CustomTkinter 现代 UI
├── run.py           # 启动脚本
├── start.bat        # Windows 快捷启动
└── create_shortcut.py  # 创建桌面快捷方式
```

## 🎯 阈值建议

| 运动 | Down Angle | Up Angle |
|------|-----------|----------|
| 深蹲 | 95° | 160° |
| 半俯卧撑 | 120° | 160° |

所有阈值都可在 UI 中通过滑块实时调整。

## 📋 参数说明

```bash
python run.py --help
```

- `--camera N`：摄像头索引
- `--exercise squat|half_pushup`：运动类型
- `--down-angle`/`--up-angle`：角度阈值
- `--voice-every N`：语音播报间隔（0=关闭）
- `--no-gui`：使用 OpenCV 窗口模式
- `--list-cameras`：列出可用摄像头
