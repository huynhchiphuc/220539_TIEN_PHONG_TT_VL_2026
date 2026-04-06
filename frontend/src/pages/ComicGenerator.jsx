import { useState, useRef, useCallback, useEffect } from 'react';
import { useSearchParams, useNavigate } from 'react-router-dom';
import { comicService } from '../services/comicService';
import { COMIC_CONFIG } from '../utils/constants';
import './ComicGenerator.css';

const LAYOUT_MODE_PRESETS = {
    advanced: {
        adaptiveLayout: true,
        smartCrop: true,
        analyzeShotType: false,
        classifyCharacters: true,
        perspectiveWarp: false,
    },
    simple: {
        adaptiveLayout: true,
        smartCrop: true,
        analyzeShotType: false,
        classifyCharacters: false,
        perspectiveWarp: false,
    },
};

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
        aspectRatio: '9:16',
        adaptiveLayout: true,
        smartCrop: false,
        analyzeShotType: false,
        classifyCharacters: false,
        perspectiveWarp: false,
        readingDirection: 'ltr',
        targetDPI: 150,
        drawSpeechBubblesOutside: true,
    });

    // UI state
    const [phase, setPhase] = useState('idle'); // idle | uploading | generating | done | error
    const [progress, setProgress] = useState(0);
    const [statusText, setStatusText] = useState('');
    const [resultPages, setResultPages] = useState([]);
    const [errorMsg, setErrorMsg] = useState('');
    const [validationWarnings, setValidationWarnings] = useState([]); // Per-file rejection reasons
    const [isValidating, setIsValidating] = useState(false);
    const [isCloudSyncing, setIsCloudSyncing] = useState(false);
    const [frameLayout, setFrameLayout] = useState(null);
    const [layoutSlots, setLayoutSlots] = useState([]);
    const [layoutLoading, setLayoutLoading] = useState(false);
    const [manualMapping, setManualMapping] = useState({});
    const [activeDropPanel, setActiveDropPanel] = useState(null);
    const [isFillingPanels, setIsFillingPanels] = useState(false);

    // Cover uploads
    const [covers, setCovers] = useState({ front: null, back: null, thank_you: null });
    const [coverStatus, setCoverStatus] = useState({ front: false, back: false, thank_you: false });

    const fileInputRef = useRef(null);

    const getOrderedUploadName = (file, idx) => {
        const original = String(file?.name || '').toLowerCase();
        const dotIdx = original.lastIndexOf('.');
        let ext = dotIdx >= 0 ? original.slice(dotIdx + 1) : '';

        if (!ext) {
            if (file?.type === 'image/png') ext = 'png';
            else if (file?.type === 'image/webp') ext = 'webp';
            else if (file?.type === 'image/gif') ext = 'gif';
            else ext = 'jpg';
        }

        if (ext === 'jpeg') ext = 'jpg';
        const order = String(idx + 1).padStart(4, '0');
        return `anh_${order}.${ext}`;
    };

    const guessMimeFromName = (name) => {
        const lower = String(name || '').toLowerCase();
        if (lower.endsWith('.png')) return 'image/png';
        if (lower.endsWith('.webp')) return 'image/webp';
        if (lower.endsWith('.gif')) return 'image/gif';
        return 'image/jpeg';
    };

    // ── Load Session from URL (if exists) ──────────────────────────────────────

    useEffect(() => {
        const sessionFromUrl = searchParams.get('session');
        if (sessionFromUrl) {
            loadExistingSession(sessionFromUrl);
        }
    }, [searchParams]);

    useEffect(() => {
        setSettings((prev) => {
            const preset = LAYOUT_MODE_PRESETS[prev.layoutMode] || LAYOUT_MODE_PRESETS.advanced;
            const next = { ...prev, ...preset };
            const changed = Object.keys(preset).some((k) => prev[k] !== next[k]);
            return changed ? next : prev;
        });
    }, [settings.layoutMode]);

    const normalizeLayoutSlots = useCallback((pages = []) => {
        const normalized = [];
        const sortedPages = [...pages].sort((a, b) => Number(a?.page_number || 0) - Number(b?.page_number || 0));

        sortedPages.forEach((page) => {
            const pageNumber = Number(page?.page_number || 0);
            const panels = Array.isArray(page?.layout?.panels) ? page.layout.panels : [];
            const sortedPanels = [...panels].sort(
                (a, b) => Number(a?.panel_order ?? a?.panel_id ?? 0) - Number(b?.panel_order ?? b?.panel_id ?? 0)
            );

            sortedPanels.forEach((panel) => {
                const panelOrder = Number(panel?.panel_order ?? panel?.panel_id ?? 0);
                normalized.push({
                    globalOrder: normalized.length + 1,
                    pageNumber,
                    panelOrder,
                });
            });
        });

        return normalized;
    }, []);

    const loadFrameLayout = useCallback(async (sid = sessionId) => {
        if (!sid) return;
        setLayoutLoading(true);
        try {
            const res = await comicService.getFrameLayout(sid);
            const pages = Array.isArray(res?.pages) ? res.pages : [];
            setFrameLayout(res || null);
            setLayoutSlots(normalizeLayoutSlots(pages));
        } catch (err) {
            setFrameLayout(null);
            setLayoutSlots([]);
            console.warn('Không tải được frame-layout:', err?.message || err);
        } finally {
            setLayoutLoading(false);
        }
    }, [normalizeLayoutSlots, sessionId]);

    useEffect(() => {
        if (!layoutSlots.length) {
            setManualMapping({});
            return;
        }

        const allowedPanels = new Set(layoutSlots.map((slot) => slot.globalOrder));
        setManualMapping((prev) => {
            const next = {};
            Object.entries(prev).forEach(([k, v]) => {
                const panelOrder = Number(k);
                const fileIdx = Number(v);
                if (allowedPanels.has(panelOrder) && fileIdx >= 0 && fileIdx < selectedFiles.length) {
                    next[panelOrder] = fileIdx;
                }
            });
            return next;
        });
    }, [layoutSlots, selectedFiles]);

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
                await hydrateSessionSourceFiles(sid);
                loadFrameLayout(sid);
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

                // Ảnh dưới 200x200: hỏi người dùng muốn xóa hay vẫn giữ lại.
                if (width < 200 || height < 200) {
                    const shouldDeleteSmallImage = window.confirm(
                        `Ảnh ${name} có kích thước ${width}×${height}px (< 200×200).\n` +
                        'Ảnh này có thể bị mờ khi ghép truyện.\n\n' +
                        'OK = Xóa ảnh này\nCancel = Giữ ảnh này'
                    );

                    if (shouldDeleteSmallImage) {
                        rejected.push(`⚠️ ${name}: Đã bị xóa theo lựa chọn người dùng vì ảnh nhỏ (${width}×${height}px)`);
                        continue;
                    }
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
        const file = selectedFiles[idx];
        const shouldRemove = window.confirm(
            `Bạn có muốn bỏ ảnh này khỏi danh sách không?\n${file?.name || `Ảnh #${idx + 1}`}\n\nChọn Cancel để GIỮ ảnh.`
        );
        if (!shouldRemove) return;

        setSelectedFiles((prev) => prev.filter((_, i) => i !== idx));
        setFilesChanged(true);
    };

    const moveFile = (fromIdx, toIdx) => {
        if (toIdx < 0 || toIdx >= selectedFiles.length || fromIdx === toIdx) return;
        setSelectedFiles((prev) => {
            const next = [...prev];
            const [moved] = next.splice(fromIdx, 1);
            next.splice(toIdx, 0, moved);
            return next;
        });
        setFilesChanged(true);
    };

    const reverseFileOrder = () => {
        setSelectedFiles((prev) => [...prev].reverse());
        setFilesChanged(true);
    };

    const sortFilesByName = (direction = 'asc') => {
        setSelectedFiles((prev) => {
            const next = [...prev].sort((a, b) =>
                a.name.localeCompare(b.name, undefined, { numeric: true, sensitivity: 'base' })
            );
            return direction === 'desc' ? next.reverse() : next;
        });
        setFilesChanged(true);
    };

    const clearAllFiles = () => {
        if (selectedFiles.length > 0) {
            const shouldClear = window.confirm(
                `Bạn có chắc muốn xóa toàn bộ ${selectedFiles.length} ảnh khỏi danh sách hiện tại không?\nChọn Cancel để GIỮ ảnh.`
            );
            if (!shouldClear) return;
        }

        setSelectedFiles([]);
        setSessionId(null);
        setFilesChanged(false);
        setResultPages([]);
        setCovers({ front: null, back: null, thank_you: null });
        setCoverStatus({ front: false, back: false, thank_you: false });
        setValidationWarnings([]);
        setFrameLayout(null);
        setLayoutSlots([]);
        setManualMapping({});
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
        setFrameLayout(null);
        setLayoutSlots([]);
        setManualMapping({});

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
                enable_perspective_warp: settings.perspectiveWarp,
                draw_speech_bubbles_outside: settings.drawSpeechBubblesOutside,
                target_dpi: settings.targetDPI,
                resolution: settings.resolution,
                aspect_ratio: settings.aspectRatio,
                margin: 40,
                gap: 30,
            });

            setProgress(100);
            setStatusText('XONG RỒI! Đang tạo bản xem trước...');
            setIsCloudSyncing(true);
            
            // Poll for preview data twice to ensure we get any newly uploaded Cloud links
            const previewData = await comicService.preview(currentSessionId);
            setResultPages(previewData.pages || []);
            
            setTimeout(async () => {
                try {
                    const finalPreview = await comicService.preview(currentSessionId);
                    setResultPages(finalPreview.pages || []);
                } finally {
                    setIsCloudSyncing(false);
                }
            }, 3000);

            setPhase('done');
            loadFrameLayout(currentSessionId);

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

    const hydrateSessionSourceFiles = async (sid) => {
        try {
            const uploadRes = await comicService.getSessionUploads(sid);
            const remoteFiles = Array.isArray(uploadRes?.files) ? uploadRes.files : [];

            if (!remoteFiles.length) {
                setSelectedFiles([]);
                return;
            }

            const restored = await Promise.all(
                remoteFiles.map(async (item, idx) => {
                    const response = await fetch(item.url, { credentials: 'include' });
                    if (!response.ok) {
                        throw new Error(`Không tải lại được ảnh nguồn #${idx + 1}`);
                    }
                    const blob = await response.blob();
                    const filename = item.filename || `anh_${String(idx + 1).padStart(4, '0')}.jpg`;
                    const mime = blob.type || guessMimeFromName(filename);
                    return new File([blob], filename, {
                        type: mime,
                        lastModified: Date.now(),
                    });
                })
            );

            setSelectedFiles(restored);
            setFilesChanged(false);
        } catch (err) {
            console.warn('Không nạp lại được ảnh nguồn từ session:', err?.message || err);
            setSelectedFiles([]);
        }
    };

    const assignFileToPanel = (panelOrder, fileIdx) => {
        if (fileIdx === '' || fileIdx === null || Number.isNaN(Number(fileIdx))) {
            setManualMapping((prev) => {
                const next = { ...prev };
                delete next[panelOrder];
                return next;
            });
            return;
        }
        const parsedIndex = Number(fileIdx);
        if (parsedIndex < 0 || parsedIndex >= selectedFiles.length) return;
        setManualMapping((prev) => ({ ...prev, [panelOrder]: parsedIndex }));
    };

    const handleDirectPanelUpload = (panelOrder, file) => {
        if (!file) return;
        setSelectedFiles((prev) => {
            const newFiles = [...prev, file];
            setManualMapping((mapping) => ({ ...mapping, [panelOrder]: newFiles.length - 1 }));
            return newFiles;
        });
        setFilesChanged(true);
    };

    const handlePanelDrop = (event, panelOrder) => {
        event.preventDefault();
        setActiveDropPanel(null);

        // Hỗ trợ kéo thả file trực tiếp từ máy tính vào panel
        if (event.dataTransfer.files && event.dataTransfer.files.length > 0) {
            const file = event.dataTransfer.files[0];
            if (file.type.startsWith('image/')) {
                handleDirectPanelUpload(panelOrder, file);
            }
            return;
        }

        const dropped = event.dataTransfer.getData('text/plain');
        if (dropped !== undefined && dropped !== '') {
            const fileIdx = Number(dropped);
            if (!Number.isNaN(fileIdx)) {
                assignFileToPanel(panelOrder, fileIdx);
            }
        }
    };

    const handleFillPanelsAuto = async () => {
        if (!sessionId) {
            showError('Chưa có session để ghép ảnh');
            return;
        }
        if (selectedFiles.length === 0) {
            showError('Cần có ảnh nguồn để ghép vào khung');
            return;
        }

        setIsFillingPanels(true);
        setStatusText('Đang ghép ảnh tự động vào khung...');
        try {
            await comicService.fillPanelsAuto(sessionId, selectedFiles);
            const previewData = await comicService.preview(sessionId);
            setResultPages(previewData.pages || []);
            setStatusText('✅ Đã ghép ảnh tự động vào khung');
        } catch (err) {
            showError(err.response?.data?.detail || err.message || 'Ghép ảnh tự động thất bại');
        } finally {
            setIsFillingPanels(false);
        }
    };

    const handleFillPanelsManual = async () => {
        if (!sessionId) {
            showError('Chưa có session để ghép ảnh');
            return;
        }
        if (selectedFiles.length === 0) {
            showError('Cần có ảnh nguồn để ghép vào khung');
            return;
        }
        if (!layoutSlots.length) {
            showError('Chưa tải được layout khung');
            return;
        }
        if (Object.keys(manualMapping).length === 0) {
            showError('Bạn chưa gán ảnh vào khung nào');
            return;
        }

        setIsFillingPanels(true);
        setStatusText('Đang ghép ảnh thủ công theo mapping...');
        try {
            await comicService.fillPanelsManual(sessionId, selectedFiles, manualMapping);
            const previewData = await comicService.preview(sessionId);
            setResultPages(previewData.pages || []);
            setStatusText('✅ Đã ghép ảnh thủ công vào khung');
        } catch (err) {
            showError(err.response?.data?.detail || err.message || 'Ghép ảnh thủ công thất bại');
        } finally {
            setIsFillingPanels(false);
        }
    };

    // ── Download ───────────────────────────────────────────────────────────────

    const triggerBlobDownload = (blob, filename) => {
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = filename;
        document.body.appendChild(a);
        a.click();
        a.remove();
        window.URL.revokeObjectURL(url);
    };

    const downloadZip = async () => {
        if (!sessionId) return;
        try {
            await comicService.downloadZip(sessionId);
        } catch (err) {
            showError(`Lỗi tải ZIP: ${err.message}`);
        }
    };

    const downloadPdf = async () => {
        if (!sessionId) return;
        try {
            await comicService.downloadPdf(sessionId);
        } catch (err) {
            showError(`Lỗi tải PDF: ${err.message}`);
        }
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
                                <div className="file-order-tools">
                                    <button
                                        className="btn-order"
                                        onClick={() => sortFilesByName('asc')}
                                        disabled={isGenerating || selectedFiles.length < 2}
                                        title="Sắp theo tên tăng dần"
                                    >
                                        A→Z
                                    </button>
                                    <button
                                        className="btn-order"
                                        onClick={() => sortFilesByName('desc')}
                                        disabled={isGenerating || selectedFiles.length < 2}
                                        title="Sắp theo tên giảm dần"
                                    >
                                        Z→A
                                    </button>
                                    <button
                                        className="btn-order"
                                        onClick={reverseFileOrder}
                                        disabled={isGenerating || selectedFiles.length < 2}
                                        title="Đảo thứ tự toàn bộ"
                                    >
                                        Đảo
                                    </button>
                                    <button
                                        className="btn-text-danger"
                                        onClick={clearAllFiles}
                                        disabled={isGenerating}
                                    >
                                        Xóa tất cả
                                    </button>
                                </div>
                            </div>
                            <div className="file-grid">
                                {selectedFiles.map((file, idx) => (
                                    <div key={`${file.name}-${file.size}-${idx}`} className="file-item">
                                        <div className="file-order-badge">#{idx + 1}</div>
                                        <img
                                            src={URL.createObjectURL(file)}
                                            alt={file.name}
                                            className="file-thumb"
                                        />
                                        <div className="file-reorder-actions">
                                            <button
                                                type="button"
                                                className="file-move-btn"
                                                onClick={() => moveFile(idx, idx - 1)}
                                                disabled={isGenerating || idx === 0}
                                                title="Đưa lên trước"
                                            >
                                                ↑
                                            </button>
                                            <button
                                                type="button"
                                                className="file-move-btn"
                                                onClick={() => moveFile(idx, idx + 1)}
                                                disabled={isGenerating || idx === selectedFiles.length - 1}
                                                title="Đưa xuống sau"
                                            >
                                                ↓
                                            </button>
                                        </div>
                                        <button
                                            className="file-remove-btn"
                                            onClick={() => removeFile(idx)}
                                            disabled={isGenerating}
                                        >
                                            ✕
                                        </button>
                                        <div className="file-name" title={`Tên gốc: ${file.name}`}>
                                            {getOrderedUploadName(file, idx)}
                                        </div>
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
                                <div className="setting-group">
                                    <p className="setting-help-text">
                                        ADVANCED đang dùng cấu hình cố định: Bố cục thích ứng, Smart Crop và Phân tích nhân vật bật; Phân tích bối cảnh và Biến dạng phối cảnh tắt.
                                    </p>
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
                        <div>
                            <h2 className="result-title">✨ KẾT QUẢ CỦA BẠN</h2>
                            {isCloudSyncing && (
                                <div className="sync-badge">
                                    <span className="sync-dot"></span>
                                    ☁️ Đang đồng bộ Cloud...
                                </div>
                            )}
                        </div>
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
                                                src={`${import.meta.env.VITE_API_URL || 'https://two20539-tien-phong-tt-vl-2026.onrender.com/api/v1'}${covers[c.key]}`}
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

                    {sessionId && (
                        <div className="panel-fill-section">
                            <div className="panel-fill-header">
                                <div>
                                    <h3 className="panel-fill-title">🧩 Ghép ảnh vào template khung</h3>
                                    <p className="panel-fill-subtitle">
                                        Kéo ảnh từ danh sách nguồn vào từng panel, hoặc để hệ thống ghép tự động.
                                    </p>
                                </div>
                                <div className="panel-fill-actions">
                                    <button
                                        type="button"
                                        className="btn btn-outline"
                                        onClick={() => loadFrameLayout(sessionId)}
                                        disabled={layoutLoading || isFillingPanels}
                                    >
                                        {layoutLoading ? 'Đang tải khung...' : 'Tải lại khung'}
                                    </button>
                                    <button
                                        type="button"
                                        className="btn btn-blue"
                                        onClick={handleFillPanelsAuto}
                                        disabled={isFillingPanels || selectedFiles.length === 0 || layoutSlots.length === 0}
                                    >
                                        {isFillingPanels ? 'Đang ghép...' : 'Ghép tự động'}
                                    </button>
                                    <button
                                        type="button"
                                        className="btn btn-green"
                                        onClick={handleFillPanelsManual}
                                        disabled={
                                            isFillingPanels
                                            || selectedFiles.length === 0
                                            || layoutSlots.length === 0
                                            || Object.keys(manualMapping).length === 0
                                        }
                                    >
                                        {isFillingPanels ? 'Đang ghép...' : 'Ghép thủ công'}
                                    </button>
                                </div>
                            </div>

                            <div className="panel-fill-stats">
                                <span>Tổng khung: {layoutSlots.length}</span>
                                <span>Đã gán: {Object.keys(manualMapping).length}</span>
                                <span>Ảnh nguồn: {selectedFiles.length}</span>
                                <span>Trang template: {frameLayout?.count || 0}</span>
                            </div>

                            {selectedFiles.length > 0 && (
                                <div className="source-files-strip">
                                    {selectedFiles.map((file, idx) => (
                                        <div
                                            key={`${file.name}-${file.size}-${idx}`}
                                            className="source-file-chip"
                                            draggable={!isFillingPanels}
                                            onDragStart={(e) => {
                                                e.dataTransfer.setData('text/plain', String(idx));
                                                e.dataTransfer.effectAllowed = 'copy';
                                            }}
                                        >
                                            <img
                                                src={URL.createObjectURL(file)}
                                                alt={file.name}
                                                className="source-file-thumb"
                                            />
                                            <div className="source-file-meta">
                                                <span className="source-file-order">#{idx + 1}</span>
                                                <span className="source-file-name">{getOrderedUploadName(file, idx)}</span>
                                            </div>
                                        </div>
                                    ))}
                                </div>
                            )}

                            {layoutSlots.length > 0 ? (
                                <div className="panel-mapping-grid">
                                    {layoutSlots.map((slot) => {
                                        const mappedFileIndex = manualMapping[slot.globalOrder];
                                        const mappedFile = Number.isInteger(mappedFileIndex)
                                            ? selectedFiles[mappedFileIndex]
                                            : null;
                                        return (
                                            <div
                                                key={`panel-slot-${slot.globalOrder}`}
                                                className={`panel-map-card${mappedFile ? ' mapped' : ''}${activeDropPanel === slot.globalOrder ? ' drag-over' : ''}`}
                                                onDragOver={(e) => {
                                                    e.preventDefault();
                                                    setActiveDropPanel(slot.globalOrder);
                                                }}
                                                onDragLeave={() => setActiveDropPanel((prev) => (prev === slot.globalOrder ? null : prev))}
                                                onDrop={(e) => handlePanelDrop(e, slot.globalOrder)}
                                            >
                                                <div className="panel-map-title">
                                                    Panel #{slot.globalOrder}
                                                    <span>Trang {slot.pageNumber} · Khung {slot.panelOrder}</span>
                                                </div>

                                                {mappedFile ? (
                                                    <div className="mapped-file">
                                                        <img
                                                            src={URL.createObjectURL(mappedFile)}
                                                            alt={mappedFile.name}
                                                            className="mapped-file-thumb"
                                                        />
                                                        <div className="mapped-file-name">{getOrderedUploadName(mappedFile, mappedFileIndex)}</div>
                                                    </div>
                                                ) : (
                                                    <div className="panel-drop-hint">Thả ảnh vào đây</div>
                                                )}

                                                <select
                                                    className="panel-map-select"
                                                    value={Number.isInteger(mappedFileIndex) ? String(mappedFileIndex) : ''}
                                                    onChange={(e) => assignFileToPanel(slot.globalOrder, e.target.value)}
                                                    disabled={isFillingPanels}
                                                >
                                                    <option value="">-- Chọn ảnh thủ công --</option>
                                                    {selectedFiles.map((file, idx) => (
                                                        <option key={`opt-${slot.globalOrder}-${idx}`} value={idx}>
                                                            #{idx + 1} · {getOrderedUploadName(file, idx)}
                                                        </option>
                                                    ))}
                                                </select>

                                                <div className="panel-map-actions">
                                                    <label className={`btn-map-upload${isFillingPanels ? ' disabled' : ''}`}>
                                                        <input 
                                                            type="file"
                                                            accept="image/*"
                                                            className="hidden-input"
                                                            onChange={(e) => {
                                                                if (e.target.files && e.target.files[0]) {
                                                                    handleDirectPanelUpload(slot.globalOrder, e.target.files[0]);
                                                                }
                                                                // Reset value to allow uploading the same file again if needed
                                                                e.target.value = null;
                                                            }}
                                                            disabled={isFillingPanels}
                                                        />
                                                        Tải lên
                                                    </label>
                                                    <button
                                                        type="button"
                                                        className="btn-map-clear"
                                                        onClick={() => assignFileToPanel(slot.globalOrder, '')}
                                                        disabled={isFillingPanels || !mappedFile}
                                                    >
                                                        Bỏ gán
                                                    </button>
                                                </div>
                                            </div>
                                        );
                                    })}
                                </div>
                            ) : (
                                <div className="panel-layout-empty">
                                    Chưa có layout khung trong session này. Hãy tạo khung trước, sau đó bấm "Tải lại khung".
                                </div>
                            )}
                        </div>
                    )}

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
