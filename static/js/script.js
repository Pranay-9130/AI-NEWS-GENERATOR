async function generateNews() {
    const topicElem = document.getElementById("topic");
    const levelElem = document.getElementById("level");
    const outputElem = document.getElementById("output");
    const generateBtn = document.getElementById("generateBtn");

    const topic = topicElem.value.trim();
    const level = levelElem.value;

    if (!topic) {
        outputElem.innerHTML = '<span style="color: #f87171;">Please enter a topic to generate news.</span>';
        return;
    }

    // Enter loading state
    document.body.classList.add('loading');
    generateBtn.disabled = true;
    outputElem.innerText = 'Consulting Gemini AI and drafting your article...';

    // Smooth scroll to output on mobile
    if (window.innerWidth < 768) {
        outputElem.scrollIntoView({ behavior: 'smooth' });
    }

    try {
        const response = await fetch("/generate", {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({ topic: topic, level: level })
        });

        const data = await response.json();

        // Typewriter effect for article display
        const article = data.article;
        outputElem.innerText = '';
        let index = 0;
        
        function typeWriter() {
            if (index < article.length) {
                outputElem.innerText += article.charAt(index);
                index++;
                // Scroll to bottom as text is being typed
                outputElem.scrollTop = outputElem.scrollHeight;
                setTimeout(typeWriter, 5); // Adjust speed here (lower = faster)
            } else {
                showNotification('Article generated successfully!', 'success');
            }
        }
        
        // Start typing effect (or show immediately if article is very short)
        if (article.length > 100) {
            typeWriter();
        } else {
            outputElem.innerText = article;
            showNotification('Article generated successfully!', 'success');
        }
        
        // Add success animation to output container
        const outputContainer = document.querySelector('.output-container');
        if (outputContainer) {
            outputContainer.classList.add('success-animation');
            setTimeout(() => outputContainer.classList.remove('success-animation'), 1000);
        }

    } catch (err) {
        outputElem.innerHTML = '<span style="color: #f87171;">Failed to generate article. Please check your connection or API configuration.</span>';
        showNotification('Failed to generate article. Please try again.', 'error');
    } finally {
        // Exit loading state
        document.body.classList.remove('loading');
        generateBtn.disabled = false;
    }
}

async function copyContent() {
    const outputElem = document.getElementById("output");
    const copyBtn = document.getElementById("copyBtn");
    const text = outputElem.innerText;

    if (!text || text === 'Your AI-generated article will appear here...') return;

    try {
        await navigator.clipboard.writeText(text);

        // Visual feedback
        const originalHTML = copyBtn.innerHTML;
        copyBtn.innerHTML = '<i data-lucide="check"></i><span class="btn-text-mobile-hidden">Copied!</span>';
        lucide.createIcons();
        copyBtn.style.borderColor = '#10b981';
        copyBtn.style.color = '#10b981';
        copyBtn.classList.add('success-animation');

        setTimeout(() => {
            copyBtn.innerHTML = originalHTML;
            lucide.createIcons();
            copyBtn.style.borderColor = '';
            copyBtn.style.color = '';
            copyBtn.classList.remove('success-animation');
        }, 2000);
    } catch (err) {
        console.error('Failed to copy text: ', err);
        showNotification('Failed to copy. Please try again.', 'error');
    }
}

async function downloadContent() {
    const outputElem = document.getElementById("output");
    const text = outputElem.innerText;
    const topic = document.getElementById("topic").value || "article";

    if (!text || text === 'Your AI-generated article will appear here...') {
        showNotification('No article to download. Please generate an article first.', 'error');
        return;
    }

    try {
        const blob = new Blob([text], { type: 'text/plain' });
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `AI_News_Article_${topic.replace(/\s+/g, '_')}_${new Date().getTime()}.txt`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        window.URL.revokeObjectURL(url);
        
        showNotification('Article downloaded successfully!', 'success');
    } catch (err) {
        console.error('Failed to download: ', err);
        showNotification('Failed to download. Please try again.', 'error');
    }
}

