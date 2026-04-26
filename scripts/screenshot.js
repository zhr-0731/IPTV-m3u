const { chromium } = require('playwright');

(async () => {
  const browser = await chromium.launch();
  const page = await browser.newPage({
    viewport: { width: 1400, height: 900 }
  });

  const url = 'https://my.feishu.cn/share/base/dashboard/shrcnuIzAL4nel5s1CFA8YYs56e';
  console.log(`正在加载页面: ${url}`);
  await page.goto(url, { waitUntil: 'networkidle', timeout: 60000 });

  // 等待仪表盘主体内容出现（可根据实际结构调整选择器）
  const contentSelector = '.ud-content'; // 飞书仪表盘常用内容容器
  await page.waitForSelector(contentSelector, { timeout: 30000 });
  console.log('仪表盘内容已加载');

  // 自动滚动到底部，触发懒加载
  console.log('开始自动滚动页面...');
  let previousHeight = 0;
  let currentHeight = await page.evaluate(() => document.body.scrollHeight);
  let attempts = 0;
  const maxAttempts = 20; // 最多滚动20次，防止无限循环
  const scrollStep = 600; // 每次滚动像素

  while (currentHeight !== previousHeight && attempts < maxAttempts) {
    previousHeight = currentHeight;
    await page.evaluate((step) => {
      window.scrollBy(0, step);
    }, scrollStep);
    // 等待新内容加载
    await page.waitForTimeout(1000);
    currentHeight = await page.evaluate(() => document.body.scrollHeight);
    attempts++;
    console.log(`滚动第 ${attempts} 次，页面高度: ${currentHeight}`);
  }

  // 回滚到顶部，再慢慢滚动以确保所有异步加载完成
  await page.evaluate(() => window.scrollTo(0, 0));
  await page.waitForTimeout(500);

  // 最后进行一次完整滚动
  console.log('正在执行最终完整滚动...');
  await page.evaluate(async () => {
    const distance = 500;
    let totalHeight = 0;
    while (totalHeight < document.body.scrollHeight) {
      window.scrollBy(0, distance);
      await new Promise(r => setTimeout(r, 150));
      totalHeight += distance;
    }
  });
  await page.waitForTimeout(2000);

  // 截取整页截图
  console.log('开始截图...');
  await page.screenshot({ path: 'img/dashboard.png', fullPage: true });
  console.log('截图已保存到 img/dashboard.png');
  await browser.close();
})();