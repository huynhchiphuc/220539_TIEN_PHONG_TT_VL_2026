const fs = require('fs');

const block = fs.readFileSync('blockToReplace.jsx', 'utf8');

const getBlock = (pattern) => {
    const match = block.match(pattern);
    if (!match) console.error('Failed to match:', pattern);
    return match ? match[0] : '';
};

const panels = getBlock(/\{\/\* Panels per page \*\/\}[\s\S]*?<\/div>\s*<\/div>/);
const diagonal = getBlock(/\{\/\* Diagonal Probability \*\/\}[\s\S]*?<\/div>\s*<\/div>/);
const layoutMode = getBlock(/\{\/\* Layout Mode \*\/\}[\s\S]*?<\/div>\s*<\/div>/);
const simpleOptions = getBlock(/\{\/\* Resolution & Aspect Ratio \(Simple mode\) \*\/\}[\s\S]*?<\/div>\s*\)\}/);
const toggles = getBlock(/\{\/\* Toggle checkboxes \*\/\}[\s\S]*?<\/div>\s*\)\}/);

const readingDir = getBlock(/\{\/\* Reading Direction \*\/\}[\s\S]*?<\/div>\s*<\/div>/);
const quality = getBlock(/\{\/\* Quality \*\/\}[\s\S]*?<\/div>\s*<\/div>/);

const statsLoadingStart = block.indexOf('{statsLoading && (');
const statsLoadingEnd = block.indexOf(')}', statsLoadingStart) + 2;
const statsLoading = block.substring(statsLoadingStart, statsLoadingEnd);

const imageStatsStart = block.indexOf('{imageStats && !statsLoading && (');
const imageStatsBoxEnd = block.indexOf('</div>\\n                                    )}', imageStatsStart) + 45;
const imageStats = block.substring(imageStatsStart, imageStatsBoxEnd);

// Advanced tilt slider
const tiltSlider = getBlock(/\{\/\* Slider độ nghiêng khung 1–3° \*\/\}[\s\S]*?<\/div>\s*<\/div>/);
// Advanced aspect ratio
const aspectRatio = getBlock(/\{\/\* Tỉ lệ trang & Độ phân giải cho ADVANCED \*\/\}[\s\S]*?<\/div>\s*<\/div>/);


const newJSX = `<div className="settings-layout">
                                <div className="settings-main">
                                    {/* --- Section 1: Cấu hình Cơ bản --- */}
                                    <div className="settings-section">
                                        <h4 className="settings-section-title">🔧 Cấu hình Cơ bản</h4>
                                        <div className="settings-grid">
${panels}
${diagonal}
${layoutMode}
${readingDir}
${quality}
${simpleOptions}
${toggles}
                                        </div>
                                    </div>

                                    {/* --- Section 2: Tuỳ chỉnh Chuyên sâu --- */}
                                    {settings.layoutMode === 'advanced' && (
                                        <div className="settings-section advanced-section">
                                            <h4 className="settings-section-title">✨ Tuỳ chỉnh Chuyên sâu (Advanced)</h4>
                                            <div className="settings-grid">
${tiltSlider}
${aspectRatio}
                                            </div>
                                        </div>
                                    )}
                                </div>

                                {/* --- Sidebar: Image Stats --- */}
                                {settings.layoutMode === 'advanced' && (
                                    <div className="settings-sidebar">
                                        {/* Phân tích kích thước/tỉ lệ ảnh đầu vào */}
                                        ${statsLoading}
                                        ${imageStats}
                                    </div>
                                )}
                            </div>`;

const fullJSX = fs.readFileSync('frontend/src/pages/ComicGenerator.jsx', 'utf8');
const targetContent = fullJSX.replace(block, newJSX);

fs.writeFileSync('frontend/src/pages/ComicGenerator.jsx', targetContent);
console.log('Replaced successfully!');