async function shareContent() {
    const outputElem = document.getElementById("output");
    const text = outputElem.innerText;
    const topic = document.getElementById("topic").value || "AI Generated Article";

    if (!text || text === 'Your AI-generated article will appear here...') {
        showNotification('No article to share. Please generate an article first.', 'error');
        return;
    }

    const shareData = {
        title: `AI News Article: ${topic}`,
        text: text.substring(0, 500) + (text.length > 500 ? '...' : ''),
        url: window.location.href
    };

    try {
        if (navigator.share && navigator.canShare && navigator.canShare(shareData)) {
            await navigator.share(shareData);
            showNotification('Article shared successfully!', 'success');
        } else {
            // Fallback: copy to clipboard
            await navigator.clipboard.writeText(`${shareData.title}\n\n${text}\n\n${shareData.url}`);
            showNotification('Article link copied to clipboard!', 'success');
        }
    } catch (err) {
        if (err.name !== 'AbortError') {
            // Fallback: copy to clipboard
            try {
                await navigator.clipboard.writeText(`${shareData.title}\n\n${text}\n\n${shareData.url}`);
                showNotification('Article link copied to clipboard!', 'success');
            } catch (clipboardErr) {
                console.error('Failed to share: ', err);
                showNotification('Sharing not available. Please use copy or download.', 'error');
            }
        }
    }
}



function showNotification(message, type = 'info') {
    // Remove existing notification if any
    const existing = document.querySelector('.notification');
    if (existing) {
        existing.remove();
    }

    const notification = document.createElement('div');
    notification.className = `notification notification-${type}`;
    notification.innerHTML = `
        <i data-lucide="${type === 'success' ? 'check-circle' : type === 'error' ? 'alert-circle' : 'info'}"></i>
        <span>${message}</span>
    `;
    document.body.appendChild(notification);
    lucide.createIcons();

    // Animate in
    setTimeout(() => notification.classList.add('show'), 10);

    // Remove after 3 seconds
    setTimeout(() => {
        notification.classList.remove('show');
        setTimeout(() => notification.remove(), 300);
    }, 3000);
}

// Dashboard Tab Switching
function switchTab(tabName) {
    // Hide all tab contents
    document.querySelectorAll('.tab-content').forEach(tab => {
        tab.classList.remove('active');
    });
    
    // Remove active class from all tab buttons
    document.querySelectorAll('.tab-btn').forEach(btn => {
        btn.classList.remove('active');
    });
    
    // Show selected tab content
    const selectedTab = document.getElementById(`${tabName}-tab`);
    if (selectedTab) {
        selectedTab.classList.add('active');
    }
    
    // Activate selected tab button
    const selectedBtn = document.querySelector(`[data-tab="${tabName}"]`);
    if (selectedBtn) {
        selectedBtn.classList.add('active');
    }
    
    // Show/hide output containers based on active tab
    if (tabName === 'article') {
        document.getElementById('articleOutput').style.display = 'block';
        document.getElementById('eventContentContainer').style.display = 'none';
    } else if (tabName === 'upload') {
        document.getElementById('articleOutput').style.display = 'none';
        // eventContentContainer shown when content is generated
    }
    
    // Reinitialize icons
    lucide.createIcons();
}

// File Upload Handling
let uploadedFile = null;

function handleFileSelect(event) {
    const file = event.target.files[0];
    if (file) {
        if (file.size > 10 * 1024 * 1024) {
            showNotification('File size must be less than 10MB', 'error');
            return;
        }
        const isImage = file.type && file.type.startsWith('image/');
        const isPdf = file.type === 'application/pdf' || file.name.toLowerCase().endsWith('.pdf');
        if (!isImage && !isPdf) {
            showNotification('Please upload an image or PDF brochure', 'error');
            return;
        }
        uploadedFile = file;
        if (isImage) {
            displayPreview(file);
        } else {
            displayPdfPlaceholder(file);
        }
    }
}

function displayPreview(file) {
    const reader = new FileReader();
    reader.onload = function(e) {
        const preview = document.getElementById('uploadPreview');
        const placeholder = document.querySelector('.upload-placeholder');
        const previewImage = document.getElementById('previewImage');
        const pdfInfo = document.getElementById('previewPdfInfo');
        const analyzeBtn = document.getElementById('analyzeBtn');

        previewImage.src = e.target.result;
        previewImage.style.display = 'block';
        if (pdfInfo) {
            pdfInfo.style.display = 'none';
        }
        placeholder.style.display = 'none';
        preview.style.display = 'block';
        analyzeBtn.style.display = 'flex';

        lucide.createIcons();
    };
    reader.readAsDataURL(file);
}

