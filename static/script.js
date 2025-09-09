// Audio player controls and form enhancements
document.addEventListener('DOMContentLoaded', function() {
    const audioPlayer = document.getElementById('audioPlayer');
    const transcriptionForm = document.getElementById('transcriptionForm');
    const transcriptionTextarea = document.getElementById('transcription');
    
    // Initialize page
    initializeAudio();
    initializeForm();
    initializeCustomAudioPlayer();
    initializeGuidelines();
    initializeIME();
    
    // Auto-hide messages after 5 seconds
    hideMessagesAfterDelay();
});

/**
 * Initialize custom audio player
 */
function initializeCustomAudioPlayer() {
    const audioPlayer = document.getElementById('audioPlayer');
    const progressBar = document.getElementById('progressBar');
    const progressHandle = document.getElementById('progressHandle');
    const progressContainer = document.querySelector('.audio-progress');
    const currentTimeEl = document.getElementById('currentTime');
    const totalTimeEl = document.getElementById('totalTime');
    const durationEl = document.getElementById('audioDuration');
    const speedEl = document.getElementById('audioSpeed');
    const playPauseBtn = document.getElementById('playPauseBtn');
    
    if (!audioPlayer) return;
    
    let isDragging = false;
    
    // Update progress bar
    function updateProgress() {
        if (isDragging) return;
        
        const progress = (audioPlayer.currentTime / audioPlayer.duration) * 100;
        progressBar.style.width = progress + '%';
        progressHandle.style.left = progress + '%';
        
        currentTimeEl.textContent = formatTime(audioPlayer.currentTime);
    }
    
    // Format time in MM:SS format
    function formatTime(seconds) {
        if (isNaN(seconds)) return '0:00';
        const mins = Math.floor(seconds / 60);
        const secs = Math.floor(seconds % 60);
        return mins + ':' + (secs < 10 ? '0' : '') + secs;
    }
    
    // Audio event listeners
    audioPlayer.addEventListener('timeupdate', updateProgress);
    
    audioPlayer.addEventListener('loadedmetadata', function() {
        totalTimeEl.textContent = formatTime(audioPlayer.duration);
        durationEl.textContent = formatTime(audioPlayer.duration);
    });
    
    audioPlayer.addEventListener('play', function() {
        document.querySelector('.play-icon').style.display = 'none';
        document.querySelector('.pause-icon').style.display = 'block';
        document.querySelector('.custom-audio-player').classList.remove('audio-loading');
    });
    
    audioPlayer.addEventListener('pause', function() {
        document.querySelector('.play-icon').style.display = 'block';
        document.querySelector('.pause-icon').style.display = 'none';
    });
    
    audioPlayer.addEventListener('ended', function() {
        document.querySelector('.play-icon').style.display = 'block';
        document.querySelector('.pause-icon').style.display = 'none';
        progressBar.style.width = '0%';
        progressHandle.style.left = '0%';
        
        // Auto-focus on transcription when audio ends
        const transcriptionTextarea = document.getElementById('transcription');
        if (transcriptionTextarea) {
            transcriptionTextarea.focus();
        }
    });
    
    audioPlayer.addEventListener('loadstart', function() {
        document.querySelector('.custom-audio-player').classList.add('audio-loading');
    });
    
    audioPlayer.addEventListener('canplay', function() {
        document.querySelector('.custom-audio-player').classList.remove('audio-loading');
    });
    
    audioPlayer.addEventListener('error', function() {
        document.querySelector('.custom-audio-player').classList.add('audio-error');
    });
    
    // Progress bar interaction
    if (progressContainer) {
        progressContainer.addEventListener('click', function(e) {
            const rect = progressContainer.getBoundingClientRect();
            const clickX = e.clientX - rect.left;
            const percentage = clickX / rect.width;
            const newTime = percentage * audioPlayer.duration;
            
            audioPlayer.currentTime = newTime;
        });
        
        // Progress handle dragging
        progressHandle.addEventListener('mousedown', function(e) {
            isDragging = true;
            e.preventDefault();
        });
        
        document.addEventListener('mousemove', function(e) {
            if (!isDragging) return;
            
            const rect = progressContainer.getBoundingClientRect();
            const clickX = e.clientX - rect.left;
            const percentage = Math.max(0, Math.min(1, clickX / rect.width));
            
            progressBar.style.width = (percentage * 100) + '%';
            progressHandle.style.left = (percentage * 100) + '%';
            
            if (audioPlayer.duration) {
                audioPlayer.currentTime = percentage * audioPlayer.duration;
            }
        });
        
        document.addEventListener('mouseup', function() {
            isDragging = false;
        });
    }
}

