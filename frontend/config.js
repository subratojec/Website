// Global Configuration for Frontend
// This automatically switches between your local backend and your deployed Render backend.

const API_URL = (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1')
    ? 'http://localhost:8000'
    : 'https://website-1-ot33.onrender.com';