function displayPdfPlaceholder(file) {
    const preview = document.getElementById('uploadPreview');
    const placeholder = document.querySelector('.upload-placeholder');
    const previewImage = document.getElementById('previewImage');
    const pdfInfo = document.getElementById('previewPdfInfo');
    const pdfName = document.getElementById('previewPdfName');
    const analyzeBtn = document.getElementById('analyzeBtn');

    if (previewImage) {
        previewImage.style.display = 'none';
        previewImage.src = '';
    }
    if (pdfInfo) {
        pdfInfo.style.display = 'flex';
    }
    if (pdfName) {
        pdfName.textContent = file.name;
    }

    placeholder.style.display = 'none';
    preview.style.display = 'block';
    analyzeBtn.style.display = 'flex';

    lucide.createIcons();
}

function removeUploadedImage() {
    uploadedFile = null;
    const preview = document.getElementById('uploadPreview');
    const placeholder = document.querySelector('.upload-placeholder');
    const analyzeBtn = document.getElementById('analyzeBtn');
    const fileInput = document.getElementById('photoUpload');
    
    const previewImage = document.getElementById('previewImage');
    const pdfInfo = document.getElementById('previewPdfInfo');
    const pdfName = document.getElementById('previewPdfName');

    placeholder.style.display = 'flex';
    preview.style.display = 'none';
    analyzeBtn.style.display = 'none';
    fileInput.value = '';
    if (previewImage) {
        previewImage.src = '';
        previewImage.style.display = 'none';
    }
    if (pdfInfo) {
        pdfInfo.style.display = 'none';
    }
    if (pdfName) {
        pdfName.textContent = '';
    }
}

// Drag and Drop
document.addEventListener('DOMContentLoaded', function() {
    const uploadArea = document.getElementById('uploadArea');
    const fileInput = document.getElementById('photoUpload');
    
    if (uploadArea) {
        uploadArea.addEventListener('dragover', function(e) {
            e.preventDefault();
            uploadArea.classList.add('dragover');
        });
        
        uploadArea.addEventListener('dragleave', function(e) {
            e.preventDefault();
            uploadArea.classList.remove('dragover');
        });
        
        uploadArea.addEventListener('drop', function(e) {
            e.preventDefault();
            uploadArea.classList.remove('dragover');
            
            const files = e.dataTransfer.files;
            if (files.length > 0) {
                fileInput.files = files;
                handleFileSelect({ target: { files: files } });
            }
        });
    }
    
    // Enter key support for article generation
    const topicInput = document.getElementById("topic");
    if (topicInput) {
        topicInput.addEventListener('keypress', function(e) {
            if (e.key === 'Enter') {
                generateNews();
            }
        });
    }

});