/**
 * Initialize audio player functionality
 */
function initializeAudio() {
    const audioPlayer = document.getElementById('audioPlayer');
    if (!audioPlayer) return;
    
    // Debug audio source
    console.log('Audio player initialized');
    console.log('Audio sources:', Array.from(audioPlayer.querySelectorAll('source')).map(s => s.src));
    
    // Auto-focus on transcription when audio ends
    audioPlayer.addEventListener('ended', function() {
        const transcriptionTextarea = document.getElementById('transcription');
        if (transcriptionTextarea) {
            transcriptionTextarea.focus();
        }
    });
    
    // Handle audio loading errors
    audioPlayer.addEventListener('error', function(e) {
        console.error('Audio loading error:', e);
        console.error('Audio error details:', {
            error: audioPlayer.error,
            networkState: audioPlayer.networkState,
            readyState: audioPlayer.readyState
        });
        showNotification('Error loading audio file. Check console for details.', 'error');
    });
    
    // Handle source errors
    audioPlayer.querySelectorAll('source').forEach((source, index) => {
        source.addEventListener('error', function(e) {
            console.error(`Source ${index + 1} error:`, e);
            console.error('Source URL:', source.src);
        });
    });
    
    // Show loading state
    // audioPlayer.addEventListener('loadstart', function() {
    //     console.log('Audio loading started...');
    //     showNotification('Loading audio...', 'info', 2000);
    // });
    
    // audioPlayer.addEventListener('canplay', function() {
    //     console.log('Audio ready to play');
    //     showNotification('Audio loaded successfully', 'success', 2000);
    // });
    
    audioPlayer.addEventListener('loadeddata', function() {
        console.log('Audio data loaded');
    });
    
    audioPlayer.addEventListener('loadedmetadata', function() {
        console.log('Audio metadata loaded, duration:', audioPlayer.duration);
    });
    
    // Test if we can play the audio
    audioPlayer.addEventListener('canplaythrough', function() {
        console.log('Audio can play through without buffering');
    });
    
    // Monitor network state
    audioPlayer.addEventListener('stalled', function() {
        console.warn('Audio download stalled');
        showNotification('Audio download stalled. Check your connection.', 'error');
    });
    
    audioPlayer.addEventListener('suspend', function() {
        console.log('Audio download suspended');
    });
    
    audioPlayer.addEventListener('abort', function() {
        console.warn('Audio download aborted');
        showNotification('Audio download was interrupted.', 'error');
    });
}

/**
 * Initialize form functionality
 */
