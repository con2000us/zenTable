let currentMode = 'css';
let currentTheme = 'dark';
let loadedThemes = {};  // 從 theme_api.php 載入的 theme 列表
let currentThemeTemplate = null;  // 目前選定 theme 的完整 template
let cssEditMode = 'selector';  // 'selector' | 'advanced'

// 從 API 載入 theme 列表（依目前模式）
async function loadThemesFromApi() {
    const modeParam = currentMode === 'ascii' ? 'text' : currentMode;
    try {
        const response = await fetch(`theme_api.php?action=list&mode=${modeParam}`);
        const data = await response.json();
        if (data.success && data.themes && data.themes.length > 0) {
            loadedThemes = {};
            data.themes.forEach(t => {
                loadedThemes[t.id] = { ...t, source: 'api', source_type: t.source_type || 'unknown' };
            });
            // 僅當主題確實不存在於清單時才重設，避免誤覆蓋 cookie 還原的選擇
            if (!loadedThemes[currentTheme]) {
                currentTheme = Object.keys(loadedThemes)[0] || currentTheme;
            }
            renderThemeList();
        } else {
            throw new Error('No themes');
        }
    } catch (e) {
        console.error('Failed to load themes:', e);
        loadedThemes = {
            dark: { id: 'dark', name: 'Dark', description: '深色主題', source: 'fallback' },
            light: { id: 'light', name: 'Light', description: '淺色主題', source: 'fallback' },
            forest: { id: 'forest', name: 'Forest', description: '森林主題', source: 'fallback' },
            glass: { id: 'glass', name: 'Glass', description: '毛玻璃', source: 'fallback' },
            gradient_modern: { id: 'gradient_modern', name: 'Gradient Modern', description: '漸層', source: 'fallback' }
        };
        if (!loadedThemes[currentTheme]) {
            currentTheme = 'dark';
        }
        renderThemeList();
    }
}

// 載入特定 theme 的完整 template（ASCII 用 mode=text）
async function loadThemeTemplate(themeId) {
    const modeParam = currentMode === 'ascii' ? 'text' : currentMode;
    try {
        const response = await fetch(`theme_api.php?action=load&mode=${modeParam}&theme=${themeId}`);
        const data = await response.json();
        if (data.success) {
            currentThemeTemplate = data.template;
            if (data.frontend) {
                // 更新前端預覽用的顏色
                return data.frontend;
            }
        }
    } catch (e) {
        console.error('Failed to load theme template:', e);
    }
    return null;
}

