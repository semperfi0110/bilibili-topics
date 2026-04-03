// 获取今日日期字符串
function getTodayString() {
  const today = new Date();
  return today.toISOString().split('T')[0];
}

// 格式化日期显示
function formatDate(dateStr) {
  const date = new Date(dateStr);
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, '0');
  const day = String(date.getDate()).padStart(2, '0');
  return `${year}年${month}月${day}日`;
}

// 加载指定日期的灵感
async function loadInspirations(date) {
  const loadingState = document.getElementById('loadingState');
  const contentState = document.getElementById('contentState');
  const errorState = document.getElementById('errorState');
  const currentDateEl = document.getElementById('currentDate');

  // 显示加载状态
  loadingState.classList.remove('hidden');
  contentState.classList.add('hidden');
  errorState.classList.add('hidden');

  try {
    const response = await fetch(`history/${date}.json`);

    if (!response.ok) {
      throw new Error(`暂无 ${formatDate(date)} 的数据`);
    }

    const data = await response.json();
    renderInspirations(data);

    // 显示内容
    currentDateEl.textContent = formatDate(date);
    loadingState.classList.add('hidden');
    contentState.classList.remove('hidden');
    contentState.classList.add('fade-in');

  } catch (error) {
    // 显示错误状态
    document.getElementById('errorMessage').textContent = error.message;
    loadingState.classList.add('hidden');
    errorState.classList.remove('hidden');
  }
}

// 渲染灵感内容
function renderInspirations(data) {
  const container = document.getElementById('inspirationsContainer');
  container.innerHTML = '';

  const tiers = ['head', 'mid', 'tail'];
  const tierNames = {
    head: '头部UP主',
    mid: '中腰部UP主',
    tail: '长尾/新人UP主'
  };
  const tierDescriptions = {
    head: '全职自媒体/有团队/200万粉 - 高创意/高制作成本',
    mid: '兼职自媒体/有剪辑能力/10万粉 - 实用性强/稳步涨粉',
    tail: '业余创作/<1000粉/简单剪辑 - 低门槛/模板化/快速产出'
  };

  tiers.forEach(tier => {
    if (!data.inspirations[tier]) return;

    const tierData = data.inspirations[tier];
    const tierSection = document.createElement('div');
    tierSection.className = 'fade-in';

    tierSection.innerHTML = `
      <div class="card tier-${tier} p-6 mb-6">
        <div class="flex items-center gap-3 mb-4">
          <span class="tier-badge-${tier} px-4 py-1.5 rounded-full text-white text-sm font-semibold">
            ${tierNames[tier]}
          </span>
          <span class="text-gray-400 text-sm">${tierDescriptions[tier]}</span>
        </div>
        <div class="space-y-4">
          ${tierData.inspirations.map((insp, index) => renderInspirationCard(insp, index)).join('')}
        </div>
      </div>
    `;

    container.appendChild(tierSection);
  });
}

// 渲染单条灵感卡片
function renderInspirationCard(inspiration, index) {
  const contentTypeClass = getContentTypeClass(inspiration.content_type);

  return `
    <div class="reference-link rounded-lg p-4">
      <div class="flex items-start gap-3 mb-3">
        <span class="${contentTypeClass} px-2 py-0.5 rounded text-xs font-medium">
          ${inspiration.content_type}
        </span>
        <span class="text-gray-500 text-xs">#${index + 1}</span>
      </div>

      <h3 class="text-lg font-semibold mb-3 text-white leading-relaxed">
        ${inspiration.title}
      </h3>

      <div class="grid md:grid-cols-2 gap-4 text-sm">
        <div>
          <p class="text-gray-400 mb-1">目标受众</p>
          <p class="text-gray-200">${inspiration.target_audience}</p>
        </div>
        <div>
          <p class="text-gray-400 mb-1">受欢迎原因</p>
          <p class="text-gray-200">${inspiration.why_popular}</p>
        </div>
        <div>
          <p class="text-gray-400 mb-1">制作难点</p>
          <p class="text-gray-200">${inspiration.制作难点}</p>
        </div>
        <div>
          <p class="text-gray-400 mb-1">内容结构</p>
          <p class="text-gray-200">${inspiration.content_structure}</p>
        </div>
      </div>

      ${inspiration.reference_videos && inspiration.reference_videos.length > 0 ? `
        <div class="mt-4 pt-4 border-t border-gray-700">
          <p class="text-gray-400 text-sm mb-2">参考视频</p>
          <div class="space-y-2">
            ${inspiration.reference_videos.map(video => `
              <a href="${video.url}" target="_blank" rel="noopener noreferrer"
                 class="flex items-center gap-2 text-sm text-blue-400 hover:text-blue-300 transition-colors">
                <span class="text-gray-500">▶</span>
                <span class="truncate flex-1">${video.title}</span>
                <span class="text-gray-500 text-xs">${video.views_str || video.views} 播放</span>
              </a>
            `).join('')}
          </div>
        </div>
      ` : ''}
    </div>
  `;
}

// 获取内容类型样式
function getContentTypeClass(contentType) {
  const classes = {
    '美食制作': 'bg-orange-500/20 text-orange-400 border border-orange-500',
    '美食探店': 'bg-green-500/20 text-green-400 border border-green-500',
    '美食测评': 'bg-blue-500/20 text-blue-400 border border-blue-500',
    '美食记录': 'bg-purple-500/20 text-purple-400 border border-purple-500'
  };
  return classes[contentType] || 'bg-gray-500/20 text-gray-400 border border-gray-500';
}

// 初始化
document.addEventListener('DOMContentLoaded', () => {
  const datePicker = document.getElementById('datePicker');

  // 设置日期选择器默认值为今天
  const today = getTodayString();
  datePicker.value = today;
  datePicker.max = today;

  // 加载今日数据
  loadInspirations(today);

  // 日期改变时重新加载
  datePicker.addEventListener('change', (e) => {
    loadInspirations(e.target.value);
  });
});
