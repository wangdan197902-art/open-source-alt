/**
 * Fuse.js 客户端搜索逻辑 — OSSAF
 *
 * 工作流程：
 * 1. 用户首次输入时，异步加载当前语种的 index.json
 * 2. JSON 加载后初始化 Fuse 实例
 * 3. localStorage 缓存 24 小时，避免重复请求
 * 4. 输入防抖 200ms，避免频繁搜索
 * 5. 高亮匹配关键词
 */

(function () {
  'use strict';

  // ============ 配置 ============
  var DEBOUNCE_MS = 200;           // 输入防抖时间
  var MAX_RESULTS = 20;            // 最大返回结果数
  var FUSE_THRESHOLD = 0.3;        // 匹配阈值（0=精确，1=任意）
  var CACHE_HOURS = 24;            // localStorage 缓存时长
  var CACHE_KEY_PREFIX = 'ossaf_fuse_data_';
  var CACHE_TIME_KEY = 'ossaf_fuse_data_time_';
  var MIN_QUERY_LENGTH = 2;        // 最小搜索字符数

  // ============ 状态 ============
  var fuseInstance = null;
  var isLoading = false;
  var dataLoaded = false;
  var debounceTimer = null;

  // ============ DOM 元素 ============
  var searchInput = document.getElementById('search-input');
  var searchClear = document.getElementById('search-clear');
  var searchResults = document.getElementById('search-results');

  if (!searchInput || !searchResults || !searchClear) {
    // 当前页面未引入搜索组件，直接退出
    return;
  }

  // 检查 Fuse.js 是否已加载
  if (typeof window.Fuse === 'undefined') {
    console.warn('[OSSAF Search] Fuse.js 库未加载，搜索功能不可用');
    return;
  }

  // ============ 获取当前语种 ============
  function getCurrentLang() {
    // 从 URL 提取 /en/ /zh/ /ja/ 等
    var match = window.location.pathname.match(/^\/([a-z]{2})\//i);
    return match ? match[1].toLowerCase() : 'en';
  }

  // ============ 获取 JSON URL ============
  function getJsonUrl(lang) {
    return '/' + lang + '/index.json';
  }

  // ============ 加载 JSON 数据（带缓存）============
  function loadSearchData(lang) {
    var cacheKey = CACHE_KEY_PREFIX + lang;
    var timeKey = CACHE_TIME_KEY + lang;

    // 1. 检查 localStorage 缓存
    var cachedTime = localStorage.getItem(timeKey);
    if (cachedTime) {
      var ageHours = (Date.now() - parseInt(cachedTime, 10)) / (1000 * 60 * 60);
      if (ageHours < CACHE_HOURS) {
        var cached = localStorage.getItem(cacheKey);
        if (cached) {
          try {
            return Promise.resolve(JSON.parse(cached));
          } catch (e) {
            console.warn('[OSSAF Search] 缓存解析失败，重新加载');
          }
        }
      }
    }

    // 2. 异步请求 JSON
    var url = getJsonUrl(lang);
    return fetch(url)
      .then(function (response) {
        if (!response.ok) {
          throw new Error('加载搜索数据失败: ' + response.status);
        }
        return response.json();
      })
      .then(function (data) {
        // 3. 写入缓存
        try {
          localStorage.setItem(cacheKey, JSON.stringify(data));
          localStorage.setItem(timeKey, Date.now().toString());
        } catch (e) {
          // localStorage 空间不足时，忽略错误
          console.warn('[OSSAF Search] localStorage 缓存失败:', e);
        }
        return data;
      });
  }

  // ============ 初始化 Fuse 实例 ============
  function initFuse(data) {
    var items = data.items || data.terms || [];
    return new window.Fuse(items, {
      keys: [
        { name: 'title', weight: 0.6 },                 // 标题权重最高
        { name: 'openSourceAlternative', weight: 0.2 }, // 开源替代品
        { name: 'vendor', weight: 0.1 },                // 厂商
        { name: 'summary', weight: 0.05 },              // 摘要
        { name: 'content', weight: 0.05 }               // 正文
      ],
      threshold: FUSE_THRESHOLD,
      ignoreLocation: true,
      minMatchCharLength: 1,
      includeScore: true,
      includeMatches: true,
      ignoreFieldNorm: true
    });
  }

  // ============ 工具函数 ============
  function escapeHtml(str) {
    if (!str) return '';
    var div = document.createElement('div');
    div.textContent = String(str);
    return div.innerHTML;
  }

  function escapeRegExp(str) {
    return String(str).replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
  }

  function highlightText(text, query) {
    if (!text || !query) return escapeHtml(text);
    var safeText = escapeHtml(text);
    var keywords = query.trim().split(/\s+/).filter(Boolean);
    if (keywords.length === 0) return safeText;
    keywords.forEach(function (kw) {
      var re = new RegExp('(' + escapeRegExp(kw) + ')', 'gi');
      safeText = safeText.replace(re, '<mark class="search-highlight">$1</mark>');
    });
    return safeText;
  }

  // ============ 渲染搜索结果 ============
  function renderResults(results, query) {
    if (!results || results.length === 0) {
      searchResults.innerHTML =
        '<div class="search-empty">未找到匹配的内容</div>';
      searchResults.style.display = 'block';
      return;
    }

    var html = results.slice(0, MAX_RESULTS).map(function (item) {
      var entry = item.item;
      var score = (1 - item.score).toFixed(2);
      var title = highlightText(entry.title, query);
      var summary = highlightText(entry.summary, query);
      var altHtml = entry.openSourceAlternative
        ? '<span class="result-alt">→ ' + escapeHtml(entry.openSourceAlternative) + '</span>'
        : '';

      return ''
        + '<a href="' + entry.permalink + '" class="search-result-item" role="option">'
        +   '<div class="result-title">' + title + ' ' + altHtml + '</div>'
        +   (summary ? '<div class="result-summary">' + summary + '</div>' : '')
        +   '<div class="result-score">匹配度: ' + score + '</div>'
        + '</a>';
    }).join('');

    searchResults.innerHTML = html;
    searchResults.style.display = 'block';
  }

  // ============ 执行搜索 ============
  function doSearch(query) {
    if (!query || query.trim().length < MIN_QUERY_LENGTH) {
      searchResults.style.display = 'none';
      searchResults.innerHTML = '';
      return;
    }

    // 懒加载：首次搜索时才加载数据
    if (!dataLoaded) {
      if (isLoading) return;
      isLoading = true;
      searchResults.innerHTML = '<div class="search-loading">加载搜索数据中...</div>';
      searchResults.style.display = 'block';

      var lang = getCurrentLang();
      loadSearchData(lang)
        .then(function (data) {
          fuseInstance = initFuse(data);
          dataLoaded = true;
          isLoading = false;
          var results = fuseInstance.search(query);
          renderResults(results, query);
        })
        .catch(function (err) {
          console.error('[OSSAF Search] 搜索初始化失败:', err);
          isLoading = false;
          searchResults.innerHTML =
            '<div class="search-error">搜索服务暂时不可用</div>';
        });
      return;
    }

    var results = fuseInstance.search(query);
    renderResults(results, query);
  }

  // ============ 事件监听 ============
  searchInput.addEventListener('input', function (e) {
    clearTimeout(debounceTimer);
    var query = e.target.value.trim();

    if (query.length === 0) {
      searchClear.style.display = 'none';
      searchResults.style.display = 'none';
      searchResults.innerHTML = '';
      return;
    }

    searchClear.style.display = 'block';
    debounceTimer = setTimeout(function () {
      doSearch(query);
    }, DEBOUNCE_MS);
  });

  searchClear.addEventListener('click', function () {
    searchInput.value = '';
    searchClear.style.display = 'none';
    searchResults.style.display = 'none';
    searchResults.innerHTML = '';
    searchInput.focus();
  });

  // 点击外部关闭结果
  document.addEventListener('click', function (e) {
    if (!e.target.closest('.search-container')) {
      searchResults.style.display = 'none';
    }
  });

  // 输入框获取焦点时，如果有内容则重新显示结果
  searchInput.addEventListener('focus', function () {
    if (searchInput.value.trim().length >= MIN_QUERY_LENGTH && searchResults.innerHTML) {
      searchResults.style.display = 'block';
    }
  });

  // 按 / 快捷键聚焦
  document.addEventListener('keydown', function (e) {
    if (e.key === '/' && document.activeElement.tagName !== 'INPUT' && document.activeElement.tagName !== 'TEXTAREA') {
      e.preventDefault();
      searchInput.focus();
    }
    // 按 ESC 清除搜索
    if (e.key === 'Escape' && document.activeElement === searchInput) {
      searchInput.value = '';
      searchClear.style.display = 'none';
      searchResults.style.display = 'none';
      searchResults.innerHTML = '';
      searchInput.blur();
    }
  });
})();
