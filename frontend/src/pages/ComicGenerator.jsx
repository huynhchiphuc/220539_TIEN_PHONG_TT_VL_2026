import { useState, useRef, useCallback, useEffect } from 'react';
import { useSearchParams, useNavigate } from 'react-router-dom';
import { comicService } from '../services/comicService';
import { COMIC_CONFIG } from '../utils/constants';
import './ComicGenerator.css';

const ComicGenerator = () => {
    const [searchParams] = useSearchParams();
    const navigate = useNavigate();
    const [selectedFiles, setSelectedFiles] = useState([]);
    const [sessionId, setSessionId] = useState(null);
    const [filesChanged, setFilesChanged] = useState(false);
    const [isDragging, setIsDragging] = useState(false);

    // Settings state
    const [settings, setSettings] = useState({
        panelsPerPage: 5,
        diagonalProb: 30,
        layoutMode: 'advanced',
        resolution: '2K',
        aspectRatio: 'auto',
        adaptiveLayout: true,
        smartCrop: false,
        analyzeShotType: false,
        classifyCharacters: false,
        readingDirection: 'ltr',
        targetDPI: 150,
        singlePageMode: false,
    });

    // UI state
    const [phase, setPhase] = useState('idle'); // idle | uploading | generating | done | error
    const [progress, setProgress] = useState(0);
    const [statusText, setStatusText] = useState('');
    const [resultPages, setResultPages] = useState([]);
    const [errorMsg, setErrorMsg] = useState('');
    const [validationWarnings, setValidationWarnings] = useState([]); // Per-file rejection reasons
    const [isValidating, setIsValidating] = useState(false);

    // Cover uploads
    const [covers, setCovers] = useState({ front: null, back: null, thank_you: null });
    const [coverStatus, setCoverStatus] = useState({ front: false, back: false, thank_you: false });

    const fileInputRef = useRef(null);

    // ── Load Session from URL (if exists) ──────────────────────────────────────

    useEffect(() => {
        const sessionFromUrl = searchParams.get('session');
        if (sessionFromUrl) {
            loadExistingSession(sessionFromUrl);
        }
    }, [searchParams]);

    const loadExistingSession = async (sid) => {
        setPhase('loading');
        setStatusText('Đang tải dự án...');
        
        try {
            const res = await comicService.preview(sid);
            if (res && res.pages && res.pages.length > 0) {
                setSessionId(sid);
                setResultPages(res.pages);
                setPhase('done');
                setStatusText('✅ Đã tải dự án thành công!');
            } else {
                showError('Không thể tải dự án này');
                setPhase('idle');
            }
        } catch (error) {
            console.error('Load session error:', error);
            showError('Lỗi khi tải dự án: ' + (error.response?.data?.detail || error.message));
            setPhase('idle');
        }
    };

    // ── File Handling ──────────────────────────────────────────────────────────

    const handleFiles = useCallback(async (files) => {
        const arr = Array.from(files);
        if (arr.length === 0) return;

        setIsValidating(true);
        setValidationWarnings([]);

        const valid = [];
        const rejected = [];

        // Snapshot current count to check total limit
        const currentCount = selectedFiles.length;
        const remaining = COMIC_CONFIG.MAX_IMAGES - currentCount;

        for (const file of arr) {
            const name = file.name;

            // 1. MIME type whitelist
            if (!COMIC_CONFIG.ALLOWED_IMAGE_TYPES.includes(file.type)) {
                rejected.push(`❌ ${name}: Định dạng không hỗ trợ (${file.type || 'unknown'})`);
                continue;
            }

            // 2. Min size — < 1KB likely corrupted / empty
            if (file.size < COMIC_CONFIG.MIN_FILE_SIZE) {
                rejected.push(`❌ ${name}: File quá nhỏ (${(file.size / 1024).toFixed(1)} KB, tối thiểu 1 KB)`);
                continue;
            }

            // 3. Max size per file
            if (file.size > COMIC_CONFIG.MAX_FILE_SIZE) {
                rejected.push(`❌ ${name}: File quá lớn (${(file.size / 1024 / 1024).toFixed(1)} MB, tối đa 50 MB)`);
                continue;
            }

            // 4. Duplicate detection (same name + size)
            const isDuplicate = selectedFiles.some((f) => f.name === name && f.size === file.size)
                || valid.some((f) => f.name === name && f.size === file.size);
            if (isDuplicate) {
                rejected.push(`⚠️ ${name}: Ảnh đã được thêm (trùng lặp)`);
                continue;
            }

            // 5. Count limit
            if (valid.length >= remaining) {
                rejected.push(`⚠️ ${name}: Vượt giới hạn ${COMIC_CONFIG.MAX_IMAGES} ảnh`);
                continue;
            }

            // 6. Image integrity + resolution check via browser
            try {
                const bitmap = await createImageBitmap(file);
                const { width, height } = bitmap;
                bitmap.close();

                if (width < COMIC_CONFIG.MIN_RESOLUTION || height < COMIC_CONFIG.MIN_RESOLUTION) {
                    rejected.push(`❌ ${name}: Ảnh quá nhỏ (${width}×${height}px, tối thiểu ${COMIC_CONFIG.MIN_RESOLUTION}×${COMIC_CONFIG.MIN_RESOLUTION}px)`);
                    continue;
                }
                if (width > COMIC_CONFIG.MAX_RESOLUTION || height > COMIC_CONFIG.MAX_RESOLUTION) {
                    // Warn but still allow — backend will also validate
                    rejected.push(`⚠️ ${name}: Ảnh rất lớn (${width}×${height}px) — có thể chậm`);
                }
            } catch {
                rejected.push(`❌ ${name}: File ảnh bị hỏng hoặc không đọc được`);
                continue;
            }

            valid.push(file);
        }

        setIsValidating(false);

        if (valid.length === 0 && rejected.length > 0) {
            showError('Không có ảnh hợp lệ nào được thêm!');
            setValidationWarnings(rejected);
            return;
        }

        if (rejected.length > 0) {
            setValidationWarnings(rejected);
        }

        if (valid.length > 0) {
            setSelectedFiles((prev) => [...prev, ...valid]);
            setFilesChanged(true);
            setResultPages([]);
            setErrorMsg('');
        }
    }, [selectedFiles]);

    const removeFile = (idx) => {
        setSelectedFiles((prev) => prev.filter((_, i) => i !== idx));
        setFilesChanged(true);
    };

    const clearAllFiles = () => {
        setSelectedFiles([]);
        setSessionId(null);
        setFilesChanged(false);
        setResultPages([]);
        setCovers({ front: null, back: null, thank_you: null });
        setCoverStatus({ front: false, back: false, thank_you: false });
        setValidationWarnings([]);
        setPhase('idle');
    };

    const dismissWarnings = () => setValidationWarnings([]);

    // ── Drag & Drop ────────────────────────────────────────────────────────────

    const onDragOver = (e) => { e.preventDefault(); setIsDragging(true); };
    const onDragLeave = () => setIsDragging(false);
    const onDrop = (e) => {
        e.preventDefault();
        setIsDragging(false);
        handleFiles(e.dataTransfer.files);
    };

    // ── Error ──────────────────────────────────────────────────────────────────

    const showError = (msg) => {
        setErrorMsg(msg);
        setTimeout(() => setErrorMsg(''), 5000);
    };

    // ── Settings ───────────────────────────────────────────────────────────────

    const updateSetting = (key, value) => setSettings((s) => ({ ...s, [key]: value }));

    // ── Generate ───────────────────────────────────────────────────────────────

    const handleGenerate = async () => {
        if (selectedFiles.length === 0) {
            showError('Vui lòng chọn ít nhất 1 ảnh!');
            return;
        }

        setPhase('uploading');
        setProgress(10);
        setStatusText('Đang gửi dữ liệu lên server...');
        setErrorMsg('');
        setResultPages([]);

        try {
            let currentSessionId = sessionId;

            // Upload nếu có thay đổi hoặc chưa có session
            if (!currentSessionId || filesChanged) {
                const uploadData = await comicService.uploadImages(selectedFiles, (p) => {
                    setProgress(10 + Math.round(p * 0.25)); // 10% → 35%
                });
                currentSessionId = uploadData.session_id;
                setSessionId(currentSessionId);
                setFilesChanged(false);
                setCovers({ front: null, back: null, thank_you: null });
                setCoverStatus({ front: false, back: false, thank_you: false });
            }

            setPhase('generating');
            setProgress(40);
            setStatusText('Họa sĩ AI đang vẽ khung hình...');

            await comicService.generate({
                session_id: currentSessionId,
                layout_mode: settings.layoutMode,
                panels_per_page: settings.panelsPerPage,
                diagonal_prob: settings.diagonalProb / 100,
                adaptive_layout: settings.adaptiveLayout,
                use_smart_crop: settings.smartCrop,
                reading_direction: settings.readingDirection,
                analyze_shot_type: settings.analyzeShotType,
                classify_characters: settings.classifyCharacters,
                target_dpi: settings.targetDPI,
                resolution: settings.resolution,
                aspect_ratio: settings.aspectRatio,
                margin: 40,
                gap: 30,
                single_page_mode: settings.singlePageMode,
            });

            setProgress(80);
            setStatusText('Đang hoàn thiện...');

            const previewData = await comicService.preview(currentSessionId);
            setResultPages(previewData.pages || []);

            setProgress(100);
            setStatusText('XONG RỒI! CHIÊM NGƯỠNG THÔI!');
            setTimeout(() => setPhase('done'), 800);

        } catch (err) {
            const msg = err.response?.data?.detail || err.message || 'Lỗi không xác định';
            showError(msg);
            setPhase(selectedFiles.length > 0 ? 'idle' : 'idle');
        }
    };

    // ── Cover Upload ───────────────────────────────────────────────────────────

    const handleCoverUpload = async (coverType, file) => {
        if (!sessionId || !file) return;
        try {
            const data = await comicService.uploadCover(sessionId, coverType, file);
            setCovers((prev) => ({ ...prev, [coverType]: data.url }));
            setCoverStatus((prev) => ({ ...prev, [coverType]: true }));
        } catch (err) {
            showError(`Lỗi upload bìa: ${err.response?.data?.detail || err.message}`);
        }
    };

    // ── Download ───────────────────────────────────────────────────────────────

    const downloadZip = () => {
        if (sessionId) window.open(comicService.getDownloadZipUrl(sessionId));
    };
    const downloadPdf = () => {
        if (sessionId) window.open(comicService.getDownloadPdfUrl(sessionId));
    };

    // ── Render ─────────────────────────────────────────────────────────────────

    const isGenerating = phase === 'uploading' || phase === 'generating';

    return (
        <div className="comic-generator">
            {/* Header stripe */}
            <div className="comic-header-stripe">
                {searchParams.get('session') && (
                    <button 
                        onClick={() => navigate('/upload')}
                        className="back-to-projects-btn"
                        title="Quay lại Dự Án"
                    >
                        ← Dự Án
                    </button>
                )}
                <div className="comic-logo">
                    <span className="logo-icon">📚</span>
                    <div>
                        <h1 className="comic-title">ComicCraft AI</h1>
                        <p className="comic-subtitle">AUTOMATIC PANEL GENERATOR</p>
                    </div>
                </div>
            </div>

            <div className="comic-layout">
                {/* ── Left Column ── */}
                <div className="comic-left">

                    {/* Upload Zone */}
                    <div
                        className={`upload-zone${isDragging ? ' dragging' : ''}${selectedFiles.length > 0 ? ' has-files' : ''}`}
                        onClick={() => !isGenerating && fileInputRef.current?.click()}
                        onDragOver={onDragOver}
                        onDragLeave={onDragLeave}
                        onDrop={onDrop}
                    >
                        <input
                            ref={fileInputRef}
                            type="file"
                            multiple
                            accept="image/*"
                            className="hidden-input"
                            onChange={(e) => handleFiles(e.target.files)}
                            disabled={isGenerating}
                        />
                        {selectedFiles.length === 0 ? (
                            <>
                                <div className="upload-icon">🖼️</div>
                                <h3 className="upload-title">Thả ảnh vào đây để bắt đầu</h3>
                                <p className="upload-hint">Hỗ trợ PNG, JPG, WebP, GIF · Tối đa 50MB/ảnh · 100 ảnh</p>
                                <button className="btn btn-blue" disabled={isGenerating}>
                                    Chọn ảnh từ máy
                                </button>
                            </>
                        ) : (
                            <p className="upload-hint">🖼️ Nhấn để thêm ảnh · Kéo thả thêm ảnh vào đây</p>
                        )}
                    </div>

                    {/* File List */}
                    {selectedFiles.length > 0 && (
                        <div className="file-list-card">
                            <div className="file-list-header">
                                <h3 className="file-list-title">
                                    📸 Danh sách ảnh{' '}
                                    <span className="badge">{selectedFiles.length}</span>
                                </h3>
                                <button
                                    className="btn-text-danger"
                                    onClick={clearAllFiles}
                                    disabled={isGenerating}
                                >
                                    Xóa tất cả
                                </button>
                            </div>
                            <div className="file-grid">
                                {selectedFiles.map((file, idx) => (
                                    <div key={idx} className="file-item">
                                        <img
                                            src={URL.createObjectURL(file)}
                                            alt={file.name}
                                            className="file-thumb"
                                        />
                                        <button
                                            className="file-remove-btn"
                                            onClick={() => removeFile(idx)}
                                            disabled={isGenerating}
                                        >
                                            ✕
                                        </button>
                                        <div className="file-name">{file.name}</div>
                                    </div>
                                ))}
                            </div>
                        </div>
                    )}
                </div>

                {/* ── Right Column: Settings ── */}
                {selectedFiles.length > 0 && (
                    <div className="comic-right">
                        <div className="settings-card">
                            <h3 className="settings-title">⚙️ Cấu hình truyện tranh</h3>

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
                                        checked={settings.singlePageMode}
                                        onChange={(e) => updateSetting('singlePageMode', e.target.checked)}
                                        disabled={isGenerating}
                                    />
                                    <span className="checkbox-text purple">📄 Chỉ 1 trang (ghép tất cả)</span>
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
                                        <option value="16:9">16:9 - NGANG (HD) 🖥️</option>
                                        <option value="3:2">3:2 - NGANG (Photo)</option>
                                        <option value="4:3">4:3 - NGANG</option>
                                        <option value="5:4">5:4 - NGANG</option>
                                        <option value="21:9">21:9 - NGANG (Siêu rộng)</option>
                                    </select>
                                </div>
                            )}

                            {/* Toggle checkboxes */}
                            <div className="setting-group toggles-group">
                                {[
                                    { key: 'adaptiveLayout', label: 'Bố cục thích ứng' },
                                    { key: 'smartCrop', label: 'Smart Crop (AI)' },
                                    { key: 'analyzeShotType', label: 'Phân tích bối cảnh' },
                                    { key: 'classifyCharacters', label: '🎭 Phân tích nhân vật (AI)' },
                                ].map((t) => (
                                    <label key={t.key} className="toggle-item">
                                        <span className="toggle-label">{t.label}</span>
                                        <input
                                            type="checkbox"
                                            checked={settings[t.key]}
                                            onChange={(e) => updateSetting(t.key, e.target.checked)}
                                            disabled={isGenerating}
                                        />
                                    </label>
                                ))}
                            </div>

                            {/* Reading Direction */}
                            <div className="setting-group">
                                <label className="setting-label-block">Hướng đọc</label>
                                <div className="radio-grid">
                                    {[
                                        { value: 'ltr', label: 'LTR (Tây)' },
                                        { value: 'rtl', label: 'RTL (Manga)' },
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

                            {/* Generate Button */}
                            <button
                                className={`btn btn-generate${isGenerating ? ' loading' : ''}`}
                                onClick={handleGenerate}
                                disabled={isGenerating || selectedFiles.length === 0}
                            >
                                {isGenerating ? `⏳ ${statusText || 'Đang xử lý...'}` : '🚀 BẮT ĐẦU TẠO TRUYỆN'}
                            </button>
                        </div>
                    </div>
                )}
            </div>

            {/* ── Progress ── */}
            {isGenerating && (
                <div className="progress-section">
                    <h3 className="progress-title">{statusText}</h3>
                    <div className="progress-bar-outer">
                        <div
                            className="progress-bar-fill"
                            style={{ width: `${progress}%` }}
                        >
                            {progress}%
                        </div>
                    </div>
                    <div className="spinner">🖌️</div>
                </div>
            )}

            {/* ── Results ── */}
            {phase === 'done' && resultPages.length > 0 && (
                <div className="result-section">
                    <div className="result-header">
                        <h2 className="result-title">✨ KẾT QUẢ CỦA BẠN</h2>
                        <div className="result-actions">
                            <button className="btn btn-green" onClick={downloadZip}>📦 TẢI ZIP</button>
                            <button className="btn btn-red" onClick={downloadPdf}>📄 TẢI PDF (có bìa)</button>
                        </div>
                    </div>

                    {/* Cover Upload */}
                    <div className="cover-section">
                        <div className="cover-section-header">
                            <h3 className="cover-title">
                                📖 Thêm bìa vào PDF
                                <span className="cover-hint">(Tùy chọn)</span>
                            </h3>
                            <div className="cover-badges">
                                {coverStatus.front && <span className="badge-green">✅ Bìa trước</span>}
                                {coverStatus.back && <span className="badge-green">✅ Bìa sau</span>}
                                {coverStatus.thank_you && <span className="badge-green">✅ Lời cảm ơn</span>}
                            </div>
                        </div>
                        <div className="cover-grid">
                            {[
                                { key: 'front', icon: '🎨', label: 'Bìa trước', hint: 'Trang đầu tiên trong PDF' },
                                { key: 'back', icon: '📘', label: 'Bìa sau', hint: 'Trang cuối (trước lời cảm ơn)' },
                                { key: 'thank_you', icon: '💐', label: 'Lời cảm ơn', hint: 'Trang cuối cùng' },
                            ].map((c) => (
                                <div key={c.key} className="cover-item">
                                    <label className="cover-label">{c.icon} {c.label}</label>
                                    <label
                                        className={`cover-slot${covers[c.key] ? ' has-cover' : ''}`}
                                    >
                                        <input
                                            type="file"
                                            accept="image/*"
                                            className="hidden-input"
                                            onChange={(e) => e.target.files[0] && handleCoverUpload(c.key, e.target.files[0])}
                                        />
                                        {covers[c.key] ? (
                                            <img
                                                src={`${import.meta.env.VITE_API_URL || 'http://localhost:60074/api/v1'}${covers[c.key]}`}
                                                alt={c.label}
                                                className="cover-preview"
                                            />
                                        ) : (
                                            <>
                                                <span className="cover-slot-icon">{c.icon}</span>
                                                <span className="cover-slot-hint">Click để chọn</span>
                                            </>
                                        )}
                                        <div className="cover-overlay">Thay đổi</div>
                                    </label>
                                    <p className="cover-caption">{c.hint}</p>
                                </div>
                            ))}
                        </div>
                    </div>

                    {/* Pages grid */}
                    <div className="pages-grid">
                        {resultPages.map((url, i) => (
                            <div key={i} className={`page-card${i % 2 === 0 ? ' tilt-left' : ' tilt-right'}`}>
                                <img src={url} alt={`Trang ${i + 1}`} className="page-img" />
                                <div className="page-footer">
                                    <span className="page-number">PAGE #{i + 1}</span>
                                    <a href={url} download={`page-${i + 1}.png`} className="page-download">
                                        TẢI LẺ
                                    </a>
                                </div>
                            </div>
                        ))}
                    </div>
                </div>
            )}

            {/* ── Error Toast ── */}
            {errorMsg && (
                <div className="error-toast">
                    💥 OOPS: {errorMsg}
                </div>
            )}

            {/* ── Validation Warnings Panel ── */}
            {validationWarnings.length > 0 && (
                <div className="validation-warnings">
                    <div className="validation-warnings-header">
                        <span>⚠️ {validationWarnings.length} file bị bỏ qua</span>
                        <button className="dismiss-warnings-btn" onClick={dismissWarnings}>×</button>
                    </div>
                    <ul className="validation-warnings-list">
                        {validationWarnings.map((w, i) => (
                            <li key={i}>{w}</li>
                        ))}
                    </ul>
                </div>
            )}

            {/* ── Validating indicator ── */}
            {isValidating && (
                <div className="validating-indicator">
                    🔍 Đang kiểm tra ảnh...
                </div>
            )}
        </div>
    );
};

export default ComicGenerator;
