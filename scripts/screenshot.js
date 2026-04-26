const { chromium } = require('playwright');

(async () => {
  const browser = await chromium.launch();
  const context = await browser.newContext({
    viewport: { width: 1400, height: 900 }
  });
  const page = await context.newPage();

  // 你的飞书仪表盘共享链接
  const url = 'https://my.feishu.cn/share/base/dashboard/shrcnuIzAL4nel5s1CFA8YYs56e';
  console.log(`正在加载页面: ${url}`);

  // --------- 关键修正 1 ---------
  // 不要在这里指定具体的仪表盘内容选择器，让它同步加载
  await page.goto(url, { waitUntil: 'networkidle', timeout: 60000 });

  // --------- 关键修正 2 ---------
  // 强行等待全局 JS 稳定（因为飞书仪表盘是重度 SPA）
  // 用一个宽泛的 JS 表达式判断关键布局已存在，而不是等待某个特定的 DOM 节点
  try {
    await page.waitForFunction(
      () => {
        const iframes = document.querySelectorAll('iframe');
        // 如果有 iframe，说明仪表盘内容很可能是嵌入的，先确保它加载出来
        if (iframes.length > 0) {
          return true;
        }
        // 如果没有 iframe，检查 body 中是否有任何可见的表格或画布元素
        return document.body.innerText.trim().length > 0 || document.querySelector('canvas');
      },
      { timeout: 30000 }
    );
    console.log('页面关键结构（iframe 或 body内容）已出现');
  } catch (e) {
    console.warn('等待关键结构超时，尝试继续截图...');
  }

  // --------- 关键修正 3 ---------
  // 处理 iframe 穿透（飞书仪表盘最常见的场景）
  // 先检查主页面中的 iframe，如果有，需要把后续操作切到 iframe 内部
  let mainPage = page;
  let hasIframe = false;

  try {
    const iframeElement = await page.waitForSelector('iframe', { timeout: 5000 });
    if (iframeElement) {
      const frame = await iframeElement.contentFrame();
      if (frame) {
        console.log('检测到 iframe，已切换至仪表盘内部上下文');
        mainPage = frame;
        hasIframe = true;
      }
    }
  } catch (e) {
    // 没有 iframe 更好，直接操作主页面
    console.log('未检测到外层 iframe，继续在主页面中截图');
  }

  // --------- 滚动触发懒加载 ---------
  // 动态内容的加载经常需要滚动触发，此处进行渐进滚动
  console.log('开始自动滚动以触发懒加载...');
  let previousHeight = 0;
  let currentHeight = await mainPage.evaluate(() => document.body.scrollHeight);
  let maxAttempts = 20;
  let attempts = 0;

  while (currentHeight !== previousHeight && attempts < maxAttempts) {
    previousHeight = currentHeight;
    await mainPage.evaluate((step) => {
      window.scrollBy(0, step);
    }, 600);
    // 等待新内容渲染
    await mainPage.waitForTimeout(1500);
    currentHeight = await mainPage.evaluate(() => document.body.scrollHeight);
    attempts++;
    console.log(`滚动第 ${attempts} 次，当前页面高度: ${currentHeight}`);
  }

  // 回到顶部并微调
  await mainPage.evaluate(() => window.scrollTo(0, 0));
  await mainPage.waitForTimeout(1000);

  // 最后一次平缓滚动，确保所有静态资源、图表画布完全绘制
  console.log('执行最终完整遍历滚动...');
  await mainPage.evaluate(async () => {
    const distance = 400;
    let totalHeight = 0;
    while (totalHeight < document.body.scrollHeight) {
      window.scrollBy(0, distance);
      await new Promise(r => setTimeout(r, 200));
      totalHeight += distance;
    }
  });
  await mainPage.waitForTimeout(3000);

  // --------- 截图（全页面） ---------
  console.log('开始捕获整个仪表盘...');
  await mainPage.screenshot({ path: 'img/dashboard.png', fullPage: true });
  console.log('截图成功，已保存至 img/dashboard.png');
  await browser.close();
})();
