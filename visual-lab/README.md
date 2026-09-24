# Visual Lab · 视觉效果实验室

## `ice-works-showcase/` — Tina Shen · Works

线上：<https://aenorhabditis6.github.io/ASTRA_3D_House/works/>

上游 [ICE WORKS](https://github.com/MegD1/Ice-works-showcase) 的液态玻璃轮播，**机制原封不动**，
只把卡片里的图纹换成了自己的东西。

滚轮或拖拽转动圆环，相邻卡片在 SDF 里互相融化、拉出蜜丝，上下边缘有玻璃折射带，
光标附近的场会变软、卡片会让位。这些全部来自上游的那一个全屏片元着色器，没有改动。

### 六项工作，每项三张

顺序即圆环顺序：滚一圈是走完一个问题——测到了什么、这留下什么、最后出来什么——
再换下一个色系。左侧名字下面的说明属于**项目**而不是卡片，所以三张之间它保持不动；
右侧目录常驻六个项目名，只有当前那个展开它的三张。

| 项目 | 三张卡片 |
| --- | --- |
| **NASA VfOx** · 金星大气氧逸度传感器，DAVINCI / APL 交付 | Cloud Deck · Oxygen Fugacity · Descent Profile |
| **Stanford RSL** · 稀疏视角锥束 CT，REU | Sparse Sinogram · Back Projection · Reconstruction |
| **Johns Hopkins** · 与 Dr. Fei Lu 的生成模型／相互作用粒子系统 | Interacting Particles · Optimal Transport · Noise to Form |
| **Beller Group** · 布朗动力学与活性物质 | Brownian Path · Bead and Spring · Nematic Defects |
| **Backside of the Moon** · 程序化生成与游戏物理 | Far Side · Level Seed · Night Terrain |
| **ASTRA** · 本仓库的空间捕获工作 | Point Cloud · Coverage Plan · Scan Route |

图纹全部由 [`components/ring/plates.js`](ice-works-showcase/components/ring/plates.js)
在加载时用 Canvas 2D 画出，**底下是真的数学**：Sparse Sinogram 是同一个体模的 Radon 变换
积分，Back Projection 把它的七个视角反投影回去（条纹就是稀疏采样的代价），
Nematic Defects 的指向矢场是从 ±1/2 缺陷求和出来的，Brownian Path 是真的高斯随机游走。
整套约 250 ms 画完，不下载任何图片。

这些是**示意图，不是仿真结果，也不是临床影像**。

窄屏（≤1024px）会按原设计的思路逐级减少标签：说明收起，右侧目录只留六个项目名；
再窄（≤640px）只剩当前卡片的名字。

### 本地运行

需要 Node.js 20.9+。

```bash
npm --prefix visual-lab/ice-works-showcase ci
npm --prefix visual-lab/ice-works-showcase run dev -- --hostname 127.0.0.1 --port 3101
```

打开 <http://127.0.0.1:3101>。开发模式右上角有 lil-gui 调参面板（生产构建不含）。
入场动画约八秒：计数器走到 100 才放行，卡片从一团液态里长出来，展开成环，再转到左侧定位。

`/observatory` 是之前那版每个项目一颗星球的读法，一并留着。

### 改哪里

| 想改 | 改这个 |
| --- | --- |
| 项目、说明、卡片顺序、外链 | `components/ring/projects.js` 的 `WORKS`（唯一数据源，圆环／目录／说明都从它派生） |
| 某张卡的画法 | `components/ring/plates.js` 里对应的 painter |
| 说明块的排版与动画 | `components/ring/note.js`，参数在 `params.js` 的 note 段，调参面板有对应 folder |
| 开场标题、入场节奏、几何、手感 | `components/ring/params.js`，每个参数在 `ring/gui.js` 都有控件 |

检查：`npm run lint`、`npm run build`。GLSL 是运行时编译的，着色器改动必须开页面看。
使用 Webpack 而非 Turbopack，绕开本机的子进程端口问题。

### 发布

GitHub Pages 用的是**经典分支源**：`codex/github-pages` 分支的根目录，那里是拍摄指南。
[`.github/workflows/publish-works.yml`](../.github/workflows/publish-works.yml)
只往那个分支的 `works/` 子目录写，不碰根目录的指南。

推到 `main` 且改动落在 `visual-lab/ice-works-showcase/**` 时自动跑；也可以手动触发：

```bash
gh workflow run publish-works.yml --ref main
```

子路径由仓库名推导（`/<repo>/works`），通过 `NEXT_PUBLIC_BASE_PATH` 传进构建。
应用是 `output: "export"` 的纯静态导出，本地和线上是同一个构建方式。

### 上游与授权

源自 <https://github.com/MegD1/Ice-works-showcase>，提交 `bed3534a43125f6ef93890c75854427ed6a261a1`，MIT。
上游的 README、AGENTS.md、LICENSE 和着色器署名全部保留。

本分支移除了上游打包的 Pinterest 示例图片和 PP Neue Montreal 商业字体；标题改用随仓库分发的
Satoshi（ITF Free Font Licence），数字用 Geist（OFL）。新增的图纹与界面代码沿用 MIT。

后续实验放独立子目录、独立端口（3102、3103……），并记录来源与授权。
