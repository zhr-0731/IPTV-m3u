const { chromium } = require('playwright');

(async () => {
  const browser = await chromium.launch();
  const context = await browser.newContext({
    viewport: { width: 1400, height: 900 }
  });
  const page = await context.newPage();

  const url = 'https://my.feishu.cn/share/base/dashboard/shrcnuIzAL4nel5s1CFA8YYs56e';
  console.log(`正在加载页面: ${url}`);
  await page.goto(url, { waitUntil: 'networkidle', timeout: 60000 });

  // 等待关键内容出现
  try {
    await page.waitForFunction(
      () => {
        const iframes = document.querySelectorAll('iframe');
        if (iframes.length > 0) return true;
        return document.body.innerText.trim().length > 0 || document.querySelector('canvas');
      },
      { timeout: 30000 }
    );
    console.log('页面关键结构已出现');
  } catch (e) {
    console.warn('等待关键结构超时，尝试继续截图...');
  }

  // 检测 iframe 并执行内部滚动
  let frame = null;
  try {
    const iframeElement = await page.waitForSelector('iframe', { timeout: 5000 });
    if (iframeElement) {
      frame = await iframeElement.contentFrame();
      if (frame) {
        console.log('检测到 iframe，将触发内部滚动');
      }
    }
  } catch (e) {
    console.log('未检测到 iframe，在主页面中操作');
  }

  // 滚动函数：接收一个 page 或 frame 对象进行滚动
  const scrollContent = async (target) => {
    console.log('开始自动滚动以触发懒加载...');
    let previousHeight = 0;
    let currentHeight = await target.evaluate(() => document.body.scrollHeight);
    let attempts = 0;
    const maxAttempts = 20;

    while (currentHeight !== previousHeight && attempts < maxAttempts) {
      previousHeight = currentHeight;
      await target.evaluate((step) => {
        window.scrollBy(0, step);
      }, 600);
      await target.waitForTimeout(1500);
      currentHeight = await target.evaluate(() => document.body.scrollHeight);
      attempts++;
      console.log(`滚动第 ${attempts} 次，当前高度: ${currentHeight}`);
    }

    // 回到顶部并最终遍历
    await target.evaluate(() => window.scrollTo(0, 0));
    await target.waitForTimeout(1000);
    console.log('执行最终完整遍历滚动...');
    await target.evaluate(async () => {
      const distance = 400;
      let totalHeight = 0;
      while (totalHeight < document.body.scrollHeight) {
        window.scrollBy(0, distance);
        await new Promise(r => setTimeout(r, 200));
        totalHeight += distance;
      }
    });
    await target.waitForTimeout(3000);
  };

  if (frame) {
    await scrollContent(frame);
  } else {
    await scrollContent(page);
  }

  // 最终使用 page 对象截图（原生支持 fullPage）
  console.log('开始捕获整个仪表盘...');
  await page.screenshot({ path: 'img/dashboard.png', fullPage: true });
  console.log('截图成功，已保存至 img/dashboard.png');
  await browser.close();
})();
