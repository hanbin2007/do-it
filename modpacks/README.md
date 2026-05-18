# Hammer 整合包（Minecraft 1.20.1 + Forge）

## 文件说明

| 文件 | 用途 |
|------|------|
| `Hammer-1.19.0-1.20.1-forge-complete.zip` | **Hammer 完整可用包**：含所有模组 jar 和配置文件，开箱即用 |
| `Hammer-1.19.0+1.20.1.forge.mrpack` | Modrinth 原始清单文件，可导入支持的启动器 |
| `build_pack.py` | 从 `.mrpack` 重建 Hammer 完整 zip 的脚本 |
| `build_sbw_pack.py` + `sbw_addons.json` | 构建 Superb Warfare 包的脚本（zip 体积 >100MB，未提交） |

来源：https://modrinth.com/modpack/hammer

依赖：Minecraft **1.20.1** + Forge **47.4.20**

## 相对上游的自定义改动

- 移除 `xenon-0.3.31+mc1.20.1.jar` 及其配置（`xenon++.toml`, `xenon-options.json`）
- 添加 [Embeddium](https://modrinth.com/mod/embeddium) `0.3.31+mc1.20.1`（Sodium 的 Forge 移植，替代 Xenon）
- 添加 [Chloride（原 Embeddium++）](https://modrinth.com/mod/chloride) `FORGE-mc1.20.1-v1.7.7`（Embeddium 增强插件）

## 使用方法（完整 zip）

1. 安装 Minecraft 1.20.1 + Forge 47.4.20（用 PCL2 / HMCL / 官方启动器等）。
2. 解压 `Hammer-1.19.0-1.20.1-forge-complete.zip`。
3. 把解压出来的 `mods/`、`config/`、`configureddefaults/` 等文件夹复制到你的游戏目录（`.minecraft` 或独立版本的实例文件夹）。
4. 启动 Forge 版本即可。

## 重新构建

如需更新到新版本：

```bash
# 1. 从 Modrinth 下载新的 .mrpack 放到 modpacks/ 下
# 2. 修改 build_pack.py 顶部的 MRPACK / OUT_DIR_NAME 常量
python3 modpacks/build_pack.py
```

脚本会下载所有 jar，校验 SHA1，合并 overrides 配置，生成完整 zip。

## Superb Warfare 包

不基于 Hammer，独立的军事/武器整合包，**不含任何优化 mod**。

包含：
- **Superb Warfare** `0.8.9-final`（主体）
- **17 个 [SBW] 附属**：Vintage Vehicle Pack、Frontline Combat Pack、AshVehicle、Tactical Drone、More Drone Detector、HeadSound、Wrecked!、TracerFire、Drone Detector、Remoove Recipe Gun、Drill Baby Drill、Suppressing、Colorized!、No Pocket Vehicles、Combined Perk、ClusterMines、Survival Recipe Fix
- **依赖库**：Kotlin for Forge `4.12.0`、Curios `5.14.1+1.20.1`、GeckoLib `4.8.3`

构建：

```bash
python3 modpacks/build_sbw_pack.py
```

输出 `SuperbWarfare-1.20.1-forge-complete.zip`（~113 MiB）。该文件超过 GitHub 单文件 100MB 限制，未纳入仓库，需要本地运行脚本生成。
