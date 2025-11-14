// API Configuration
// Có thể override bằng environment variable hoặc config file
const API_CONFIG = {
    // API URL - sẽ được set tự động dựa trên environment
    // Development: http://localhost:8000
    // Production: sẽ được set khi deploy
    baseURL: (() => {
        // Kiểm tra nếu có config từ window (có thể set từ build process)
        if (window.API_BASE_URL) {
            return window.API_BASE_URL;
        }
        // Kiểm tra environment variable (cho build tools)
        if (typeof process !== 'undefined' && process.env && process.env.REACT_APP_API_URL) {
            return process.env.REACT_APP_API_URL;
        }
        // Default: relative path (same origin)
        return '';
    })()
};

// Helper function để get full API URL
function getAPIUrl(endpoint) {
    const base = API_CONFIG.baseURL.replace(/\/$/, ''); // Remove trailing slash
    const path = endpoint.startsWith('/') ? endpoint : `/${endpoint}`;
    return `${base}${path}`;
}

