# Hammer 整合包（Minecraft 1.20.1 + Forge）

## 文件说明

| 文件 | 用途 |
|------|------|
| `Hammer-1.19.0-1.20.1-forge-complete.zip` | **完整可用包**：含所有 20 个模组 jar 和配置文件，开箱即用 |
| `Hammer-1.19.0+1.20.1.forge.mrpack` | Modrinth 原始清单文件，可导入支持的启动器 |
| `build_pack.py` | 从 `.mrpack` 重建完整 zip 的脚本 |

来源：https://modrinth.com/modpack/hammer

依赖：Minecraft **1.20.1** + Forge **47.4.20**

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