function initializeForm() {
    const transcriptionForm = document.getElementById('transcriptionForm');
    const transcriptionTextarea = document.getElementById('transcription');
    
    if (!transcriptionForm || !transcriptionTextarea) return;
    
    // Auto-resize textarea
    transcriptionTextarea.addEventListener('input', function() {
        this.style.height = 'auto';
        this.style.height = this.scrollHeight + 'px';
    });
    
    // Form validation
    transcriptionForm.addEventListener('submit', function(e) {
        const transcription = transcriptionTextarea.value.trim();
        const speakerGender = document.getElementById('speaker_gender').value;
        
        if (!transcription) {
            e.preventDefault();
            showNotification('Please provide a transcription before submitting.', 'error');
            transcriptionTextarea.focus();
            return;
        }
        
        if (!speakerGender) {
            e.preventDefault();
            showNotification('Please select the speaker gender.', 'error');
            document.getElementById('speaker_gender').focus();
            return;
        }
        
        if (transcription.length < 3) {
            e.preventDefault();
            showNotification('Transcription seems too short. Please provide a more detailed transcription.', 'error');
            transcriptionTextarea.focus();
            return;
        }
        
        // Show loading state
        const submitButton = transcriptionForm.querySelector('button[type="submit"]');
        if (submitButton) {
            submitButton.textContent = '⏳ Submitting...';
            submitButton.disabled = true;
        }
    });
    
    // Keyboard shortcuts
    document.addEventListener('keydown', function(e) {
        // Ctrl/Cmd + Enter to submit form
        if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') {
            e.preventDefault();
            transcriptionForm.dispatchEvent(new Event('submit'));
        }
        
        // Space to play/pause audio when not typing
        if (e.code === 'Space' && e.target.tagName !== 'INPUT' && e.target.tagName !== 'TEXTAREA') {
            e.preventDefault();
            toggleAudio();
        }
        
        // Arrow keys for seeking when not typing
        if (e.target.tagName !== 'INPUT' && e.target.tagName !== 'TEXTAREA') {
            if (e.key === 'ArrowLeft') {
                e.preventDefault();
                skipBackward();
            } else if (e.key === 'ArrowRight') {
                e.preventDefault();
                skipForward();
            }
        }
        
        // Number keys for speed control when not typing
        if (e.target.tagName !== 'INPUT' && e.target.tagName !== 'TEXTAREA') {
            if (e.key === '1') {
                e.preventDefault();
                adjustSpeed(0.75);
            } else if (e.key === '2') {
                e.preventDefault();
                adjustSpeed(1.0);
            } else if (e.key === '3') {
                e.preventDefault();
                adjustSpeed(1.25);
            } else if (e.key === '4') {
                e.preventDefault();
                adjustSpeed(1.5);
            }
        }
        
        // R for replay when not typing
        if (e.key === 'r' && e.target.tagName !== 'INPUT' && e.target.tagName !== 'TEXTAREA') {
            e.preventDefault();
            replayAudio();
        }
        
        // M for mute when not typing
        if (e.key === 'm' && e.target.tagName !== 'INPUT' && e.target.tagName !== 'TEXTAREA') {
            e.preventDefault();
            toggleMute();
        }
    });
}

/**
 * Test audio URL accessibility
 */
function testAudioUrl() {
    const audioPlayer = document.getElementById('audioPlayer');
    if (!audioPlayer) return;
    
    const sources = audioPlayer.querySelectorAll('source');
    if (sources.length === 0) return;
    
    const audioUrl = sources[0].src;
    console.log('Testing audio URL:', audioUrl);
    
    // Test with fetch
    fetch(audioUrl, { method: 'HEAD' })
        .then(response => {
            console.log('URL test response:', response);
            if (response.ok) {
                showNotification('Audio URL is accessible', 'success');
                console.log('Response headers:', Object.fromEntries(response.headers.entries()));
            } else {
                showNotification(`URL test failed: ${response.status} ${response.statusText}`, 'error');
            }
        })
        .catch(error => {
            console.error('URL test error:', error);
            showNotification(`URL test error: ${error.message}`, 'error');
        });
    
    // Also try to open in new window for manual testing
    showNotification('Opening URL in new window for manual testing...', 'info', 3000);
    window.open(audioUrl, '_blank');
}

/**
 * Replay audio from the beginning
 */
function replayAudio() {
    const audioPlayer = document.getElementById('audioPlayer');
    if (audioPlayer) {
        audioPlayer.currentTime = 0;
        audioPlayer.play().catch(e => {
            console.error('Error playing audio:', e);
            showNotification('Error playing audio. Please check your browser settings.', 'error');
        });
    }
}

/**
 * Adjust audio playback speed
 */
function adjustSpeed(speed) {
    const audioPlayer = document.getElementById('audioPlayer');
    if (audioPlayer) {
        audioPlayer.playbackRate = speed;
        
        // Update button states
        document.querySelectorAll('.audio-controls .btn-secondary').forEach(btn => {
            btn.classList.remove('active');
        });
        
        // Find and highlight the active speed button
        document.querySelectorAll('.audio-controls .btn-secondary').forEach(btn => {
            if (btn.textContent.includes(speed + 'x')) {
                btn.classList.add('active');
            }
        });
        
        showNotification(`Playback speed set to ${speed}x`, 'success', 2000);
    }
}

