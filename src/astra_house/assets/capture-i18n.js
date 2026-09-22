/* Presentation-only locale overlay. Source plans, event logs and notes stay intact. */
(() => {
  "use strict";
  const words = {
    "ASTRA · Field capture pilot": "ASTRA · 房间拍摄试用版",
    "Room capture guide": "房间拍摄指引", "Choose a route": "选择拍摄路线",
    "Change mode": "切换路线", "Export progress": "导出进度", "Undo last action": "撤销上一步",
    "Reset this mode": "重置当前路线", "Progress export": "导出拍摄进度",
    "Progress JSON — metadata only": "进度 JSON（仅含记录，不含照片）", "Progress JSON": "进度 JSON",
    "Copy JSON": "复制 JSON", "Select all for manual copy": "全选，手动复制",
    "Stations and planned directions": "站位与拍摄方向", "Show coverage diagnostics": "显示取景覆盖范围",
    "Numbered circles: stations. Arrow: planned shot. Shaded cone: usable field of view. Current, completed, skipped/gap and upcoming states also use labels and line styles.": "数字圆圈表示站位；箭头表示拍摄方向；扇形表示可用视野。当前、已完成、跳过和待拍状态也会用文字与线型区分。",
    "Before starting · Xiaomi 17 Ultra": "开始前检查 · 小米 17 Ultra",
    "Use the 1× Leica 23 mm main camera, landscape 4:3 JPG, on one phone for the entire route.": "全程使用同一部手机的 1× 徕卡 23 mm 主摄，横屏、4:3、JPG。",
    "Keep one unchanged Leica style. Turn watermark, filters, AI-scene, HDR, flash, digital zoom and Dynamic Shot off.": "固定使用一种徕卡风格。关闭水印、滤镜、AI 场景、HDR、闪光灯、数码变焦和动态照片。",
    "Keep both doors closed: entry and bathroom. If a door state must change, restart under a new capture ID.": "拍摄期间保持出口门和洗手间门关闭。如果必须改变门的状态，请使用新的拍摄批次 ID 重新开始。",
    "Keep room lights and curtains stable. Stop moving screens; keep people out of the scene. Clean the lens, charge the phone, and check free space.": "保持灯光和窗帘不变，关闭动态屏幕，让人物离开画面。擦净镜头，确认电量和剩余空间。",
    "Station confirmation is manual and visit-local. This guide cannot verify your position, camera settings, shutter action, or existence of photographs.": "站位由你手动确认，仅在本次停留期间有效。指引无法验证实际位置、相机设置、快门操作或照片是否存在。",
    "Room orientation and wall review": "房间朝向与墙面核对",
    "+X runs north-to-south; +Y runs west-to-east. Map top is east, right is south, left is north. wall-00 is east/double-window; wall-01 is south; wall-05 is north; wall-02 and wall-04 face west. Both legacy-named windows (window-west and window-east) belong to wall-00. bath-door-south belongs to wall-02. wall-03 has no opening.": "坐标 +X 从北向南，+Y 从西向东。图上方是东、右侧是南、左侧是北。wall-00 为东侧双窗墙，wall-01 为南墙，wall-05 为北墙，wall-02 与 wall-04 朝西。两扇窗的历史编号 window-west / window-east 都属于东墙；洗手间门在 wall-02，wall-03 没有门窗。",
    "Wall": "墙面", "Role": "用途", "Openings": "门窗", "none": "无",
    "east double-window wall": "东侧双窗墙", "south long wall": "南侧长墙",
    "west-facing bathroom-door wall": "朝西的洗手间门墙", "connecting return": "转折连接墙",
    "west-facing entry wall": "朝西的出口门墙", "north measured wall": "北侧已测量墙",
    "Coverage warnings and review": "覆盖警告与审核状态",
    "Complete printable instructions — all modes": "完整可打印指引（所有路线）",
    "Choose one route per capture. The two ledgers are alternatives, not one combined batch.": "每次拍摄选择一条路线，两份清单是不同方案，不需要合并拍摄。",
    "Finish and upload": "完成与上传",
    "Export progress JSON alongside all original photos in one folder or ZIP. Keep original filenames, bytes and EXIF. Do not rename, crop, compress, discard extras, or send through a recompressing message app. The export contains metadata only; this guide never reads or stores image bytes.": "将进度 JSON 和所有原始照片放在同一个文件夹或 ZIP 中上传。保留原始文件名、文件内容和 EXIF；不要改名、裁剪、压缩、删除补拍照片，或通过会压缩图片的聊天应用传输。导出只包含拍摄记录，指引不会读取或保存照片。",
    "Completion is an operator report, not proof of shutter timing. Group order is inferred. EXIF time, subseconds and timezone guide later matching; missing EXIF, repeats, reopened shots or ambiguous matches require manual review. Unassigned images remain available.": "完成状态来自手动记录，不代表真实快门时间；整组照片的顺序为推定。后续参考 EXIF 时间、毫秒和时区匹配照片。缺少 EXIF、补拍、重新打开的任务或匹配不明确时需人工核对；未匹配照片仍会保留。",
    "Keep one stable address": "全程使用同一个网址",
    "Use current Chrome on the Xiaomi at one stable HTTPS URL, or the same Mac LAN HTTP origin for the whole capture. Keep the Mac powered, awake, lid open and server running. Open and reload the exact URL before starting. Direct file/content URLs, in-app browsers, Xiaomi Browser and message-app WebViews have unverified persistence/download. Browser storage may be cleared: export regularly and before reset.": "请在小米手机的 Chrome 中使用固定 HTTPS 网址，或全程使用同一个 Mac 局域网 HTTP 地址。Mac 需保持供电、唤醒、开盖且服务运行。拍摄前先打开并刷新该网址。直接打开文件、小米浏览器、应用内浏览器及聊天应用网页的保存与下载功能尚未验证。浏览器数据可能被清除，请定期导出，重置前也要导出。",
    "I checked the Xiaomi settings": "我已检查小米相机设置", "Start route": "开始拍摄",
    "1× 23 mm main camera · landscape 4:3 JPG · unchanged Leica style. Turn watermark, filters, AI scene, HDR, flash, digital zoom and Dynamic Shot off. Keep lighting/curtains stable; both doors closed. If doors change, restart with a new capture ID.": "使用 1× 23 mm 主摄、横屏 4:3 JPG，固定徕卡风格。关闭水印、滤镜、AI 场景、HDR、闪光灯、数码变焦和动态照片。灯光与窗帘保持不变，两扇门保持关闭；门状态改变时请用新的批次 ID 重新开始。",
    "Manual confirmation only; the guide does not detect your position or observe the camera.": "仅为手动确认；指引不会检测你的位置，也不会监控相机。",
    "Save note": "保存备注", "All photos taken — complete group": "本组已全部拍好，完成本组",
    "Next incomplete": "下一个未完成任务", "Checklist complete — verify the album": "清单已完成，请核对相册",
    "Route reviewed with gaps": "路线已走完，仍有漏拍",
    "Upload all untouched original Xiaomi JPG files as one folder or ZIP with the exported progress JSON. Do not rename, edit, recompress, or transfer through messaging apps. Mention moved stations and untracked retakes.": "将所有未经修改的小米 JPG 原图与进度 JSON 一起打包上传。不要改名、编辑、重新压缩或通过聊天应用传图。请说明偏离站位的情况和未记录的补拍。",
    "Reset current mode? Export first if you need this history.": "确定重置当前路线？如果需要保留历史记录，请先导出。",
    "Progress JSON copied.": "进度 JSON 已复制。", "Press Copy in your browser or keyboard to copy the selected JSON.": "请使用浏览器的复制功能或快捷键，复制已选中的 JSON。",
    "Export older raw progress": "导出旧版原始记录",
    "This origin/browser has unverified persistence and downloads. Use current Chrome over a stable HTTP(S) URL; export before leaving.": "当前网址或浏览器的保存与下载能力尚未验证。请使用 Chrome 和固定 HTTP(S) 网址，离开前先导出记录。",
    "Could not read saved progress. Original data was quarantined for recovery; a clean route can be started.": "无法读取保存的进度。原始数据已隔离保留，可供恢复；现在可以开始新路线。",
    "Room stations and capture directions": "房间站位与拍摄方向",
    "East at the top, south at the right. Numbered station buttons below provide the same navigation. Rays show planned directions, not measured camera positions.": "上方为东，右侧为南。可用下方站位按钮进行相同的导航。箭头表示计划方向，不是实测相机位置。",
    "Capture actions": "拍摄操作", "Station navigation": "站位导航",
    "Structure": "房间结构", "Measured anchors": "实测尺寸参照物", "Floor seams": "地墙交界线",
    "Additional wall patches": "补充墙面", "Ceiling seams": "顶墙交界线", "Additional anchors and detail": "补充参照物与细节",
    "Move only after recording this group; reconfirm after changing station.": "记录完本组再移动，换站位后请重新确认。",
    "Separate proposed route; geometry checks are provisional and do not certify texture, physical occlusion or reconstruction success.": "这是独立候选路线。几何检查仅为初步验证，不代表纹理、实际遮挡或重建效果已经通过验证。",
    "UNAPPROVED CANDIDATE. Keep both doors closed; restart under a new capture ID if door state changes. Check actual visibility and station safety in the room. Phone/FOV trial and route review remain required.": "候选草稿，尚未批准实拍发布。两扇门保持关闭；门状态改变时用新的批次 ID 重新开始。请现场核对取景是否被遮挡、站位是否安全，仍需手机视野校准与路线审核。",
    "Frame the central 60 cm square of bed-top texture. This is an additional local detail image, not a whole-bed scale measurement.": "拍摄床面中央约 60 厘米见方的纹理区域。这是补充局部细节，不是整张床的尺寸测量照片。",
    "just inside the entry area": "出口门内侧附近", "inner north-side route point": "北侧路线内圈站位",
    "bathroom-door/closet approach": "靠近洗手间门和柜子的通道", "far side beside the bed zone": "床区旁较远一侧",
    "central crossing point": "房间中央通道", "window side near the bed": "靠窗、床附近",
    "window side near the desk": "靠窗、书桌附近", "desk/entry-side return point": "书桌与出口一侧的返回站位",
    "paired shot bearings exceed the provisional overlap threshold": "同组相邻拍摄方向的间隔超过暂定重叠阈值",
    "pitched coverage overlaps compatible level coverage by less than 30%": "俯仰视角与相应平视画面的重叠不足 30%",
    "no planned shot covers this required floor-wall seam": "没有计划照片覆盖此处必需的地墙交界线",
    "current": "当前", "completed": "已完成", "pending": "待拍", "skipped": "已跳过", "gap": "有漏拍",
    "in progress": "进行中", "upcoming": "待进行", "not in pass": "不在本轮", "not in this pass": "不在本轮",
    "level": "平视", "up": "仰拍", "down": "俯拍", "draft": "草稿", "missing": "未审核", "blocked": "未通过",
    "Draft candidate": "候选草稿", "Recommended": "推荐",
  };
  const target = id => ({"wall-00":"东侧双窗墙（wall-00）", "wall-01":"南墙（wall-01）", "wall-02":"洗手间门所在的西墙（wall-02）", "wall-03":"西侧转折短墙（wall-03）", "wall-04":"出口门所在的西墙（wall-04）", "wall-05":"北墙（wall-05）", "window-west":"第一扇东窗（window-west）", "window-east":"第二扇东窗（window-east）", "entry-door":"出口门（entry-door）", "bath-door-south":"洗手间门（bath-door-south）", "bed-full":"床（bed-full）", "desk":"书桌（desk）", "closet":"柜子（closet）"}[id] || id);
  const patterns = [
    [/^Draft candidate · (\d+) photographs$/, (_,n) => `候选草稿 · ${n} 张照片`],
    [/^Go to station (\d+)$/, (_,n) => `请前往 ${n} 号站位`],
    [/^I am at station (\d+)$/, (_,n) => `我已到达 ${n} 号站位`],
    [/^At station (\d+) — manually confirmed$/, (_,n) => `已手动确认在 ${n} 号站位`],
    [/^Station (\d+)$/, (_,n) => `${n} 号站位`],
    [/^(.+) at station (\d+)$/, (_,p,n) => `${chinese(p)} · ${n} 号站位`],
    [/^(\S+) coverage$/, (_,id) => `${id} 覆盖审核`],
    [/^Note \/ skip reason for (.+)$/, (_,id) => `${id} 的备注 / 跳过原因`],
    [/^Note for (.+)$/, (_,id) => `${id} 的备注`],
    [/^Skip (\S+)$/, (_,id) => `跳过 ${id}`], [/^Restore (\S+)$/, (_,id) => `恢复 ${id}`],
    [/^(\d+) shots$/, (_,n) => `${n} 张照片`], [/^(\d+) groups$/, (_,n) => `${n} 组`],
    [/^(\d+) photographs$/, (_,n) => `${n} 张照片`],
    [/^whole route (.+)$/, (_,s) => `整条路线：${words[s] || s}`],
    [/^Frame the central approximately 1 m patch of (wall-\d+) at lens height, retaining texture and local wall context\. Do not try to fit the entire wall\.$/, (_,id) => `将镜头朝向${target(id)}中央、与镜头等高的约 1 米宽区域，保留纹理及周边墙面，不必把整面墙塞进画面。`],
    [/^Frame the local (wall-\d+) patch centered (\d+)% along its modeled segment; retain textured context and overlap with adjacent patches\.$/, (_,id,n) => `拍摄${target(id)}沿建模线段约 ${n}% 位置的局部墙面，保留纹理和与相邻区域的重叠。`],
    [/^Tilt down to include a continuous approximately 1 m floor-to-wall seam on (wall-\d+); keep visible floor texture around it\. Record a skip if furniture hides the seam\.$/, (_,id) => `向下俯拍${target(id)}约 1 米长的连续地墙交界线，保留周围地面纹理。若被家具挡住，请记录跳过。`],
    [/^Tilt up toward the central ceiling-to-wall seam of (wall-\d+)\. Keep a continuous seam and surrounding wall visible\.$/, (_,id) => `向上仰拍${target(id)}中央的顶墙交界线，保留连续接缝及周围墙面。`],
    [/^Frame ([\w-]+): keep (.+) visible in one photograph\. This width\/depth view does not require the entire opening height\. Keep both doors closed\.( Additional independent station view\.)?$/, (_,id,extent,extra) => `拍摄${target(id)}：在同一张照片里完整保留${extent === "the full top outline (all four corners)" ? "顶面的四个角与完整轮廓" : extent === "both ends of the measured depth" ? "实测深度的两端" : "与镜头等高的门窗实测宽度两端"}。这张用于宽度或深度参照，不要求拍全门窗高度。两扇门保持关闭。${extra ? "这是从另一站位拍摄的补充视角。" : ""}`],
    [/^Missing planned photos: (.+)$/, (_,ids) => `缺少的计划照片：${ids}`],
    [/^Expected at least (\d+) planned originals for a complete route\. Keep extra retakes\. These checks do not verify photo existence\.$/, (_,n) => `完成整条路线预计至少需要 ${n} 张计划原图，补拍照片也请保留。勾选清单不代表指引已验证照片存在。`],
    [/^Operator event window: (.+) to (.+)\. Action times are advisory; group photo order is inferred, not observed shutter timing\.$/, (_,a,b) => `操作记录时间：${a} 至 ${b}。时间仅供参考；组内照片顺序为推定，并非观测到的快门时序。`],
    [/^Release status: (.+)\. Pilot: real Xiaomi device verification is still required\.$/, (_,s) => `发布状态：${words[s] || s}。试用版仍需小米真机验证。`],
    [/^Hold steadily at (.+) m ± (.+) m\. Laser focus is not LiDAR\. ARCore: optional \/ unverified\.$/, (_,h,t) => `镜头稳定保持在离地 ${h} 米、上下误差约 ${t} 米的位置。激光对焦并非 LiDAR；ARCore 为可选项，尚未验证。`],
    [/^station clearance is (.+) m$/, (_,d) => `站位与障碍物的间距为 ${d} 米`],
    [/^first boundary ray is (.+) m$/, (_,d) => `当前方向到第一面墙的距离为 ${d} 米`],
    [/^maximum shared structural span is (.+) m$/, (_,d) => `相邻站位可共同拍到的最长墙段为 ${d} 米`],
    [/^Saved progress unavailable: (.+)\. Refresh or closing this page can lose progress; export regularly\.$/, (_,reason) => `无法保存进度：${reason}。刷新或关闭页面可能丢失进度，请定期导出。`],
    [/^Older \/ quarantined (.+) progress: (.+) events\. Not applied to this route\.$/, (_,id,n) => `旧版 / 隔离记录 ${id}：${n === "unknown" ? "未知数量的" : n} 条操作，未套用到当前路线。`],
  ];
  const key = "astra.capture.ui.language";
  let language = "en";
  try { language = new URLSearchParams(location.search).get("lang") || localStorage.getItem(key) || "en"; } catch (_) { /* storage is optional */ }
  if (language !== "zh") language = "en";
  function chinese(text) {
    if (words[text]) return words[text];
    for (const [pattern, replacement] of patterns) if (pattern.test(text)) return text.replace(pattern, replacement);
    if (text.includes(" · ")) return text.split(" · ").map(chinese).join(" · ");
    if (/^\s*\/ \d+ complete$/.test(text)) return text.replace("complete", "已完成");
    if (/^\d+ skipped$/.test(text)) return text.replace("skipped", "已跳过");
    if (text === "Resume") return "继续拍摄";
    if (text === "camera setup") return "相机设置";
    if (text.startsWith("Next: ")) return "接下来：" + chinese(text.slice(6));
    if (text.startsWith("Start ")) return "开始 " + chinese(text.slice(6));
    if (text.startsWith("Targets: ")) return text.replace("Targets: ", "目标：").replace(". Aim: ", "；朝向坐标：");
    return text;
  }
  const records = new WeakMap();
  function localize(node, field, value, write) {
    const entry = records.get(node) || {};
    let record = entry[field];
    if (!record || value !== record.output) record = {source: value};
    const output = language === "zh" ? chinese(record.source) : record.source;
    record.output = output; entry[field] = record; records.set(node, entry);
    if (value !== output) write(output);
  }
  function apply() {
    if (!document.body) return;
    document.documentElement.lang = language === "zh" ? "zh-CN" : "en";
    const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
    while (walker.nextNode()) {
      const node = walker.currentNode;
      if (node.parentElement?.closest("script,style,textarea,code,[data-no-translate]")) continue;
      localize(node, "text", node.nodeValue, value => { node.nodeValue = value; });
    }
    for (const node of document.querySelectorAll("[aria-label]")) {
      if (node.closest("[data-no-translate]")) continue;
      localize(node, "aria-label", node.getAttribute("aria-label"), value => node.setAttribute("aria-label", value));
    }
    const select = document.getElementById("guide-language");
    if (select) select.value = language;
  }
  window.AstraI18n = {text: value => language === "zh" ? chinese(value) : value};
  window.addEventListener("DOMContentLoaded", () => {
    const select = document.getElementById("guide-language");
    select?.addEventListener("change", () => {
      language = select.value === "zh" ? "zh" : "en";
      try { localStorage.setItem(key, language); } catch (_) { /* no capture state is touched */ }
      const url = new URL(location.href);
      if (url.searchParams.has("lang")) {
        url.searchParams.set("lang", language);
        try { history.replaceState(null, "", url); } catch (_) { /* file origins may restrict history */ }
      }
      apply();
    });
    const observer = new MutationObserver(() => { observer.disconnect(); apply(); observe(); });
    const observe = () => observer.observe(document.body, {subtree: true, childList: true, characterData: true, attributes: true, attributeFilter: ["aria-label"]});
    apply(); observe();
  });
})();
