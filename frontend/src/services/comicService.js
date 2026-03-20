import api from './api';

const BASE = '/comic';

export const comicService = {
    /**
     * Upload nhiều ảnh lên server, trả về session_id
     * @param {File[]} files - Mảng các file ảnh
     * @param {Function} onProgress - Callback tiến độ (0-100)
     * @returns {Promise<{success, session_id, files, count}>}
     */
    uploadImages: async (files, onProgress) => {
        const formData = new FormData();
        files.forEach((file) => formData.append('files', file));

        const response = await api.post(`${BASE}/upload`, formData, {
            headers: { 'Content-Type': 'multipart/form-data' },
            onUploadProgress: (evt) => {
                if (onProgress && evt.total) {
                    onProgress(Math.round((evt.loaded * 100) / evt.total));
                }
            },
        });
        return response.data;
    },

    /**
     * Tạo comic book từ ảnh đã upload
     * @param {Object} params - Tham số generate (session_id, layout_mode, ...)
     * @returns {Promise<{success, session_id, pages, layout_mode}>}
     */
    generate: async (params) => {
        const response = await api.post(`${BASE}/generate`, params, {
            headers: { 'Content-Type': 'application/json' },
            timeout: 300000, // 5 phút vì AI processing có thể lâu
        });
        return response.data;
    },

    generateAutoFrames: async (params) => {
        const response = await api.post(`${BASE}/auto-frames`, params, {
            headers: { 'Content-Type': 'application/json' },
            timeout: 120000,
        });
        return response.data;
    },

    saveSessionToCloud: async (sessionId) => {
        const response = await api.post(`${BASE}/sessions/${sessionId}/save-cloud`);
        return response.data;
    },

    /**
     * Lấy danh sách URL các trang comic đã tạo
     * @param {string} sessionId
     * @returns {Promise<{success, pages: string[]}>}
     */
    preview: async (sessionId) => {
        const response = await api.get(`${BASE}/preview/${sessionId}`);
        return response.data;
    },

    downloadZip: async (sessionId) => {
        const token = localStorage.getItem('access_token');
        const apiBase = import.meta.env.VITE_API_URL || 'https://two20539-tien-phong-tt-vl-2026.onrender.com/api/v1';
        window.location.href = `${apiBase}${BASE}/download/${sessionId}?token=${token}`;
        return true;
    },

    downloadPdf: async (sessionId) => {
        const token = localStorage.getItem('access_token');
        const apiBase = import.meta.env.VITE_API_URL || 'https://two20539-tien-phong-tt-vl-2026.onrender.com/api/v1';
        
        // Mở URL mới để backend trả file trực tiếp, dùng url param token
        window.location.href = `${apiBase}${BASE}/download_pdf/${sessionId}?token=${token}`;
        
        // Không dùng axios tải file để tránh crash trình duyệt
        return true;
    },

    /**
     * Upload ảnh bìa (front/back/thank_you)
     * @param {string} sessionId
     * @param {string} coverType - 'front' | 'back' | 'thank_you'
     * @param {File} file
     * @returns {Promise<{success, cover_type, url}>}
     */
    uploadCover: async (sessionId, coverType, file) => {
        const formData = new FormData();
        formData.append('file', file);

        const response = await api.post(
            `${BASE}/upload_cover/${sessionId}?cover_type=${coverType}`,
            formData,
            { headers: { 'Content-Type': 'multipart/form-data' } }
        );
        return response.data;
    },

    /**
     * Kiểm tra trạng thái các AI features
     * @returns {Promise<Object>}
     */
    getAiCapabilities: async () => {
        const response = await api.get(`${BASE}/ai_capabilities`);
        return response.data;
    },

    /**
     * Xóa session (upload + output)
     * @param {string} sessionId
     */
    clearSession: async (sessionId) => {
        const response = await api.delete(`${BASE}/clear/${sessionId}`);
        return response.data;
    },
};
