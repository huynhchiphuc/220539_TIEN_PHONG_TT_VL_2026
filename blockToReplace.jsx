<div className="settings-content">
                                {/* Panels per page */}
                            <div className="setting-group">
                                <div className="setting-row">
                                    <label className="setting-label">Số khung mỗi trang</label>
                                    <span className="setting-value">{settings.panelsPerPage}</span>
                                </div>
                                <input
                                    type="range" min="2" max="10" step="1"
                                    value={settings.panelsPerPage}
                                    onChange={(e) => updateSetting('panelsPerPage', +e.target.value)}
                                    className="slider"
                                    disabled={isGenerating}
                                />
                                <label className="checkbox-label">
                                    <input
                                        type="checkbox"
                                        checked={settings.drawSpeechBubblesOutside}
                                        onChange={(e) => updateSetting('drawSpeechBubblesOutside', e.target.checked)}
                                        disabled={isGenerating}
                                    />
                                    <span className="checkbox-text">💬 Cho phép chữ/bóng thoại tràn khỏi khung</span>
                                </label>
                            </div>

                            {/* Diagonal Probability */}
                            <div className="setting-group">
                                <div className="setting-row">
                                    <label className="setting-label">Tỉ lệ đường kẻ chéo</label>
                                    <span className="setting-value">{settings.diagonalProb}%</span>
                                </div>
                                <input
                                    type="range" min="0" max="100" step="5"
                                    value={settings.diagonalProb}
                                    onChange={(e) => updateSetting('diagonalProb', +e.target.value)}
                                    className="slider"
                                    disabled={isGenerating}
                                />
                            </div>

                            {/* Layout Mode */}
                            <div className="setting-group">
                                <label className="setting-label-block">🎨 Chế độ Layout</label>
                                <div className="radio-grid">
                                    {[
                                        { value: 'advanced', icon: '🧠', label: 'ADVANCED', sub: 'Diagonal + AI' },
                                        { value: 'simple', icon: '⚡', label: 'SIMPLE', sub: 'PIL Fast' },
                                    ].map((opt) => (
                                        <label
                                            key={opt.value}
                                            className={`radio-card${settings.layoutMode === opt.value ? ' selected' : ''}`}
                                        >
                                            <input
                                                type="radio"
                                                name="layoutMode"
                                                value={opt.value}
                                                checked={settings.layoutMode === opt.value}
                                                onChange={() => updateSetting('layoutMode', opt.value)}
                                                disabled={isGenerating}
                                            />
                                            <div className="radio-icon">{opt.icon}</div>
                                            <div className="radio-label">{opt.label}</div>
                                            <div className="radio-sub">{opt.sub}</div>
                                        </label>
                                    ))}
                                </div>
                            </div>

                            {/* Resolution & Aspect Ratio (Simple mode) */}
                            {settings.layoutMode === 'simple' && (
                                <div className="setting-group simple-options">
                                    <label className="setting-label-block">📐 Độ phân giải</label>
                                    <select
                                        value={settings.resolution}
                                        onChange={(e) => updateSetting('resolution', e.target.value)}
                                        className="select-input"
                                        disabled={isGenerating}
                                    >
                                        <option value="1K">1K (1000px)</option>
                                        <option value="2K">2K (2000px) - Khuyên dùng</option>
                                        <option value="4K">4K (4000px) - Chất lượng cao</option>
                                    </select>

                                    <label className="setting-label-block" style={{ marginTop: '12px' }}>📏 Tỷ lệ khung hình</label>
                                    <select
                                        value={settings.aspectRatio}
                                        onChange={(e) => updateSetting('aspectRatio', e.target.value)}
                                        className="select-input"
                                        disabled={isGenerating}
                                    >
                                        <option value="auto">🤖 AUTO - Tự động phát hiện ⭐</option>
                                        <option value="1:1">1:1 - Vuông</option>
                                        <option value="9:16">9:16 - DỌC (Story) 📱</option>
                                        <option value="2:3">2:3 - DỌC (Photo) 📷</option>
                                        <option value="3:4">3:4 - DỌC</option>
                                        <option value="4:5">4:5 - DỌC (Instagram)</option>
                                    </select>
                                </div>
                            )}

                            {/* Toggle checkboxes */}
                            {settings.layoutMode === 'simple' && (
                                <div className="setting-group toggles-group">
                                    {[
                                        { key: 'adaptiveLayout', label: 'Bố cục thích ứng' },
                                        { key: 'smartCrop', label: 'Smart Crop (AI)' },
                                    ].map((t) => (
                                        <label key={t.key} className="toggle-item">
                                            <span className="toggle-label">{t.label}</span>
                                            <input
                                                type="checkbox"
                                                checked={settings[t.key]}
                                                onChange={(e) => updateSetting(t.key, e.target.checked)}
                                                disabled
                                            />
                                        </label>
                                    ))}
                                </div>
                            )}

                            {settings.layoutMode === 'advanced' && (
                                <div className="setting-group advanced-tilt-group">
                                    {/* Phân tích kích thước/tỉ lệ ảnh đầu vào */}
                                    {statsLoading && (
                                        <p className="setting-help-text" style={{ color: '#888', fontStyle: 'italic' }}>
                                            ⏳ Đang phân tích kích thước ảnh...
                                        </p>
                                    )}
                                    {imageStats && !statsLoading && (
                                        <div className="image-stats-box">
                                            <div className="image-stats-title">📊 Phân tích ảnh đầu vào ({imageStats.analyzed}/{imageStats.count} ảnh)</div>
                                            <div className="image-stats-grid">
                                                <div className="comic-stat-item">
                                                    <span className="comic-stat-icon">➡️</span>
                                                    <span className="comic-stat-label">Nằm ngang</span>
                                                    <span className="comic-stat-value">{imageStats.landscape}</span>
                                                </div>
                                                <div className="comic-stat-item">
                                                    <span className="comic-stat-icon">⬆️</span>
                                                    <span className="comic-stat-label">Đứng dọc</span>
                                                    <span className="comic-stat-value">{imageStats.portrait}</span>
                                                </div>
                                                <div className="comic-stat-item">
                                                    <span className="comic-stat-icon">◼️</span>
                                                    <span className="comic-stat-label">Vuông</span>
                                                    <span className="comic-stat-value">{imageStats.square}</span>
                                                </div>
                                                <div className="comic-stat-item comic-stat-item--full">
                                                    <span className="comic-stat-icon">📐</span>
                                                    <span className="comic-stat-label">Tỉ lệ đa số</span>
                                                    <span className="comic-stat-value comic-stat-value--highlight">{imageStats.dominantAR}</span>
                                                </div>
                                                <div className="comic-stat-item comic-stat-item--full">
                                                    <span className="comic-stat-icon">📏</span>
                                                    <span className="comic-stat-label">Kích thước</span>
                                                    <span className="comic-stat-value">{imageStats.minW}–{imageStats.maxW}×{imageStats.minH}–{imageStats.maxH}px</span>
                                                </div>
                                                <div className="comic-stat-item comic-stat-item--full">
                                                    <span className="comic-stat-icon">💡</span>
                                                    <span className="comic-stat-label">Gợi ý trang</span>
                                                    <span className="comic-stat-value comic-stat-value--suggest">{imageStats.suggestedAspect}</span>
                                                </div>
                                            </div>
                                        </div>
                                    )}
                                </div>
                            )}
                                
                            {settings.layoutMode === 'advanced' && (
                                    <div className="setting-group advanced-tilt-group">
                                        {/* Slider độ nghiêng khung 1–3° */}
                                        <div className="tilt-slider-group" style={{ marginTop: 0 }}>
                                        <div className="setting-row">
                                            <label className="setting-label">🎯 Độ nghiêng khung (manga tilt)</label>
                                            <span className="setting-value tilt-value">{settings.frameTiltDegree}°</span>
                                        </div>
                                        <input
                                            type="range" min="1" max="3" step="0.5"
                                            value={settings.frameTiltDegree}
                                            onChange={(e) => updateSetting('frameTiltDegree', +e.target.value)}
                                            className="slider slider--tilt"
                                            disabled={isGenerating}
                                        />
                                        <div className="tilt-labels">
                                            <span>1° Nhẹ</span>
                                            <span>2° Vừa ⭐</span>
                                            <span>3° Mạnh</span>
                                        </div>
                                        <p className="setting-help-text" style={{ marginTop: '6px' }}>
                                            Khung ADVANCED hơi nghiêng theo kích thước ảnh thật — khác với Auto Frame (khung trắng thẳng). Chọn 1–3° để kiểm soát cảm giác manga.
                                        </p>
                                    </div>
                                </div>
                            )}
                                
                            {settings.layoutMode === 'advanced' && (
                                    <div className="setting-group advanced-tilt-group">
                                        {/* Tỉ lệ trang & Độ phân giải cho ADVANCED */}
                                        <div>
                                            <label className="setting-label-block" style={{ color: '#a5b4fc' }}>📏 Tỷ lệ trang (ADVANCED)</label>
                                        <select
                                            value={settings.aspectRatio}
                                            onChange={(e) => updateSetting('aspectRatio', e.target.value)}
                                            className="select-input"
                                            style={{ borderColor: 'rgba(99,102,241,0.4)' }}
                                            disabled={isGenerating}
                                        >
                                            <option value="auto">🤖 AUTO — theo ảnh đầu vào ⭐</option>
                                            <option value="9:16">9:16 — Dọc (Story) 📱</option>
                                            <option value="2:3">2:3 — Dọc (Photo) 📷</option>
                                            <option value="3:4">3:4 — Dọc</option>
                                            <option value="4:5">4:5 — Dọc (Instagram)</option>
                                            <option value="1:1">1:1 — Vuông</option>
                                        </select>
                                        <label className="setting-label-block" style={{ color: '#a5b4fc', marginTop: '10px' }}>📐 Độ phân giải</label>
                                        <select
                                            value={settings.resolution}
                                            onChange={(e) => updateSetting('resolution', e.target.value)}
                                            className="select-input"
                                            style={{ borderColor: 'rgba(99,102,241,0.4)' }}
                                            disabled={isGenerating}
                                        >
                                            <option value="1K">1K (1000px) — Nhanh</option>
                                            <option value="2K">2K (2000px) — Khuyên dùng ⭐</option>
                                            <option value="4K">4K (4000px) — Chất lượng cao</option>
                                        </select>
                                        {imageStats && (
                                            <p className="setting-help-text" style={{ marginTop: '6px', color: '#34d399' }}>
                                                💡 Gợi ý theo ảnh của bạn: <strong>{imageStats.suggestedAspect}</strong>
                                            </p>
                                        )}
                                        </div>
                                    </div>
                                )}

                            {/* Reading Direction */}
                            <div className="setting-group">
                                <label className="setting-label-block">Hướng đọc</label>
                                <p className="setting-help-text">
                                    Luôn đọc theo thứ tự từ trên xuống dưới; tùy chọn bên dưới chỉ đổi hướng đọc trong từng hàng.
                                </p>
                                <div className="radio-grid">
                                    {[
                                        { value: 'ltr', label: 'LTR (Trái → Phải, trên → xuống)' },
                                        { value: 'rtl', label: 'RTL (Phải → Trái, trên → xuống)' },
                                    ].map((opt) => (
                                        <label
                                            key={opt.value}
                                            className={`radio-card compact${settings.readingDirection === opt.value ? ' selected' : ''}`}
                                        >
                                            <input
                                                type="radio"
                                                name="readingDirection"
                                                value={opt.value}
                                                checked={settings.readingDirection === opt.value}
                                                onChange={() => updateSetting('readingDirection', opt.value)}
                                                disabled={isGenerating}
                                            />
                                            {opt.label}
                                        </label>
                                    ))}
                                </div>
                            </div>

                            {/* Quality */}
                            <div className="setting-group">
                                <label className="setting-label-block">Chất lượng</label>
                                <div className="radio-inline">
                                    {[{ value: 150, label: 'Web' }, { value: 300, label: 'In ấn' }].map((opt) => (
                                        <label key={opt.value} className="radio-inline-item">
                                            <input
                                                type="radio"
                                                name="targetDPI"
                                                value={opt.value}
                                                checked={settings.targetDPI === opt.value}
                                                onChange={() => updateSetting('targetDPI', opt.value)}
                                                disabled={isGenerating}
                                            />
                                            {opt.label}
                                        </label>
                                    ))}
                                </div>
                            </div>

                            </div>