/**
 * Toggle audio play/pause
 */
function toggleAudio() {
    const audioPlayer = document.getElementById('audioPlayer');
    if (audioPlayer) {
        if (audioPlayer.paused) {
            audioPlayer.play().catch(e => {
                console.error('Error playing audio:', e);
                showNotification('Error playing audio. Please check your browser settings.', 'error');
            });
        } else {
            audioPlayer.pause();
        }
    }
}

/**
 * Replay audio from the beginning
 */
function replayAudio() {
    const audioPlayer = document.getElementById('audioPlayer');
    if (audioPlayer) {
        audioPlayer.currentTime = 0;
        audioPlayer.play().catch(e => {
            console.error('Error playing audio:', e);
            showNotification('Error playing audio. Please check your browser settings.', 'error');
        });
    }
}

/**
 * Skip backward 10 seconds
 */
function skipBackward() {
    const audioPlayer = document.getElementById('audioPlayer');
    if (audioPlayer) {
        audioPlayer.currentTime = Math.max(0, audioPlayer.currentTime - 10);
    }
}

/**
 * Skip forward 10 seconds
 */
function skipForward() {
    const audioPlayer = document.getElementById('audioPlayer');
    if (audioPlayer) {
        audioPlayer.currentTime = Math.min(audioPlayer.duration, audioPlayer.currentTime + 10);
    }
}

/**
 * Adjust audio playback speed
 */
function adjustSpeed(speed) {
    const audioPlayer = document.getElementById('audioPlayer');
    const speedEl = document.getElementById('audioSpeed');
    
    if (audioPlayer) {
        audioPlayer.playbackRate = speed;
        
        // Update speed display
        if (speedEl) {
            speedEl.textContent = speed + 'x';
        }
        
        // Update button states
        document.querySelectorAll('.speed-btn').forEach(btn => {
            btn.classList.remove('active');
            if (btn.dataset.speed == speed) {
                btn.classList.add('active');
            }
        });
        
        showNotification(`Playback speed: ${speed}x`, 'success', 2000);
    }
}

/**
 * Toggle mute/unmute
 */
function toggleMute() {
    const audioPlayer = document.getElementById('audioPlayer');
    const volumeIcon = document.querySelector('.volume-icon');
    const muteIcon = document.querySelector('.mute-icon');
    
    if (audioPlayer) {
        audioPlayer.muted = !audioPlayer.muted;
        
        if (audioPlayer.muted) {
            volumeIcon.style.display = 'none';
            muteIcon.style.display = 'block';
            showNotification('Audio muted', 'info', 1500);
        } else {
            volumeIcon.style.display = 'block';
            muteIcon.style.display = 'none';
            showNotification('Audio unmuted', 'info', 1500);
        }
    }
}

/**
 * Show notification message
 */
function showNotification(message, type = 'info', duration = 5000) {
    // Remove existing notifications
    const existingNotifications = document.querySelectorAll('.notification');
    existingNotifications.forEach(n => n.remove());
    
    // Create notification element
    const notification = document.createElement('div');
    notification.className = `notification notification-${type}`;
    notification.innerHTML = `
        <span class="notification-icon">${type === 'error' ? '❌' : type === 'success' ? '✅' : 'ℹ️'}</span>
        <span class="notification-message">${message}</span>
        <button class="notification-close" onclick="this.parentElement.remove()">×</button>
    `;
    
    // Add styles
    notification.style.cssText = `
        position: fixed;
        top: 20px;
        right: 20px;
        background: ${type === 'error' ? '#2e1a1a' : type === 'success' ? '#1a2e1a' : '#1a1a2e'};
        color: ${type === 'error' ? '#e57373' : type === 'success' ? '#7cb87c' : '#7c7ce5'};
        padding: 12px 16px;
        border-radius: 6px;
        border: 1px solid ${type === 'error' ? '#5a2d2d' : type === 'success' ? '#2d5a2d' : '#2d2d5a'};
        box-shadow: 0 4px 12px rgba(0,0,0,0.3);
        z-index: 1000;
        max-width: 300px;
        display: flex;
        align-items: center;
        gap: 8px;
        font-weight: 500;
        font-size: 0.9rem;
        animation: slideIn 0.3s ease;
    `;
    
    // Add to page
    document.body.appendChild(notification);
    
    // Auto-remove after duration
    if (duration > 0) {
        setTimeout(() => {
            if (notification.parentElement) {
                notification.style.animation = 'slideOut 0.3s ease';
                setTimeout(() => notification.remove(), 300);
            }
        }, duration);
    }
}