const COOKIE_KEY = 'zentable_settings';
const STAGE1_PIL_COOKIE_KEY = 'zentable_stage1PilPreview';
const COOKIE_DAYS = 365;
const BACKEND_CAL_CONTROLS_KEY = 'zentable_backend_cal_controls';
function getSettingsStorage() {
    let fromLocal = null;
    let fromCookie = null;
    try { fromLocal = localStorage.getItem(COOKIE_KEY); } catch (e) {}
    fromCookie = getCookie(COOKIE_KEY);

    // 若 local/cookie 同時存在且不同，取 updatedAt 較新的（避免 localStorage 寫入失敗導致讀到舊值）
    if (fromLocal && fromCookie && fromLocal !== fromCookie) {
        try {
            const a = JSON.parse(fromLocal);
            const b = JSON.parse(fromCookie);
            const at = Number(a?.updatedAt || 0);
            const bt = Number(b?.updatedAt || 0);
            return (bt > at) ? fromCookie : fromLocal;
        } catch (e) {
            return fromLocal;
        }
    }
    return fromLocal || fromCookie;
}
function setSettingsStorage(value) {
    try {
        localStorage.setItem(COOKIE_KEY, value);
    } catch (e) {
        // 若寫入失敗，移除舊值，避免下次 getSettingsStorage 永遠讀到 stale localStorage
        try { localStorage.removeItem(COOKIE_KEY); } catch (e2) {}
    }
    setCookie(COOKIE_KEY, value, COOKIE_DAYS);
}
const CAL_TABLE_CONTROLS_KEY = 'zentable_cal_table_controls';
function getCookie(name) {
    const m = document.cookie.match(new RegExp('(^| )' + name + '=([^;]+)'));
    return m ? decodeURIComponent(m[2]) : null;
}
function setCookie(name, value, days) {
    const d = new Date();
    d.setTime(d.getTime() + (days || 30) * 864e5);
    document.cookie = name + '=' + encodeURIComponent(value) + ';path=/;expires=' + d.toUTCString() + ';SameSite=Lax';
}
function saveBackendCalControls() {
    try {
        const payload = {
            backendCalCharsPerLine: document.getElementById('backendCalCharsPerLine')?.value ?? '6',
            backendCalCharRepeat: document.getElementById('backendCalCharRepeat')?.value ?? '5',
            backendCalCustomChars: document.getElementById('backendCalCustomChars')?.value ?? '',
            backendStartPattern: document.getElementById('backendStartPattern')?.value ?? '',
            backendEndPattern: document.getElementById('backendEndPattern')?.value ?? '',
            backendWidthTestChars: document.getElementById('backendWidthTestChars')?.value ?? ''
        };
        localStorage.setItem(BACKEND_CAL_CONTROLS_KEY, JSON.stringify(payload));
    } catch (e) {}
}
function loadBackendCalControls() {
    try {
        const raw = localStorage.getItem(BACKEND_CAL_CONTROLS_KEY);
        if (!raw) return;
        const o = JSON.parse(raw);
        const perLineEl = document.getElementById('backendCalCharsPerLine');
        const repeatEl = document.getElementById('backendCalCharRepeat');
        const customEl = document.getElementById('backendCalCustomChars');
        const startPatternEl = document.getElementById('backendStartPattern');
        const endPatternEl = document.getElementById('backendEndPattern');
        const widthCharsEl = document.getElementById('backendWidthTestChars');
        if (perLineEl && o.backendCalCharsPerLine != null) perLineEl.value = String(o.backendCalCharsPerLine);
        if (repeatEl && o.backendCalCharRepeat != null) repeatEl.value = String(o.backendCalCharRepeat);
        if (customEl && o.backendCalCustomChars != null) customEl.value = String(o.backendCalCustomChars);
        if (startPatternEl && o.backendStartPattern != null) startPatternEl.value = String(o.backendStartPattern);
        if (endPatternEl && o.backendEndPattern != null) endPatternEl.value = String(o.backendEndPattern);
        if (widthCharsEl && o.backendWidthTestChars != null) widthCharsEl.value = String(o.backendWidthTestChars);
    } catch (e) {}
}
function saveCalTableControls() {
    try {
        const payload = {
            calTableCustomChars: document.getElementById('calTableCustomChars')?.value ?? '',
            calTableCharsPerLine: document.getElementById('calTableCharsPerLine')?.value ?? '2',
            calTableCharRepeat: document.getElementById('calTableCharRepeat')?.value ?? '5'
        };
        localStorage.setItem(CAL_TABLE_CONTROLS_KEY, JSON.stringify(payload));
    } catch (e) {}
}
function loadCalTableControls() {
    try {
        const raw = localStorage.getItem(CAL_TABLE_CONTROLS_KEY);
        if (!raw) return;
        const o = JSON.parse(raw);
        const customEl = document.getElementById('calTableCustomChars');
        const perLineEl = document.getElementById('calTableCharsPerLine');
        const repeatEl = document.getElementById('calTableCharRepeat');
        if (customEl && o.calTableCustomChars != null) customEl.value = String(o.calTableCustomChars);
        if (perLineEl && o.calTableCharsPerLine != null) perLineEl.value = String(o.calTableCharsPerLine);
        if (repeatEl && o.calTableCharRepeat != null) repeatEl.value = String(o.calTableCharRepeat);
    } catch (e) {}
}
function saveSettingsToCookie() {
    const hex = document.getElementById('backendPreviewBgHex')?.value || document.getElementById('backendPreviewBgColor')?.value || '';
    const exampleKey = (document.getElementById('exampleSelect')?.value || '').trim();
    const o = {
        updatedAt: Date.now(),
        theme: currentTheme,
        example: exampleKey,
        mode: currentMode,
        // 左側選項：Example Data、Title、Footer、Page/每頁/排序、dataJson（無範例時）等
        dataJson: exampleKey ? '' : (document.getElementById('dataJson')?.value || ''),
        tableTitle: document.getElementById('tableTitle')?.value || '',
        tableFooter: document.getElementById('tableFooter')?.value || '',
        page: document.getElementById('backendPage')?.value || '1',
        perPage: document.getElementById('backendPerPage')?.value || '15',
        sort: document.getElementById('backendSort')?.value || '',
        sortDesc: document.getElementById('backendSortDesc')?.checked || false,
        transparent: document.getElementById('cssTransparent')?.checked ?? true,
        previewBgByTheme: {},
        previewWidthMult: document.getElementById('previewWidthMult')?.value || '1.08',
        renderWidth: document.getElementById('renderWidth')?.value || '',
        renderTextScale: document.getElementById('renderTextScale')?.value || '',
        renderTextScaleMax: document.getElementById('renderTextScaleMax')?.value || '2.5',
        renderScale: document.getElementById('renderScale')?.value || '1',
        renderFillWidth: document.getElementById('renderFillWidth')?.value || '',
        renderBg: document.getElementById('renderBg')?.value || '',
        calibration: getCalibrationFromForm(),
        calTableCustomChars: document.getElementById('calTableCustomChars')?.value || '',
        calTableCharsPerLine: document.getElementById('calTableCharsPerLine')?.value || '2',
        calTableCharRepeat: document.getElementById('calTableCharRepeat')?.value || '5',
        ocrTestAnchor: document.getElementById('ocrTestAnchor')?.value || '',
        ocrTestEndAnchor: document.getElementById('ocrTestEndAnchor')?.value || '',
        ocrTestMethod: document.getElementById('ocrTestMethod')?.value || 'none',
        pixelPattern: document.getElementById('pixelPattern')?.value || '1 2 1 3 1 2',
        pixelEndPattern: document.getElementById('pixelEndPattern')?.value || '2 1 3 1 2 1',
        calibrationBlockContent: document.getElementById('calibrationBlockEdit')?.value || '',
        stage3CalibrationJson: document.getElementById('backendStage3CalibrationJson')?.value || '',
        // 新增校準參數
        backendCalCharsPerLine: document.getElementById('backendCalCharsPerLine')?.value || '6',
        backendCalCharRepeat: document.getElementById('backendCalCharRepeat')?.value || '5',
        backendCalCustomChars: document.getElementById('backendCalCustomChars')?.value || '',
        backendStartPattern: document.getElementById('backendStartPattern')?.value || '',
        backendEndPattern: document.getElementById('backendEndPattern')?.value || '',
        backendWidthTestChars: document.getElementById('backendWidthTestChars')?.value || '',

        // ASCII debug: stage1 PIL blueprint preview
        backendStage1PilPreviewEnabled: !!document.getElementById('backendStage1PilPreviewEnabled')?.checked,
        backendStage1UnitPx: document.getElementById('backendStage1UnitPx')?.value || ''
    };
    const existing = (() => { try { const r = getSettingsStorage(); return r ? JSON.parse(r) : {}; } catch(e) { return {}; } })();
    o.previewBgByTheme = existing.previewBgByTheme || {};
    if (hex && /^#[0-9A-Fa-f]{6}$/.test(hex) && currentTheme) {
        o.previewBgByTheme[currentTheme] = hex;
    }
    setSettingsStorage(JSON.stringify(o));
    saveBackendCalControls();
    saveCalTableControls();
}
function loadSettingsFromCookie() {
    const raw = getSettingsStorage();
    let hadPreviewBg = false;
    if (raw) {
        try {
            const o = JSON.parse(raw);
            if (o.theme) currentTheme = o.theme;
            if (o.mode && ['css', 'pil', 'ascii'].includes(String(o.mode))) currentMode = String(o.mode);
            const exSel = document.getElementById('exampleSelect');
            if (exSel && o.hasOwnProperty('example')) exSel.value = o.example != null ? String(o.example) : '';
            const dataEl = document.getElementById('dataJson');
            if (dataEl && o.dataJson != null && o.dataJson !== '') dataEl.value = o.dataJson;
            const titleEl = document.getElementById('tableTitle');
            if (titleEl && o.tableTitle != null) titleEl.value = o.tableTitle;
            const footerEl = document.getElementById('tableFooter');
            if (footerEl && o.tableFooter != null) footerEl.value = o.tableFooter;
            const pageEl = document.getElementById('backendPage');
            if (pageEl && o.page) pageEl.value = o.page;
            const perEl = document.getElementById('backendPerPage');
            if (perEl && o.perPage) perEl.value = o.perPage;
            const sortEl = document.getElementById('backendSort');
            if (sortEl && o.sort != null) sortEl.value = o.sort;
            const descEl = document.getElementById('backendSortDesc');
            if (descEl) descEl.checked = !!o.sortDesc;
            const transEl = document.getElementById('cssTransparent');
            if (transEl) transEl.checked = o.transparent !== false;
            const multEl = document.getElementById('previewWidthMult');
            if (multEl && o.previewWidthMult != null) multEl.value = String(o.previewWidthMult);
            const rwEl = document.getElementById('renderWidth');
            if (rwEl && o.renderWidth != null) rwEl.value = String(o.renderWidth);
            const rtsEl = document.getElementById('renderTextScale');
            if (rtsEl && o.renderTextScale != null) rtsEl.value = String(o.renderTextScale);
            const rtsmEl = document.getElementById('renderTextScaleMax');
            if (rtsmEl && o.renderTextScaleMax != null) rtsmEl.value = String(o.renderTextScaleMax);
            const rsEl = document.getElementById('renderScale');
            if (rsEl && o.renderScale != null) rsEl.value = String(o.renderScale);
            const rfwEl = document.getElementById('renderFillWidth');
            if (rfwEl && o.renderFillWidth != null) rfwEl.value = String(o.renderFillWidth);
            const rbgEl = document.getElementById('renderBg');
            if (rbgEl && o.renderBg != null) rbgEl.value = String(o.renderBg);
            const cal = o.calibration;
            if (cal && typeof cal === 'object') {
                ['ascii','cjk','box','half_space','full_space','emoji'].forEach(k => {
                    const el = document.getElementById('cal_' + k);
                    if (el && cal[k] != null) el.value = String(cal[k]);
                });
                const listEl = document.getElementById('cal_custom_list');
                if (listEl && cal.custom && typeof cal.custom === 'object') {
                    listEl.innerHTML = '';
                    Object.entries(cal.custom).forEach(([ch, w]) => addCalCustomRow(ch, w));
                }
            }
            const calTableInput = document.getElementById('calTableCustomChars');
            if (calTableInput && o.calTableCustomChars != null) {
                calTableInput.value = String(o.calTableCustomChars);
            }
            const calCharsPerLineEl = document.getElementById('calTableCharsPerLine');
            if (calCharsPerLineEl && o.calTableCharsPerLine != null) {
                calCharsPerLineEl.value = String(o.calTableCharsPerLine);
            }
            const calCharRepeatEl = document.getElementById('calTableCharRepeat');
            if (calCharRepeatEl && o.calTableCharRepeat != null) {
                calCharRepeatEl.value = String(o.calTableCharRepeat);
            }
            const ocrAnchorEl = document.getElementById('ocrTestAnchor');
            if (ocrAnchorEl && o.ocrTestAnchor != null) {
                ocrAnchorEl.value = String(o.ocrTestAnchor);
            }
            const ocrEndAnchorEl = document.getElementById('ocrTestEndAnchor');
            if (ocrEndAnchorEl && o.ocrTestEndAnchor != null) {
                ocrEndAnchorEl.value = String(o.ocrTestEndAnchor);
            }
            const ocrMethodEl = document.getElementById('ocrTestMethod');
            if (ocrMethodEl && o.ocrTestMethod && ['tesseract', 'rapidocr', 'none'].includes(String(o.ocrTestMethod))) {
                ocrMethodEl.value = String(o.ocrTestMethod);
            }
            const pixelPatternEl = document.getElementById('pixelPattern');
            if (pixelPatternEl && o.pixelPattern) {
                pixelPatternEl.value = String(o.pixelPattern);
            }
            const pixelEndPatternEl = document.getElementById('pixelEndPattern');
            if (pixelEndPatternEl && o.pixelEndPattern) {
                pixelEndPatternEl.value = String(o.pixelEndPattern);
            }
            const calBlockEdit = document.getElementById('calibrationBlockEdit');
            if (calBlockEdit && o.calibrationBlockContent != null && o.calibrationBlockContent !== '') {
                calBlockEdit.value = String(o.calibrationBlockContent);
                syncCalibrationPreFromEdit();
            }
            const stage3CalJsonEl = document.getElementById('backendStage3CalibrationJson');
            if (stage3CalJsonEl && o.stage3CalibrationJson != null && o.stage3CalibrationJson !== '') {
                stage3CalJsonEl.value = String(o.stage3CalibrationJson);
            }
            // 載入校準參數
            if (o.backendCalCharsPerLine != null) {
                const el = document.getElementById('backendCalCharsPerLine');
                if (el) el.value = String(o.backendCalCharsPerLine);
            }
            if (o.backendCalCharRepeat != null) {
                const el = document.getElementById('backendCalCharRepeat');
                if (el) el.value = String(o.backendCalCharRepeat);
            }
            if (o.backendCalCustomChars != null) {
                const el = document.getElementById('backendCalCustomChars');
                if (el) el.value = String(o.backendCalCustomChars);
            }
            {
                const startEl = document.getElementById('backendStartPattern');
                if (startEl) startEl.value = String(o.backendStartPattern != null ? o.backendStartPattern : (o.pixelPattern || '1 2 1 3 1 2'));
            }
            {
                const endEl = document.getElementById('backendEndPattern');
                if (endEl) endEl.value = String(o.backendEndPattern != null ? o.backendEndPattern : (o.pixelEndPattern || '2 1 3 1 2 1'));
            }
            {
                const widthCharsEl = document.getElementById('backendWidthTestChars');
                if (widthCharsEl) widthCharsEl.value = String(o.backendWidthTestChars != null ? o.backendWidthTestChars : '');
            }

            // ASCII debug: stage1 PIL blueprint preview
            {
                const pilEnabledEl = document.getElementById('backendStage1PilPreviewEnabled');
                if (pilEnabledEl && o.backendStage1PilPreviewEnabled != null) {
                    pilEnabledEl.checked = !!o.backendStage1PilPreviewEnabled;
                }
                const unitPxEl = document.getElementById('backendStage1UnitPx');
                if (unitPxEl && o.backendStage1UnitPx != null && o.backendStage1UnitPx !== '') {
                    const n = Math.max(5, Math.min(30, parseInt(String(o.backendStage1UnitPx), 10) || 14));
                    unitPxEl.value = String(n);
                }
            }
            const byTheme = o.previewBgByTheme || {};
            const themeBg = currentTheme && byTheme[currentTheme];
            if (themeBg && /^#[0-9A-Fa-f]{6}$/.test(themeBg)) {
                const colorEl = document.getElementById('backendPreviewBgColor');
                const hexEl = document.getElementById('backendPreviewBgHex');
                if (colorEl) colorEl.value = themeBg;
                if (hexEl) hexEl.value = themeBg;
                hadPreviewBg = true;
            }
        } catch (e) {}
    }
    return hadPreviewBg;
}
function getThemeBodyBg() {
    const bodyStyle = currentThemeTemplate?.styles?.body || currentThemeTemplate?.styles?.['body'] || '';
    let m = bodyStyle.match(/(?:^|[;\s])background(?:-color)?\s*:\s*(#[0-9A-Fa-f]{6})\b/i);
    if (!m) m = bodyStyle.match(/(?:^|[;\s])background\s*:\s*[^;]*?\s+(#[0-9A-Fa-f]{6})\b/i);
    if (!m) m = bodyStyle.match(/#([0-9A-Fa-f]{6})\b/);
    if (!m || !m[1]) return null;
    return m[1].startsWith('#') ? m[1] : '#' + m[1];
}
function applyPreviewBgForTheme(themeId, forceUseTheme) {
    themeId = themeId || currentTheme;
    let hex = null;
    if (!forceUseTheme) {
        try {
            const raw = getSettingsStorage();
            const o = raw ? JSON.parse(raw) : {};
            const byTheme = o.previewBgByTheme || {};
            hex = themeId && byTheme[themeId];
        } catch (e) {}
    }
    if (!hex || !/^#[0-9A-Fa-f]{6}$/.test(hex)) {
        hex = getThemeBodyBg();
        if (!hex) {
            const t = loadedThemes?.[themeId];
            const themeColor = t?.theme_color || t?.accent || '#e94560';
            hex = themeColor.startsWith('#') ? themeColor : (themeColor.length === 6 ? '#' + themeColor : '#e94560');
            if (!/^#[0-9A-Fa-f]{6}$/.test(hex)) hex = '#e94560';
        }
    }
    const colorEl = document.getElementById('backendPreviewBgColor');
    const hexEl = document.getElementById('backendPreviewBgHex');
    if (colorEl) colorEl.value = hex;
    if (hexEl) hexEl.value = hex;
    applyBackendPreviewBg(hex);
}
function applyThemeColorToPreviewBg() {
    applyPreviewBgForTheme(currentTheme);
}
window.onload = async () => {
    const hadPreviewBg = loadSettingsFromCookie();
    loadBackendCalControls();
    loadCalTableControls();
    initBackendStage3LiveSync();
    syncBackendOcrMethodControl(true);
    const dataEl = document.getElementById('dataJson');
    const exSel = document.getElementById('exampleSelect');
    const exampleKey = exSel?.value?.trim();
    if (exampleKey) {
        await loadExample(exampleKey);
    } else if (!dataEl?.value?.trim()) {
        await loadExample('servers');
    }
    await setMode(currentMode || 'css');
    if (!hadPreviewBg) applyThemeColorToPreviewBg();
    if (currentMode === 'ascii') refreshCalibrationTable();
    updatePreview();
    saveSettingsToCookie();
};
function syncNum(source, target) { document.getElementById(target).value = source.value; }
/** 從數字輸入同步回滑桿，並將數值 clamp 到滑桿的 min/max，使滑桿與數值範圍一致 */
function syncNumFromNum(numEl) {
    const rangeId = (numEl && numEl.id) ? numEl.id.replace(/_num$/, '') : '';
    const r = rangeId ? document.getElementById(rangeId) : null;
    if (r && r.type === 'range') {
        const min = Number(r.min);
        const max = Number(r.max);
        const step = r.step ? Number(r.step) : 1;
        let v = Number(numEl.value);
        if (isNaN(v)) v = min;
        v = Math.max(min, Math.min(max, v));
        if (step > 0) v = Math.round(v / step) * step;
        r.value = v;
        numEl.value = v;
    }
    updatePreview();
}
function syncColorFromText(input) {
    const colorInput = input.nextElementSibling;
    if (colorInput && colorInput.type === 'color') {
        let hex = input.value;
        if (hex && hex.startsWith('#') && (hex.length === 7 || hex.length === 9)) {
            colorInput.value = hex.substring(0, 7);
        }
    }
}
const CSS_SELECTOR_PLACEHOLDERS = {
    body: 'background: #1a1a2e; color: #fff; padding: 20px;',
    container: 'width: auto; border-radius: 8px;',
    table: 'width: 100%; table-layout: auto;',
    title: 'padding: 20px; font-size: 20px; font-weight: bold;',
    th: 'padding: 8px 12px; background: #0f3460;',
    td: 'padding: 6px 12px; font-size: 13px;',
    tr_even: 'background: #16213e;',
    tr_odd: 'background: #1a1a2e;',
    footer: 'padding: 8px 16px; font-size: 11px;',
    col_1: 'width: 200px;', col_2: 'width: 120px;', col_3: 'width: 150px;', col_4: 'width: 100px;',
    col_5: 'width: 100px;', col_6: 'width: 100px;', col_7: 'width: 100px;', col_8: 'width: 100px;'
};
function getSelectorKeysFromTemplate(template) {
    const styles = template?.styles || {};
    return Object.keys(styles).filter(k => k && typeof styles[k] === 'string');
}
// 編輯框顯示：將 ";" 轉為換行
function cssStoredToDisplay(text) {
    if (!text || typeof text !== 'string') return '';
    return text.split(';').map(s => s.trim()).filter(Boolean).join('\n');
}
// 儲存時：將換行整理回 ";" 分隔的單行字串
function cssDisplayToStored(text) {
    if (!text || typeof text !== 'string') return '';
    return text.split(/\r?\n/).map(s => s.trim()).filter(Boolean).join('; ');
}
// 從 CSS 字串解析 font-family 值，回傳字型名稱陣列
function extractFontsFromCss(cssText) {
    if (!cssText || typeof cssText !== 'string') return [];
    const m = cssText.match(/font-family\s*:\s*([^;]+)/i);
    if (!m) return [];
    return m[1].split(',').map(s => s.trim().replace(/^['"]|['"]$/g, '')).filter(Boolean);
}
// 前端預覽可從 CDN 載入的字型（後端通常已有系統字型）
const PREVIEW_WEB_FONTS = {
    'Noto Color Emoji': `@font-face{font-family:'Noto Color Emoji';font-style:normal;font-display:swap;font-weight:400;src:url(https://cdn.jsdelivr.net/fontsource/fonts/noto-color-emoji@latest/emoji-400-normal.woff2) format('woff2'),url(https://cdn.jsdelivr.net/fontsource/fonts/noto-color-emoji@latest/emoji-400-normal.woff) format('woff');}`,
    'Apple Color Emoji': null,
    'Segoe UI Emoji': null,
    'Segoe UI Symbol': null
};
function getPreviewFontFaceCss(fontList) {
    const needLoad = (fontList || []).filter(f => PREVIEW_WEB_FONTS[f]);
    if (needLoad.length === 0) return '';
    return needLoad.map(f => PREVIEW_WEB_FONTS[f]).join(' ');
}
function getLoadableWebFontNames(fontList) {
    return (fontList || []).filter(f => PREVIEW_WEB_FONTS[f]);
}
// 從主題 template 提取各選擇器的 font-family
function getFontsFromTheme(template) {
    const styles = template?.styles || {};
    const out = { frontend: [], backend: [] };
    const allFonts = new Set();
    Object.entries(styles).forEach(([selector, css]) => {
        const fonts = extractFontsFromCss(css);
        if (fonts.length) {
            fonts.forEach(f => allFonts.add(f));
        }
    });
    out.frontend = [...allFonts];
    out.backend = [...allFonts];
    return out;
}
function updateFontDetection() {
    const frontEl = document.getElementById('fontListFrontend');
    const backEl = document.getElementById('fontListBackend');
    const noteEl = document.getElementById('fontLoadNoteText');
    const noteWrap = document.getElementById('fontLoadNote');
    if (!frontEl || !backEl) return;
    let template = currentThemeTemplate;
    if (currentMode === 'css' && cssEditMode === 'advanced') {
        try { template = JSON.parse(document.getElementById('cssThemeJson').value); } catch(e) {}
    }
    const fonts = getFontsFromTheme(template);
    const fmt = arr => arr.length ? arr.join(', ') : '(無)';
    frontEl.textContent = fmt(fonts.frontend);
    backEl.textContent = fmt(fonts.backend);
    const loaded = getLoadableWebFontNames(fonts.frontend);
    if (noteEl && noteWrap) {
        if (loaded.length) {
            noteWrap.style.display = '';
            noteEl.textContent = '✓ 前端預覽已從 CDN 載入: ' + loaded.join(', ');
        } else {
            noteWrap.style.display = 'none';
        }
    }
}
function renderSelectorList(template) {
    const list = document.getElementById('css-selector-list');
    if (!list) return;
    if (!template) template = { type: 'css', name: 'Custom', version: '1.0.0', styles: {} };
    const keys = getSelectorKeysFromTemplate(template);
    if (keys.length === 0) keys.push('body', 'container', 'table');
    const esc = v => String(v).replace(/&/g,'&amp;').replace(/"/g,'&quot;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
    list.innerHTML = keys.map(key => {
        const ph = esc(cssStoredToDisplay(CSS_SELECTOR_PLACEHOLDERS[key] || ''));
        const safeId = 'css_style_' + String(key).replace(/[^a-zA-Z0-9_-]/g, '_');
        const escKey = esc(key);
        return `<div class="selector-item collapsed" data-key="${escKey}" id="sel_${safeId}">
            <div class="selector-item-header" onclick="toggleSelectorItem('${safeId}')">
                <span>${escKey}</span>
                <span class="toggle">▼</span>
            </div>
            <div class="selector-item-content">
                <textarea id="${safeId}" rows="5" class="css-selector-input" placeholder="${ph}" data-key="${escKey}" onchange="buildCssTemplateFromSelectors(); updatePreview();"></textarea>
            </div>
        </div>`;
    }).join('');
    keys.forEach(key => {
        const val = (template?.styles || {})[key] || '';
        const safeId = 'css_style_' + String(key).replace(/[^a-zA-Z0-9_-]/g, '_');
        const ta = document.getElementById(safeId);
        if (ta) ta.value = cssStoredToDisplay(val);
    });
}
function toggleSelectorItem(safeId) {
    const item = document.getElementById('sel_' + safeId);
    if (item) item.classList.toggle('collapsed');
}
function addSelectorElement() {
    const sel = document.getElementById('cssSelectorAddSelect');
    const key = sel?.value?.trim();
    if (!key) return;
    const template = currentThemeTemplate ? { ...currentThemeTemplate } : { type: 'css', name: 'Custom', version: '1.0.0' };
    template.styles = { ...(template.styles || {}), [key]: '' };
    currentThemeTemplate = template;
    renderSelectorList(template);
    sel.value = '';
    updateSelectorAddOptions();
}
function updateSelectorAddOptions() {
    const sel = document.getElementById('cssSelectorAddSelect');
    if (!sel) return;
    const keys = getSelectorKeysFromTemplate(currentThemeTemplate);
    [...sel.options].forEach(opt => {
        if (opt.value && keys.includes(opt.value)) opt.disabled = true;
        else if (opt.value) opt.disabled = false;
    });
}
function toggleCssEditMode(mode) {
    cssEditMode = mode;
    document.getElementById('css-selector-editor').classList.toggle('hidden', mode !== 'selector');
    document.getElementById('css-advanced-editor').classList.toggle('hidden', mode !== 'advanced');
        if (mode === 'selector') {
        if (cssEditMode === 'advanced') {
            try { currentThemeTemplate = JSON.parse(document.getElementById('cssThemeJson').value); } catch(e) {}
        }
        renderSelectorList(currentThemeTemplate);
        updateSelectorAddOptions();
        buildCssTemplateFromSelectors();
    }
}
function buildCssTemplateFromSelectors() {
    const styles = {};
    document.querySelectorAll('#css-selector-list textarea[data-key]').forEach(ta => {
        const k = ta.getAttribute('data-key');
        if (k) styles[k] = cssDisplayToStored(ta.value || '');
    });
    const template = currentThemeTemplate ? { ...currentThemeTemplate } : { type: 'css', name: 'Custom', version: '1.0.0' };
    template.styles = styles;
    currentThemeTemplate = template;
    if (cssEditMode === 'advanced') document.getElementById('cssThemeJson').value = JSON.stringify(template, null, 2);
    updateSelectorAddOptions();
}
function populateCssSelectorsFromTemplate(template) {
    renderSelectorList(template);
    if (cssEditMode === 'selector') updateSelectorAddOptions();
}
function hasUnsavedChanges() {
    if (currentMode !== 'css') return false;
    if (cssEditMode === 'advanced') {
        try {
            const edited = JSON.parse(document.getElementById('cssThemeJson').value);
            return JSON.stringify(edited) !== JSON.stringify(currentThemeTemplate);
        } catch(e) { return true; }
    }
    const styles = currentThemeTemplate?.styles || {};
    let hasDiff = false;
    document.querySelectorAll('#css-selector-list textarea[data-key]').forEach(ta => {
        const k = ta.getAttribute('data-key');
        const val = cssDisplayToStored(ta.value || '');
        const orig = (styles[k] || '').trim();
        if (val !== orig) hasDiff = true;
    });
    return hasDiff;
}
async function maybeSetMode(mode) {
    if (mode === currentMode) return;
    if (hasUnsavedChanges()) {
        const choice = confirm('未儲存變更將遺失。是否先儲存？\n\n[確定] 儲存後切換\n[取消] 不儲存，直接切換');
        if (choice === null) return; // 使用者關閉對話框
        if (choice) {
            await saveThemeToServer();
        }
    }
    await setMode(mode);
}
async function setMode(mode) {
    currentMode = mode;
    saveSettingsToCookie();
    document.querySelectorAll('.mode-btn').forEach(b => b.classList.toggle('active', b.innerText.toLowerCase().includes(mode)));
    document.getElementById('currentModeLabel').innerText = mode.toUpperCase();
    document.getElementById('editor-css').classList.toggle('hidden', mode !== 'css');
    document.getElementById('editor-pil').classList.toggle('hidden', mode !== 'pil');
    document.getElementById('editor-ascii').classList.toggle('hidden', mode !== 'ascii');
    const tw = document.getElementById('cssTransparentWrap');
    if (tw) tw.style.display = mode === 'css' ? 'flex' : 'none';
    const pw = document.getElementById('previewWidthWrap');
    if (pw) pw.style.display = mode === 'css' ? 'flex' : 'none';
    const calTab = document.getElementById('previewTabCalibration');
    if (calTab) calTab.style.display = mode === 'ascii' ? '' : 'none';
    const calResultTab = document.getElementById('previewTabCalibrationResult');
    if (calResultTab) calResultTab.style.display = mode === 'ascii' ? '' : 'none';
    if (mode !== 'ascii') {
        const calView = document.getElementById('view-calibration');
        const calResultView = document.getElementById('view-calibration-result');
        if ((calView && !calView.classList.contains('hidden')) || (calResultView && !calResultView.classList.contains('hidden'))) setPreviewTab('frontend');
    }
    await loadThemesFromApi();
    await loadThemeTemplate(currentTheme);
    await updateStyleEditor();
    updatePreview();
}
function setPreviewTab(tab) {
    const mainTabs = document.getElementById('mainPreviewTabs');
    if (mainTabs) Array.from(mainTabs.children).filter(t => t.classList.contains('preview-tab')).forEach(t => {
        t.classList.toggle('active', t.getAttribute('data-tab') === tab);
    });
    document.getElementById('view-frontend').classList.toggle('hidden', tab !== 'frontend');
    document.getElementById('view-backend').classList.toggle('hidden', tab !== 'backend');
    document.getElementById('view-code').classList.toggle('hidden', tab !== 'code');
    const calView = document.getElementById('view-calibration');
    if (calView) calView.classList.toggle('hidden', tab !== 'calibration');
    const calResultView = document.getElementById('view-calibration-result');
    if (calResultView) calResultView.classList.toggle('hidden', tab !== 'calibration-result');
    if (tab === 'calibration') {
        loadCalTableControls();
        const editEl = document.getElementById('calibrationBlockEdit');
        if (editEl && !editEl.value.trim()) refreshCalibrationTable();
    }
    const wrapEl = document.getElementById('calBlockEditorWrap');
    if (wrapEl) wrapEl.classList.toggle('hidden', tab !== 'calibration');
}

function parseCalTableCharsInput(inputText) {
    const raw = String(inputText || '').trim();
    if (!raw) return [];
    // 新格式：以 "U+XXXX" 或 "U+AAAA U+BBBB"（flag pair）表示
    if (raw.includes('U+')) {
        const decoded = decodeCalibrationCodesInput(raw);
        if (decoded.length > 0) return decoded;
    }
    // 舊格式相容：直接輸入字元字串
    return [...raw].filter(c => c.trim());
}

function formatCharsAsQuotedCodes(chars) {
    return (chars || []).map(ch => `"${formatUnicodeCodes(ch)}"`).join(' ');
}
function extractCharsFromCurrentPattern() {
    try {
        // 從當前編輯器中提取字元
        const uniqueChars = new Set();
        
        // 1. 從表格數據中提取字元
        const rawData = document.getElementById('rawData')?.value;
        if (rawData && rawData.trim()) {
            try {
                const data = JSON.parse(rawData);
                // 提取標題欄字元
                if (data.headers && Array.isArray(data.headers)) {
                    data.headers.forEach(h => {
                        if (typeof h === 'string') {
                            for (const c of h) {
                                if (c.trim() && c !== ' ' && c !== '\u3000') uniqueChars.add(c);
                            }
                        }
                    });
                }
                // 提取資料列字元
                if (data.rows && Array.isArray(data.rows)) {
                    data.rows.forEach(row => {
                        if (Array.isArray(row)) {
                            row.forEach(cell => {
                                if (typeof cell === 'string') {
                                    for (const c of cell) {
                                        if (c.trim() && c !== ' ' && c !== '\u3000') uniqueChars.add(c);
                                    }
                                } else if (typeof cell === 'number') {
                                    String(cell).split('').forEach(c => uniqueChars.add(c));
                                }
                            });
                        }
                    });
                }
            } catch (e) {
                console.warn('無法解析表格數據:', e);
            }
        }
        
        // 2. 從框線字元中提取
        const boxKeys = ['box_tl', 'box_tr', 'box_bl', 'box_br', 'box_h', 'box_v', 'box_header', 'box_row', 'box_footer'];
        boxKeys.forEach(key => {
            const el = document.getElementById(key);
            if (el && el.value && el.value.trim()) {
                uniqueChars.add(el.value.trim()[0]);
            }
        });
        
        // 3. 轉換為字串（保持一定順序：ASCII -> 框線 -> CJK）
        const resultChars = [];
        const boxChars = '─═│║╔╗╚╝┌┐└┘├┤┬┴┼╠╣╬┏┓┗┛┣┫┳┻╋';
        
        // ASCII 字母數字
        const asciiChars = Array.from(uniqueChars).filter(c => {
            const code = c.charCodeAt(0);
            return code < 128 && /[A-Za-z0-9]/.test(c);
        }).sort();
        resultChars.push(...asciiChars);
        
        // 框線字元
        const boxCharsList = Array.from(uniqueChars).filter(c => boxChars.includes(c)).sort();
        resultChars.push(...boxCharsList);
        
        // CJK 字元
        const cjkChars = Array.from(uniqueChars).filter(c => {
            const code = c.charCodeAt(0);
            return code >= 0x4E00 && code <= 0x9FFF;
        }).sort();
        resultChars.push(...cjkChars);
        
        // 其他字元
        const otherChars = Array.from(uniqueChars).filter(c => !resultChars.includes(c)).sort();
        resultChars.push(...otherChars);
        
        // 限制最多 50 個字元，並用 U+ 格式回填（含 flag pair key）
        const finalChars = resultChars.slice(0, 50);
        
        // 填入輸入框
        const customInput = document.getElementById('calTableCustomChars');
        if (customInput) {
            customInput.value = finalChars.length ? formatCharsAsQuotedCodes(finalChars) : '"U+0041" "U+0042" "U+0043" "U+5B57"';
            saveSettingsToCookie();
            refreshCalibrationTable();
            alert('已提取 ' + finalChars.length + ' 個字元');
        }
    } catch (e) {
        console.error('提取字元失敗:', e);
        alert('提取字元失敗: ' + e.message);
    }
}

function parsePositivePattern(patternText, fallbackText) {
    const src = (patternText && String(patternText).trim()) ? String(patternText).trim() : String(fallbackText || '').trim();
    const nums = src.split(/\s+/).map(s => parseInt(s, 10)).filter(n => !isNaN(n) && n > 0);
    return nums.length > 0 ? nums : String(fallbackText || '').trim().split(/\s+/).map(s => parseInt(s, 10)).filter(n => !isNaN(n) && n > 0);
}
function patternToBlockLine(patternNums, fallbackLiteral) {
    if (!Array.isArray(patternNums) || patternNums.length === 0) return String(fallbackLiteral || '');
    const parts = [];
    for (const n of patternNums) {
        parts.push('\u2588'.repeat(n));
        parts.push(' ');
    }
    return parts.join('').trim();
}
function getEffectivePixelPatterns() {
    const backendStart = document.getElementById('backendStartPattern')?.value?.trim() || '';
    const backendEnd = document.getElementById('backendEndPattern')?.value?.trim() || '';
    const panelStart = document.getElementById('pixelPattern')?.value?.trim() || '';
    const panelEnd = document.getElementById('pixelEndPattern')?.value?.trim() || '';
    const startRaw = backendStart || panelStart || '1 2 1 3 1 2';
    const endRaw = backendEnd || panelEnd || '2 1 3 1 2 1';
    return { startRaw, endRaw };
}

/** 產生校準區塊文字。
 *  overrideCustomChars: 傳入則使用該字元集，否則從表單讀取。
 *  overrideCharsPerLine: 傳入則使用該每行字數，否則從表單讀取（1-10）。
 */
function getCalibrationBlockText(overrideCustomChars, overrideCharsPerLine) {
    const customInput = document.getElementById('calTableCustomChars');
    const customChars = (overrideCustomChars != null && overrideCustomChars !== '')
        ? (Array.isArray(overrideCustomChars) ? overrideCustomChars : parseCalTableCharsInput(String(overrideCustomChars)))
        : parseCalTableCharsInput((customInput && customInput.value) ? customInput.value.trim() : '"U+0041" "U+0042" "U+0043" "U+5B57"');
    const charsPerLineInput = document.getElementById('calTableCharsPerLine');
    const charsPerLine = (overrideCharsPerLine != null)
        ? Math.max(1, Math.min(10, parseInt(overrideCharsPerLine) || 2))
        : Math.max(1, Math.min(10, parseInt(charsPerLineInput?.value) || 2));
    const repeatInput = document.getElementById('calTableCharRepeat');
    const charRepeat = Math.max(3, Math.min(20, parseInt(repeatInput?.value, 10) || 5));
    const ocrMethod = document.getElementById('ocrTestMethod')?.value || 'none';
    const isPixelMode = (ocrMethod === 'none');
    const lines = [];

    if (isPixelMode) {
        const { startRaw, endRaw } = getEffectivePixelPatterns();
        const startPattern = parsePositivePattern(startRaw, '1 2 1 3 1 2');
        let startLine = patternToBlockLine(startPattern, '\u2588 \u2588\u2588 \u2588 \u2588\u2588\u2588 \u2588 \u2588\u2588');
        lines.push(startLine);
        lines.push('\u2588     \u2588 \u2588\u3000\u3000\u3000\u3000\u3000\u2588');

        const chars = customChars;
        for (let i = 0; i < chars.length; i += charsPerLine) {
            const lineChars = chars.slice(i, i + charsPerLine);
            let line = '';
            for (let j = 0; j < lineChars.length; j++) {
                line += (j === 0 ? '\u2588 ' : ' \u2588 ') + lineChars[j].repeat(charRepeat) + ' \u2588';
            }
            lines.push(line);
        }

        const endPattern = parsePositivePattern(endRaw, '2 1 3 1 2 1');
        let endLine = patternToBlockLine(endPattern, '\u2588\u2588 \u2588 \u2588\u2588\u2588 \u2588 \u2588\u2588 \u2588');
        lines.push(endLine);
    } else {
        const anchorEl = document.getElementById('ocrTestAnchor');
        lines.push((anchorEl && anchorEl.value) ? anchorEl.value.trim() : '[ZENT-BLE-MKR]');
        const endAnchorEl = document.getElementById('ocrTestEndAnchor');
        lines.push((endAnchorEl && endAnchorEl.value) ? endAnchorEl.value.trim() : '[END]');
    }
    return lines.join('\n');
}

function refreshCalibrationTable() {
    const el = document.getElementById('calibrationOutput');
    const editEl = document.getElementById('calibrationBlockEdit');
    if (!el) return;
    const patternWrap = document.getElementById('pixelPatternWrap');
    const endPatternWrap = document.getElementById('pixelEndPatternWrap');
    const ocrMethod = document.getElementById('ocrTestMethod')?.value || 'none';
    const isPixelMode = (ocrMethod === 'none');
    if (patternWrap) patternWrap.classList.toggle('hidden', !isPixelMode);
    if (endPatternWrap) endPatternWrap.classList.toggle('hidden', !isPixelMode);

    const text = getCalibrationBlockText(null);
    el.textContent = text;
    if (editEl) editEl.value = text;
}
function syncCalibrationPreFromEdit() {
    const editEl = document.getElementById('calibrationBlockEdit');
    const preEl = document.getElementById('calibrationOutput');
    if (editEl && preEl) preEl.textContent = editEl.value;
}
function syncCalibrationEditFromPre() {
    const preEl = document.getElementById('calibrationOutput');
    const editEl = document.getElementById('calibrationBlockEdit');
    if (preEl && editEl) editEl.value = preEl.textContent;
}
let isBackendStage3Syncing = false;
function setBackendStage3Text(text, source = 'render', updateBase = true) {
    if (isBackendStage3Syncing) return;
    isBackendStage3Syncing = true;
    try {
        const next = String(text || '');
        const stage3El = document.getElementById('backendAsciiStage3Text');
        const editEl = document.getElementById('backendStage3LiveEdit');
        if (stage3El) {
            stage3El.textContent = next;
            if (updateBase) stage3El.dataset.baseText = next;
        }
        if (editEl && source !== 'edit') {
            editEl.textContent = next;
        }
        if (source === 'edit') {
            // 手動改寫後，trace 與內容不再一致，清掉避免 debug 誤導
            window.__backendStage3Details = null;
        }
        refreshBackendStage3Debug();
    } finally {
        isBackendStage3Syncing = false;
    }
}
function initBackendStage3LiveSync() {
    const editEl = document.getElementById('backendStage3LiveEdit');
    if (!editEl || editEl.dataset.bound === '1') return;
    editEl.dataset.bound = '1';
    editEl.addEventListener('input', () => {
        setBackendStage3Text(editEl.textContent || '', 'edit', true);
    });
}
function copyCalibrationBlock() {
    const editEl = document.getElementById('calibrationBlockEdit');
    const text = (editEl && editEl.value) ? editEl.value : (document.getElementById('calibrationOutput')?.textContent || '');
    if (navigator.clipboard?.writeText) {
        navigator.clipboard.writeText(text).then(() => alert('已複製')).catch(() => {});
    } else {
        const ta = document.createElement('textarea');
        ta.value = text;
        document.body.appendChild(ta);
        ta.select();
        document.execCommand('copy');
        document.body.removeChild(ta);
        alert('已複製');
    }
}
// 清除貼上的圖片
function clearPastedImage(e) {
    if (e) e.stopPropagation();
    pastedOcrTestImage = null;
    currentTestImage = null;
    const imgWrap = document.getElementById('ocrTestPasteImgWrap');
    const hint = document.getElementById('ocrTestPasteHint');
    const img = document.getElementById('ocrTestPastePreview');
    if (imgWrap) imgWrap.style.display = 'none';
    if (hint) hint.textContent = 'Ctrl+V 貼上截圖';
    if (img) { img.src = ''; }
}
function clearBackendPastedImage(e) {
    if (e) e.stopPropagation();
    pastedOcrTestImage = null;
    currentTestImage = null;
    const fileInput = document.getElementById('backendOcrTestInput');
    if (fileInput) fileInput.value = '';
    const wrap = document.getElementById('backendOcrPasteImgWrap');
    const img = document.getElementById('backendOcrPastePreview');
    const hint = document.getElementById('backendOcrPasteHint');
    const uploadHint = document.getElementById('backendOcrUploadHint');
    if (wrap) wrap.style.display = 'none';
    if (img) { img.src = ''; }
    if (hint) hint.textContent = 'Ctrl+V 貼上截圖';
    if (uploadHint) uploadHint.textContent = '尚未選擇圖片';
}
function resetBackendUploadUi() {
    const wrap = document.getElementById('backendOcrPasteImgWrap');
    const img = document.getElementById('backendOcrPastePreview');
    const hint = document.getElementById('backendOcrPasteHint');
    const uploadHint = document.getElementById('backendOcrUploadHint');
    const fileInput = document.getElementById('backendOcrTestInput');
    if (wrap) wrap.style.display = 'none';
    if (img) img.src = '';
    if (hint) hint.textContent = 'Ctrl+V 貼上截圖';
    if (uploadHint) uploadHint.textContent = '尚未選擇圖片';
    if (fileInput) fileInput.value = '';
}

let pastedOcrTestImage = null;
(function initOcrTestPaste() {
    const zone = document.getElementById('ocrTestPasteZone');
    if (!zone) return;
    zone.addEventListener('click', () => zone.focus());
    zone.addEventListener('paste', (e) => {
        const item = e.clipboardData?.items && Array.from(e.clipboardData.items).find(x => x.type.startsWith('image/'));
        if (!item) return;
        e.preventDefault();
        const blob = item.getAsFile();
        if (!blob) return;
        pastedOcrTestImage = blob;
        const img = document.getElementById('ocrTestPastePreview');
        const imgWrap = document.getElementById('ocrTestPasteImgWrap');
        const hint = document.getElementById('ocrTestPasteHint');
        if (img) img.src = URL.createObjectURL(blob);
        if (imgWrap) imgWrap.style.display = '';
        if (hint) hint.textContent = '已貼上，點測試按鈕';
    });
})();
(function initBackendOcrPaste() {
    const zone = document.getElementById('backendOcrPasteZone');
    if (!zone) return;
    zone.addEventListener('click', () => zone.focus());
    zone.addEventListener('paste', (e) => {
        const item = e.clipboardData?.items && Array.from(e.clipboardData.items).find(x => x.type.startsWith('image/'));
        if (!item) return;
        e.preventDefault();
        const blob = item.getAsFile();
        if (!blob) return;
        pastedOcrTestImage = blob;
        currentTestImage = null;
        const img = document.getElementById('backendOcrPastePreview');
        const wrap = document.getElementById('backendOcrPasteImgWrap');
        const hint = document.getElementById('backendOcrPasteHint');
        const uploadHint = document.getElementById('backendOcrUploadHint');
        if (img) img.src = URL.createObjectURL(blob);
        if (wrap) wrap.style.display = '';
        if (hint) hint.textContent = '已貼上，點測試按鈕';
        if (uploadHint) uploadHint.textContent = '已貼上截圖';
    });
    zone.addEventListener('keydown', (e) => { if (e.key === ' ' || e.key === 'Enter') e.preventDefault(); });
})();
function syncBackendOcrMethodControl(fromMain) {
    const mainEl = document.getElementById('ocrTestMethod');
    const backendEl = document.getElementById('backendOcrTestMethod');
    if (!mainEl || !backendEl) return;
    if (fromMain) {
        backendEl.value = mainEl.value || 'none';
        return;
    }
    mainEl.value = backendEl.value || 'none';
    saveSettingsToCookie();
    refreshCalibrationTable();
}
function handleBackendImageUpload(input) {
    if (!input?.files?.length) return;
    const file = input.files[0];
    currentTestImage = file;
    pastedOcrTestImage = null;
    const hint = document.getElementById('backendOcrUploadHint');
    if (hint) hint.textContent = `已選擇: ${file.name} (${Math.round(file.size / 1024)} KB)`;
    const pasteWrap = document.getElementById('backendOcrPasteImgWrap');
    const pasteHint = document.getElementById('backendOcrPasteHint');
    const pasteImg = document.getElementById('backendOcrPastePreview');
    if (pasteWrap) pasteWrap.style.display = 'none';
    if (pasteHint) pasteHint.textContent = 'Ctrl+V 貼上截圖';
    if (pasteImg) pasteImg.src = '';
}
function getBackendExportCharContext() {
    const backendWidthInput = document.getElementById('backendWidthTestChars');
    const customInput = document.getElementById('backendCalCustomChars');
    const usedCodesInput = document.getElementById('backendStage3UsedCalibrationCodes');
    const backendWidthChars = parseCalTableCharsInput((backendWidthInput && backendWidthInput.value) ? backendWidthInput.value.trim() : '');
    const extraChars = decodeCalibrationCodesInput((customInput && customInput.value) ? customInput.value.trim() : '');
    const usedCodesChars = decodeCalibrationCodesInput((usedCodesInput && usedCodesInput.value) ? usedCodesInput.value.trim() : '');
    const baseChars = backendWidthChars.length > 0
        ? backendWidthChars
        : (extraChars.length > 0 ? extraChars : usedCodesChars);
    const mergedChars = mergeUniqueChars(baseChars, extraChars);
    return {
        backendWidthChars,
        extraChars,
        usedCodesChars,
        baseChars,
        mergedChars,
        customChars: mergedChars.join(''),
        testCharGroups: encodeCharsToQuotedCodeList(mergedChars)
    };
}
function buildBackendExportParamSummary(file, ocrMethod) {
    const { startRaw, endRaw } = getEffectivePixelPatterns();
    const ctx = getBackendExportCharContext();
    const perLineInput = document.getElementById('backendCalCharsPerLine');
    const calTableCharsPerLineInput = document.getElementById('calTableCharsPerLine');
    const repeatInput = document.getElementById('backendCalCharRepeat');
    const charsPerLine = (perLineInput && perLineInput.value)
        ? String(Math.max(1, Math.min(10, parseInt(perLineInput.value, 10) || 6)))
        : (calTableCharsPerLineInput ? (calTableCharsPerLineInput.value || '2') : '2');
    const repeatCount = String(Math.max(1, Math.min(20, parseInt(repeatInput?.value, 10) || 5)));
    const lines = [];
    lines.push(`file: ${file?.name || '(pasted image)'} (${file?.type || 'unknown'}, ${file?.size || 0} bytes)`);
    lines.push(`ocr: ${ocrMethod}`);
    lines.push(`use_startpoint_pipeline: ${ocrMethod === 'none' ? '1' : '0'}`);
    lines.push(`pixel_pattern: ${startRaw}`);
    lines.push(`pixel_end_pattern: ${endRaw}`);
    lines.push(`chars_per_line: ${charsPerLine}`);
    lines.push(`repeat_count: ${repeatCount}`);
    lines.push(`backendWidthChars count: ${ctx.backendWidthChars.length}`);
    lines.push(`backendCalCustomChars count: ${ctx.extraChars.length}`);
    lines.push(`usedCalibrationCodes count: ${ctx.usedCodesChars.length}`);
    lines.push(`mergedChars count: ${ctx.mergedChars.length}`);
    lines.push(`custom_chars (送出): ${ctx.customChars}`);
    lines.push(`custom_chars_uplus_view: ${ctx.testCharGroups}`);
    lines.push(`test_char_groups (找錨點): ${ctx.testCharGroups}`);
    return lines.join('\n');
}
function showBackendExportParamPreview(text) {
    const overlay = document.getElementById('backendExportParamModal');
    const pre = document.getElementById('backendExportParamText');
    const cancelBtn = document.getElementById('backendExportParamCancelBtn');
    const okBtn = document.getElementById('backendExportParamConfirmBtn');
    if (!overlay || !pre || !cancelBtn || !okBtn) return Promise.resolve(true);
    pre.textContent = text || '(無內容)';
    overlay.classList.remove('hidden');
    return new Promise(resolve => {
        const cleanup = (result) => {
            overlay.classList.add('hidden');
            cancelBtn.onclick = null;
            okBtn.onclick = null;
            resolve(result);
        };
        cancelBtn.onclick = () => cleanup(false);
        okBtn.onclick = () => cleanup(true);
    });
}
async function runBackendAnchorDetection() {
    syncBackendOcrMethodControl(false);
    const file = currentTestImage || pastedOcrTestImage;
    if (!file) { alert('請先上傳或貼上截圖'); return; }
    const f = file instanceof File ? file : new File([file], 'test.png', { type: file.type || 'image/png' });
    const ocrMethod = document.getElementById('ocrTestMethod')?.value || 'none';
    if (ocrMethod === 'none') {
        await findCalibrationStartPoint({ files: [f] }, { suppressTabSwitch: true });
    } else {
        await uploadOcrTestScreenshot({ files: [f] });
    }
}
async function runBackendExportCalibrationJson() {
    syncBackendOcrMethodControl(false);
    const file = currentTestImage || pastedOcrTestImage;
    if (!file) { alert('請先上傳或貼上截圖'); return; }
    const f = file instanceof File ? file : new File([file], 'test.png', { type: file.type || 'image/png' });
    const ocrMethod = document.getElementById('ocrTestMethod')?.value || 'none';
    const confirmCheck = document.getElementById('backendExportParamCheck');
    if (confirmCheck && confirmCheck.checked) {
        const summary = buildBackendExportParamSummary(f, ocrMethod);
        const ok = await showBackendExportParamPreview(summary);
        if (!ok) return;
    }
    if (ocrMethod === 'none') {
        const anchorRes = await findCalibrationStartPoint({ files: [f] }, { suppressTabSwitch: true });
        if (!anchorRes || !anchorRes.success) return;
    }
    const exportRes = await uploadCalibrationScreenshot(
        { files: [f] },
        { suppressTabSwitch: true, fillBackendJson: true, promptApply: true, useBackendCharSet: true, useStartpointPipeline: true }
    );
    if (exportRes && exportRes.success) {
        currentTestImage = null;
        pastedOcrTestImage = null;
        resetBackendUploadUi();
    }
}
async function runBackendFullTest() {
    await runBackendExportCalibrationJson();
}
function fillBackendWidthCharsFromUsedCodes(runAnalysis) {
    const usedEl = document.getElementById('backendStage3UsedCalibrationCodes');
    const inputEl = document.getElementById('backendWidthTestChars');
    if (!usedEl || !inputEl) return;
    const text = String(usedEl.value || '').trim();
    if (!text) {
        alert('目前沒有可貼用的已使用校準字碼，請先按「顯示校準文字」。');
        return;
    }
    inputEl.value = text;
    saveBackendCalControls();
    saveSettingsToCookie();
    if (runAnalysis) runBackendExportCalibrationJson();
}
async function uploadOcrTestPastedImage() {
    if (!pastedOcrTestImage) { alert('請先 Ctrl+V 貼上截圖'); return; }
    const file = pastedOcrTestImage instanceof File ? pastedOcrTestImage : new File([pastedOcrTestImage], 'pasted.png', { type: pastedOcrTestImage.type || 'image/png' });
    const fakeInput = { files: [file] };
    await uploadOcrTestScreenshot(fakeInput);
    pastedOcrTestImage = null;
    const img = document.getElementById('ocrTestPastePreview');
    const hint = document.getElementById('ocrTestPasteHint');
    const btn = document.getElementById('ocrTestPasteUploadBtn');
    if (img) { if (img.src) URL.revokeObjectURL(img.src); img.src = ''; img.style.display = 'none'; }
    if (hint) hint.textContent = 'Ctrl+V 貼上截圖';
    if (btn) btn.classList.add('hidden');
}

// 統一的圖片處理函式
let currentTestImage = null;

function handleImageUpload(input) {
    if (!input?.files?.length) return;
    const file = input.files[0];
    currentTestImage = file;
    // 顯示預覽
    const img = document.getElementById('ocrTestPastePreview');
    const imgWrap = document.getElementById('ocrTestPasteImgWrap');
    const hint = document.getElementById('ocrTestPasteHint');
    if (img) img.src = URL.createObjectURL(file);
    if (imgWrap) imgWrap.style.display = '';
    if (hint) hint.textContent = '已上傳，點測試按鈕';
}

// 定位分析測試
async function runPositioningTest() {
    const file = currentTestImage || pastedOcrTestImage;
    if (!file) { alert('請先上傳或貼上截圖'); return; }
    const f = file instanceof File ? file : new File([file], 'test.png', { type: file.type || 'image/png' });
    const ocrMethod = document.getElementById('ocrTestMethod')?.value || 'none';
    
    // 如果選擇「無（Pixel 定位）」，使用 calibrate_upload.php 來顯示 pixel 偵錯日誌
    if (ocrMethod === 'none') {
        await uploadCalibrationScreenshot({ files: [f] });
    } else {
        await uploadOcrTestScreenshot({ files: [f] });
    }
    
    // 清除圖片
    currentTestImage = null;
    pastedOcrTestImage = null;
    const img = document.getElementById('ocrTestPastePreview');
    const imgWrap = document.getElementById('ocrTestPasteImgWrap');
    const hint = document.getElementById('ocrTestPasteHint');
    if (img) { if (img.src) URL.revokeObjectURL(img.src); img.src = ''; }
    if (imgWrap) imgWrap.style.display = 'none';
    if (hint) hint.textContent = 'Ctrl+V 貼上截圖';
    resetBackendUploadUi();
}

// 字元寬度分析 - 先找起點再分析寬度
async function runWidthTest() {
    const file = currentTestImage || pastedOcrTestImage;
    if (!file) { alert('請先上傳或貼上截圖'); return; }
    const f = file instanceof File ? file : new File([file], 'test.png', { type: file.type || 'image/png' });

    // 先找校準起點
    await findCalibrationStartPoint({ files: [f] });
}

function buildAnchorCandidatesDebugText(sp) {
    if (!sp || typeof sp !== 'object') return '';
    const startCandidates = Array.isArray(sp.start_candidates) ? sp.start_candidates : [];
    const endCandidates = Array.isArray(sp.end_candidates) ? sp.end_candidates : [];
    if (startCandidates.length === 0 && endCandidates.length === 0) return '';

    function fmtArr(v) {
        return Array.isArray(v) ? `[${v.join(', ')}]` : '[]';
    }
    function keyOf(c, includeXDiff) {
        const base = [
            c.x, c.y, c.top, c.bottom,
            c.start_idx, c.end_idx,
            c.unit_width,
            JSON.stringify(c.actual_widths || []),
            JSON.stringify(c.ratio_seq || [])
        ];
        if (includeXDiff) base.push(c.x_diff);
        return base.join('|');
    }
    function dedupeCandidates(list, includeXDiff) {
        const map = new Map();
        list.forEach(c => {
            const key = keyOf(c, includeXDiff);
            if (!map.has(key)) {
                map.set(key, {
                    sample: c,
                    count: 1,
                    rowMin: c.row,
                    rowMax: c.row
                });
                return;
            }
            const item = map.get(key);
            item.count += 1;
            item.rowMin = Math.min(item.rowMin, c.row);
            item.rowMax = Math.max(item.rowMax, c.row);
        });
        return Array.from(map.values()).sort((a, b) => a.rowMin - b.rowMin);
    }

    const startGroups = dedupeCandidates(startCandidates, false);
    const endGroups = dedupeCandidates(endCandidates, true);
    const lines = [];
    lines.push('─────── 錨點候選清單（完整版）───────');
    lines.push(`start 候選數: ${startCandidates.length}（去重後: ${startGroups.length}）`);
    startGroups.forEach((g, idx) => {
        const c = g.sample;
        lines.push(
            `S${idx + 1}. rows=${g.rowMin}${g.rowMax !== g.rowMin ? ('..' + g.rowMax) : ''}, count=${g.count}, ` +
            `x=${c.x}, y=${c.y}, top=${c.top}, bottom=${c.bottom}, idx=${c.start_idx}-${c.end_idx}, ` +
            `unit=${c.unit_width}, actual=${fmtArr(c.actual_widths)}, ratio=${fmtArr(c.ratio_seq)}`
        );
    });
    lines.push(`end 候選數: ${endCandidates.length}（去重後: ${endGroups.length}）`);
    endGroups.forEach((g, idx) => {
        const c = g.sample;
        lines.push(
            `E${idx + 1}. rows=${g.rowMin}${g.rowMax !== g.rowMin ? ('..' + g.rowMax) : ''}, count=${g.count}, ` +
            `x=${c.x}, y=${c.y}, top=${c.top}, bottom=${c.bottom}, x_diff=${c.x_diff}, idx=${c.start_idx}-${c.end_idx}, ` +
            `unit=${c.unit_width}, actual=${fmtArr(c.actual_widths)}, ratio=${fmtArr(c.ratio_seq)}`
        );
    });
    return lines.join('\n');
}

// 找校準起點
async function findCalibrationStartPoint(input, options = {}) {
    if (!input?.files?.length) return { success: false, error: '未提供圖片' };
    const suppressTabSwitch = !!options.suppressTabSwitch;
    const file = input.files[0];
    const ocrMethod = document.getElementById('ocrTestMethod')?.value || 'none';

    if (ocrMethod !== 'none') {
        // 顯示提示在頁面中
        if (!suppressTabSwitch) {
            setPreviewTab('calibration-result');
            const emptyEl = document.getElementById('calResultEmpty');
            const contentEl = document.getElementById('calResultContent');
            if (emptyEl) emptyEl.classList.add('hidden');
            if (contentEl) {
                contentEl.classList.remove('hidden');
                contentEl.innerHTML = `
                    <div style="padding:20px; background:#fff3cd; color:#856404; border-radius:8px; border:1px solid #ffeeba;">
                        <strong>⚠️ 提示：</strong>定位分析僅支援 Pixel 模式（無 OCR）。<br><br>
                        請先在「OCR 辨識引擎」選擇「無（Pixel 定位）」，再重新上傳截圖。
                    </div>
                `;
            }
        } else {
            alert('定位錨點檢測僅支援 Pixel 模式（OCR 引擎請選「無」）。');
        }
        return { success: false, error: '定位分析僅支援 Pixel 模式' };
    }

    const { startRaw: pixelPattern, endRaw: pixelEndPattern } = getEffectivePixelPatterns();
    
    // 取得測試字符與每行字數（優先序：Backend 專用字元集 -> 自訂校準字元 -> 已使用校準字碼）
    const ctx = getBackendExportCharContext();
    const perLineInput = document.getElementById('backendCalCharsPerLine');
    const calTableCharsPerLineInput = document.getElementById('calTableCharsPerLine');
    const mergedChars = ctx.mergedChars;
    // 與 getCalibrationBlockText 一致：以 Unicode code point 送出（flag pair 會以兩碼組成單一字元）
    const testChars = mergedChars.join('');
    const testCharGroups = ctx.testCharGroups;
    const charsPerLine = (perLineInput && perLineInput.value)
        ? String(Math.max(1, Math.min(10, parseInt(perLineInput.value) || 6)))
        : (calTableCharsPerLineInput ? (calTableCharsPerLineInput.value || '2') : '2');
    const repeatInput = document.getElementById('backendCalCharRepeat');
    const repeatCount = String(Math.max(1, Math.min(20, parseInt(repeatInput?.value, 10) || 5)));

    const formData = new FormData();
    formData.append('image', file);
    formData.append('ocr', 'none');
    formData.append('pixel_pattern', pixelPattern);
    formData.append('pixel_end_pattern', pixelEndPattern);
    formData.append('find_start_point', '1');
    formData.append('test_chars', testChars);
    formData.append('test_char_groups', testCharGroups);
    formData.append('test_chars_count', String(mergedChars.length));
    formData.append('chars_per_line', charsPerLine);
    formData.append('repeat_count', repeatCount);

    // Debug: 記錄發送的參數（總字數與每行字數用於後端預期色塊：content_lines = 1 + ceil(總字數/每行)，expected_blocks = content_lines*2+1）
    console.log('[DEBUG] findCalibrationStartPoint 發送參數:');
    console.log('  test_chars 字元數:', mergedChars.length, '(預期色塊:', (1 + Math.ceil(mergedChars.length / parseInt(charsPerLine, 10))) * 2 + 1 + ')');
    console.log('  test_chars:', testChars);
    console.log('  chars_per_line:', charsPerLine);
    console.log('  repeat_count:', repeatCount);
    console.log('  pixel_pattern:', pixelPattern);
    console.log('  pixel_end_pattern:', pixelEndPattern);

    const btn = document.getElementById('calUploadBtn');
    if (btn) { btn.disabled = true; btn.textContent = '分析中…'; }

    try {
        const fetchRes = await fetch('calibrate_upload.php', { method: 'POST', body: formData });
        const textRes = await fetchRes.text();
        console.log('[DEBUG] findCalibrationStartPoint 原始回應:', textRes.substring(0, 1000));

        if (!textRes || !textRes.trim()) {
            alert('伺服器回應為空，請檢查 PHP 錯誤日誌');
            if (btn) { btn.disabled = false; btn.textContent = '上傳並分析'; }
            return { success: false, error: '伺服器回應為空' };
        }

        const res = JSON.parse(textRes);

        // Debug: 記錄收到的回應
        console.log('[DEBUG] findCalibrationStartPoint 收到回應:', JSON.stringify(res).substring(0, 500));

        if (btn) { btn.disabled = false; btn.textContent = '上傳並分析'; }

        const sp = (res && res.start_point) ? res.start_point : res;
        const hasStartPointData = !!(sp && sp.start_x !== undefined && sp.start_y !== undefined);

        if (!res.success || !hasStartPointData) {
            // 顯示失敗在頁面中
            if (!suppressTabSwitch) {
                setPreviewTab('calibration-result');
                const emptyEl = document.getElementById('calResultEmpty');
                const contentEl = document.getElementById('calResultContent');
                const startWrap = document.getElementById('calResultStartPointWrap');
                const startText = document.getElementById('calResultStartPointText');
                const startLogs = document.getElementById('calResultStartPointLogs');
                if (emptyEl) emptyEl.classList.add('hidden');
                if (contentEl) {
                    contentEl.classList.remove('hidden');
                }
                if (startWrap && startText) {
                    startWrap.classList.remove('hidden');
                    startWrap.style.background = '#f8d7da';
                    startWrap.style.color = '#721c24';
                    startWrap.style.borderColor = '#f5c6cb';
                    const candidateText = buildAnchorCandidatesDebugText(sp);
                    startText.textContent = `❌ 找起點失敗\n\n${candidateText ? (candidateText + '\n\n') : ''}${res.debug_output || JSON.stringify(res).substring(0, 500)}`;
                }
                if (startLogs) {
                    startLogs.classList.add('hidden');
                    startLogs.textContent = '';
                }
            } else {
                alert(`定位錨點檢測失敗：${res.error || '未知錯誤'}\n\n${res.debug_output || ''}`);
            }
            return { success: false, res, sp };
        }

        // 切換到校準結果頁面
        if (!suppressTabSwitch) setPreviewTab('calibration-result');

        // 顯示在頁面中
        const emptyEl = document.getElementById('calResultEmpty');
        const contentEl = document.getElementById('calResultContent');
        const startWrap = document.getElementById('calResultStartPointWrap');
        const startText = document.getElementById('calResultStartPointText');
        const startLogs = document.getElementById('calResultStartPointLogs');

        if (emptyEl) emptyEl.classList.add('hidden');
        if (contentEl) {
            contentEl.classList.remove('hidden');
        }
        if (startWrap && startText) {
            startWrap.classList.remove('hidden');
            startWrap.style.background = '#d4edda';
            startWrap.style.color = '#155724';
            startWrap.style.borderColor = '#c3e6cb';
            
            let displayText = '';
            const candidateText = buildAnchorCandidatesDebugText(sp);
            if (candidateText) {
                displayText += `${candidateText}\n\n`;
            }
            
            if (sp.start_anchor_bottom_left && sp.start_anchor_bottom_left.length >= 2) {
                displayText += `開始錨點左下: (${sp.start_anchor_bottom_left[0]}, ${sp.start_anchor_bottom_left[1]})\n`;
            }
            if (sp.end_anchor_top_left && sp.end_anchor_top_left.length >= 2) {
                displayText += `結束錨點左上: (${sp.end_anchor_top_left[0]}, ${sp.end_anchor_top_left[1]})\n`;
            }
            if (sp.start_x !== undefined && sp.start_y !== undefined) {
                displayText += `校準起點: (${sp.start_x}, ${sp.start_y})`;
            }
            
            // 顯示垂直色塊分析結果
            if (sp.vertical_analysis) {
                const va = sp.vertical_analysis;
                displayText += `\n\n─────── 垂直色塊分析 ───────\n`;
                displayText += `背景顏色: RGB${JSON.stringify(va.bg_color)} (第1個色塊)\n`;
                displayText += `文字顏色: RGB${JSON.stringify(va.text_color)} (第2個色塊)\n`;
                displayText += `文字高度: ${va.text_height || 0}px (第2個色塊)\n`;
                displayText += `行間距: ${va.line_spacing || 0}px (第3個色塊)\n`;
                displayText += `色塊數量: ${va.vertical_blocks.length} (預期: ${va.expected_blocks})\n`;
                displayText += `驗證結果: ${va.is_valid ? '✅ 通過' : '❌ 不符'}\n`;
                displayText += `內容行數: ${va.content_lines}\n`;
                displayText += `色塊高度陣列: [${va.vertical_blocks.join(', ')}]\n`;
                
            }

            // 顯示第一文字行的水平連續色塊分析（與 debug log 對齊）
            if (sp.first_row_horizontal) {
                const hr = sp.first_row_horizontal;
                displayText += `\n─────── 第一文字行水平色塊分析 ───────\n`;
                if (hr.horizontal_blocks && hr.horizontal_blocks.length > 0) {
                    displayText += `[HORIZONTAL] 第一文字行連續色塊記錄陣列: [${hr.horizontal_blocks.join(', ')}]\n`;
                }
                if (hr.row_width !== undefined && hr.row_right_x !== undefined) {
                    displayText += `[HORIZONTAL] 行總寬度: ${hr.row_width}, 右邊界 x: ${hr.row_right_x}\n`;
                }
                if (hr.bg_color) {
                    displayText += `[HORIZONTAL] 背景色(最多): RGB${JSON.stringify(hr.bg_color)}\n`;
                }
                if (hr.fg_color) {
                    displayText += `[HORIZONTAL] 前景色(第二多): RGB${JSON.stringify(hr.fg_color)}\n`;
                }
                if (hr.color_stats && Object.keys(hr.color_stats).length > 0) {
                    displayText += `[HORIZONTAL] 顏色統計:\n`;
                    Object.entries(hr.color_stats).forEach(([color, count]) => {
                        displayText += `  ${color}: ${count} px\n`;
                    });
                }
                if (hr.major_blocks_gt3 && hr.major_blocks_gt3.length > 0) {
                    displayText += `[HORIZONTAL] >3px 主要色塊(前7): [${hr.major_blocks_gt3.join(', ')}]\n`;
                }
                if (hr.block_widths_1_3_5_7 && hr.block_widths_1_3_5_7.length > 0) {
                    displayText += `[HORIZONTAL] 第1/3/5/7塊(視為█): [${hr.block_widths_1_3_5_7.join(', ')}]\n`;
                }
                if (hr.estimated_block_width !== undefined) {
                    displayText += `[HORIZONTAL] 推算單一█寬度: ${hr.estimated_block_width}px\n`;
                }
            }

            // 顯示每行第一個 █ 的寬度（放在第一文字行水平分析之後）
            if (sp.vertical_analysis && sp.vertical_analysis.row_block_widths && sp.vertical_analysis.row_block_widths.length > 0) {
                const widths = sp.vertical_analysis.row_block_widths;
                displayText += `\n─────── 各行第一個 █ 寬度 ───────\n`;
                widths.forEach((width, idx) => {
                    displayText += `第 ${idx + 1} 行: ${width}px\n`;
                });
            }
            
            // 顯示所有找到的色塊
            if (sp.all_blocks && sp.all_blocks.length > 0) {
                displayText += `\n─────── 所有符合的色塊 ───────\n`;
                displayText += `總共找到: ${sp.all_blocks.length} 個\n\n`;
                
                // 按行分組顯示
                const blocksByRow = {};
                sp.all_blocks.forEach(block => {
                    if (!blocksByRow[block.row]) {
                        blocksByRow[block.row] = [];
                    }
                    blocksByRow[block.row].push(block);
                });
                
                Object.keys(blocksByRow).sort((a, b) => parseInt(a) - parseInt(b)).forEach(rowNum => {
                    const blocks = blocksByRow[rowNum];
                    displayText += `第 ${rowNum} 行 (${blocks.length} 個):\n`;
                    blocks.forEach((block, idx) => {
                        const leftX = block.x;
                        const rightX = block.x + block.width - 1;
                        displayText += `  ${idx + 1}. x: ${leftX} ~ ${rightX} (寬度 ${block.width}px)\n`;
                    });
                });
            }
            
            // 顯示空隙寬度計算結果
            if (sp.gap_errors && sp.gap_errors.length > 0) {
                displayText += `\n─────── 空隙寬度計算錯誤 ───────\n`;
                sp.gap_errors.forEach(err => {
                    displayText += `❌ ${err.message}\n`;
                });
            }
            
            if (sp.gap_widths && sp.gap_widths.length > 0) {
                displayText += `\n─────── 空隙寬度 ───────\n`;
                
                // 收集所有空隙寬度值
                const allGapValues = [];
                
                sp.gap_widths.forEach(rowData => {
                    displayText += `第 ${rowData.row} 行:\n`;
                    rowData.gaps.forEach(gap => {
                        displayText += `  配對 ${gap.pair}: ${gap.block2_left} - ${gap.block1_right} - 1 = ${gap.gap_width}px\n`;
                        allGapValues.push(gap.gap_width);
                    });
                });
                
                displayText += `\n所有空隙寬度值: [${allGapValues.join(', ')}]`;
                
                // 計算字元寬度
                if (allGapValues.length >= 2 && sp.test_chars) {
                    const repeatCount = Math.max(1, Math.min(20, parseInt(sp.repeat_count, 10) || parseInt(document.getElementById('backendCalCharRepeat')?.value, 10) || 5));
                    displayText += `\n\n─────── 字元寬度計算 ───────\n`;
                    displayText += `每字重複次數: ${repeatCount}\n`;
                    
                    // 第一個間隙：半形空白
                    const halfSpaceWidth = allGapValues[0] / repeatCount;
                    displayText += `半形空白: ${allGapValues[0]} ÷ ${repeatCount} = ${halfSpaceWidth.toFixed(2)}px\n`;
                    
                    // 第二個間隙：全形空白
                    const fullSpaceWidth = allGapValues[1] / repeatCount;
                    displayText += `全形空白: ${allGapValues[1]} ÷ ${repeatCount} = ${fullSpaceWidth.toFixed(2)}px\n`;
                    
                    // 測試字元
                    if (allGapValues.length > 2) {
                        displayText += `\n測試字元寬度:\n`;
                        const testChars = sp.test_chars;
                        for (let i = 2; i < allGapValues.length; i++) {
                            const charIndex = i - 2;
                            if (charIndex < testChars.length) {
                                const char = testChars[charIndex];
                                const gap = allGapValues[i];
                                const charWidth = (gap - halfSpaceWidth * 2) / repeatCount;
                                displayText += `  ${char}: (${gap} - ${halfSpaceWidth.toFixed(2)} × 2) ÷ ${repeatCount} = ${charWidth.toFixed(2)}px\n`;
                            }
                        }
                    }
                }
            }
            
            // 顯示標準 calibration JSON
            if (sp.calibration && sp.pixel_per_unit) {
                displayText += `\n\n─────── 標準 Calibration JSON ───────\n`;
                displayText += `基準值 (pixel_per_unit): ${sp.pixel_per_unit}\n\n`;
                displayText += `Calibration:\n`;
                displayText += JSON.stringify(sp.calibration, null, 2);
                fillCalibrationJsonOutput(sp.calibration);
            } else if (sp.calibration) {
                fillCalibrationJsonOutput(sp.calibration);
            } else {
                fillCalibrationJsonOutput(null);
            }
            
            startText.textContent = displayText;
        }
        if (startLogs) {
            if (sp.debug_logs && sp.debug_logs.length > 0) {
                startLogs.classList.remove('hidden');
                startLogs.textContent = sp.debug_logs.join('\n');
            } else {
                startLogs.classList.add('hidden');
                startLogs.textContent = '';
            }
        }
        return { success: true, res, sp };

    } catch (e) {
        if (btn) { btn.disabled = false; btn.textContent = '上傳並分析'; }
        alert('錯誤: ' + e.message);
        return { success: false, error: e.message };
    }
}

// 完整測試
async function runFullTest() {
    const file = currentTestImage || pastedOcrTestImage;
    if (!file) { alert('請先上傳或貼上截圖'); return; }
    const f = file instanceof File ? file : new File([file], 'test.png', { type: file.type || 'image/png' });
    // 先執行定位分析
    await uploadOcrTestScreenshot({ files: [f] });
    // 再執行寬度分析
    await uploadCalibrationScreenshot({ files: [f] });
    // 清除圖片
    currentTestImage = null;
    pastedOcrTestImage = null;
    const img = document.getElementById('ocrTestPastePreview');
    const imgWrap = document.getElementById('ocrTestPasteImgWrap');
    const hint = document.getElementById('ocrTestPasteHint');
    if (img) { if (img.src) URL.revokeObjectURL(img.src); img.src = ''; }
    if (imgWrap) imgWrap.style.display = 'none';
    if (hint) hint.textContent = 'Ctrl+V 貼上截圖';
    resetBackendUploadUi();
}

async function uploadOcrTestScreenshot(input) {
    if (!input?.files?.length) return;
    const file = input.files[0];
    const formData = new FormData();
    formData.append('image', file);
    const anchor = (document.getElementById('ocrTestAnchor')?.value || '').trim();
    if (anchor) formData.append('anchor', anchor);
    const ocrMethod = (document.getElementById('ocrTestMethod')?.value || 'none').trim();
    formData.append('ocr', ocrMethod);
    const wrap = document.getElementById('ocrTestScoreWrap');
    wrap.classList.remove('hidden');
    document.getElementById('ocrTestFound').textContent = '…';
    document.getElementById('ocrTestDetail').textContent = '分析中…';
    const imgWrap = document.getElementById('ocrTestImageWrap');
    const previewImg = document.getElementById('ocrTestPreviewImg');
    const overlaysEl = document.getElementById('ocrTestBboxOverlays');
    const refinedWrap = document.getElementById('ocrTestRefinedWrap');
    const refinedImg = document.getElementById('ocrTestRefinedImg');
    const refinedOverlay = document.getElementById('ocrTestRefinedBboxOverlay');
    imgWrap.style.display = 'none';
    overlaysEl.innerHTML = '';
    refinedWrap.classList.add('hidden');
    refinedOverlay.innerHTML = '';
    const annoWrap = document.getElementById('ocrTestAnnotatedWrap');
    if (annoWrap) { annoWrap.classList.add('hidden'); annoWrap.style.display = 'none'; }
    try {
        const res = await fetch('ocr_test_upload.php', { method: 'POST', body: formData }).then(r => r.json());
        document.getElementById('ocrTestFound').textContent = res.found ? '✅ 已找到' : '❌ 未找到';
        let detail = '';
        const imgW = res.img_size?.width || 1;
        const imgH = res.img_size?.height || 1;
        const elapsed = res.elapsed_ms;
        if (res.img_size || elapsed != null) {
            const w = res.img_size?.width, h = res.img_size?.height;
            detail += `截圖: ${w ?? '-'}×${h ?? '-'} px`;
            if (elapsed != null) detail += ` | 計算: ${elapsed} ms`;
            if (res._debug_ocr_param) detail += ` | [DEBUG OCR: ${res._debug_ocr_param}]`;
            detail += '\n\n';
        }
        if (res.ocr_text != null) {
            const preview = (res.ocr_text || '').slice(0, 120);
            detail += `辨識到的文字 (前120字): ${preview ? JSON.stringify(preview) : '(空)'}\n\n`;
        }
        if (res.strategy_ocr_results && res.strategy_ocr_results.length > 0) {
            detail += `各策略辨識結果:\n`;
            res.strategy_ocr_results.forEach(s => {
                if (s.found && s.bbox) {
                    const b = s.bbox;
                    detail += `  ${s.strategy}: ✅ 找到 | 座標 left=${b.left} top=${b.top} right=${b.right} bottom=${b.bottom} (${b.width}×${b.height}) | 得分 ${s.score ?? '-'} | 平均 ${s.avg ?? '-'}% | 辨識片段 "${s.ocr_snippet || ''}"\n`;
                } else {
                    const t = (s.text || '').slice(0, 120);
                    detail += `  ${s.strategy}: ❌ 未找到 | 辨識到的文字(前120字): ${t ? JSON.stringify(t) : '(空)'}\n`;
                }
            });
            detail += '\n';
        }
        if (res.match_stages) {
            const s = res.match_stages;
            detail += `字數存量比對:\n`;
            detail += `  全文: ${s.full}% | 前半: ${s.half1}% | 後半: ${s.half2}%\n`;
            detail += `  平均: ${s.avg}% (門檻 ${s.threshold}%)${!res.found ? ' 未達門檻' : ''}\n`;
            detail += `  錨點: ${s.anchor || res.target}\n`;
            detail += `  最佳: ${s.ocr_snippet || '-'}\n`;
        }
        if (file && res.img_size) {
            const url = URL.createObjectURL(file);
            previewImg.src = url;
            previewImg.onload = function() {
                URL.revokeObjectURL(url);
                imgWrap.style.display = 'inline-block';
                if (res.candidates && res.candidates.length > 0 && imgW > 0 && imgH > 0) {
                    overlaysEl.innerHTML = '';
                    const colors = ['#e94560','#22c55e','#3b82f6','#f59e0b','#8b5cf6'];
                    res.candidates.forEach((c, i) => {
                        if (c.bbox) {
                            const b = c.bbox;
                            const col = colors[i % colors.length];
                            const box = document.createElement('div');
                            box.style.cssText = `position:absolute; left:${100*b.left/imgW}%; top:${100*b.top/imgH}%; width:${100*b.width/imgW}%; height:${100*b.height/imgH}%; border:2px solid ${col}; box-sizing:border-box; pointer-events:none;`;
                            box.title = `候選 ${i+1}: left=${b.left} top=${b.top} right=${b.right} bottom=${b.bottom}`;
                            const tl = document.createElement('span');
                            tl.style.cssText = `position:absolute; left:0; top:0; transform:translate(-100%, -50%); margin-left:-6px; font-size:12px; font-weight:700; color:${col}; text-shadow:0 0 2px #fff, 0 0 4px #fff; white-space:nowrap;`;
                            tl.textContent = i + 1;
                            const br = document.createElement('span');
                            br.style.cssText = `position:absolute; left:100%; top:100%; transform:translate(0, -50%); margin-left:6px; font-size:12px; font-weight:700; color:${col}; text-shadow:0 0 2px #fff, 0 0 4px #fff; white-space:nowrap;`;
                            br.textContent = i + 1;
                            box.appendChild(tl);
                            box.appendChild(br);
                            overlaysEl.appendChild(box);
                        }
                    });
                } else if (res.found && res.bbox && imgW > 0 && imgH > 0) {
                    imgWrap.style.display = 'inline-block';
                    const b = res.bbox;
                    overlaysEl.innerHTML = '<div style="position:absolute; left:' + (100*b.left/imgW) + '%; top:' + (100*b.top/imgH) + '%; width:' + (100*b.width/imgW) + '%; height:' + (100*b.height/imgH) + '%; border:2px solid #e94560; box-sizing:border-box;"></div>';
                }
            };
        }
        if (res.candidates && res.candidates.length > 0) {
            detail += `\n候選 (${res.candidates.length}):\n`;
            res.candidates.slice(0, 15).forEach((c, i) => {
                const scoreStr = c.score != null ? ` 得分 ${c.score.toFixed(4)}` : '';
                detail += `  ${i + 1}. "${c.ocr_snippet}" 平均 ${c.avg}%${scoreStr}\n`;
                if (c.bbox) {
                    const b = c.bbox;
                    detail += `     座標: left=${b.left} top=${b.top} right=${b.right} bottom=${b.bottom} (${b.width}×${b.height})\n`;
                }
            });
            if (res.candidates.length > 15) detail += `  ... 共 ${res.candidates.length} 個\n`;
        }
        if (res.found && res.bbox) {
            const b = res.bbox;
            detail += `\n📍 最佳座標: left=${b.left} top=${b.top} right=${b.right} bottom=${b.bottom}\n`;
            detail += `   寬×高: ${b.width}×${b.height}`;
        }
        if (res.refined_run) {
            const r = res.refined_run;
            detail += `\n\n🔄 裁切重辨 (5%迭代四方向):`;
            if (r.strategy) detail += `\n   固定策略: ${r.strategy}`;
            detail += `\n   原第一名得分: ${r.original_score ?? '-'}`;
            detail += `\n   裁切後得分: ${r.score ?? '-'}`;
            if (r.original_bbox) {
                const ob = r.original_bbox;
                detail += `\n   原圖座標: left=${ob.left} top=${ob.top} right=${ob.right} bottom=${ob.bottom}`;
            }
            detail += `\n   裁切範圍: (${r.crop_bounds?.left},${r.crop_bounds?.top})-(${r.crop_bounds?.right},${r.crop_bounds?.bottom})`;
            detail += `\n   ${r.better ? '✅ 裁切後較佳' : '原結果較佳或相當'}`;
            if (r.ocr_snippet) detail += `\n   裁切OCR: "${r.ocr_snippet}"`;
            if (r.annotated_image_base64) {
                const annoImg = document.getElementById('ocrTestAnnotatedImg');
                const annoWrap = document.getElementById('ocrTestAnnotatedWrap');
                if (annoImg && annoWrap) {
                    annoImg.src = 'data:image/png;base64,' + r.annotated_image_base64;
                    annoWrap.classList.remove('hidden');
                    annoWrap.style.display = '';
                }
            }
            if (r.crop_image_base64 && r.refined_bbox && r.crop_size) {
                refinedWrap.classList.remove('hidden');
                refinedImg.src = 'data:image/png;base64,' + r.crop_image_base64;
                const cw = r.crop_size.width || 1;
                const ch = r.crop_size.height || 1;
                const b = r.refined_bbox;
                function drawRefinedOverlay() {
                    refinedOverlay.innerHTML = '<div style="position:absolute; left:' + (100*b.left/cw) + '%; top:' + (100*b.top/ch) + '%; width:' + (100*b.width/cw) + '%; height:' + (100*b.height/ch) + '%; border:2px solid #22c55e; box-sizing:border-box; box-shadow:0 0 4px rgba(34,197,94,0.8);"></div>';
                }
                refinedImg.onload = drawRefinedOverlay;
                if (refinedImg.complete) drawRefinedOverlay();
            }
        }
        if (!res.found && res.ocr_text && !res.match_stages?.ocr_snippet) {
            detail += (detail ? '\n' : '') + 'OCR 辨識: ' + (res.ocr_text || '').substring(0, 80) + (res.ocr_text?.length > 80 ? '…' : '');
        }
        document.getElementById('ocrTestDetail').textContent = detail || '-';
    } catch (e) {
        document.getElementById('ocrTestFound').textContent = '錯誤';
        document.getElementById('ocrTestDetail').textContent = '上傳失敗: ' + (e.message || e);
    }
    if (input && 'value' in input) input.value = '';
}
let lastCalibrationResult = null;
let pastedCalibrationImage = null;
(function initCalPasteZone() {
    const zone = document.getElementById('calPasteZone');
    if (!zone) return;
    zone.addEventListener('click', () => zone.focus());
    zone.addEventListener('paste', (e) => {
        const item = e.clipboardData?.items && Array.from(e.clipboardData.items).find(x => x.type.startsWith('image/'));
        if (!item) return;
        e.preventDefault();
        const blob = item.getAsFile();
        if (!blob) return;
        pastedCalibrationImage = blob;
        const img = document.getElementById('calPastePreview');
        const hint = document.getElementById('calPasteHint');
        const btn = document.getElementById('calPasteUploadBtn');
        if (img) { img.src = URL.createObjectURL(blob); img.style.display = ''; }
        if (hint) hint.textContent = '已貼上，點「上傳此圖」';
        if (btn) btn.classList.remove('hidden');
    });
    zone.addEventListener('keydown', (e) => { if (e.key === ' ' || e.key === 'Enter') e.preventDefault(); });
})();
async function uploadCalibrationPastedImage() {
    if (!pastedCalibrationImage) { alert('請先 Ctrl+V 貼上截圖'); return; }
    const file = pastedCalibrationImage instanceof File ? pastedCalibrationImage : new File([pastedCalibrationImage], 'pasted.png', { type: pastedCalibrationImage.type || 'image/png' });
    const fakeInput = { files: [file] };
    await uploadCalibrationScreenshot(fakeInput);
    pastedCalibrationImage = null;
    const img = document.getElementById('calPastePreview');
    const hint = document.getElementById('calPasteHint');
    const btn = document.getElementById('calPasteUploadBtn');
    if (img) { if (img.src) URL.revokeObjectURL(img.src); img.src = ''; img.style.display = 'none'; }
    if (hint) hint.textContent = 'Ctrl+V 貼上截圖';
    if (btn) btn.classList.add('hidden');
}
async function uploadCalibrationScreenshot(input, options = {}) {
    if (!input?.files?.length) return { success: false, error: '未提供圖片' };
    const suppressTabSwitch = !!options.suppressTabSwitch;
    const fillBackendJson = !!options.fillBackendJson;
    const promptApply = !!options.promptApply;
    const useBackendCharSet = !!options.useBackendCharSet;
    const useStartpointPipeline = !!options.useStartpointPipeline;
    const file = input.files[0];
    let customChars = '';
    if (useBackendCharSet) {
        customChars = getBackendExportCharContext().customChars;
    } else {
        const customCharsInput = document.getElementById('calTableCustomChars')?.value?.trim() || '';
        const parsedCustomChars = parseCalTableCharsInput(customCharsInput);
        customChars = parsedCustomChars.join('');
    }
    const ocrMethod = document.getElementById('ocrTestMethod')?.value || 'none';
    const { startRaw: pixelPattern, endRaw: pixelEndPattern } = getEffectivePixelPatterns();

    const formData = new FormData();
    formData.append('image', file);
    formData.append('custom_chars', customChars);
    if (ocrMethod && ['tesseract', 'rapidocr', 'none'].includes(ocrMethod)) {
        formData.append('ocr', ocrMethod);
    }
    if (ocrMethod === 'none' && pixelPattern) {
        formData.append('pixel_pattern', pixelPattern);
        formData.append('pixel_end_pattern', pixelEndPattern);
    }
    if (useStartpointPipeline && ocrMethod === 'none') {
        const perLineInput = document.getElementById('backendCalCharsPerLine');
        const calTableCharsPerLineInput = document.getElementById('calTableCharsPerLine');
        const repeatInput = document.getElementById('backendCalCharRepeat');
        const charsPerLine = (perLineInput && perLineInput.value)
            ? String(Math.max(1, Math.min(10, parseInt(perLineInput.value, 10) || 6)))
            : (calTableCharsPerLineInput ? (calTableCharsPerLineInput.value || '2') : '2');
        const repeatCount = String(Math.max(1, Math.min(20, parseInt(repeatInput?.value, 10) || 5)));
        const ctx = getBackendExportCharContext();
        formData.append('use_startpoint_pipeline', '1');
        formData.append('test_chars', ctx.customChars);
        formData.append('test_char_groups', ctx.testCharGroups);
        formData.append('test_chars_count', String(ctx.mergedChars.length));
        formData.append('chars_per_line', charsPerLine);
        formData.append('repeat_count', repeatCount);
    }
    const btn = document.getElementById('calUploadBtn');
    if (btn) { btn.disabled = true; btn.textContent = '上傳中…'; }
    try {
        const res = await fetch('calibrate_upload.php', { method: 'POST', body: formData }).then(r => r.json());
        
        if (!res.success || !res.calibration) {
            if (res.calibration_steps_summary) {
                setPreviewTab('calibration-result');
                const emptyEl = document.getElementById('calResultEmpty');
                const contentEl = document.getElementById('calResultContent');
                if (contentEl) {
                    emptyEl.classList.add('hidden');
                    contentEl.classList.remove('hidden');
                    const stepsSummaryWrap = document.getElementById('calResultStepsSummaryWrap');
                    const stepsSummaryEl = document.getElementById('calResultStepsSummary');
                    if (stepsSummaryEl) {
                        stepsSummaryWrap.classList.remove('hidden');
                        stepsSummaryEl.textContent = res.calibration_steps_summary;
                    }
                    if (res.debug_output) {
                        const debugEl = document.getElementById('calResultDebugOutput');
                        if (debugEl) { debugEl.textContent = res.error + '\n\n' + res.debug_output; debugEl.classList.remove('hidden'); }
                    }
                    if (res.pixel_debug_logs && res.pixel_debug_logs.length > 0) {
                        const pixelDebugWrap = document.getElementById('calResultPixelDebugWrap');
                        const pixelDebugEl = document.getElementById('calResultPixelDebug');
                        if (pixelDebugEl) { pixelDebugWrap.classList.remove('hidden'); pixelDebugEl.textContent = res.pixel_debug_logs.join('\n'); }
                    }
                }
            }
            alert('上傳失敗或無回應\n' + (res.debug_output || JSON.stringify(res).substring(0, 500)));
            return { success: false, res };
        }
        
        lastCalibrationResult = res;
        const emptyEl = document.getElementById('calResultEmpty');
        const contentEl = document.getElementById('calResultContent');
        
        if (contentEl) {
            emptyEl.classList.add('hidden');
            contentEl.classList.remove('hidden');
            const startWrap = document.getElementById('calResultStartPointWrap');
            const startLogs = document.getElementById('calResultStartPointLogs');
            if (startWrap) startWrap.classList.add('hidden');
            if (startLogs) startLogs.classList.add('hidden');
            const ocrLines = res.ocr_lines || [];
            const charArr = res.char_measurements || [];
            const pixelUnit = res.pixel_per_unit;
            const ocrMethodUsed = res.ocr_method_used || 'unknown';
            const noOcrData = !ocrLines.length && !charArr.length && (pixelUnit == null || pixelUnit === 1);
            const warnEl = document.getElementById('calResultOcrWarning');
            if (warnEl) warnEl.classList.toggle('hidden', !noOcrData);
            document.getElementById('calResultPixelPerUnit').textContent = (pixelUnit ?? '-') + ' (' + ocrMethodUsed + ')';
            
            if (res.debug_output) {
                const debugEl = document.getElementById('calResultDebugOutput');
                if (debugEl) { debugEl.textContent = res.debug_output; debugEl.classList.remove('hidden'); }
            } else {
                const debugEl = document.getElementById('calResultDebugOutput');
                if (debugEl) debugEl.classList.add('hidden');
            }
            
            // 顯示 Pixel 偵錯日誌
            const pixelDebugWrap = document.getElementById('calResultPixelDebugWrap');
            const pixelDebugEl = document.getElementById('calResultPixelDebug');
            if (res.pixel_debug_logs && res.pixel_debug_logs.length > 0) {
                pixelDebugWrap.classList.remove('hidden');
                pixelDebugEl.textContent = res.pixel_debug_logs.join('\n');
            } else {
                pixelDebugWrap.classList.add('hidden');
            }
            const stepsSummaryWrap = document.getElementById('calResultStepsSummaryWrap');
            const stepsSummaryEl = document.getElementById('calResultStepsSummary');
            if (res.calibration_steps_summary && stepsSummaryEl) {
                stepsSummaryWrap.classList.remove('hidden');
                stepsSummaryEl.textContent = res.calibration_steps_summary;
            } else if (stepsSummaryWrap) {
                stepsSummaryWrap.classList.add('hidden');
            }
            document.getElementById('calResultOcr').textContent = ocrLines.join('\n') || '(無)';
            const charsEl = document.getElementById('calResultChars');
            if (charsEl) {
                const arr = charArr;
                charsEl.innerHTML = arr.length ? '<table style="border-collapse:collapse; font-size:12px; color:#222;"><tr style="background:#e8e8e8; color:#222;"><th style="padding:4px 8px; text-align:left;">字元</th><th style="padding:4px 8px; text-align:left;">Pair Key</th><th style="padding:4px 8px;">像素寬</th><th style="padding:4px 8px;">單位寬</th></tr>' + arr.map((x, i) => {
                    const ch = x.char === ' ' ? '␣' : (x.char === '\u3000' ? '　' : x.char);
                    const pairKey = x.char ? formatUnicodeCodes(x.char) : '';
                    const bg = i % 2 ? '' : 'background:#f5f5f5;';
                    return `<tr style="${bg}"><td style="padding:3px 8px; font-family:monospace; color:#222;">${escapeHtml(ch)}</td><td style="padding:3px 8px; font-family:monospace; color:#333;">${escapeHtml(pairKey)}</td><td style="padding:3px 8px; text-align:right; color:#222;">${x.pixel_width}</td><td style="padding:3px 8px; text-align:right; color:#222;">${x.unit_width}</td></tr>`;
                }).join('') + '</table>' : '(無字元資料)';
            }
            if (res.calibration) fillCalibrationJsonOutput(res.calibration);
            if (!suppressTabSwitch) setPreviewTab('calibration-result');
        } else {
            emptyEl.classList.remove('hidden');
            contentEl.classList.add('hidden');
            alert(res.error || '上傳或分析失敗');
            return { success: false, res };
        }

        if (res.calibration && fillBackendJson) {
            const ta = document.getElementById('backendStage3CalibrationJson');
            if (ta) {
                ta.value = JSON.stringify(res.calibration, null, 2);
                saveSettingsToCookie();
            }
        }
        if (res.calibration && promptApply) {
            const ok = confirm('已輸出校準 JSON，是否直接套用至右側表單？');
            if (ok) {
                if (applyCalibrationObject(res.calibration)) {
                    alert('已套用校準至右側表單');
                    saveSettingsToCookie();
                } else {
                    alert('套用失敗：校準 JSON 格式不完整');
                }
            }
        }
        return { success: true, res };
    } catch (e) {
        alert('上傳失敗: ' + (e.message || e));
        return { success: false, error: e.message || String(e) };
    } finally {
        if (btn) { btn.disabled = false; btn.textContent = '📷 截圖上傳'; }
        if (input && 'value' in input) input.value = '';
    }
}
function escapeHtml(s) {
    const d = document.createElement('div');
    d.textContent = s;
    return d.innerHTML;
}
function calibrationKeyToChar(key) {
    const k = String(key || '').trim();
    if (!k) return '';
    // 支援 "U+XXXX" 或 "U+AAAA U+BBBB" 格式
    if (k.includes('U+')) {
        const decoded = decodeCalibrationCodesInput(`"${k}"`);
        if (decoded.length > 0) return decoded[0];
    }
    return k;
}
function calibrationCustomToCodeMap(customObj) {
    const out = {};
    if (!customObj || typeof customObj !== 'object') return out;
    Object.entries(customObj).forEach(([k, v]) => {
        const ch = calibrationKeyToChar(k);
        if (!ch) return;
        const codeKey = formatUnicodeCodes(ch);
        out[codeKey] = v;
    });
    return out;
}
function calibrationCustomToCharMap(customObj) {
    const out = {};
    if (!customObj || typeof customObj !== 'object') return out;
    Object.entries(customObj).forEach(([k, v]) => {
        const ch = calibrationKeyToChar(k);
        if (!ch) return;
        out[ch] = v;
    });
    return out;
}
function getGlobalCalibrationDefaults() {
    return {
        ascii: 1.0,
        cjk: 2.0,
        box: 1.0,
        half_space: 1.0,
        full_space: 2.0,
        emoji: 2.0,
        custom: {}
    };
}
function getThemeCalibrationDefaults() {
    const out = {};
    const params = (currentThemeTemplate && currentThemeTemplate.params) ? currentThemeTemplate.params : {};
    const calObj = (params && typeof params.calibration === 'object') ? params.calibration : {};
    ['ascii','cjk','box','half_space','full_space','emoji'].forEach(k => {
        const rawVal = calObj[k] != null ? calObj[k] : params[k];
        if (rawVal != null && rawVal !== '') {
            const n = parseFloat(rawVal);
            if (!isNaN(n)) out[k] = n;
        }
    });
    const customObj = (calObj && typeof calObj.custom === 'object')
        ? calObj.custom
        : ((params && typeof params.custom === 'object') ? params.custom : null);
    if (customObj && Object.keys(customObj).length > 0) out.custom = calibrationCustomToCharMap(customObj);
    return normalizeCalibrationForRuntime(out);
}
function getCalibrationFromJsonTextarea() {
    const ta = document.getElementById('backendStage3CalibrationJson');
    if (!ta || !ta.value.trim()) return {};
    try {
        const raw = JSON.parse(ta.value.trim());
        const c = raw && raw.calibration != null ? raw.calibration : raw;
        if (!c || typeof c !== 'object') return {};
        return normalizeCalibrationForRuntime(c);
    } catch (e) {
        return null;
    }
}
function mergeCalibrationLayers(base, override) {
    const out = { ...(base || {}) };
    const o = (override && typeof override === 'object') ? override : {};
    ['ascii','cjk','box','half_space','full_space','emoji'].forEach(k => {
        if (o[k] != null && o[k] !== '') {
            const v = parseFloat(o[k]);
            if (!isNaN(v)) out[k] = v;
        }
    });
    out.custom = { ...(base?.custom || {}) };
    if (o.custom && typeof o.custom === 'object') {
        const customMap = calibrationCustomToCharMap(o.custom);
        Object.entries(customMap).forEach(([k, v]) => {
            const fv = parseFloat(v);
            if (!isNaN(fv)) out.custom[k] = fv;
        });
    }
    return out;
}
function getMergedCalibrationWithPriority() {
    // 優先序：校準 JSON > 右側校準內容 > theme 預設 > 全域預設
    let merged = getGlobalCalibrationDefaults();
    merged = mergeCalibrationLayers(merged, getThemeCalibrationDefaults());
    merged = mergeCalibrationLayers(merged, normalizeCalibrationForRuntime(getCalibrationFromForm()));
    const fromJson = getCalibrationFromJsonTextarea();
    if (fromJson === null) return null;
    merged = mergeCalibrationLayers(merged, fromJson);
    return normalizeCalibrationForRuntime(merged);
}
function normalizeCalibrationForRuntime(cal) {
    if (!cal || typeof cal !== 'object') return {};
    const out = { ...cal };
    out.custom = calibrationCustomToCharMap(cal.custom || {});
    return out;
}
/** 整理成與 ASCII mode 校準規格一致的 JSON 並填入可複製區塊 */
function buildAsciiModeCalibrationJson(cal) {
    if (!cal || typeof cal !== 'object') return null;
    const out = {};
    ['ascii','cjk','box','half_space','full_space','emoji'].forEach(k => {
        if (cal[k] != null) out[k] = cal[k];
    });
    if (cal.ascii == null) out.ascii = 1.0;
    if (cal.cjk == null) out.cjk = 2.0;
    if (cal.emoji == null) out.emoji = 2.0;
    if (cal.custom && typeof cal.custom === 'object' && Object.keys(cal.custom).length > 0) {
        out.custom = calibrationCustomToCodeMap(cal.custom);
    }
    return out;
}
function fillCalibrationJsonOutput(cal) {
    const wrap = document.getElementById('calResultCalibrationJsonWrap');
    const ta = document.getElementById('calResultCalibrationJson');
    if (!wrap || !ta) return;
    const obj = buildAsciiModeCalibrationJson(cal);
    if (obj) {
        ta.value = JSON.stringify(obj, null, 2);
        wrap.classList.remove('hidden');
    } else {
        ta.value = '';
        wrap.classList.add('hidden');
    }
}
function copyCalibrationJsonResult() {
    const ta = document.getElementById('calResultCalibrationJson');
    const text = ta && ta.value ? ta.value.trim() : '';
    if (!text) { alert('尚無校準 JSON 可複製'); return; }
    if (navigator.clipboard && navigator.clipboard.writeText) {
        navigator.clipboard.writeText(text).then(() => alert('已複製校準 JSON，可貼回校準輸出區的校準 JSON 輸入框')).catch(() => {});
    } else {
        const el = document.createElement('textarea');
        el.value = text;
        document.body.appendChild(el);
        el.select();
        document.execCommand('copy');
        document.body.removeChild(el);
        alert('已複製校準 JSON，可貼回校準輸出區的校準 JSON 輸入框');
    }
}
function applyCalibrationObject(c) {
    if (!c || typeof c !== 'object') return false;
    const n = normalizeCalibrationForRuntime(c);
    ['ascii','cjk','box','half_space','full_space','emoji'].forEach(k => {
        const el = document.getElementById('cal_' + k);
        if (el && n[k] != null) el.value = String(n[k]);
    });
    const listEl = document.getElementById('cal_custom_list');
    if (listEl && n.custom && typeof n.custom === 'object') {
        listEl.innerHTML = '';
        Object.entries(n.custom).forEach(([ch, w]) => addCalCustomRow(ch, w));
    }
    onCalibrationChange();
    return true;
}
function applyCalibrationResult() {
    if (!lastCalibrationResult?.calibration) return;
    if (applyCalibrationObject(lastCalibrationResult.calibration)) alert('已套用校準至右側表單');
}
function applyBackendStage3CalibrationJson() {
    const ta = document.getElementById('backendStage3CalibrationJson');
    if (!ta || !ta.value.trim()) { alert('請輸入校準 JSON'); return; }
    try {
        const raw = JSON.parse(ta.value.trim());
        const c = raw.calibration != null ? raw.calibration : raw;
        if (applyCalibrationObject(c)) {
            alert('已套用校準至右側表單');
            saveSettingsToCookie();
        }
        else alert('JSON 格式需包含 ascii、cjk 等欄位');
    } catch (e) {
        alert('JSON 解析失敗: ' + (e.message || e));
    }
}
function clearBackendStage3CalibrationJson() {
    const ta = document.getElementById('backendStage3CalibrationJson');
    if (!ta) return;
    ta.value = '';
    saveSettingsToCookie();
}
var lastMissingCalibrationChars = [];

function checkMissingCalibrationChars() {
    const stage3El = document.getElementById('backendAsciiStage3Text');
    const outEl = document.getElementById('backendStage3MissingChars');
    const actionsEl = document.getElementById('backendStage3MissingActions');
    if (!stage3El || !outEl) return;
    const tableText = String(stage3El.dataset.baseText || stage3El.innerText || '').trim();
    if (!tableText) {
        outEl.textContent = '請先 Render Backend（勾選 ascii_debug）取得校準輸出表格後再檢查。';
        if (actionsEl) actionsEl.classList.add('hidden');
        return;
    }
    const cal = getMergedCalibrationWithPriority();
    if (cal === null) {
        outEl.textContent = '校準 JSON 解析失敗，請檢查格式。';
        if (actionsEl) actionsEl.classList.add('hidden');
        return;
    }
    const custom = (cal && cal.custom && typeof cal.custom === 'object') ? cal.custom : {};
    const traceTokens = getStage3TokensFromBackendTrace();
    const inTable = new Set(traceTokens.length > 0 ? traceTokens : extractCalibrationChars(tableText));
    const missing = [];
    inTable.forEach(c => {
        if (!(c in custom)) missing.push(c);
    });
    missing.sort((a, b) => String(a).localeCompare(String(b)));
    lastMissingCalibrationChars = missing;

    if (missing.length === 0) {
        outEl.textContent = '無遺漏：表格中字元皆在校準 JSON 的 custom 中或有對應類別。';
        if (actionsEl) actionsEl.classList.add('hidden');
        return;
    }
    const displayStr = missing.join(' ');
    outEl.textContent = `共 ${missing.length} 個：${displayStr}`;
    if (actionsEl) actionsEl.classList.remove('hidden');
}

// 字元分類與代表字元（與 calibrate_analyze.py 同步）
const ASCII_CHAR_CATEGORIES = {
    uppercase: { chars: 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', representative: 'A' },
    lowercase: { chars: 'abcdefghijklmnopqrstuvwxyz', representative: 'a' },
    digits: { chars: '0123456789', representative: '0' },
    narrow_punct: { chars: '.,;:!\'"`', representative: '.' },
    brackets: { chars: '()[]{}<>', representative: '(' },
    other_operators: { chars: '+', representative: '+' },
    slashes: { chars: '/\\|', representative: '/' },
    special: { chars: '@#$%^&~?', representative: '@' }
};
const BOX_CHAR_CATEGORIES = {
    single_line: { chars: '─│┌┐└┘├┤┬┴┼', representative: '─' },
    double_line: { chars: '═║╔╗╚╝╠╣╬', representative: '═' },
    mixed_line: { chars: '╒╓╕╖╘╙╛╜╞╟╡╢╤╥╧╨╪╫', representative: '╒' }
};
const MUST_MEASURE_INDIVIDUALLY = '-=_*';

function getRepresentativeForChar(char) {
    if (MUST_MEASURE_INDIVIDUALLY.includes(char)) return null;
    for (const cat of Object.values(ASCII_CHAR_CATEGORIES)) {
        if (cat.chars.includes(char)) return cat.representative;
    }
    for (const cat of Object.values(BOX_CHAR_CATEGORIES)) {
        if (cat.chars.includes(char)) return cat.representative;
    }
    return null;
}

function isCJK(char) {
    const cp = char.codePointAt(0);
    return (cp >= 0x4E00 && cp <= 0x9FFF) ||  // CJK Unified
           (cp >= 0x3400 && cp <= 0x4DBF) ||  // CJK Ext A
           (cp >= 0x20000 && cp <= 0x2A6DF) || // CJK Ext B+
           (cp >= 0x3000 && cp <= 0x303F) ||  // CJK Symbols
           (cp >= 0xFF00 && cp <= 0xFFEF);    // Half/Fullwidth
}

function isBoxChar(char) {
    for (const cat of Object.values(BOX_CHAR_CATEGORIES)) {
        if (cat.chars.includes(char)) return true;
    }
    return false;
}
function isEmojiChar(char) {
    if (!char) return false;
    for (const c of String(char)) {
        const cp = c.codePointAt(0);
        if (
            (cp >= 0x1F300 && cp <= 0x1FAFF) ||
            (cp >= 0x2600 && cp <= 0x27BF) ||
            (cp >= 0x1F1E6 && cp <= 0x1F1FF)
        ) {
            return true;
        }
    }
    return false;
}

function getCharWidth(char, calibration) {
    const custom = calibration.custom || {};
    const defaults = {
        ascii: calibration.ascii ?? 1.0,
        cjk: calibration.cjk ?? 2.0,
        box: calibration.box ?? 1.0,
        half_space: calibration.half_space ?? 1.0,
        full_space: calibration.full_space ?? 2.0,
        emoji: calibration.emoji ?? 2.0
    };

    // 1. 優先使用 custom 個別定義
    if (char in custom) return custom[char];

    // 2. 看是否有代表字元
    const rep = getRepresentativeForChar(char);
    if (rep && rep in custom) return custom[rep];

    // 3. 半形/全形空白
    if (char === ' ') return defaults.half_space;
    if (char === '　') return defaults.full_space;

    // 4. 框線字元
    if (isBoxChar(char)) {
        return defaults.box;
    }

    // 5. CJK 字元
    if (isCJK(char)) {
        return defaults.cjk;
    }

    // 6. Emoji
    if (isEmojiChar(char)) {
        return defaults.emoji;
    }

    // 7. 預設 ASCII
    return defaults.ascii;
}

function calculateLineWidthsDebug() {
    const stage3El = document.getElementById('backendAsciiStage3Text');
    const outEl = document.getElementById('backendStage3DebugOutput');
    const sectionEl = document.getElementById('backendStage3DebugSection');
    if (!stage3El || !outEl) return;
    if (sectionEl) sectionEl.classList.remove('hidden');
    const backendTrace = window.__backendStage3Details;
    if (backendTrace && Array.isArray(backendTrace.lines) && backendTrace.lines.length > 0) {
        const lines = backendTrace.lines;
        const firstWidth = parseFloat(lines[0].line_width || 0) || 0;
        const maxLine = lines.reduce((acc, cur) => (parseFloat(cur.line_width || 0) > parseFloat(acc.line_width || 0) ? cur : acc), lines[0]);
        const output = [];
        output.push(`資料來源: backend stage3_details（權威）`);
        output.push(`總行數: ${backendTrace.line_count || lines.length} | 顯示行數: ${lines.length}${backendTrace.lines_truncated ? ' (已截斷)' : ''}`);
        output.push(`第一行寬度: ${firstWidth.toFixed(2)}`);
        output.push(`最寬行: 第 ${maxLine.line_no} 行 (${(parseFloat(maxLine.line_width || 0) || 0).toFixed(2)})`);
        output.push('---');
        lines.forEach((lineInfo, idx) => {
            const w = parseFloat(lineInfo.line_width || 0) || 0;
            const diff = w - firstWidth;
            const diffStr = idx === 0 ? '0 (基準)' : (diff >= 0 ? `+${diff.toFixed(2)}` : diff.toFixed(2));
            output.push(`L${String(lineInfo.line_no).padStart(3, ' ')} | 寬度: ${w.toFixed(2).padStart(8, ' ')} | 差距: ${diffStr.padStart(10, ' ')} | ${lineInfo.text || ''}`);
            const tokens = Array.isArray(lineInfo.tokens) ? lineInfo.tokens : [];
            tokens.forEach(t => {
                const tok = String(t.token || '').replace(/ /g, '␣');
                const codes = String(t.codes || '');
                const tw = (parseFloat(t.width || 0) || 0).toFixed(2);
                const src = String(t.source || 'unknown');
                output.push(`    - ${tok} [${codes}] w=${tw} src=${src}`);
            });
            if (lineInfo.tokens_truncated) output.push('    ... (本行 token 已截斷)');
        });
        outEl.textContent = output.join('\n');
        return;
    }

    // 使用 innerHTML 獲取原始內容，再處理換行
    // 因為 innerText 在某些情況下會丟失換行資訊
    let tableText = stage3El.innerHTML || '';
    // 將 HTML 實體轉回原始字符
    const tempDiv = document.createElement('div');
    tempDiv.innerHTML = tableText;
    tableText = tempDiv.textContent || tempDiv.innerText || '';
    
    if (!tableText.trim()) {
        outEl.textContent = '請先 Render Backend（勾選 ascii_debug）取得校準輸出表格。';
        return;
    }

    const cal = getMergedCalibrationWithPriority();
    if (cal === null) {
        outEl.textContent = '校準 JSON 解析失敗，請檢查格式。';
        return;
    }

    // 處理各種換行符格式，並過濾空行
    const allLines = tableText.split(/\r?\n/);
    const lines = allLines.filter(line => line.trim().length > 0);
    const lineWidths = [];
    let maxWidth = 0;
    let maxLineIdx = 0;

    lines.forEach((line, idx) => {
        let width = 0;
        for (const tok of iterDisplayTokens(line)) {
            if (tok === '\r') continue;
            width += getCharWidth(tok, cal);
        }
        lineWidths.push({ idx: idx + 1, line, width });
        if (width > maxWidth) {
            maxWidth = width;
            maxLineIdx = idx;
        }
    });

    const firstWidth = lineWidths.length > 0 ? lineWidths[0].width : 0;
    const output = [];
    output.push(`原始行數: ${allLines.length} | 非空行數: ${lines.length}`);
    output.push(`第一行寬度: ${firstWidth.toFixed(2)}`);
    output.push(`最寬行: 第 ${maxLineIdx + 1} 行 (${maxWidth.toFixed(2)})`);
    output.push('---');
    lineWidths.forEach((info, i) => {
        const diff = info.width - firstWidth;
        const diffStr = i === 0 ? '0 (基準)' : (diff >= 0 ? `+${diff.toFixed(2)}` : diff.toFixed(2));
        output.push(`L${String(info.idx).padStart(3, ' ')} | 寬度: ${info.width.toFixed(2).padStart(8, ' ')} | 差距: ${diffStr.padStart(10, ' ')} | ${info.line}`);
    });

    outEl.textContent = output.join('\n');
}
function onCalibrationChange() {
    saveSettingsToCookie();
    updatePreview();
}
function refreshBackendStage3Debug() {
    // 從設定儲存重新載入校準 JSON
    try {
        const raw = getSettingsStorage();
        if (raw) {
            const o = JSON.parse(raw);
            const stage3CalJsonEl = document.getElementById('backendStage3CalibrationJson');
            if (stage3CalJsonEl && o.stage3CalibrationJson) {
                stage3CalJsonEl.value = String(o.stage3CalibrationJson);
            }
        }
    } catch (e) {}
    // 校準參數改由 localStorage 的獨立儲存載入，避免舊 cookie 覆蓋
    loadBackendCalControls();
    setTimeout(() => calculateLineWidthsDebug(), 50);
}

// 可收折區塊切換
function toggleStageCollapse(id) {
    const el = document.getElementById(id);
    if (!el) return;
    const isCollapsed = el.classList.contains('collapsed');
    const content = el.querySelector('.collapsible-content');
    if (isCollapsed) {
        el.classList.remove('collapsed');
        if (content) content.style.display = 'block';
    } else {
        el.classList.add('collapsed');
        if (content) content.style.display = 'none';
    }
}

// Unicode 字碼格式化（支援雙字碼 emoji）
function formatUnicodeCodes(char) {
    const codes = [];
    // 使用 for...of 正確處理代理對（surrogate pairs）
    for (const c of char) {
        const code = c.codePointAt(0);
        codes.push('U+' + code.toString(16).toUpperCase().padStart(4, '0'));
    }
    return codes.join(' ');
}
// 逐 Unicode 字元切分（不合併 RI/ZWJ/VS/emoji modifier）
// 需求：每個字元都獨立計算與顯示其寬度/字碼
function iterDisplayTokens(text) {
    return Array.from(String(text || ''));
}
function getStage3TokensFromBackendTrace() {
    const trace = window.__backendStage3Details;
    if (!trace || !Array.isArray(trace.lines)) return [];
    const out = [];
    const seen = new Set();
    trace.lines.forEach(lineInfo => {
        const tokens = Array.isArray(lineInfo?.tokens) ? lineInfo.tokens : [];
        tokens.forEach(t => {
            const tok = String(t?.token || '');
            if (!tok) return;
            if (tok === '\n' || tok === '\r') return;
            if (!seen.has(tok)) {
                seen.add(tok);
                out.push(tok);
            }
        });
    });
    return out;
}
function extractCalibrationChars(text) {
    const s = String(text || '');
    const chars = Array.from(s);
    const out = [];
    const seen = new Set();
    for (let i = 0; i < chars.length; i++) {
        const ch = chars[i];
        if (!ch) continue;
        if (ch === '\n' || ch === '\r') continue;
        if (!(ch.trim() || ch === ' ' || ch === '　')) continue;
        if (!seen.has(ch)) {
            seen.add(ch);
            out.push(ch);
        }
    }
    return out;
}

// 從表格提取所有用字
function extractAllCharsFromTable() {
    const stage3El = document.getElementById('backendAsciiStage3Text');
    if (!stage3El) return [];
    const traceTokens = getStage3TokensFromBackendTrace();
    if (traceTokens.length > 0) return traceTokens;
    
    // 僅取 baseText（不含附加的校準區塊），避免抽字污染
    const baseText = stage3El.dataset.baseText;
    let tableText = (baseText != null) ? String(baseText) : (stage3El.innerText || '');
    return extractCalibrationChars(tableText);
}

// 顯示字碼對照表
function displayCharCodes(chars, containerId) {
    const container = document.getElementById(containerId);
    if (!container) return;
    
    // 排序：ASCII 優先，然後是 CJK，最後是其他
    const sorted = [...chars].sort((a, b) => {
        const codeA = a.codePointAt(0);
        const codeB = b.codePointAt(0);
        // ASCII (0x00-0x7F) 優先
        const isAsciiA = codeA <= 0x7F;
        const isAsciiB = codeB <= 0x7F;
        if (isAsciiA && !isAsciiB) return -1;
        if (!isAsciiA && isAsciiB) return 1;
        // CJK (0x4E00-0x9FFF) 次之
        const isCjkA = codeA >= 0x4E00 && codeA <= 0x9FFF;
        const isCjkB = codeB >= 0x4E00 && codeB <= 0x9FFF;
        if (isCjkA && !isCjkB) return -1;
        if (!isCjkA && isCjkB) return 1;
        // 其他按 code point 排序
        return codeA - codeB;
    });
    
    let html = '<div style="display:flex; flex-wrap:wrap; gap:4px;">';
    sorted.forEach(char => {
        const codes = formatUnicodeCodes(char);
        const displayChar = char.replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/ /g, '␣');
        html += `<span class="char-code-item"><span class="char">${displayChar}</span><span class="code">${codes}</span></span>`;
    });
    html += '</div>';
    html += `<div style="margin-top:8px; font-size:11px; color:#888;">共 ${sorted.length} 個不重複字元</div>`;
    container.innerHTML = html;
}

function decodeCalibrationCodesInput(inputText) {
    const raw = String(inputText || '').trim();
    if (!raw) return [];
    const groups = [];
    const quoted = [...raw.matchAll(/"([^"]+)"/g)];
    if (quoted.length > 0) {
        quoted.forEach(m => { if (m[1] && m[1].trim()) groups.push(m[1].trim()); });
    } else {
        raw.split(/\s+/).forEach(t => { if (t.trim()) groups.push(t.trim()); });
    }
    const chars = [];
    groups.forEach(group => {
        const cps = group.split(/\s+/).filter(Boolean).map(token => {
            const m = token.match(/^U\+([0-9A-Fa-f]{4,6})$/);
            if (!m) return null;
            const cp = parseInt(m[1], 16);
            if (Number.isNaN(cp) || cp < 0 || cp > 0x10FFFF) return null;
            return cp;
        });
        if (cps.length === 0 || cps.some(v => v == null)) return;
        chars.push(String.fromCodePoint(...cps));
    });
    return chars;
}

function encodeCharsToQuotedCodeList(chars) {
    return (chars || []).map(ch => `"${formatUnicodeCodes(ch)}"`).join(' ');
}

function mergeUniqueChars(listA, listB) {
    const out = [];
    const seen = new Set();
    [...(listA || []), ...(listB || [])].forEach(ch => {
        if (!ch || !String(ch).trim()) return;
        if (!seen.has(ch)) {
            seen.add(ch);
            out.push(ch);
        }
    });
    return out;
}

function getBackendCalibrationCharsFromControls(fallbackChars) {
    const customRaw = document.getElementById('backendCalCustomChars')?.value || '';
    const parsedCustom = decodeCalibrationCodesInput(customRaw);
    const base = (fallbackChars && fallbackChars.length) ? fallbackChars : [];
    const merged = mergeUniqueChars(base, parsedCustom);
    if (merged.length > 0) return merged;
    return ['A', 'B', 'C', 'D', 'E', '字'];
}

function showCopySuccessState(btn) {
    if (!btn) return;
    const original = btn.dataset.originalText || btn.textContent || '複製';
    btn.dataset.originalText = original;
    btn.textContent = '✅ 已複製';
    btn.disabled = true;
    clearTimeout(btn._copySuccessTimer);
    btn._copySuccessTimer = setTimeout(() => {
        btn.textContent = original;
        btn.disabled = false;
    }, 1500);
}

function copyUsedCalibrationCodes(btn) {
    const ta = document.getElementById('backendStage3UsedCalibrationCodes');
    const text = ta ? (ta.value || '') : '';
    if (!text.trim()) {
        alert('目前沒有可複製的校準字碼。');
        return;
    }
    if (navigator.clipboard?.writeText) {
        navigator.clipboard.writeText(text).then(() => {
            showCopySuccessState(btn || document.getElementById('backendUsedCodesCopyBtn'));
        }).catch(() => {
            const el = document.createElement('textarea');
            el.value = text;
            document.body.appendChild(el);
            el.select();
            document.execCommand('copy');
            document.body.removeChild(el);
            showCopySuccessState(btn || document.getElementById('backendUsedCodesCopyBtn'));
        });
    } else {
        const el = document.createElement('textarea');
        el.value = text;
        document.body.appendChild(el);
        el.select();
        document.execCommand('copy');
        document.body.removeChild(el);
        showCopySuccessState(btn || document.getElementById('backendUsedCodesCopyBtn'));
    }
}

function onBackendCalibrationControlInput() {
    saveBackendCalControls();
    saveSettingsToCookie();
    const stage3Wrap = document.getElementById('backendStage3CalibrationImageContainer');
    if (stage3Wrap && !stage3Wrap.classList.contains('hidden')) {
        showCalibrationImageInStage3(true);
    }
}
function onBackendPatternInputChange() {
    onBackendCalibrationControlInput();
    refreshCalibrationTable();
}

// 以 No OCR（pixel）格式產生校準文字
function buildNoOcrCalibrationText(chars, charsPerLine, charRepeat) {
    const safeCharsPerLine = Math.max(1, Math.min(10, parseInt(charsPerLine, 10) || 6));
    const safeRepeat = Math.max(1, Math.min(20, parseInt(charRepeat, 10) || 5));
    const lines = [];
    const { startRaw, endRaw } = getEffectivePixelPatterns();
    lines.push(patternToBlockLine(parsePositivePattern(startRaw, '1 2 1 3 1 2'), '█ ██ █ ███ █ ██'));
    // 空白校準行依每字重複次數輸出：半形空白 N 個、全形空白 N 個
    lines.push(`█${' '.repeat(safeRepeat)}█ █${'\u3000'.repeat(safeRepeat)}█`);
    for (let i = 0; i < chars.length; i += safeCharsPerLine) {
        const lineChars = chars.slice(i, i + safeCharsPerLine);
        let line = '';
        for (let j = 0; j < lineChars.length; j++) {
            line += (j === 0 ? '█ ' : ' █ ') + lineChars[j].repeat(safeRepeat) + ' █';
        }
        lines.push(line);
    }
    lines.push(patternToBlockLine(parsePositivePattern(endRaw, '2 1 3 1 2 1'), '██ █ ███ █ ██ █'));
    return lines.join('\n');
}

// 複製遺漏字元到校準字元欄位
function copyMissingCharsToCalibration() {
    const customInput = document.getElementById('backendCalCustomChars');
    if (!customInput) return;
    if (!lastMissingCalibrationChars || lastMissingCalibrationChars.length === 0) {
        alert('尚無遺漏字元，請先按「檢查遺漏字元」。');
        return;
    }
    const existingChars = decodeCalibrationCodesInput(customInput.value || '');
    const mergedChars = mergeUniqueChars(existingChars, lastMissingCalibrationChars);
    customInput.value = encodeCharsToQuotedCodeList(mergedChars);
    saveSettingsToCookie();
    alert('已填入自訂校準字元欄位。');
}

// 在校準輸出區顯示校準圖片（從表格提取所有用字）
function showCalibrationImageInStage3(silent) {
    const tableChars = extractAllCharsFromTable();
    const chars = getBackendCalibrationCharsFromControls(tableChars);
    if (chars.length === 0) {
        if (!silent) alert('請先 Render Backend（勾選 ascii_debug）取得校準輸出表格。');
        return;
    }
    
    // 獲取參數
    const charsPerLine = parseInt(document.getElementById('backendCalCharsPerLine')?.value) || 6;
    const charRepeat = parseInt(document.getElementById('backendCalCharRepeat')?.value) || 5;
    
    const text = buildNoOcrCalibrationText(chars, charsPerLine, charRepeat);
    
    // 顯示校準圖片區（保留字碼對照與複製區塊）
    const container = document.getElementById('backendStage3CalibrationImageContainer');
    const pre = document.getElementById('backendStage3CalibrationImagePre');
    if (container) container.classList.remove('hidden');
    if (pre) pre.textContent = text;

    // 直接把校準區塊接到上方 table 區塊中（間隔 3 行）
    const stage3El = document.getElementById('backendAsciiStage3Text');
    if (stage3El) {
        const baseText = stage3El.dataset.baseText ?? stage3El.textContent ?? '';
        setBackendStage3Text(`${baseText}\n\n\n${text}`, 'append', false);
    }
    
    // 顯示字碼對照表
    displayCharCodes(chars, 'backendStage3CalibrationImageCharCodesContent');
    const usedEl = document.getElementById('backendStage3UsedCalibrationCodes');
    if (usedEl) usedEl.value = encodeCharsToQuotedCodeList(chars);
}
function addCalCustomRow(char, width) {
    const list = document.getElementById('cal_custom_list');
    if (!list) return;
    const row = document.createElement('div');
    row.className = 'cal-custom-row';
    row.style.cssText = 'display:flex; align-items:center; gap:8px;';
    const charIn = document.createElement('input');
    charIn.type = 'text';
    charIn.className = 'cal-custom-char';
    charIn.maxLength = 4;
    charIn.placeholder = '字元（如 ─ ═）';
    charIn.style.cssText = 'width:64px; font-family:monospace; text-align:center; padding:4px 6px;';
    if (char) charIn.value = String(char);
    const widthIn = document.createElement('input');
    widthIn.type = 'number';
    widthIn.className = 'cal-custom-width';
    widthIn.min = 0.1;
    widthIn.max = 4;
    widthIn.step = 0.1;
    widthIn.placeholder = '寬度';
    widthIn.style.cssText = 'width:72px; padding:4px 6px;';
    if (width != null) widthIn.value = String(width);
    const delBtn = document.createElement('button');
    delBtn.type = 'button';
    delBtn.textContent = '刪除';
    delBtn.style.cssText = 'font-size:12px; padding:4px 8px;';
    delBtn.onclick = () => { removeCalCustomRow(row); onCalibrationChange(); };
    [charIn, widthIn].forEach(el => { el.onchange = onCalibrationChange; });
    row.appendChild(charIn);
    row.appendChild(widthIn);
    row.appendChild(delBtn);
    list.appendChild(row);
}
function _isAsciiCalibrationChar(char) {
    if (!char || char.length !== 1) return false;
    const cp = char.codePointAt(0);
    return cp >= 0x21 && cp <= 0x7E;
}
function _getCalibrationCategoryForChar(char) {
    if (!char) return null;
    if (char === ' ') return 'half_space';
    if (char === '　') return 'full_space';
    if (isBoxChar(char)) return 'box';
    if (isCJK(char)) return 'cjk';
    if (isEmojiChar(char)) return 'emoji';
    if (_isAsciiCalibrationChar(char)) return 'ascii';
    return null;
}
function clearCalibrationCategory(category) {
    const key = String(category || '').trim();
    if (!key) return;
    const baseInput = document.getElementById('cal_' + key);
    if (baseInput) baseInput.value = '';
    const rows = Array.from(document.querySelectorAll('.cal-custom-row'));
    rows.forEach(row => {
        const charIn = row.querySelector('.cal-custom-char');
        const ch = (charIn && charIn.value) ? charIn.value.trim() : '';
        if (!ch) return;
        if (_getCalibrationCategoryForChar(ch) === key) row.remove();
    });
    onCalibrationChange();
}
function removeCalCustomRow(rowEl) {
    if (rowEl && rowEl.parentElement) rowEl.remove();
}
function clearCalibrationForm() {
    ['ascii','cjk','box','half_space','full_space','emoji'].forEach(k => {
        const el = document.getElementById('cal_' + k);
        if (el) el.value = '';
    });
    const list = document.getElementById('cal_custom_list');
    if (list) list.innerHTML = '';
}
function getCalibrationFromForm() {
    const keys = ['ascii','cjk','box','half_space','full_space','emoji'];
    const obj = {};
    keys.forEach(k => {
        const el = document.getElementById('cal_' + k);
        if (el && el.value.trim() !== '') {
            const v = parseFloat(el.value);
            if (!isNaN(v)) obj[k] = v;
        }
    });
    const rows = document.querySelectorAll('.cal-custom-row');
    if (rows.length > 0) {
        const custom = {};
        rows.forEach(r => {
            const charIn = r.querySelector('.cal-custom-char');
            const widthIn = r.querySelector('.cal-custom-width');
            const ch = charIn && charIn.value.trim();
            const w = widthIn && widthIn.value.trim();
            if (ch && w !== '') {
                const v = parseFloat(w);
                if (!isNaN(v)) custom[ch] = v;
            }
        });
        if (Object.keys(custom).length > 0) obj.custom = custom;
    }
    return obj;
}
async function loadExample(key) {
    if (!key) return;
    try {
        const r = await fetch(`doc/${key}.json`);
        if (!r.ok) throw new Error(r.statusText);
        const data = await r.json();
        document.getElementById('dataJson').value = JSON.stringify(data, null, 2);
        document.getElementById('tableTitle').value = (data.title != null) ? data.title : 'Zeble Table';
        document.getElementById('tableFooter').value = (data.footer != null) ? data.footer : '';
        document.getElementById('exampleSelect').value = key;
        setPreviewTab('frontend');
        updatePreview();
    } catch (e) {
        console.error('Failed to load', key, e);
        alert('載入失敗: ' + (e.message || '無法讀取檔案'));
    }
}
function hexToRgba(hex, a) {
    if (!hex || typeof hex !== 'string') return `rgba(233,69,96,${a})`;
    hex = hex.replace(/^#/, '');
    if (hex.length === 3) hex = hex[0]+hex[0]+hex[1]+hex[1]+hex[2]+hex[2];
    if (hex.length !== 6) return `rgba(233,69,96,${a})`;
    const r = parseInt(hex.slice(0,2), 16), g = parseInt(hex.slice(2,4), 16), b = parseInt(hex.slice(4,6), 16);
    return `rgba(${r},${g},${b},${a})`;
}

function getThemeSourceInfo(theme) {
    const source = theme?.source || 'unknown';
    if (source === 'api') {
        const sourceType = theme?.source_type || 'unknown';
        if (sourceType === 'json') return { key: 'api_json', title: '來源：API（JSON / template.json）', order: 1 };
        if (sourceType === 'zip') return { key: 'api_zip', title: '來源：API（ZIP）', order: 2 };
        return { key: 'api_other', title: '來源：API（其他）', order: 3 };
    }
    if (source === 'fallback') {
        return { key: 'fallback', title: '來源：前端備援清單（Fallback）', order: 8 };
    }
    return { key: 'other', title: '來源：其他', order: 9 };
}

function createThemeItemElement(themeId, theme) {
    const themeColor = theme.theme_color || theme.accent || '#e94560';
    const isActive = currentTheme === themeId;
    const div = document.createElement('div');
    div.className = `theme-item ${isActive ? 'active' : ''}`;
    div.style.background = isActive ? hexToRgba(themeColor, 0.22) : hexToRgba(themeColor, 0.08);
    div.style.color = themeColor;
    div.onclick = async () => {
        currentTheme = themeId;
        await loadThemeTemplate(themeId);
        applyPreviewBgForTheme(themeId);
        saveSettingsToCookie();
        renderThemeList();
        await updateStyleEditor();
        setPreviewTab('frontend');
        updatePreview();
    };
    div.innerHTML = `<div class="color-dot" style="background:${themeColor}"></div><span>${theme.name}</span>`;
    return div;
}

function renderThemeList() {
    const list = document.getElementById('themeList');
    list.innerHTML = '';
    list.classList.add('theme-grid-by-source');

    const groups = {};
    Object.keys(loadedThemes).forEach((themeId) => {
        const theme = loadedThemes[themeId];
        const src = getThemeSourceInfo(theme);
        if (!groups[src.key]) groups[src.key] = { ...src, items: [] };
        groups[src.key].items.push({ themeId, theme });
    });

    const orderedGroups = Object.values(groups).sort((a, b) => a.order - b.order || a.title.localeCompare(b.title));
    orderedGroups.forEach(group => {
        const section = document.createElement('div');
        section.className = 'theme-source-group';

        const title = document.createElement('div');
        title.className = 'theme-source-title';
        title.textContent = `${group.title}（${group.items.length}）`;
        section.appendChild(title);

        const grid = document.createElement('div');
        grid.className = 'theme-grid';
        group.items.forEach(({ themeId, theme }) => {
            grid.appendChild(createThemeItemElement(themeId, theme));
        });

        section.appendChild(grid);
        list.appendChild(section);
    });
    updateStyleEditor();
}

async function updateStyleEditor() {
    // 確保已載入 theme template
    if (!currentThemeTemplate) {
        await loadThemeTemplate(currentTheme);
    }
    
    const template = currentThemeTemplate;
    if (!template) return;

    if (currentMode === 'css' && template.type === 'css') {
        // CSS Mode: 填充選擇器或 raw JSON
        populateCssSelectorsFromTemplate(template);
        document.getElementById('cssThemeJson').value = JSON.stringify(template, null, 2);
        document.getElementById('css-selector-editor').classList.toggle('hidden', cssEditMode !== 'selector');
        document.getElementById('css-advanced-editor').classList.toggle('hidden', cssEditMode !== 'advanced');
        updateFontDetection();
    } else if (currentMode === 'pil' && template.type === 'pil') {
        // PIL Mode: 從 params 設定參數（同時更新 range/input 與對應 _num）
        const params = template.params || {};
        const setPilParam = (id, val) => {
            const el = document.getElementById(id);
            if (!el) return;
            let v = val;
            if (el.type === 'range') {
                const min = Number(el.min);
                const max = Number(el.max);
                const step = el.step ? Number(el.step) : 1;
                v = Math.max(min, Math.min(max, Number(v) ?? min));
                if (step > 0) v = Math.round(v / step) * step;
                el.value = v;
            } else {
                el.value = val;
            }
            const numEl = document.getElementById(id + '_num');
            if (numEl) numEl.value = el.value;
        };
        setPilParam('p_bg_color', params.bg_color || '#1a1a2e');
        setPilParam('p_text_color', params.text_color || '#ffffff');
        setPilParam('p_header_bg', params.header_bg || '#0f3460');
        setPilParam('p_header_text', params.header_text || '#e94560');
        setPilParam('p_alt_row_color', params.alt_row_color || '#16213e');
        setPilParam('p_border_color', params.border_color || '#4a5568');
        setPilParam('p_font_size', params.font_size ?? 10);
        setPilParam('p_header_font_size', params.header_font_size ?? 12);
        setPilParam('p_title_font_size', params.title_font_size ?? 14);
        setPilParam('p_title_height', params.title_height ?? 48);
        setPilParam('p_footer_font_size', params.footer_font_size ?? 10);
        setPilParam('p_padding', params.padding || 20);
        setPilParam('p_cell_padding', params.cell_padding || 12);
        setPilParam('p_row_height', params.row_height || 44);
        setPilParam('p_header_height', params.header_height || 52);
        setPilParam('p_border_radius', params.border_radius || 12);
        setPilParam('p_border_width', params.border_width || 1);
        setPilParam('p_shadow_color', params.shadow_color || '#000000');
        setPilParam('p_shadow_offset', params.shadow_offset || 8);
        setPilParam('p_shadow_blur', params.shadow_blur || 20);
        setPilParam('p_shadow_opacity', params.shadow_opacity || 0.3);
        setPilParam('p_title_padding', params.title_padding || 16);
        setPilParam('p_footer_padding', params.footer_padding || 12);
        setPilParam('p_line_spacing', params.line_spacing || 1.4);
        setPilParam('p_cell_align', params.cell_align || 'left');
        setPilParam('p_header_align', params.header_align || 'left');
        const wm = template.watermark || {};
        const wmEnabled = document.getElementById('p_watermark_enabled');
        if (wmEnabled) wmEnabled.checked = wm.enabled !== false;
        const wmText = document.getElementById('p_watermark_text');
        if (wmText) wmText.value = wm.text || 'Generated by ZenTable';
        const wmOpacity = document.getElementById('p_watermark_opacity');
        if (wmOpacity) wmOpacity.value = wm.opacity ?? 0.5;
        const fontFamilyEl = document.getElementById('p_font_family');
        if (fontFamilyEl) fontFamilyEl.value = params.font_family || '';
    } else if (currentMode === 'ascii' && (template.type === 'text' || template.type === 'ascii')) {
        const params = template.params || {};
        const aStyle = document.getElementById('a_style');
        if (aStyle) aStyle.value = params.style || 'double';
        const aPad = document.getElementById('a_padding');
        const aPadNum = document.getElementById('a_padding_num');
        if (aPad) aPad.value = params.padding ?? 2;
        if (aPadNum) aPadNum.value = params.padding ?? 2;
        const aAlign = document.getElementById('a_align');
        if (aAlign) aAlign.value = params.align || 'center';
        const aHeaderAlign = document.getElementById('a_header_align');
        if (aHeaderAlign) aHeaderAlign.value = params.header_align || 'center';
        // 自訂框線字元（有值則顯示，否則留空由 style 預設）
        ['tl','tr','bl','br','h','v','header','row','footer'].forEach(k => {
            const el = document.getElementById('a_box_' + k);
            if (el) el.value = params['box_' + k] || '';
        });
        const aBorderMode = document.getElementById('a_border_mode');
        if (aBorderMode) aBorderMode.value = params.border_mode || 'full';
        const aRowInterval = document.getElementById('a_row_interval');
        if (aRowInterval) aRowInterval.value = params.row_interval ?? 5;
        const aColInterval = document.getElementById('a_col_interval');
        if (aColInterval) aColInterval.value = params.col_interval ?? 1;
        const aCellPadLeft = document.getElementById('a_cell_pad_left');
        if (aCellPadLeft) aCellPadLeft.value = params.cell_pad_left ?? 1;
        const aCellPadRight = document.getElementById('a_cell_pad_right');
        if (aCellPadRight) aCellPadRight.value = params.cell_pad_right ?? 1;
        const aGridCfg = document.getElementById('a_grid_config');
        if (aGridCfg) aGridCfg.value = typeof params.grid_config === 'string' ? params.grid_config : (params.grid_config ? JSON.stringify(params.grid_config, null, 2) : '');
        applyAsciiStyleDefaults();
    }
}
// 估算表格寬度（與 zeble_render estimate_css_viewport 一致，供前端預覽對齊後端）
function _parseFontSizePx(css, def) {
    if (!css) return def;
    const m = String(css).match(/font-size\s*:\s*(\d+)px/i);
    return m ? parseInt(m[1], 10) : def;
}
function _parseWidthPx(css) {
    if (!css) return null;
    const m = String(css).match(/(?:^|[;\s])(?:width|min-width)\s*:\s*(\d+)px/i);
    return m ? parseInt(m[1], 10) : null;
}
function _estimateTextWidth(str, fontSize) {
    const s = String(str || '');
    let w = 0;
    for (let i = 0; i < s.length; i++) {
        const c = s.charCodeAt(i);
        w += (c > 0x7f) ? fontSize * 1.0 : fontSize * 0.55;
    }
    return Math.ceil(w);
}
function estimateTableWidthPx(data, template) {
    const styles = template?.styles || {};
    const thStyle = styles.th || styles['.cell-header'] || '';
    const tdStyle = styles.td || styles['.cell'] || '';
    const headerFs = _parseFontSizePx(thStyle, 18);
    const cellFs = _parseFontSizePx(tdStyle, 14);
    const headers = data?.headers || [];
    const rows = data?.rows || [];
    const colCount = Math.max(1, headers.length);
    let tableWidth = 0;
    for (let i = 0; i < colCount; i++) {
        let w = _estimateTextWidth(headers[i], headerFs);
        for (const row of rows) {
            if (i < row.length) w = Math.max(w, _estimateTextWidth(getCellText(row[i]), cellFs));
        }
        w = Math.min(400, Math.max(60, w + 28));
        tableWidth += w;
    }
    let vw = Math.ceil((40 + tableWidth + 40) * 1.15);
    const cStyle = styles.container || styles['.container'] || '';
    const explicitW = _parseWidthPx(cStyle);
    if (explicitW != null && explicitW > vw) vw = Math.min(explicitW, 16384);
    return vw;
}
function normalizeCell(cell) {
    const isObjectCell = cell && typeof cell === 'object' && !Array.isArray(cell);
    if (!isObjectCell) {
        return {
            text: cell == null ? '' : String(cell),
            colspan: 1,
            rowspan: 1
        };
    }
    const rawColspan = parseInt(cell.colspan, 10);
    const rawRowspan = parseInt(cell.rowspan, 10);
    return {
        text: cell.text == null ? '' : String(cell.text),
        colspan: Number.isFinite(rawColspan) && rawColspan > 0 ? rawColspan : 1,
        rowspan: Number.isFinite(rawRowspan) && rawRowspan > 0 ? rawRowspan : 1
    };
}
function getCellText(cell) {
    return normalizeCell(cell).text;
}
function buildCssRowsHtml(rows, tdStyle, trEvenStyle, trOddStyle) {
    const activeRowspans = [];
    return (Array.isArray(rows) ? rows : []).map((row, ri) => {
        const trStyle = (ri % 2 === 0 ? trEvenStyle : trOddStyle) || '';
        const rowArr = Array.isArray(row) ? row : [];
        let colCursor = 0;
        let tds = '';
        rowArr.forEach((rawCell) => {
            while ((activeRowspans[colCursor] || 0) > 0) colCursor += 1;
            const cell = normalizeCell(rawCell);
            const attrs = [];
            if (cell.colspan > 1) attrs.push(`colspan="${cell.colspan}"`);
            if (cell.rowspan > 1) attrs.push(`rowspan="${cell.rowspan}"`);
            const styleAttr = tdStyle ? ` style="${tdStyle}"` : '';
            const extraAttrs = attrs.length > 0 ? ` ${attrs.join(' ')}` : '';
            tds += `<td${styleAttr}${extraAttrs}>${cell.text}</td>`;
            if (cell.rowspan > 1) {
                for (let i = 0; i < cell.colspan; i += 1) {
                    const idx = colCursor + i;
                    activeRowspans[idx] = Math.max(activeRowspans[idx] || 0, cell.rowspan - 1);
                }
            }
            colCursor += cell.colspan;
        });
        for (let i = 0; i < activeRowspans.length; i += 1) {
            if ((activeRowspans[i] || 0) > 0) activeRowspans[i] -= 1;
        }
        return `<tr style="${trStyle}">${tds}</tr>`;
    }).join('');
}
// 與後端一致的排序與分頁（前端預覽用）
function applySortAndPageForPreview(data) {
    const headers = data?.headers || [];
    let rows = data?.rows || [];
    const sortBy = (document.getElementById('backendSort')?.value || '').trim();
    const sortAsc = !(document.getElementById('backendSortDesc')?.checked);
    const page = Math.max(1, parseInt(document.getElementById('backendPage')?.value || '1', 10));
    const perPage = Math.max(1, Math.min(100, parseInt(document.getElementById('backendPerPage')?.value || '15', 10)));
    if (sortBy && headers.length > 0) {
        const colIdx = headers.findIndex(h => String(h).toLowerCase() === sortBy.toLowerCase());
        if (colIdx >= 0) {
            rows = [...rows].sort((a, b) => {
                const va = getCellText(a[colIdx]);
                const vb = getCellText(b[colIdx]);
                const cmp = va.localeCompare(vb, undefined, { numeric: true });
                return sortAsc ? cmp : -cmp;
            });
        }
    }
    const start = (page - 1) * perPage;
    const pagedRows = rows.slice(start, start + perPage);
    return { ...data, rows: pagedRows };
}
const ASCII_STYLES = {
    single: { tl: "+", tr: "+", bl: "+", br: "+", h: "-", v: "|", header: "+", row: "+", footer: "+" },
    double: { tl: "╔", tr: "╗", bl: "╚", br: "╝", h: "═", v: "║", header: "╠", row: "╠", footer: "╠" },
    grid: { tl: "┌", tr: "┐", bl: "└", br: "┘", h: "─", v: "│", header: "├", row: "├", footer: "├" },
    markdown: { tl: "|", tr: "|", bl: "|", br: "|", h: "-", v: "|", header: "|", row: "|", footer: "|" }
};
function getAsciiBoxChars() {
    const style = (document.getElementById('a_style')?.value || 'double').toLowerCase();
    const base = ASCII_STYLES[style] || ASCII_STYLES.double;
    const out = { ...base };
    ['tl','tr','bl','br','h','v','header','row','footer'].forEach(k => {
        const el = document.getElementById('a_box_' + k);
        const v = el?.value?.trim();
        if (v) out[k] = v.charAt(0);
    });
    return out;
}
function applyAsciiStyleDefaults() {
    const style = (document.getElementById('a_style')?.value || 'double').toLowerCase();
    const base = ASCII_STYLES[style] || ASCII_STYLES.double;
    ['tl','tr','bl','br','h','v','header','row','footer'].forEach(k => {
        const el = document.getElementById('a_box_' + k);
        if (el && !el.value.trim()) el.placeholder = base[k];
    });
}
function generateAscii(data, title) {
    // ASCII table generator，支援 theme 參數（style, padding, align, header_align, border_mode, row_interval, col_interval, 自訂框線）
    let headers, rows;
    if (Array.isArray(data) && data.length > 0) {
        headers = Object.keys(data[0]);
        rows = data.map(row => headers.map(h => row[h] ?? ''));
    } else if (data.headers && data.rows) {
        headers = data.headers;
        rows = data.rows;
    } else {
        return "No Data";
    }
    if (headers.length === 0) return "No Data";
    const pad = Math.max(0, parseInt(document.getElementById('a_padding_num')?.value || document.getElementById('a_padding')?.value || '2', 10));
    const align = document.getElementById('a_align')?.value || 'center';
    const headerAlign = document.getElementById('a_header_align')?.value || 'center';
    const borderMode = (document.getElementById('a_border_mode')?.value || 'full').toLowerCase();
    const rowInterval = Math.max(1, Math.min(20, parseInt(document.getElementById('a_row_interval')?.value || '5', 10)));
    const colInterval = Math.max(1, Math.min(10, parseInt(document.getElementById('a_col_interval')?.value || '1', 10)));
    const cellPadLeft = Math.max(0, Math.min(8, parseInt(document.getElementById('a_cell_pad_left')?.value || '1', 10)));
    const cellPadRight = Math.max(0, Math.min(8, parseInt(document.getElementById('a_cell_pad_right')?.value || '1', 10)));
    const box = getAsciiBoxChars();
    const joinCellsColInterval = (cells, vChar) => {
        if (colInterval <= 1) return vChar + cells.join(vChar) + vChar;
        const parts = [];
        for (let i = 0; i < cells.length; i += colInterval) {
            parts.push(cells.slice(i, i + colInterval).join(' '));
        }
        return vChar + parts.join(vChar) + vChar;
    };
    const colWidths = headers.map(h => Math.max(h.length, ...rows.map(row => String(row[headers.indexOf(h)] || '').length)));
    const cellWidths = colWidths.map(w => w + pad*2);
    const alignCell = (txt, w, a) => {
        const s = String(txt || '');
        const len = s.length;
        if (len >= w) return s.slice(0,w);
        const padLen = w - len;
        if (a === 'right') return ' '.repeat(padLen) + s;
        if (a === 'center') return ' '.repeat(Math.floor(padLen/2)) + s + ' '.repeat(padLen - Math.floor(padLen/2));
        return s + ' '.repeat(padLen);
    };
    const totalWidth = cellWidths.reduce((a,b)=>a+b,0) + cellWidths.length - 1 + 4;
    const delim = '  ';
    // --- border_mode: none ---
    if (borderMode === 'none') {
        const lines = [];
        if (title) lines.push(alignCell(title, totalWidth - 2, 'center'));
        if (headers.length) {
            lines.push(headers.map((h,i)=>alignCell(h, cellWidths[i], headerAlign)).join(delim).trim());
            lines.push('-'.repeat(totalWidth));
        }
        rows.forEach(row => lines.push(row.map((cell,i)=>alignCell(cell, cellWidths[i], align)).join(delim).trim()));
        if (data.footer) lines.push('', alignCell(data.footer, totalWidth - 2, 'center'));
        return lines.join('\n');
    }
    // --- border_mode: full 或 sparse ---
    const sepCells = cellWidths.map(w => box.h.repeat(w + cellPadLeft + cellPadRight));
    const buildSepLine = () => {
        if (colInterval <= 1) return box.header + sepCells.join(box.header) + box.header;
        const parts = [];
        for (let i = 0; i < sepCells.length; i += colInterval) {
            parts.push(sepCells.slice(i, i + colInterval).join(box.h));
        }
        return box.header + parts.join(box.header) + box.header;
    };
    const headerCells = headers.map((h, i) => ' '.repeat(cellPadLeft) + alignCell(h, cellWidths[i], headerAlign) + ' '.repeat(cellPadRight));
    const headerRow = joinCellsColInterval(headerCells, box.v);
    const rowWidth = headerRow.length;
    const sep = box.tl + box.h.repeat(Math.max(0, rowWidth - 2)) + box.tr;
    const headerSep = buildSepLine();
    const bottom = box.bl + box.h.repeat(Math.max(0, rowWidth - 2)) + box.br;
    let result = [sep, headerRow, headerSep];
    rows.forEach((row, idx) => {
        const cells = row.map((cell, i) => ' '.repeat(cellPadLeft) + alignCell(cell, cellWidths[i], align) + ' '.repeat(cellPadRight));
        result.push(joinCellsColInterval(cells, box.v));
        if (borderMode === 'sparse' && idx < rows.length - 1 && (idx + 1) % rowInterval === 0)
            result.push(headerSep);
    });
    result.push(bottom);
    if (title) {
        const titleW = Math.max(4, rowWidth - 6);
        result.unshift(box.tl + box.h.repeat(2) + ' ' + alignCell(title, titleW, 'center') + ' ' + box.h.repeat(2) + box.tr);
    }
    return result.join('\n');
}

async function updatePreview() {
    const view = document.getElementById('view-frontend');
    let rawData;
    try { rawData = JSON.parse(document.getElementById('dataJson').value); } catch(e) { view.innerHTML = '<div class="error">JSON Error</div>'; return; }
    const title = document.getElementById('tableTitle').value;
    const footerEl = document.getElementById('tableFooter');
    const footer = footerEl ? footerEl.value : '';
    
    // Convert array of objects to {headers, rows} format
    let data = rawData;
    if (Array.isArray(rawData) && rawData.length > 0) {
        const headers = Object.keys(rawData[0]);
        const rows = rawData.map(row => headers.map(h => row[h] ?? ''));
        data = { title: title, headers: headers, rows: rows, footer: footer };
    } else if (data && typeof data === 'object' && !Array.isArray(data)) {
        data = { ...data, title: title, footer: footer };
    }
    
    // 確保已載入 theme template；selector 模式時從 inputs 組裝
    if (currentMode === 'css' && cssEditMode === 'selector') buildCssTemplateFromSelectors();
    if (!currentThemeTemplate) {
        await loadThemeTemplate(currentTheme);
    }
    const template = currentThemeTemplate;
    
    if (currentMode === 'ascii') {
        const gridCfgRaw = document.getElementById('a_grid_config')?.value?.trim();
        if (gridCfgRaw) {
            // grid_config 啟用：改用後端渲染預覽（前端 generateAscii 不支援 grid_config）
            const dataToSend = { ...data, title, footer };
            const formData = new FormData();
            formData.append('data', JSON.stringify(dataToSend));
            formData.append('theme', currentTheme);
            const pageEl = document.getElementById('backendPage');
            const perPageEl = document.getElementById('backendPerPage');
            const sortEl = document.getElementById('backendSort');
            const descEl = document.getElementById('backendSortDesc');
            if (pageEl?.value && pageEl.value !== '1') formData.append('page', pageEl.value);
            if (perPageEl?.value && perPageEl.value !== '15') formData.append('per_page', perPageEl.value);
            if (sortEl?.value?.trim()) formData.append('sort', sortEl.value.trim());
            if (descEl?.checked) formData.append('desc', '1');
            formData.append('style', document.getElementById('a_style')?.value || 'grid');
            formData.append('padding', document.getElementById('a_padding_num')?.value || document.getElementById('a_padding')?.value || '2');
            formData.append('align', document.getElementById('a_align')?.value || 'center');
            const aHeaderAlign = document.getElementById('a_header_align');
            if (aHeaderAlign) formData.append('header_align', aHeaderAlign.value);
            formData.append('border_mode', document.getElementById('a_border_mode')?.value || 'full');
            formData.append('row_interval', document.getElementById('a_row_interval')?.value || '5');
            formData.append('col_interval', document.getElementById('a_col_interval')?.value || '1');
            formData.append('cell_pad_left', document.getElementById('a_cell_pad_left')?.value || '1');
            formData.append('cell_pad_right', document.getElementById('a_cell_pad_right')?.value || '1');
            ['tl','tr','bl','br','h','v','header','row','footer'].forEach(k => {
                const v = document.getElementById('a_box_' + k)?.value?.trim();
                if (v) formData.append('box_' + k, v);
            });
            formData.append('grid_config', gridCfgRaw);
            try {
                const res = await fetch('gentable_ascii.php', { method: 'POST', body: formData }).then(r => r.json());
                if (res.success && res.text) {
                    view.innerHTML = '<pre class="preview-code" style="color:#90ee90;">' + res.text + '</pre>';
                    return;
                }
            } catch (e) {}
        }
        const asciiData = applySortAndPageForPreview(data);
        const ascii = generateAscii(asciiData, title);
        view.innerHTML = '<pre class="preview-code" style="color:#90ee90;">' + ascii + '</pre>';
        return;
    }
    
    if (currentMode === 'pil') {
        // PIL Preview: Show placeholder with actual parameters from template
        const params = template?.params || {};
        const getVal = (id, def) => {
            const el = document.getElementById(id);
            return el ? el.value : def;
        };
        view.innerHTML = `
            <div style="padding:40px; background:${params.bg_color || '#1a1a2e'}; color:${params.text_color || '#fff'}; border-radius:8px; border:2px dashed ${params.header_text || '#e94560'}; text-align:center;">
                <div style="font-size:48px; margin-bottom:10px;">🎨</div>
                <div style="font-size:18px; color:${params.header_text || '#e94560'}; font-weight:bold;">PIL Preview</div>
                <div style="margin-top:10px; font-size:12px; opacity:0.7;">Click "Render Backend" to generate real image</div>
                <div style="margin-top:20px; text-align:left; background:rgba(0,0,0,0.3); padding:10px; border-radius:4px; font-family:monospace; font-size:13px;">
                    <div><strong>bg_color:</strong> ${getVal('p_bg_color', params.bg_color)}</div>
                    <div><strong>text_color:</strong> ${getVal('p_text_color', params.text_color)}</div>
                    <div><strong>header_text:</strong> ${getVal('p_header_text', params.header_text)}</div>
                    <div><strong>font_size:</strong> ${getVal('p_font_size', params.font_size)}</div>
                    <div><strong>header_font_size:</strong> ${getVal('p_header_font_size', params.header_font_size)}</div>
                    <div><strong>row_height:</strong> ${getVal('p_row_height', params.row_height)}</div>
                    <div><strong>cell_align:</strong> ${getVal('p_cell_align', params.cell_align)}</div>
                </div>
            </div>
        `;
        return;
    }
    
    // CSS mode: 使用與後端 generate_css_html 完全一致的 CSS class 結構渲染
    const cssData = applySortAndPageForPreview(data);
    if (template && template.styles) {
        const styles = template.styles;
        const fontList = getFontsFromTheme(template).frontend;
        const fontFaceCss = getPreviewFontFaceCss(fontList);
        const estW = Math.max(400, template ? estimateTableWidthPx(cssData, template) : 600);
        const mult = Math.max(0.9, Math.min(1.3, parseFloat(document.getElementById('previewWidthMult')?.value || '1.08') || 1.08));
        const previewMaxW = Math.ceil(estW * mult);
        const rwRaw = document.getElementById('renderWidth')?.value || '';
        const forceWidth = (rwRaw && parseInt(rwRaw, 10) > 0) ? parseInt(rwRaw, 10) : null;
        // 跟後端一致：有 --width 但未指定 --fill-width 時，預設走 container
        const rfwRaw = (document.getElementById('renderFillWidth')?.value || '').trim();
        const fillWidthMethod = (rfwRaw || 'container');
        let previewWrapWidth = previewMaxW;
        // 與後端 generate_css_html 一致的 CSS selector 映射（body 轉成 .zt-body 因為前端無真 <body>）
        const TAG_SELECTORS_PREVIEW = new Set(['table','thead','tbody','tr','th','td']);
        function cssSelectorPreview(key) {
            if (key === 'body') return '.zt-body';
            if (key === '.header' || key === 'header') return '.title';
            if (key === '.cell-header' || key === 'cell-header') return 'th';
            if (key === '.cell' || key === 'cell') return 'td';
            if (key.startsWith('.')) return key;
            if (TAG_SELECTORS_PREVIEW.has(key)) return key;
            if (key === 'tbody_tr') return 'tbody tr';
            if (key === 'tr_even') return 'tr.tr_even';
            if (key === 'tr_odd') return 'tr.tr_odd';
            if (key.includes(':nth-child') || (key.includes(',') && key.includes(':'))) return key;
            if (/^col_\d+$/.test(key)) { const n = key.slice(4); return `th:nth-child(${n}), td:nth-child(${n})`; }
            return '.' + key;
        }
        // 組合完整 CSS（與後端 generate_css_html 對應，加上 .zt-scope 限定不影響頁面其他元素）
        const scope = '.zt-scope';
        let themeCss = `${scope} * { box-sizing: border-box; }\n`;
        Object.entries(styles).forEach(([k, v]) => {
            const sel = cssSelectorPreview(k);
            themeCss += `${scope} ${sel} {${v}}\n`;
        });
        // 與後端一致的基礎字體、字重（body 樣式中的 font-family 會覆蓋此預設）
        themeCss += `${scope} .zt-body { font-weight: 400; -webkit-font-smoothing: antialiased; }\n`;
        themeCss += `${scope} table, ${scope} .data-table { border-collapse: collapse !important; }\n`;
        themeCss += `${scope} td { white-space: pre-wrap !important; }\n`;
        themeCss += `${scope} th { font-weight: 600; }\n`;
        // container 寬度：主題未指定時用 fit-content（與後端一致）
        const _cs = styles.container || styles['.container'] || '';
        if (!/(?:^|;\s*)(?:width|min-width)\s*:\s*\d/i.test(_cs)) {
            themeCss += `${scope} .container { width: fit-content !important; max-width: 100%; }\n`;
        }
        themeCss += `${scope} table { table-layout: auto; }\n`;
        // 前端預覽套用進階寬度參數（--width/--fill-width）以對齊後端寬度行為
        if (forceWidth) {
            previewWrapWidth = forceWidth;
            if (fillWidthMethod === 'container') {
                themeCss += `${scope} .container { width: 95% !important; max-width: 96% !important; margin: 0 auto; box-sizing: border-box; }\n`;
                themeCss += `${scope} table { width: 100% !important; table-layout: auto; }\n`;
            }
        }
        // 斑馬紋 rows（與後端 build_css_rows_html 一致，用 class 而非 inline style）
        function buildCssClassRows(rows, headers) {
            let out = '';
            (Array.isArray(rows) ? rows : []).forEach((row, ri) => {
                const rowClass = ri % 2 === 0 ? 'tr_even' : 'tr_odd';
                const rowArr = Array.isArray(row) ? row : [];
                let tds = '';
                rowArr.forEach(rawCell => {
                    const cell = normalizeCell(rawCell);
                    const attrs = [];
                    if (cell.colspan > 1) attrs.push(`colspan="${cell.colspan}"`);
                    if (cell.rowspan > 1) attrs.push(`rowspan="${cell.rowspan}"`);
                    tds += `<td${attrs.length ? ' ' + attrs.join(' ') : ''}>${cell.text}</td>`;
                });
                out += `<tr class="row ${rowClass}">${tds}</tr>`;
            });
            return out;
        }
        const headersHtml = (cssData.headers||[]).map(h => `<th>${h}</th>`).join('');
        const rowsHtml = buildCssClassRows(cssData.rows, cssData.headers);
        const hasTableWrapper = !!(styles['.table-wrapper'] || styles['table-wrapper']);
        let html = `<style>${fontFaceCss || ''}${themeCss}</style>`;
        html += `<div class="preview-table-wrap zt-scope" style="width:${previewWrapWidth}px; max-width:100%; margin:0 auto; min-width:0;">`;
        html += `<div class="zt-body">`;
        html += `<div class="container">`;
        if (title) html += `<div class="title">${title}</div>`;
        if (hasTableWrapper) html += `<div class="table-wrapper">`;
        html += `<table class="data-table">`;
        if (cssData.headers && cssData.headers.length > 0) {
            html += `<thead><tr>${headersHtml}</tr></thead>`;
            html += `<tbody>${rowsHtml}</tbody>`;
        }
        html += `</table>`;
        if (hasTableWrapper) html += `</div>`;
        if (footer) html += `<div class="footer">${footer}</div>`;
        html += `</div></div></div>`;
        view.innerHTML = html;
    } else {
        const estW = Math.max(400, template ? estimateTableWidthPx(cssData, template) : 600);
        const mult = Math.max(0.9, Math.min(1.3, parseFloat(document.getElementById('previewWidthMult')?.value || '1.08') || 1.08));
        const previewMaxW = Math.ceil(estW * mult);
        view.innerHTML = '<div class="error" style="padding:20px;">主題載入失敗，請選擇其他主題或檢查 theme_api。<br>使用簡化預覽：</div>' +
            `<div class="preview-table-wrap" style="width:${previewMaxW}px; max-width:100%; margin:0 auto; min-width:0;">` +
            '<div style="background:#1a1a2e;color:#fff;padding:20px;border-radius:8px;width:100%"><div style="color:#e94560;font-weight:bold;margin-bottom:12px;">' + title + '</div>' +
            '<table style="width:100%;border-collapse:collapse;">' +
            (cssData.headers && cssData.headers.length ? '<thead><tr>' + cssData.headers.map(h => '<th style="padding:8px;color:#e94560;">' + h + '</th>').join('') + '</tr></thead><tbody>' +
            buildCssRowsHtml(cssData.rows, 'padding:8px; white-space: pre-wrap;', '', '') + '</tbody>' : '') +
            '</table></div></div>';
    }
    if (currentMode === 'css') updateFontDetection();
}
function renderBackend() {
    setPreviewTab('backend');
    const backendView = document.getElementById('backendImage');
    backendView.innerHTML = '<div class="loading">Rendering...</div>';
    
    // Convert data to proper format before sending
    let rawData;
    try { rawData = JSON.parse(document.getElementById('dataJson').value); } catch(e) { 
        backendView.innerHTML = '<div class="error">Invalid JSON data</div>'; 
        return; 
    }
    
    const title = document.getElementById('tableTitle').value;
    const footerEl = document.getElementById('tableFooter');
    const footer = footerEl ? footerEl.value : '';
    let dataToSend;
    if (Array.isArray(rawData) && rawData.length > 0) {
        const headers = Object.keys(rawData[0]);
        const rows = rawData.map(row => headers.map(h => row[h] ?? ''));
        dataToSend = { title: title, headers: headers, rows: rows, footer: footer };
    } else {
        dataToSend = { ...rawData, title: title, footer: footer };
    }
    
    const formData = new FormData();
    formData.append('data', JSON.stringify(dataToSend));
    formData.append('theme', currentTheme);
    const pageEl = document.getElementById('backendPage');
    const sortEl = document.getElementById('backendSort');
    const descEl = document.getElementById('backendSortDesc');
    if (pageEl && pageEl.value && pageEl.value !== '1') formData.append('page', pageEl.value);
    const perPageEl = document.getElementById('backendPerPage');
    if (perPageEl && perPageEl.value && perPageEl.value !== '15') formData.append('per_page', perPageEl.value);
    if (sortEl && sortEl.value.trim()) formData.append('sort', sortEl.value.trim());
    if (descEl && descEl.checked) formData.append('desc', '1');
    formData.append('mode', currentMode);
    
    let endpoint = 'gentable_pil.php';
    if (currentMode === 'css') endpoint = 'gentable_css.php';
    if (currentMode === 'ascii') endpoint = 'gentable_ascii.php';
    updateCommandPreview(dataToSend, endpoint);
    
    if (currentMode === 'pil') {
        ['bg_color','text_color','header_bg','header_text','alt_row_color','border_color','font_size','header_font_size','title_font_size','footer_font_size','padding','cell_padding','row_height','header_height','title_height','border_radius','border_width','shadow_color','shadow_offset','shadow_blur','shadow_opacity','title_padding','footer_padding','line_spacing','cell_align','header_align'].forEach(k => {
            const el = document.getElementById('p_' + k);
            if (el && el.value) formData.append(k, el.value);
        });
        const fontFamilyEl = document.getElementById('p_font_family');
        if (fontFamilyEl && fontFamilyEl.value.trim()) formData.append('font_family', fontFamilyEl.value.trim());
        // Watermark parameters
        const wmEnabled = document.getElementById('p_watermark_enabled');
        const wmText = document.getElementById('p_watermark_text');
        const wmOpacity = document.getElementById('p_watermark_opacity');
        if (wmEnabled && wmEnabled.checked) {
            formData.append('watermark_enabled', 'true');
            if (wmText) formData.append('watermark_text', wmText.value);
            if (wmOpacity) formData.append('watermark_opacity', wmOpacity.value);
        }
    }
    if (currentMode === 'ascii') {
        formData.append('style', document.getElementById('a_style').value);
        formData.append('padding', document.getElementById('a_padding_num')?.value || document.getElementById('a_padding').value);
        formData.append('align', document.getElementById('a_align').value);
        const aHeaderAlign = document.getElementById('a_header_align');
        if (aHeaderAlign) formData.append('header_align', aHeaderAlign.value);
        ['tl','tr','bl','br','h','v','header','row','footer'].forEach(k => {
            const v = document.getElementById('a_box_' + k)?.value?.trim();
            if (v) formData.append('box_' + k, v);
        });
        formData.append('border_mode', document.getElementById('a_border_mode')?.value || 'full');
        formData.append('row_interval', document.getElementById('a_row_interval')?.value || '5');
        formData.append('col_interval', document.getElementById('a_col_interval')?.value || '1');
        formData.append('cell_pad_left', document.getElementById('a_cell_pad_left')?.value || '1');
        formData.append('cell_pad_right', document.getElementById('a_cell_pad_right')?.value || '1');
        const gridCfgRaw = document.getElementById('a_grid_config')?.value?.trim();
        if (gridCfgRaw) {
            try {
                formData.append('grid_config', gridCfgRaw);
            } catch (e) {}
        }
        formData.append('ascii_debug', '1');
        const calObj = getMergedCalibrationWithPriority();
        if (calObj === null) {
            backendView.innerHTML = '<div class="error">校準 JSON 解析失敗，請檢查格式</div>';
            return;
        }
        if (calObj && Object.keys(calObj).length > 0) {
            formData.append('calibration', JSON.stringify(calObj));
        }
        const stage1PilEnabledEl = document.getElementById('backendStage1PilPreviewEnabled');
        if (stage1PilEnabledEl && stage1PilEnabledEl.checked) {
            formData.append('stage1_pil_preview', '1');
        }
        const stage1UnitPxEl = document.getElementById('backendStage1UnitPx');
        if (stage1UnitPxEl) {
            const unitPx = Math.max(5, Math.min(30, parseInt(stage1UnitPxEl.value || '10', 10) || 10));
            formData.append('stage1_unit_px', String(unitPx));
        }
    }
    if (currentMode === 'css') {
        const cssTransparent = document.getElementById('cssTransparent');
        if (cssTransparent && cssTransparent.checked) formData.append('transparent', '1');
        const themeJson = getCssThemeJson?.();
        if (themeJson) formData.append('theme_json', themeJson);
    }
    // Advanced render options (--width, --scale, --fill-width, --bg)
    const rw = document.getElementById('renderWidth');
    if (rw && rw.value && parseInt(rw.value, 10) > 0) formData.append('width', rw.value);
    const rs = document.getElementById('renderScale');
    if (rs && rs.value && parseFloat(rs.value) !== 1) formData.append('scale', rs.value);
    const rfw = document.getElementById('renderFillWidth');
    if (rfw && rfw.value) formData.append('fill_width', rfw.value);
    const rbg = document.getElementById('renderBg');
    if (rbg && rbg.value.trim()) formData.append('bg', rbg.value.trim());
    // text-scale (CSS only)
    if (currentMode === 'css') {
        const rts = document.getElementById('renderTextScale');
        if (rts && rts.value.trim()) formData.append('text_scale', rts.value.trim());
        const rtsm = document.getElementById('renderTextScaleMax');
        if (rtsm && rtsm.value && parseFloat(rtsm.value) !== 2.5) formData.append('text_scale_max', rtsm.value);
    }
    
    fetch(endpoint, { method: 'POST', body: formData })
        .then(r => r.json())
        .then(res => {
            if (res.success) {
                if (res.image) {
                    backendView.innerHTML = `<div class="backend-img-wrap" id="backendImgWrap"><img src="${res.image}?t=${Date.now()}" /></div>`;
                    document.getElementById('backendAscii').classList.add('hidden');
                    document.getElementById('backendAsciiDebugWrap').classList.add('hidden');
                    window.__backendStage3Details = null;
                    applyBackendPreviewBg(document.getElementById('backendPreviewBgColor').value);
                } else if (res.text) {
                    backendView.innerHTML = '';
                    const asciiPre = document.getElementById('backendAscii');
                    const debugWrap = document.getElementById('backendAsciiDebugWrap');
                    if (res.debug && res.stage1 != null) {
                        asciiPre.classList.add('hidden');
                        debugWrap.classList.remove('hidden');
                        document.getElementById('backendAsciiStage1').innerText = res.stage1 || '';
                        document.getElementById('backendAsciiStage2').innerText = res.stage2 || '';
                        const stage1PilWrap = document.getElementById('backendAsciiStage1PilWrap');
                        const stage1PilImg = document.getElementById('backendAsciiStage1PilImg');
                        const stage1PilWarning = document.getElementById('backendAsciiStage1PilWarning');
                        if (stage1PilWrap && stage1PilImg) {
                            if (res.stage1_pil_image) {
                                stage1PilImg.src = `${res.stage1_pil_image}?t=${Date.now()}`;
                                stage1PilWrap.classList.remove('hidden');
                            } else {
                                stage1PilImg.src = '';
                                stage1PilWrap.classList.add('hidden');
                            }
                        }
                        if (stage1PilWarning) {
                            if (res.stage1_pil_warning) {
                                stage1PilWarning.textContent = `版面格式化 PIL: ${res.stage1_pil_warning}`;
                                stage1PilWarning.classList.remove('hidden');
                            } else {
                                stage1PilWarning.textContent = '';
                                stage1PilWarning.classList.add('hidden');
                            }
                        }
                        window.__backendStage3Details = res.stage3_details || null;
                        const stage3El = document.getElementById('backendAsciiStage3Text');
                        if (stage3El) {
                            setBackendStage3Text(res.text || '', 'render', true);
                        }
                        // 校準輸出預設展開
                        const outputStageEl = document.getElementById('backendOutputStageCollapsible');
                        if (outputStageEl && outputStageEl.classList.contains('collapsed')) {
                            outputStageEl.classList.remove('collapsed');
                            const content = outputStageEl.querySelector('.collapsible-content');
                            if (content) content.style.display = 'block';
                        }
                    } else {
                        window.__backendStage3Details = null;
                        debugWrap.classList.add('hidden');
                        asciiPre.classList.remove('hidden');
                        asciiPre.innerText = res.text;
                        const stage1PilWrap = document.getElementById('backendAsciiStage1PilWrap');
                        const stage1PilWarning = document.getElementById('backendAsciiStage1PilWarning');
                        const stage1PilImg = document.getElementById('backendAsciiStage1PilImg');
                        if (stage1PilWrap) stage1PilWrap.classList.add('hidden');
                        if (stage1PilImg) stage1PilImg.src = '';
                        if (stage1PilWarning) {
                            stage1PilWarning.textContent = '';
                            stage1PilWarning.classList.add('hidden');
                        }
                    }
                }
            } else {
                backendView.innerHTML = `<div class="error">Error: ${res.error}<br><pre>${res.debug || ''}</pre></div>`;
            }
        })
        .catch(e => { backendView.innerHTML = `<div class="error">Request Failed: ${e.message}</div>`; });
}

function applyBackendPreviewBg(color) {
    const wrap = document.getElementById('backendImgWrap') || document.querySelector('#backendImage .backend-img-wrap');
    if (wrap) {
        wrap.style.backgroundColor = color || '#e8e8e8';
        wrap.style.backgroundImage = 'none';
    }
}

function updateCommandPreview(dataToSend, endpoint) {
    const base = window.location.origin + (window.location.pathname.replace(/[^/]+$/, '') || '/');
    const dataStr = JSON.stringify(dataToSend);
    const theme = currentTheme;
    let cli = '# 1. Save table data to data.json, then run:\n';
    if (currentMode === 'css') {
        cli += `python3 zentable_renderer.py data.json output.png --force-css --theme-name ${theme}\n`;
    } else if (currentMode === 'pil') {
        cli += `python3 zentable_renderer.py data.json output.png --force-pil --theme-name ${theme}\n`;
    } else {
        cli += `python3 zentable_renderer.py data.json output.txt --force-ascii --output-ascii output.txt\n`;
    }

    // Advanced render options preview (best-effort)
    try {
        const rw = document.getElementById('renderWidth')?.value || '';
        const rts = document.getElementById('renderTextScale')?.value || '';
        const rtsm = document.getElementById('renderTextScaleMax')?.value || '';
        const rs = document.getElementById('renderScale')?.value || '';
        const rfw = document.getElementById('renderFillWidth')?.value || '';
        const rbg = document.getElementById('renderBg')?.value || '';
        let adv = '';
        if (rw && parseInt(rw, 10) > 0) adv += ` --width ${parseInt(rw, 10)}`;
        if (currentMode === 'css' && rts.trim()) adv += ` --text-scale ${rts.trim()}`;
        if (currentMode === 'css' && rtsm && parseFloat(rtsm) !== 2.5) adv += ` --text-scale-max ${parseFloat(rtsm)}`;
        if (rs && parseFloat(rs) !== 1) adv += ` --scale ${parseFloat(rs)}`;
        if (rfw) adv += ` --fill-width ${rfw}`;
        if (currentMode === 'css' && rbg.trim()) adv += ` --bg ${rbg.trim()}`;
        if (adv) cli = cli.replace(/\n$/, '') + adv + '\n';
    } catch (e) {}
    cli += '\n# 2. Or POST via curl:\n';
    cli += `curl -X POST "${base}${endpoint}" -d "data=${encodeURIComponent(dataStr).substring(0, 200)}..." -d "theme=${theme}" -d "mode=${currentMode}"\n`;
    const pre = document.getElementById('cmdOutput');
    pre.innerText = cli;
    pre.dataset.copyText = cli;
}
function copyCommand() {
    const pre = document.getElementById('cmdOutput');
    const text = pre.dataset.copyText || pre.innerText;
    if (navigator.clipboard && navigator.clipboard.writeText) {
        navigator.clipboard.writeText(text).then(() => alert('Copied to clipboard')).catch(() => {});
    } else {
        const ta = document.createElement('textarea');
        ta.value = text;
        document.body.appendChild(ta);
        ta.select();
        document.execCommand('copy');
        document.body.removeChild(ta);
        alert('Copied to clipboard');
    }
}
async function exportAllThemes() {
    try {
        const r = await fetch('theme_api.php?action=export-all');
        const ct = r.headers.get('Content-Type') || '';
        if (ct.includes('application/json')) {
            const data = await r.json();
            alert(data.error || 'Export failed');
            return;
        }
        const blob = await r.blob();
        const cd = r.headers.get('Content-Disposition');
        let filename = 'themes_full.zip';
        if (cd && cd.includes('filename=')) filename = cd.split('filename=')[1].replace(/"/g, '').trim();
        const a = document.createElement('a');
        a.href = URL.createObjectURL(blob);
        a.download = filename;
        a.click();
        URL.revokeObjectURL(a.href);
    } catch (e) { alert('Export failed: ' + e.message); }
}
function importZipFile(input) {
    const file = input?.files?.[0];
    if (!file) return;
    const form = new FormData();
    form.append('action', 'import');
    form.append('zip_file', file);
    form.append('mode', currentMode === 'ascii' ? 'text' : currentMode);
    fetch('theme_api.php', { method: 'POST', body: form })
        .then(r => r.json())
        .then(res => {
            if (res.success) { alert('Imported ' + (res.imported || 0) + ' theme(s).' + (res.errors?.length ? '\nErrors: ' + res.errors.join(', ') : '')); loadThemesFromApi().then(() => renderThemeList()); }
            else alert('Import failed: ' + (res.error || ''));
        })
        .catch(e => alert('Import failed: ' + e.message));
    input.value = '';
}
function getCssThemeJson() {
    if (cssEditMode === 'selector') {
        buildCssTemplateFromSelectors();
        return JSON.stringify(currentThemeTemplate);
    }
    return document.getElementById('cssThemeJson').value;
}
function exportTheme() {
    let themeJson = '';
    const modeParam = currentMode === 'ascii' ? 'text' : currentMode;
    if (currentMode === 'css') {
        themeJson = getCssThemeJson();
    } else if (currentMode === 'pil') {
        const params = {};
        ['bg_color','text_color','header_bg','header_text','alt_row_color','border_color','font_size','header_font_size','title_font_size','footer_font_size','padding','cell_padding','row_height','header_height','title_height','border_radius','border_width','shadow_color','shadow_offset','shadow_blur','shadow_opacity','title_padding','footer_padding','line_spacing','cell_align','header_align'].forEach(k => {
            const el = document.getElementById('p_' + k);
            if (el && el.value) params[k] = el.value;
        });
        const fontFamilyEl = document.getElementById('p_font_family');
        if (fontFamilyEl && fontFamilyEl.value.trim()) params.font_family = fontFamilyEl.value.trim();
        const wmEnabled = document.getElementById('p_watermark_enabled');
        const wmText = document.getElementById('p_watermark_text');
        const wmOpacity = document.getElementById('p_watermark_opacity');
        const watermark = { enabled: wmEnabled && wmEnabled.checked, text: wmText ? wmText.value : 'Generated by ZenTable', opacity: wmOpacity ? parseFloat(wmOpacity.value) : 0.5 };
        themeJson = JSON.stringify({ type: 'pil', name: currentTheme, version: '1.0.0', params: params, watermark: watermark });
    } else {
        const params = {
            style: document.getElementById('a_style')?.value || 'double',
            padding: parseInt(document.getElementById('a_padding_num')?.value || document.getElementById('a_padding')?.value || '2', 10),
            align: document.getElementById('a_align')?.value || 'center',
            header_align: document.getElementById('a_header_align')?.value || 'center',
            row_interval: Math.max(1, parseInt(document.getElementById('a_row_interval')?.value || '5', 10)),
            col_interval: Math.max(1, parseInt(document.getElementById('a_col_interval')?.value || '1', 10)),
            cell_pad_left: Math.max(0, parseInt(document.getElementById('a_cell_pad_left')?.value || '1', 10)),
            cell_pad_right: Math.max(0, parseInt(document.getElementById('a_cell_pad_right')?.value || '1', 10))
        };
        ['tl','tr','bl','br','h','v','header','row','footer'].forEach(k => {
            const v = document.getElementById('a_box_' + k)?.value?.trim();
            if (v) params['box_' + k] = v;
        });
        const gridCfgRaw = document.getElementById('a_grid_config')?.value?.trim();
        if (gridCfgRaw) {
            try { params.grid_config = JSON.parse(gridCfgRaw); } catch (e) {}
        }
        themeJson = JSON.stringify({ type: 'text', name: currentTheme, version: '1.0.0', params });
    }
    const formData = new FormData();
    formData.append('theme_name', currentTheme + '_export');
    formData.append('mode', modeParam);
    formData.append('theme_json', themeJson);
    fetch('gentable_export.php', { method: 'POST', body: formData })
        .then(r => r.json())
        .then(res => {
            if (res.success) {
                const a = document.createElement('a');
                a.href = res.url;
                a.download = res.filename;
                a.click();
            } else {
                alert('Export failed: ' + (res.error || ''));
            }
        });
}
function resetDataOnly() {
    document.getElementById('tableTitle').value = 'Zeble Table';
    const footerEl = document.getElementById('tableFooter');
    if (footerEl) footerEl.value = '';
    loadExample('servers');
    updatePreview();
}
function resetData() { if (confirm('Reset all? (reload page)')) location.reload(); }
function openAddThemeModal() {
    document.getElementById('newThemeId').value = '';
    document.getElementById('newThemeName').value = '';
    document.getElementById('newThemeMode').value = currentMode === 'ascii' ? 'text' : currentMode;
    document.getElementById('addThemeModal').classList.remove('hidden');
}
function closeAddThemeModal() { document.getElementById('addThemeModal').classList.add('hidden'); }
async function doAddTheme() {
    const id = (document.getElementById('newThemeId').value || '').trim().replace(/[^a-zA-Z0-9_-]/g, '');
    const name = (document.getElementById('newThemeName').value || '').trim() || id;
    const mode = document.getElementById('newThemeMode').value;
    if (!id) { alert('Please enter Theme ID'); return; }
    const defaultTemplate = mode === 'css' ? { type: 'css', name, version: '1.0.0', styles: { body: 'background: #1a1a2e; color: #fff; padding: 20px;', title: 'color: #e94560; font-weight: bold;', th: 'color: #e94560; padding: 8px;', td: 'padding: 8px;' } }
        : mode === 'pil' ? { type: 'pil', name, version: '1.0.0', params: { bg_color: '#1a1a2e', text_color: '#fff', header_bg: '#0f3460', header_text: '#e94560' }, watermark: { enabled: true, text: 'Generated by ZenTable', opacity: 0.5 } }
        : { type: 'text', name, version: '1.0.0', params: { style: 'double', padding: 2, align: 'center', header_align: 'center' } };
    const form = new FormData();
    form.append('action', 'save');
    form.append('mode', mode);
    form.append('theme_name', id);
    form.append('theme_json', JSON.stringify(defaultTemplate));
    try {
        const res = await fetch('theme_api.php', { method: 'POST', body: form }).then(r => r.json());
        if (res.success) { closeAddThemeModal(); currentMode = mode === 'text' ? 'ascii' : mode; await setMode(currentMode); currentTheme = id; await loadThemeTemplate(id); await loadThemesFromApi(); renderThemeList(); await updateStyleEditor(); updatePreview(); }
        else alert('Failed: ' + (res.error || ''));
    } catch (e) { alert('Request failed: ' + e.message); }
}
function openCopyThemeModal() {
    document.getElementById('copySourceName').textContent = loadedThemes[currentTheme]?.name || currentTheme;
    document.getElementById('copyThemeId').value = '';
    document.getElementById('copyThemeModal').classList.remove('hidden');
}
function closeCopyThemeModal() { document.getElementById('copyThemeModal').classList.add('hidden'); }
async function doCopyTheme() {
    const newId = (document.getElementById('copyThemeId').value || '').trim().replace(/[^a-zA-Z0-9_-]/g, '');
    if (!newId) { alert('Please enter New Theme ID'); return; }
    if (loadedThemes[newId]) { alert('Theme ID already exists'); return; }
    let template = currentThemeTemplate;
    if (currentMode === 'css' && cssEditMode === 'selector') buildCssTemplateFromSelectors();
    if (!template) { alert('No template to copy'); return; }
    template = { ...template, name: (template.name || currentTheme) + ' (Copy)' };
    const modeParam = currentMode === 'ascii' ? 'text' : currentMode;
    const form = new FormData();
    form.append('action', 'save');
    form.append('mode', modeParam);
    form.append('theme_name', newId);
    form.append('theme_json', JSON.stringify(template));
    try {
        const res = await fetch('theme_api.php', { method: 'POST', body: form }).then(r => r.json());
        if (res.success) { closeCopyThemeModal(); currentTheme = newId; await loadThemesFromApi(); renderThemeList(); await loadThemeTemplate(newId); await updateStyleEditor(); updatePreview(); }
        else alert('Failed: ' + (res.error || ''));
    } catch (e) { alert('Request failed: ' + e.message); }
}
async function confirmDeleteTheme() {
    if (!currentTheme) return;
    if (!confirm('Delete theme "' + (loadedThemes[currentTheme]?.name || currentTheme) + '"? This cannot be undone.')) return;
    const modeParam = currentMode === 'ascii' ? 'text' : currentMode;
    try {
        const res = await fetch('theme_api.php', { method: 'POST', headers: { 'Content-Type': 'application/x-www-form-urlencoded' }, body: new URLSearchParams({ action: 'delete', theme: currentTheme, mode: modeParam }) }).then(r => r.json());
        if (res.success) { const ids = Object.keys(loadedThemes).filter(k => k !== currentTheme); currentTheme = ids[0] || ''; await loadThemesFromApi(); renderThemeList(); await loadThemeTemplate(currentTheme); await updateStyleEditor(); updatePreview(); }
        else alert('Delete failed: ' + (res.error || ''));
    } catch (e) { alert('Request failed: ' + e.message); }
}
function runTableDetect() {
    const ta = document.getElementById('tableDetectInput');
    const resultEl = document.getElementById('tableDetectResult');
    const message = (ta && ta.value) ? ta.value.trim() : '';
    resultEl.innerHTML = 'Detecting...';
    fetch('table_detect_api.php', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: message })
    }).then(r => r.json()).then(res => {
        if (res.success) {
            resultEl.innerHTML = '<strong>needs_table:</strong> ' + res.needs_table + '<br><strong>reason:</strong> ' + (res.reason || '') + '<br><strong>confidence:</strong> ' + (res.confidence != null ? res.confidence : '');
        } else {
            resultEl.innerHTML = 'Error: ' + (res.error || '');
        }
    }).catch(e => { resultEl.innerHTML = 'Request failed: ' + e.message; });
}
function getBuiltThemeJson() {
    if (currentMode === 'css') {
        const raw = getCssThemeJson ? getCssThemeJson() : (currentThemeTemplate ? JSON.stringify(currentThemeTemplate) : '{}');
        try { return JSON.stringify(JSON.parse(raw), null, 2); } catch(e) { return raw; }
    }
    if (currentMode === 'pil') {
        const params = {};
        ['bg_color','text_color','header_bg','header_text','alt_row_color','border_color','font_size','header_font_size','title_font_size','footer_font_size','padding','cell_padding','row_height','header_height','title_height','border_radius','border_width','shadow_color','shadow_offset','shadow_blur','shadow_opacity','title_padding','footer_padding','line_spacing','cell_align','header_align'].forEach(k => {
            const el = document.getElementById('p_' + k);
            if (el && el.value) params[k] = el.value;
        });
        const fontFamilyEl = document.getElementById('p_font_family');
        if (fontFamilyEl && fontFamilyEl.value.trim()) params.font_family = fontFamilyEl.value.trim();
        const wmEnabled = document.getElementById('p_watermark_enabled');
        const wmText = document.getElementById('p_watermark_text');
        const wmOpacity = document.getElementById('p_watermark_opacity');
        return JSON.stringify({ type: 'pil', name: currentTheme, version: '1.0.0', params, watermark: { enabled: wmEnabled && wmEnabled.checked, text: wmText ? wmText.value : '', opacity: wmOpacity ? parseFloat(wmOpacity.value) : 0.5 } }, null, 2);
    }
    if (currentMode === 'ascii') {
        const params = {
            style: document.getElementById('a_style')?.value || 'double',
            padding: parseInt(document.getElementById('a_padding_num')?.value || document.getElementById('a_padding')?.value || '2', 10),
            align: document.getElementById('a_align')?.value || 'center',
            header_align: document.getElementById('a_header_align')?.value || 'center',
            border_mode: document.getElementById('a_border_mode')?.value || 'full',
            row_interval: Math.max(1, parseInt(document.getElementById('a_row_interval')?.value || '5', 10)),
            col_interval: Math.max(1, parseInt(document.getElementById('a_col_interval')?.value || '1', 10)),
            cell_pad_left: Math.max(0, parseInt(document.getElementById('a_cell_pad_left')?.value || '1', 10)),
            cell_pad_right: Math.max(0, parseInt(document.getElementById('a_cell_pad_right')?.value || '1', 10))
        };
        ['tl','tr','bl','br','h','v','header','row','footer'].forEach(k => {
            const v = document.getElementById('a_box_' + k)?.value?.trim();
            if (v) params['box_' + k] = v;
        });
        const gridCfgRaw = document.getElementById('a_grid_config')?.value?.trim();
        if (gridCfgRaw) {
            try { params.grid_config = JSON.parse(gridCfgRaw); } catch (e) {}
        }
        return JSON.stringify({ type: 'text', name: currentTheme, version: '1.0.0', params }, null, 2);
    }
    return currentThemeTemplate ? JSON.stringify(currentThemeTemplate, null, 2) : '{}';
}
function refreshThemeJsonView() {
    const el = document.getElementById('themeJsonContent');
    if (el) el.textContent = getBuiltThemeJson();
}
function validateTemplate(data) {
    if (!data || typeof data !== 'object') return '無效的 template';
    if (!data.name || String(data.name).trim() === '') return '缺少 name 欄位';
    if (currentMode === 'css' && (!data.styles || typeof data.styles !== 'object')) return 'CSS 模式缺少 styles';
    if ((currentMode === 'pil' || currentMode === 'ascii') && (!data.params || typeof data.params !== 'object')) return '此模式缺少 params';
    return null;
}
function openSaveThemeModal() {
    document.getElementById('saveThemeId').value = currentTheme;
    document.getElementById('saveThemeModal').classList.remove('hidden');
}
function closeSaveThemeModal() {
    document.getElementById('saveThemeModal').classList.add('hidden');
}
async function doSaveTheme() {
    const nameInput = document.getElementById('saveThemeId');
    const themeName = (nameInput?.value || '').trim().replace(/[^a-zA-Z0-9_-]/g, '');
    if (!themeName) { alert('請輸入 Theme ID'); return; }
    closeSaveThemeModal();
    await saveThemeToServer(themeName);
}
async function saveThemeToServer(saveAsName) {
    const targetName = saveAsName || currentTheme;
    let themeJson = '';
    const modeParam = currentMode === 'ascii' ? 'text' : currentMode;
    if (currentMode === 'css') {
        themeJson = getCssThemeJson();
    } else if (currentMode === 'pil') {
        const params = {};
        ['bg_color','text_color','header_bg','header_text','alt_row_color','border_color','font_size','header_font_size','title_font_size','footer_font_size','padding','cell_padding','row_height','header_height','title_height','border_radius','border_width','shadow_color','shadow_offset','shadow_blur','shadow_opacity','title_padding','footer_padding','line_spacing','cell_align','header_align'].forEach(k => {
            const el = document.getElementById('p_' + k);
            if (el && el.value) params[k] = el.value;
        });
        const fontFamilyEl = document.getElementById('p_font_family');
        if (fontFamilyEl && fontFamilyEl.value.trim()) params.font_family = fontFamilyEl.value.trim();
        const wmEnabled = document.getElementById('p_watermark_enabled');
        const wmText = document.getElementById('p_watermark_text');
        const wmOpacity = document.getElementById('p_watermark_opacity');
        themeJson = JSON.stringify({ type: 'pil', name: targetName, version: '1.0.0', params: params, watermark: { enabled: wmEnabled && wmEnabled.checked, text: wmText ? wmText.value : '', opacity: wmOpacity ? parseFloat(wmOpacity.value) : 0.5 } });
    } else {
        const params = {
            style: document.getElementById('a_style')?.value || 'double',
            padding: parseInt(document.getElementById('a_padding_num')?.value || document.getElementById('a_padding')?.value || '2', 10),
            align: document.getElementById('a_align')?.value || 'center',
            header_align: document.getElementById('a_header_align')?.value || 'center',
            border_mode: document.getElementById('a_border_mode')?.value || 'full',
            row_interval: Math.max(1, parseInt(document.getElementById('a_row_interval')?.value || '5', 10)),
            col_interval: Math.max(1, parseInt(document.getElementById('a_col_interval')?.value || '1', 10)),
            cell_pad_left: Math.max(0, parseInt(document.getElementById('a_cell_pad_left')?.value || '1', 10)),
            cell_pad_right: Math.max(0, parseInt(document.getElementById('a_cell_pad_right')?.value || '1', 10))
        };
        ['tl','tr','bl','br','h','v','header','row','footer'].forEach(k => {
            const v = document.getElementById('a_box_' + k)?.value?.trim();
            if (v) params['box_' + k] = v;
        });
        const gridCfgRaw = document.getElementById('a_grid_config')?.value?.trim();
        if (gridCfgRaw) {
            try {
                params.grid_config = JSON.parse(gridCfgRaw);
            } catch (e) {}
        }
        themeJson = JSON.stringify({ type: 'text', name: targetName, version: '1.0.0', params });
    }
    let data;
    try { data = JSON.parse(themeJson); } catch(e) { alert('Invalid JSON'); return; }
    const err = validateTemplate(data);
    if (err) { alert('Validation failed: ' + err); return; }
    if (currentMode === 'css') data.name = targetName;
    const form = new FormData();
    form.append('action', 'save');
    form.append('mode', modeParam);
    form.append('theme_name', targetName);
    form.append('theme_json', JSON.stringify(data));
    const res = await fetch('theme_api.php', { method: 'POST', body: form }).then(r => r.json()).catch(e => ({ success: false, error: e.message }));
    alert(res.success ? 'Theme saved.' : 'Save failed: ' + (res.error || ''));
    if (res.success) {
        await loadThemesFromApi();
        renderThemeList();
        if (targetName !== currentTheme) {
            currentTheme = targetName;
            await loadThemeTemplate(currentTheme);
            await updateStyleEditor();
            updatePreview();
        }
    }
}
/* ===== Panel Tab Navigation ===== */
function switchPanelTab(panelId, tabName) {
    const panel = document.getElementById(panelId);
    if (!panel) return;
    panel.querySelectorAll('.panel-tab').forEach(t => {
        t.classList.toggle('active', t.dataset.panel === tabName);
    });
    panel.querySelectorAll('.panel-view').forEach(v => {
        v.classList.toggle('active', v.id === panelId + '-' + tabName);
    });
}

/* ===== System Panel: FastAPI Management ===== */
let fastapiStatus = 'unknown';
let fastapiCheckTimer = null;

async function checkFastapiStatus() {
    const dot = document.querySelector('#fastapiIndicator .dot');
    const label = document.getElementById('fastapiStatusLabel');
    const indicator = document.getElementById('fastapiIndicator');
    try {
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), 2000);
        const port = document.getElementById('fastapiPort')?.value || '8000';
        const res = await fetch(`http://${location.hostname}:${port}/health`, {
            signal: controller.signal
        });
        clearTimeout(timeoutId);
        if (res.ok) {
            fastapiStatus = 'running';
            if (dot) dot.className = 'dot';
            if (indicator) indicator.className = 'running';
            if (label) label.textContent = 'Running';
            updateSystemPanelStatus('running', port);
            return true;
        }
    } catch (e) {
        fastapiStatus = 'stopped';
        if (dot) dot.className = 'dot';
        if (indicator) indicator.className = 'stopped';
        if (label) label.textContent = 'Stopped';
        updateSystemPanelStatus('stopped');
    }
    return false;
}

function updateSystemPanelStatus(status, port) {
    const statusDot = document.getElementById('systemFastapiDot');
    const statusText = document.getElementById('systemFastapiStatus');
    if (!statusDot || !statusText) return;
    if (status === 'running') {
        statusDot.className = 'system-status-dot green';
        statusText.textContent = `Running on port ${port || '8000'}`;
    } else {
        statusDot.className = 'system-status-dot red';
        statusText.textContent = 'Not running';
    }
}

function startFastapiPolling() {
    checkFastapiStatus();
    if (fastapiCheckTimer) clearInterval(fastapiCheckTimer);
    fastapiCheckTimer = setInterval(checkFastapiStatus, 15000);
}

async function startFastapi() {
    const btn = document.getElementById('fastapiStartBtn');
    const port = document.getElementById('fastapiPort')?.value || '8000';
    if (btn) { btn.disabled = true; btn.textContent = 'Starting...'; }
    try {
        const res = await fetch('fastapi_control.php', {
            method: 'POST',
            headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
            body: `action=start&port=${port}`
        });
        const data = await res.json();
        if (data.success) {
            setTimeout(checkFastapiStatus, 2000);
        } else {
            alert('FastAPI start failed: ' + (data.error || ''));
        }
    } catch (e) {
        alert('Request failed: ' + e.message);
    } finally {
        if (btn) { btn.disabled = false; btn.textContent = 'Start'; }
    }
}

async function stopFastapi() {
    const btn = document.getElementById('fastapiStopBtn');
    if (btn) { btn.disabled = true; btn.textContent = 'Stopping...'; }
    try {
        const res = await fetch('fastapi_control.php', {
            method: 'POST',
            headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
            body: 'action=stop'
        });
        const data = await res.json();
        if (data.success) {
            setTimeout(checkFastapiStatus, 1000);
        } else {
            alert('FastAPI stop failed: ' + (data.error || ''));
        }
    } catch (e) {
        alert('Request failed: ' + e.message);
    } finally {
        if (btn) { btn.disabled = false; btn.textContent = 'Stop'; }
    }
}

async function checkDependencies() {
    const el = document.getElementById('dependencyCheckResult');
    if (!el) return;
    el.textContent = 'Checking...';
    try {
        const res = await fetch('fastapi_control.php?action=check_deps');
        const data = await res.json();
        if (data.success) {
            const lines = [];
            (data.deps || []).forEach(d => {
                lines.push(`${d.installed ? '✅' : '❌'} ${d.name} ${d.version || ''}`);
            });
            el.textContent = lines.join('\n') || 'No dependency info';
        } else {
            el.textContent = 'Check failed: ' + (data.error || '');
        }
    } catch (e) {
        el.textContent = 'Error: ' + e.message;
    }
}

/* ===== Calibration Records Management ===== */

async function loadCalibrationRecords() {
    const user = document.getElementById('calRecordUser')?.value?.trim();
    const platform = document.getElementById('calRecordPlatform')?.value?.trim();
    if (!user || !platform) {
        alert('請輸入使用者和平台名稱');
        return;
    }
    const listEl = document.getElementById('calRecordList');
    if (listEl) listEl.innerHTML = '<div style="color:#888; font-size:12px; padding:8px;">載入中...</div>';
    try {
        const res = await fetch(`calibrate_records.php?action=load&user=${encodeURIComponent(user)}&platform=${encodeURIComponent(platform)}`);
        const data = await res.json();
        if (data.success && data.record) {
            const rec = data.record;
            const charCount = rec.char_widths ? Object.keys(rec.char_widths).length : 0;
            listEl.innerHTML = `
                <div class="cal-record-item">
                    <div style="font-weight:600; margin-bottom:4px;">${user} / ${platform}</div>
                    <div style="font-size:12px; color:#888;">校準字元數: ${charCount}</div>
                    <div style="font-size:12px; color:#888;">更新時間: ${rec.updated_at || 'N/A'}</div>
                    <div style="margin-top:8px; display:flex; gap:6px;">
                        <button onclick="applyCalibrationRecord('${user}','${platform}')" style="font-size:11px;" class="primary">套用</button>
                        <button onclick="deleteCalibrationRecord('${user}','${platform}')" style="font-size:11px; color:#e94560;">刪除</button>
                    </div>
                </div>`;
        } else {
            listEl.innerHTML = `<div style="color:#888; font-size:12px; padding:8px;">無紀錄。${data.error || ''}</div>`;
        }
    } catch (e) {
        if (listEl) listEl.innerHTML = `<div style="color:#e94560; font-size:12px; padding:8px;">錯誤: ${e.message}</div>`;
    }
}

async function saveCalibrationRecord() {
    const user = document.getElementById('calRecordUser')?.value?.trim();
    const platform = document.getElementById('calRecordPlatform')?.value?.trim();
    if (!user || !platform) {
        alert('請輸入使用者和平台名稱');
        return;
    }
    const charWidths = window.lastCalibrationResult?.char_widths || window.calibrationCharWidths || null;
    if (!charWidths || Object.keys(charWidths).length === 0) {
        alert('目前無校準資料可儲存。請先執行校準流程。');
        return;
    }
    try {
        const res = await fetch('calibrate_records.php', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ action: 'save', user, platform, char_widths: charWidths })
        });
        const data = await res.json();
        if (data.success) {
            alert('校準紀錄已儲存');
            loadCalibrationRecords();
        } else {
            alert('儲存失敗: ' + (data.error || ''));
        }
    } catch (e) {
        alert('Error: ' + e.message);
    }
}

async function listAllCalibrationRecords() {
    const el = document.getElementById('allCalRecordsList');
    if (!el) return;
    el.innerHTML = '<div style="color:#888; font-size:12px;">載入中...</div>';
    try {
        const res = await fetch('calibrate_records.php?action=list');
        const data = await res.json();
        if (data.success && data.records && data.records.length > 0) {
            el.innerHTML = data.records.map(r => `
                <div class="cal-record-item" style="margin-bottom:6px;">
                    <span style="font-weight:600;">${r.user} / ${r.platform}</span>
                    <span style="font-size:11px; color:#888; margin-left:8px;">${r.char_count || 0} chars</span>
                    <span style="font-size:11px; color:#888; margin-left:8px;">${r.updated_at || ''}</span>
                    <button onclick="applyCalibrationRecord('${r.user}','${r.platform}')" style="font-size:10px; margin-left:8px;" class="primary">套用</button>
                    <button onclick="deleteCalibrationRecord('${r.user}','${r.platform}')" style="font-size:10px; margin-left:4px; color:#e94560;">刪除</button>
                </div>`).join('');
        } else {
            el.innerHTML = '<div style="color:#888; font-size:12px;">尚無任何紀錄。</div>';
        }
    } catch (e) {
        el.innerHTML = `<div style="color:#e94560; font-size:12px;">錯誤: ${e.message}</div>`;
    }
}

async function applyCalibrationRecord(user, platform) {
    try {
        const res = await fetch(`calibrate_records.php?action=load&user=${encodeURIComponent(user)}&platform=${encodeURIComponent(platform)}`);
        const data = await res.json();
        if (data.success && data.record?.char_widths) {
            window.calibrationCharWidths = data.record.char_widths;
            window.lastCalibrationResult = data.record;
            alert(`已套用 ${user}/${platform} 的校準紀錄 (${Object.keys(data.record.char_widths).length} 字元)`);
        } else {
            alert('載入失敗: ' + (data.error || ''));
        }
    } catch (e) {
        alert('Error: ' + e.message);
    }
}

async function deleteCalibrationRecord(user, platform) {
    if (!confirm(`確定要刪除 ${user}/${platform} 的校準紀錄？`)) return;
    try {
        const res = await fetch('calibrate_records.php', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ action: 'delete', user, platform })
        });
        const data = await res.json();
        if (data.success) {
            alert('紀錄已刪除');
            loadCalibrationRecords();
            listAllCalibrationRecords();
        } else {
            alert('刪除失敗: ' + (data.error || ''));
        }
    } catch (e) {
        alert('Error: ' + e.message);
    }
}
