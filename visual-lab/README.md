# Visual Lab · 视觉效果实验室

## Tina’s Personal Observatory

`ice-works-showcase/` 是从 ICE WORKS 实验起步的个人物理作品集。主页现为原创 WebGL 星球体验：

| 星球 | CV 经历 | 原创视觉 |
| --- | --- | --- |
| Reading Venus | NASA VfOx 学生负责人，DAVINCI / APL 交付 | 金星云带、大气辉光、轨道探针 |
| Seeing the unseen | Stanford RSL REU，稀疏视角 CT | 内部结构与动态扫描切面 |
| Order from noise | Fei Lu 组的生成模型与 IPS 研究 | 球面离散粒子场 |
| Matter in motion | Beller 组软物质研究 | 流动域与细丝 |
| Backside of the Moon | 程序化 roguelike 游戏 | 线框经纬网和程序地形 |

所有星球均由 GLSL 实时生成，没有使用原项目样例图片。视觉是艺术表达，不是科学模拟结果。项目描述和已有研究链接来自用户提供的 CV；完整 CV、电话号码、邮件地址不入库。

### 本地运行

需要 Node.js 20.9+。

```bash
cd visual-lab/ice-works-showcase
npm ci
npm run dev -- --hostname 127.0.0.1 --port 3101
```

打开 <http://127.0.0.1:3101>。点击项目切换星球；聚焦星球区域后可用左右方向键切换。可暂停动画、调整每颗星球的视觉参数，或打开 field notes 查看详情和研究链接。支持手机布局和系统减少动态效果设置。WebGL 不可用时仍可访问全部项目内容。

### 修改内容

- `components/observatory/projects.js`：项目文案、颜色、链接。
- `components/observatory/shader.js`：原创星球程序绘画。
- `components/observatory/Observatory.jsx`：渲染生命周期、导航、参数和详情。
- `components/observatory/observatory.css`：响应式布局。

检查：`npm run lint`、`npm run build`。使用 Webpack 避免本机 Turbopack 子进程端口问题。

### 上游与授权

初始实验来自 <https://github.com/MegD1/Ice-works-showcase>，提交 `bed3534a43125f6ef93890c75854427ed6a261a1`。保留上游代码、README、AGENTS.md、LICENSE 和着色器署名作为参考；原始轮播不再是主页。上游文件中有关打包图片及 PP Neue Montreal 的说明仅描述原始版本：本次个人版已移除这些样例图片和商业字体。当前页面使用 Geist 和系统衬线字体。新增视觉和界面代码沿用仓库 MIT 许可。

未来实验使用独立子目录与端口（3102、3103……），并记录来源及授权。
