# Visual Lab · 视觉效果实验室

## `ice-works-showcase/` — Tina Shen · Works

上游 [ICE WORKS](https://github.com/MegD1/Ice-works-showcase) 的液态玻璃轮播，**机制原封不动**，
只把卡片里的图纹换成了自己的东西。

滚轮或拖拽转动圆环，相邻卡片在 SDF 里互相融化、拉出蜜丝，上下边缘有玻璃折射带，
光标附近的场会变软、卡片会让位。这些全部来自上游的那一个全屏片元着色器，没有改动。

### 十八张卡片

六项真实工作，每项三张，顺序即圆环顺序——滚一圈是走完一个问题，再换下一个色系。

| # | 卡片 | 归属 |
| --- | --- | --- |
| 01–03 | Cloud Deck · Oxygen Fugacity · Descent Profile | NASA VfOx，金星大气氧逸度传感器，DAVINCI / APL 交付 |
| 04–06 | Sparse Sinogram · Back Projection · Reconstruction | Stanford RSL REU，稀疏视角锥束 CT |
| 07–09 | Interacting Particles · Optimal Transport · Noise to Form | JHU，与 Dr. Fei Lu 的生成模型／相互作用粒子系统 |
| 10–12 | Brownian Path · Bead and Spring · Nematic Defects | JHU Beller 组，布朗动力学与活性物质 |
| 13–15 | Far Side · Level Seed · Night Terrain | Backside of the Moon，程序化生成与游戏物理 |
| 16–18 | Point Cloud · Coverage Plan · Scan Route | ASTRA，本仓库的空间捕获工作 |

图纹全部由 [`components/ring/plates.js`](ice-works-showcase/components/ring/plates.js)
在加载时用 Canvas 2D 画出，**底下是真的数学**：04 是同一个体模的 Radon 变换积分，05 是把
它的七个视角反投影回去（条纹就是稀疏采样的代价），12 的指向矢场是从 ±1/2 缺陷求和出来的，
10 是真的高斯随机游走。整套约 250 ms 画完，不下载任何图片。

这些是**示意图，不是仿真结果，也不是临床影像**。

### 本地运行

需要 Node.js 20.9+。

```bash
npm --prefix visual-lab/ice-works-showcase ci
npm --prefix visual-lab/ice-works-showcase run dev -- --hostname 127.0.0.1 --port 3101
```

打开 <http://127.0.0.1:3101>。开发模式右上角有 lil-gui 调参面板（生产构建不含）。
入场动画约八秒：计数器走到 100 才放行，卡片从一团液态里长出来，展开成环，再转到左侧定位。

`/observatory` 是之前那版每个项目一颗星球的读法，文字介绍在那里，一并留着。

### 改哪里

| 想改 | 改这个 |
| --- | --- |
| 某张卡的画法 | `components/ring/plates.js` 里对应的 painter |
| 卡片顺序、名字、分类、年份 | `components/ring/projects.js`（顺序即圆环顺序） |
| 开场标题、动画节奏、几何、手感 | `components/ring/params.js`，每个参数在 `ring/gui.js` 都有对应控件 |

检查：`npm run lint`、`npm run build`。GLSL 是运行时编译的，着色器改动必须开页面看。
使用 Webpack 而非 Turbopack，绕开本机的子进程端口问题。

### 上游与授权

源自 <https://github.com/MegD1/Ice-works-showcase>，提交 `bed3534a43125f6ef93890c75854427ed6a261a1`，MIT。
上游的 README、AGENTS.md、LICENSE 和着色器署名全部保留。

本分支移除了上游打包的 Pinterest 示例图片和 PP Neue Montreal 商业字体；标题改用随仓库分发的
Satoshi（ITF Free Font Licence），数字用 Geist（OFL）。新增的图纹与界面代码沿用 MIT。

后续实验放独立子目录、独立端口（3102、3103……），并记录来源与授权。
