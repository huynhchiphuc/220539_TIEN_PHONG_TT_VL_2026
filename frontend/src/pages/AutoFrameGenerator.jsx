import { useState } from 'react';
import { comicService } from '../services/comicService';
import './AutoFrameGenerator.css';

const RESOLUTION_OPTIONS = ['1K', '2K', '4K'];
const ASPECT_OPTIONS = ['1:1', '2:3', '3:2', '3:4', '4:3', '4:5', '5:4', '9:16', '16:9', '21:9'];

const AutoFrameGenerator = () => {
  const [form, setForm] = useState({
    panelsPerPage: 5,
    diagonalPercent: 30,
    aspectRatio: '16:9',
    resolution: '2K',
    pagesCount: 1,
  });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [result, setResult] = useState(null);

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

  const handleGenerate = async (event) => {
    event.preventDefault();
    setLoading(true);
    setError('');
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
      setResult(data);
    } catch (err) {
      setError(err.response?.data?.detail || err.message || 'Không thể tạo khung tự động');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="auto-frame-page">
      <div className="auto-frame-card">
        <h1>Tao khung truyen tu dong</h1>
        <p className="auto-frame-subtitle">
          Khong can upload anh. Chon thong so, nhan Enter hoac bam nut de tao bo khung comic.
        </p>

        <form className="auto-frame-form" onSubmit={handleGenerate}>
          <label>
            So khung moi trang
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
            Do nghieng khung (%)
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
            Ti le trang
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
            Kich thuoc trang
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
            So trang can tao
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
            {loading ? 'Dang tao...' : 'Tao khung tu dong'}
          </button>
        </form>

        {loading && (
          <div className="auto-frame-loading">
            Dang tao bo khung... he thong se tra ket qua trong vai giay.
          </div>
        )}

        {error && <div className="auto-frame-error">{error}</div>}

        {result?.pages?.length > 0 && (
          <div className="auto-frame-result">
            <h2>Ket qua ({result.pages.length} trang)</h2>
            <div className="auto-frame-grid">
              {result.pages.map((pageUrl, index) => (
                <a
                  key={pageUrl}
                  href={toAbsoluteUrl(pageUrl)}
                  target="_blank"
                  rel="noreferrer"
                  className="auto-frame-item"
                >
                  <img src={toAbsoluteUrl(pageUrl)} alt={`Page ${index + 1}`} loading="lazy" />
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
