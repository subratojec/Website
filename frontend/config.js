// Global Configuration for Frontend
// This automatically switches between your local backend and your deployed Render backend.

const SANITY_PROJECT_ID = 'sxojyb6p';
const SANITY_DATASET = 'production';
const SANITY_API_VERSION = '2023-01-01';

// Helper function to build Sanity GROQ query URLs
function getSanityUrl(query) {
    return `https://${SANITY_PROJECT_ID}.api.sanity.io/v${SANITY_API_VERSION}/data/query/${SANITY_DATASET}?query=${encodeURIComponent(query)}`;
}
// Hamburger Menu Logic
document.addEventListener("DOMContentLoaded", () => {
    const hamburger = document.querySelector(".hamburger");
    const navLinks = document.querySelector(".nav-links");
    
    if (hamburger && navLinks) {
        hamburger.addEventListener("click", () => {
            hamburger.classList.toggle("active");
            navLinks.classList.toggle("active");
        });
    }
});
