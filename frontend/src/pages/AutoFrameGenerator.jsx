import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { comicService } from '../services/comicService';
import './AutoFrameGenerator.css';

const RESOLUTION_OPTIONS = ['1K', '2K', '4K'];
const ASPECT_OPTIONS = ['1:1', '2:3', '3:2', '3:4', '4:3', '4:5', '5:4', '9:16', '16:9', '21:9'];

const AutoFrameGenerator = () => {
  const navigate = useNavigate();
  const [form, setForm] = useState({
    panelsPerPage: 5,
    diagonalPercent: 30,
    aspectRatio: '9:16',
    resolution: '2K',
    pagesCount: 1,
  });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [result, setResult] = useState(null);
  const [renderNonce, setRenderNonce] = useState(0);
  const [saveLoading, setSaveLoading] = useState(false);
  const [downloadLoading, setDownloadLoading] = useState(false);
  const [actionMessage, setActionMessage] = useState('');

  const toAbsoluteUrl = (url) => {
    if (!url) return '';
    if (/^https?:\/\//i.test(url)) return url;
    const apiBase = import.meta.env.VITE_API_URL || 'https://two20539-tien-phong-tt-vl-2026.onrender.com/api/v1';
    const origin = apiBase.replace(/\/api\/v1\/?$/i, '');
    if (url.startsWith('/')) return `${origin}${url}`;
    return `${origin}/${url}`;
  };

  const update = (key, value) => {
    setForm((prev) => ({ ...prev, [key]: value }));
  };

  const withCacheBust = (url, nonce, index) => {
    if (!url) return '';
    const token = `cb=${nonce}-${index}`;
    return url.includes('?') ? `${url}&${token}` : `${url}?${token}`;
  };

  const handleGenerate = async (event) => {
    event.preventDefault();
    setLoading(true);
    setError('');
    setActionMessage('');
    setResult(null);

    try {
      const payload = {
        panels_per_page: Number(form.panelsPerPage),
        diagonal_prob: Number(form.diagonalPercent) / 100,
        aspect_ratio: form.aspectRatio,
        resolution: form.resolution,
        pages_count: Number(form.pagesCount),
      };

      const data = await comicService.generateAutoFrames(payload);
      setRenderNonce(Date.now());
      setResult(data);
    } catch (err) {
      setError(err.response?.data?.detail || err.message || 'Không thể tạo khung tự động');
    } finally {
      setLoading(false);
    }
  };

  const handleSaveCloud = async () => {
    if (!result?.session_id) {
      setError('Chưa có phiên để lưu dự án');
      return;
    }
    setSaveLoading(true);
    setError('');
    setActionMessage('');
    try {
      const saved = await comicService.saveSessionToCloud(result.session_id);
      setActionMessage(`Đã lưu dự án thành công ${saved.saved_count || 0} trang`);
    } catch (err) {
      setError(err.response?.data?.detail || err.message || 'Không thể lưu dự án');
    } finally {
      setSaveLoading(false);
    }
  };

  const handleDownloadPdf = async () => {
    if (!result?.session_id) {
      setError('Chưa có phiên để tải PDF');
      return;
    }
    setDownloadLoading(true);
    setError('');
    setActionMessage('');
    try {
      const saved = await comicService.saveSessionToCloud(result.session_id);
      setActionMessage(`Đã lưu dự án ${saved.saved_count || 0} trang, đang tải PDF...`);
      await comicService.downloadPdf(result.session_id);
    } catch (err) {
      setError(err.response?.data?.detail || err.message || 'Không thể tải PDF');
    } finally {
      setDownloadLoading(false);
    }
  };

  return (
    <div className="auto-frame-page">
      <div className="auto-frame-card">
        <div className="auto-frame-hero">
          <span className="auto-frame-badge">TẠO KHUNG TỰ ĐỘNG</span>
          <h1>Tạo bộ khung truyện tự động với bố cục linh hoạt</h1>
          <p className="auto-frame-subtitle">
            Không cần upload ảnh. Chọn thông số, nhấn Tạo khung và hệ thống sẽ sinh trang panel với tỉ lệ cân bằng, gutter đều, sẵn sàng để lưu dự án hoặc tải PDF ngay lập tức.
          </p>
        </div>

        <form className="auto-frame-form" onSubmit={handleGenerate}>
          <label>
            Số khung mỗi trang
            <input
              type="number"
              min="2"
              max="10"
              value={form.panelsPerPage}
              onChange={(e) => update('panelsPerPage', e.target.value)}
              required
            />
          </label>

          <label>
            Độ ngẫu nhiên bố cục (%)
            <input
              type="number"
              min="0"
              max="100"
              value={form.diagonalPercent}
              onChange={(e) => update('diagonalPercent', e.target.value)}
              required
            />
          </label>

          <label>
            Tỉ lệ trang
            <select
              value={form.aspectRatio}
              onChange={(e) => update('aspectRatio', e.target.value)}
            >
              {ASPECT_OPTIONS.map((value) => (
                <option key={value} value={value}>{value}</option>
              ))}
            </select>
          </label>

          <label>
            Kích thước trang
            <select
              value={form.resolution}
              onChange={(e) => update('resolution', e.target.value)}
            >
              {RESOLUTION_OPTIONS.map((value) => (
                <option key={value} value={value}>{value}</option>
              ))}
            </select>
          </label>

          <label>
            Số trang cần tạo
            <input
              type="number"
              min="1"
              max="50"
              value={form.pagesCount}
              onChange={(e) => update('pagesCount', e.target.value)}
              required
            />
          </label>

          <button type="submit" disabled={loading}>
            {loading ? 'Đang tạo...' : 'Tạo khung'}
          </button>
        </form>

        {loading && (
          <div className="auto-frame-loading">
            Đang tạo bộ khung... hệ thống sẽ trả kết quả trong vài giây.
          </div>
        )}

        {error && <div className="auto-frame-error">{error}</div>}

        {result?.pages?.length > 0 && (
          <div className="auto-frame-result">
            <h2>Kết quả ({result.pages.length} trang)</h2>
            <div className="auto-frame-actions">
              <button type="button" onClick={handleSaveCloud} disabled={saveLoading || downloadLoading}>
                {saveLoading ? 'Đang lưu dự án...' : 'Lưu dự án'}
              </button>
              <button type="button" onClick={handleDownloadPdf} disabled={saveLoading || downloadLoading}>
                {downloadLoading ? 'Đang xử lý...' : 'Tải PDF và lưu dự án'}
              </button>
              <button 
                type="button" 
                onClick={() => navigate(`/comic?session=${result.session_id}`)}
                className="btn-go-session"
              >
                Đi đến ghép ảnh (Session hiện tại)
              </button>
            </div>
            {actionMessage && <div className="auto-frame-success">{actionMessage}</div>}
            <div className="auto-frame-grid">
              {result.pages.map((pageUrl, index) => (
                <a
                  key={`${pageUrl}-${renderNonce}-${index}`}
                  href={withCacheBust(toAbsoluteUrl(pageUrl), renderNonce, index)}
                  target="_blank"
                  rel="noreferrer"
                  className="auto-frame-item"
                >
                  <img
                    src={withCacheBust(toAbsoluteUrl(pageUrl), renderNonce, index)}
                    alt={`Page ${index + 1}`}
                    loading="lazy"
                  />
                  <span>Trang {index + 1}</span>
                </a>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default AutoFrameGenerator;