// Analyze Image and Generate Content
async function analyzeAndGenerateContent() {
    if (!uploadedFile) {
        showNotification('Please upload an image first', 'error');
        return;
    }
    
    const analyzeBtn = document.getElementById('analyzeBtn');
    const eventContentContainer = document.getElementById('eventContentContainer');
    
    // Enter loading state
    document.body.classList.add('loading');
    analyzeBtn.disabled = true;
    analyzeBtn.innerHTML = '<div class="loader" style="display: block;"></div><span class="btn-text">Analyzing...</span>';
    
    eventContentContainer.style.display = 'block';
    eventContentContainer.scrollIntoView({ behavior: 'smooth' });
    
    // Show loading in content area
    document.getElementById('eventDetails').innerHTML = '<tr><td colspan="2" class="event-details-loading">Analyzing image and generating content...</td></tr>';
    document.getElementById('linkedin-text').innerHTML = '<p style="text-align: center; color: var(--text-secondary);">Generating...</p>';
    document.getElementById('instagram-text').innerHTML = '<p style="text-align: center; color: var(--text-secondary);">Generating...</p>';
    document.getElementById('whatsapp-text').innerHTML = '<p style="text-align: center; color: var(--text-secondary);">Generating...</p>';
    
    try {
        const formData = new FormData();
        formData.append('image', uploadedFile);
        
        const response = await fetch('/analyze-event-image', {
            method: 'POST',
            body: formData
        });
        
        const data = await response.json();
        
        if (data.error) {
            throw new Error(data.error);
        }
        
        // Display event details
        displayEventDetails(data.event_details);
        
        // Display platform content
        document.getElementById('linkedin-text').innerText = data.content.linkedin;
        document.getElementById('instagram-text').innerText = data.content.instagram;
        document.getElementById('whatsapp-text').innerText = data.content.whatsapp;
        
        showNotification('Content generated successfully!', 'success');
        eventContentContainer.classList.add('success-animation');
        setTimeout(() => eventContentContainer.classList.remove('success-animation'), 1000);
        
    } catch (err) {
        const message = (err && err.message) ? err.message : 'Failed to analyze image. Please try again.';
        showNotification(message, 'error');
        console.error('Error:', err);
    } finally {
        document.body.classList.remove('loading');
        analyzeBtn.disabled = false;
        analyzeBtn.innerHTML = '<i data-lucide="sparkles"></i><span class="btn-text">Analyze & Generate Content</span><div class="loader"></div>';
        lucide.createIcons();
    }
}

function displayEventDetails(details) {
    const clean = (v) => (v && typeof v === 'string' ? v.replace(/\*+/g, '').trim() : '') || 'N/A';
    const rows = [
        ['Tech Event Name', details.tech_event_name],
        ['Organising Department', details.organising_department],
        ['Date', details.date],
        ['Start Time', details.start_time],
        ['End Time', details.end_time],
        ['Title', details.title],
        ['Purpose', details.purpose],
        ['Key Persons / Authors / Speakers', details.key_persons]
    ];
    const detailsHTML = rows.map(([label, value]) =>
        `<tr><td class="event-detail-label">${label}</td><td class="event-detail-value">${clean(value)}</td></tr>`
    ).join('');
    document.getElementById('eventDetails').innerHTML = detailsHTML;
}

function showPlatformContent(platform) {
    // Hide all platform content
    document.querySelectorAll('.platform-content').forEach(content => {
        content.classList.remove('active');
    });
    
    // Remove active class from all tabs
    document.querySelectorAll('.platform-tab').forEach(tab => {
        tab.classList.remove('active');
    });
    
    // Show selected platform content
    const selectedContent = document.getElementById(`${platform}-content`);
    if (selectedContent) {
        selectedContent.classList.add('active');
    }
    
    // Activate selected tab
    const selectedTab = document.querySelector(`.platform-tab[onclick="showPlatformContent('${platform}')"]`);
    if (selectedTab) {
        selectedTab.classList.add('active');
    }
}

function copyPlatformContent(platform) {
    const content = document.getElementById(`${platform}-text`).innerText;
    if (!content || content === 'Generating...') {
        showNotification('No content to copy', 'error');
        return;
    }
    
    navigator.clipboard.writeText(content).then(() => {
        showNotification(`${platform.charAt(0).toUpperCase() + platform.slice(1)} content copied!`, 'success');
    }).catch(err => {
        showNotification('Failed to copy content', 'error');
    });
}

async function sharePlatformContent(platform) {
    const content = document.getElementById(`${platform}-text`).innerText;
    if (!content || content === 'Generating...') {
        showNotification('No content to share', 'error');
        return;
    }

    const title = `${platform.charAt(0).toUpperCase() + platform.slice(1)} content`;
    try {
        if (navigator.share) {
            await navigator.share({
                title,
                text: content
            });
            showNotification('Shared successfully!', 'success');
        } else {
            await navigator.clipboard.writeText(content);
            showNotification('Sharing not available. Content copied!', 'info');
        }
    } catch (err) {
        if (err.name !== 'AbortError') {
            try {
                await navigator.clipboard.writeText(content);
                showNotification('Share failed. Content copied!', 'info');
            } catch (e) {
                showNotification('Share failed. Please use Copy.', 'error');
            }
        }
    }
}