/**
 * Hide success/error messages after delay
 */
function hideMessagesAfterDelay() {
    const messages = document.querySelectorAll('.message');
    messages.forEach(message => {
        setTimeout(() => {
            if (message.parentElement) {
                message.style.transition = 'opacity 0.5s ease';
                message.style.opacity = '0';
                setTimeout(() => {
                    if (message.parentElement) {
                        message.remove();
                    }
                }, 500);
            }
        }, 5000);
    });
}

/**
 * Initialize collapsible Guidelines section
 */
function initializeGuidelines() {
    const section = document.getElementById('guidelines');
    const toggle = document.getElementById('guidelinesToggle');
    const body = document.getElementById('guidelinesBody');
    if (!section || !toggle || !body) return;

    const STORAGE_KEY = 'guidelinesCollapsed';
    const setCollapsed = (collapsed) => {
        if (collapsed) {
            section.classList.add('collapsed');
            toggle.setAttribute('aria-expanded', 'false');
            toggle.textContent = 'Show';
        } else {
            section.classList.remove('collapsed');
            toggle.setAttribute('aria-expanded', 'true');
            toggle.textContent = 'Hide';
        }
        try { localStorage.setItem(STORAGE_KEY, collapsed ? '1' : '0'); } catch (_) {}
    };

    // Restore previous state
    try {
        const saved = localStorage.getItem(STORAGE_KEY);
        if (saved === '1') setCollapsed(true);
    } catch (_) {}

    toggle.addEventListener('click', function() {
        const collapsed = !section.classList.contains('collapsed');
        setCollapsed(collapsed);
    });
}

/**
 * Initialize IME - auto-enable on desktop devices
 */
function initializeIME() {
    const imeToggle = document.getElementById('imeToggle');
    if (!imeToggle) return;

    // Detect if device is desktop (non-mobile)
    function isDesktop() {
        return !(/Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(navigator.userAgent));
    }

    // Auto-enable IME on desktop devices
    if (isDesktop()) {
        imeToggle.checked = true;
        // Trigger change event to activate the IME
        imeToggle.dispatchEvent(new Event('change'));
    }
}

/**
 * Copy reference transcription to textarea (for assistance)
 */
function copyReferenceText() {
    const referenceText = document.querySelector('.reference-text');
    const transcriptionTextarea = document.getElementById('transcription');
    
    if (referenceText && transcriptionTextarea) {
        transcriptionTextarea.value = referenceText.textContent.trim();
        transcriptionTextarea.focus();
        transcriptionTextarea.dispatchEvent(new Event('input'));
        showNotification('Reference text copied. Please review and edit as needed.', 'info');
    }
}

// Add CSS animations
const style = document.createElement('style');
style.textContent = `
    @keyframes slideIn {
        from {
            transform: translateX(100%);
            opacity: 0;
        }
        to {
            transform: translateX(0);
            opacity: 1;
        }
    }
    
    @keyframes slideOut {
        from {
            transform: translateX(0);
            opacity: 1;
        }
        to {
            transform: translateX(100%);
            opacity: 0;
        }
    }
    
    .btn-secondary.active {
        background: #444 !important;
        color: #fff !important;
        border-color: #555 !important;
    }
    
    .notification-close {
        background: none;
        border: none;
        font-size: 1.2rem;
        cursor: pointer;
        padding: 0;
        margin-left: auto;
        opacity: 0.7;
    }
    
    .notification-close:hover {
        opacity: 1;
    }
`;
document.head.appendChild(style);
