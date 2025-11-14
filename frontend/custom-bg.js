// custom-bg.js
const uploadBtn = document.getElementById('bg-upload-btn');
const uploadInput = document.getElementById('bg-upload');
const resetBtn = document.getElementById('bg-reset-btn');
const bgDiv = document.querySelector('.background-img');

const DEFAULT_BG = "/img/default-background.jpeg";

function setBodyBg(url) {
    if (bgDiv) {
        bgDiv.style.backgroundImage = `url('${url}')`;
        bgDiv.style.backgroundSize = 'cover';
        bgDiv.style.backgroundRepeat = 'no-repeat';
        bgDiv.style.backgroundPosition = 'center center';
        bgDiv.style.backgroundAttachment = 'fixed';
    }
}

// On load, check localStorage
const savedBg = localStorage.getItem('customBg');
if (savedBg) {
    setBodyBg(savedBg);
} else {
    setBodyBg(DEFAULT_BG);
}

uploadBtn.onclick = () => uploadInput.click();
uploadInput.onchange = (e) => {
    const file = e.target.files[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onload = function(evt) {
        setBodyBg(evt.target.result);
        localStorage.setItem('customBg', evt.target.result);
    };
    reader.readAsDataURL(file);
};
resetBtn.onclick = () => {
    setBodyBg(DEFAULT_BG);
    localStorage.removeItem('customBg');
    // Also force a reload to restore sidebar color if needed
    setTimeout(() => window.location.reload(), 100);
}; 