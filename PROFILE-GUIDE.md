# 个人主页维护说明

主页入口是根目录的 `README.md`。设计使用本地 SVG 图片，支持 GitHub 深浅色主题。

## 让主页上线

将本仓库的 README、assets、scripts 和 .github 目录推送到 `Herd1s/Herd1s` 的 `main` 分支，个人主页会自动显示 README。请一起上传资源文件，不能只上传 README。

首次推送包含统计脚本和工作流时，会触发 **Refresh profile stats**。首次运行之前，已经随仓库保存的真实数据快照也能正常展示。

## 修改内容和设计

- 自我介绍、项目卡片、技术栈和交流入口：编辑 `README.md`。
- 封面文字、图形和配色：编辑 `scripts/render-brand.py`，运行 `python scripts/render-brand.py` 重新生成两个主题的封面。
- 统计卡片布局和配色：编辑 `scripts/update-stats.py`。
- 本地预览和截图保存在 `output/playwright/`，已通过 .gitignore 排除。

封面、统计卡片均由本仓库生成，不依赖外部统计图片服务。Python 脚本只使用标准库。

## 自动更新

工作流按每日北京时间 **10:23** 调度；GitHub 可能延迟执行。也可以进入仓库 **Actions → Refresh profile stats → Run workflow** 手动更新。脚本与工作流在 main 分支变更时也会触发。

工作流使用 GitHub 自动提供的 token，无需额外配置个人访问令牌。它仅提交 `assets/stats-light.svg`、`assets/stats-dark.svg` 和 `assets/stats.json` 的变化。

如果仓库或组织策略禁止 Actions 写入，或 main 分支要求所有修改必须走 PR，需要按照相应仓库策略调整写入方式。公共仓库长期无活动时，GitHub 可能停用定时工作流；可在 Actions 中重新启用。失败不会删除上一版图片。

本地刷新：

```powershell
python scripts/update-stats.py
```

## 统计口径

- **Public repos**：账号拥有的非 fork 公开仓库，包含归档仓库与个人主页仓库。
- **Stars received**：上述仓库收到的 Star 总数，不是自己点过的 Star 数。
- **Contributions**：匿名访问 GitHub 个人主页可见的近一年贡献口径，可能包含用户选择展示的匿名私有贡献数量；不读取私有仓库详情，也不等于提交次数。
- **Repo languages**：按每个仓库的主语言计数；无主语言的仓库不参与该行统计，不代表熟练程度或代码行数占比。
- **Updated**：数据抓取的 UTC 日期。完整来源、逐日贡献和仓库列表保存在 `assets/stats.json`。

贡献页面暂时不可用时，优先显示上一份有效贡献记录并标记 CACHED；没有有效历史数据时显示 N/A。仓库接口失败时退出，保留已有图片。贡献页面的 HTML 结构未来改变时，可能需要更新解析器。

## 文案依据

个人定位与技术栈来自下列公开仓库，不包含未经确认的学历、职业、奖项或技能评级：

- [Wheelbot_RDK 项目说明](https://github.com/Herd1s/Wheelbot_RDK/blob/main/README_cn.md)：轮足机器人、RDK X5、自主巡检与 SLAM；ROS 2 依赖见仓库中的 package.xml。
- [HomeDevice 项目说明](https://github.com/Herd1s/HomeDevice/blob/main/docs/README.md)：STM32、ESP32、FastAPI、SQLite、WebSocket 和 uni-app。
- [AirDevice 项目说明](https://github.com/Herd1s/AirDevice/blob/main/README.md)：空气监测、蓝牙交互、采样滤波与设备联动。
- [视觉追踪源码](https://github.com/Herd1s/2025-/blob/main/cv/main%282%29.py)：Python、OpenCV、NumPy、Kalman 滤波和串口通信。

博客入口目前指向已确认存在的博客仓库；确认线上站点可访问后，可将链接改为自己的博客域名。
