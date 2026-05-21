# Entity Radar

一个轻量的 **实体雷达 HUD** mod，给 Minecraft **1.20.1 Forge** 用。屏幕角落显示一个圆形雷达，以玩家为中心、**固定半径**扫描周围实体并用颜色区分——也就是 Xaero's Minimap+ 付费版才有的那个雷达功能。

## 功能

- 圆形雷达 HUD，玩家居中
- **固定扫描半径**（默认 48 格，可在配置里调 4~256），不随缩放变化
- 实体分色：
  - 🔴 敌对怪（红）
  - 🟢 被动/中立生物（绿）
  - ⚪ 其他玩家（白）
  - 🟡 掉落物（黄，默认关）
- 两种朝向：跟随视角（默认，正上方=你面朝方向）或固定朝北
- 位置可选四个屏幕角，边距、雷达大小、点大小、背景透明度都可调
- 快捷键 **R** 开关雷达（可在 选项→控制→实体雷达 改键）
- 纯客户端（`clientSideOnly`），不需要服务端，多人服可单边使用

## 配置

首次进游戏后生成 `config/entityradar-client.toml`，可调：

| 项 | 默认 | 说明 |
|----|------|------|
| `scanRadius` | 48 | 扫描半径（格） |
| `rotateWithPlayer` | true | true=跟随视角，false=朝北 |
| `hudRadius` | 40 | 雷达圆半径（像素） |
| `corner` | TOP_LEFT | 锚定的屏幕角 |
| `marginX`/`marginY` | 8 | 距角落的边距 |
| `dotSize` | 3 | 实体点大小 |
| `backgroundOpacity` | 100 | 背景透明度 0~255 |
| `showHostile`/`showPassive`/`showPlayers`/`showItems` | - | 各类实体开关 |

## 构建

需要 JDK 17。

```bash
cd minecraft-mod/entity-radar
./gradlew build
```

产物在 `build/libs/entityradar-1.0.0.jar`。

> 注意：如果你的网络有 TLS 拦截代理（如本仓库的云端沙箱环境），Gradle 用的 JDK 需要信任代理 CA，否则下载依赖会报 PKIX 错误。可以把系统的 Java truststore（`/etc/ssl/certs/java/cacerts`）覆盖到该 JDK 的 `lib/security/cacerts`。

## 安装

把 `entityradar-1.0.0.jar` 丢进 `.minecraft/mods/`，需要 Minecraft 1.20.1 + Forge 47.x。

## 限制

构建环境无显示无 GPU，作者**没有在游戏内肉眼验证过渲染效果**，代码逻辑正确且能编译通过，画面效果请在游戏里实测。
