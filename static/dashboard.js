// Bird Watcher Dashboard

let eventSource = null;
let soundEnabled = false;
let detections = [];

document.addEventListener('DOMContentLoaded', () => {
    loadData();
    startEventStream();
    initSoundToggle();
    setInterval(loadStats, 10000);
});

function initSoundToggle() {
    const btn = document.getElementById('soundToggle');
    btn.addEventListener('click', () => {
        soundEnabled = !soundEnabled;
        btn.classList.toggle('active', soundEnabled);
        if (soundEnabled) {
            // Test sound on first enable
            playBirdSound(0.3);
        }
    });
}

function playBirdSound(volume = 0.5) {
    if (!soundEnabled) return;
    const audio = document.getElementById('birdSound');
    audio.volume = volume;
    audio.currentTime = 0;
    audio.play().catch(() => {});
}

function flashScreen() {
    const flash = document.getElementById('detectionFlash');
    flash.classList.add('active');
    setTimeout(() => flash.classList.remove('active'), 150);
}

function loadData() {
    fetch('/api/detections')
        .then(r => r.json())
        .then(data => {
            detections = data;
            updateGallery(data);
            if (data.length > 0) {
                updateLatest(data[0]);
            }
            buildActivityBar(data);
        });
    loadStats();
}

function loadStats() {
    fetch('/api/stats')
        .then(r => r.json())
        .then(data => {
            document.getElementById('statTotal').textContent = data.total_detections || 0;
            document.getElementById('statBirds').textContent = data.bird_detections || 0;
            document.getElementById('statRecent').textContent = data.recent_detections || 0;
            document.getElementById('statSpecies').textContent = Object.keys(data.species_count || {}).length;
            updateSpeciesList(data.species_count);
        });
}

function startEventStream() {
    eventSource = new EventSource('/api/stream');
    
    eventSource.onopen = () => {
        document.getElementById('statusIndicator').className = 'status-indicator connected';
        document.getElementById('statusText').textContent = 'Live';
    };
    
    eventSource.onerror = () => {
        document.getElementById('statusIndicator').className = 'status-indicator';
        document.getElementById('statusText').textContent = 'Reconnecting';
    };
    
    eventSource.onmessage = (event) => {
        const msg = JSON.parse(event.data);
        if (msg.type === 'detection') {
            // New detection
            flashScreen();
            playBirdSound();
            loadData();
        }
    };
}

function updateGallery(data) {
    const gallery = document.getElementById('gallery');
    const count = document.getElementById('galleryCount');
    count.textContent = data.length;
    
    if (!data.length) {
        gallery.innerHTML = '<div class="gallery-empty">Waiting for detections...</div>';
        return;
    }
    
    gallery.innerHTML = data.slice(0, 20).map(det => {
        const species = getSpeciesName(det);
        const conf = getConfidence(det);
        const imgPath = det.image_path ? '/images/' + det.image_path.split('/').pop() : '';
        
        return `
            <div class="gallery-item" onclick="showDetail(${det.id})">
                ${imgPath ? `<img src="${imgPath}" alt="${species}" loading="lazy">` : ''}
                <div class="gallery-item-overlay">
                    <div class="gallery-item-species">${species}</div>
                    <div class="gallery-item-conf">${(conf * 100).toFixed(0)}%</div>
                </div>
            </div>
        `;
    }).join('');
}

function updateLatest(det) {
    const panel = document.getElementById('latestDetection');
    if (!det) {
        panel.innerHTML = '<div class="empty-state">No detections yet</div>';
        return;
    }
    
    const species = getSpeciesName(det);
    const conf = getConfidence(det);
    const imgPath = det.image_path ? '/images/' + det.image_path.split('/').pop() : '';
    const time = new Date(det.timestamp).toLocaleTimeString();
    const audio = det.audio_classification || [];
    
    let html = '';
    
    if (imgPath) {
        html += `<img src="${imgPath}" class="latest-image" alt="${species}">`;
    }
    
    html += `
        <div class="latest-info">
            <div class="latest-row">
                <span class="latest-label">Species</span>
                <span class="latest-value">${species}</span>
            </div>
            <div class="latest-row">
                <span class="latest-label">Confidence</span>
                <span class="latest-value highlight">${(conf * 100).toFixed(1)}%</span>
            </div>
            <div class="latest-row">
                <span class="latest-label">Time</span>
                <span class="latest-value">${time}</span>
            </div>
            <div class="latest-row">
                <span class="latest-label">Classification</span>
                <span class="latest-value">${det.classification_time_ms ? det.classification_time_ms.toFixed(0) + 'ms' : '-'}</span>
            </div>
        </div>
    `;
    
    if (audio.length > 0) {
        html += `
            <div class="audio-section">
                <div class="audio-header">Audio Confirmation</div>
                ${audio.slice(0, 3).map(a => `
                    <div class="audio-item">
                        <span class="audio-species">${a.species}</span>
                        <span class="audio-conf">${(a.confidence * 100).toFixed(0)}%</span>
                    </div>
                `).join('')}
            </div>
        `;
    }
    
    panel.innerHTML = html;
}

function updateSpeciesList(speciesCount) {
    const container = document.getElementById('speciesBreakdown');
    
    if (!speciesCount || Object.keys(speciesCount).length === 0) {
        container.innerHTML = '<div class="empty-state">No data</div>';
        return;
    }
    
    const sorted = Object.entries(speciesCount)
        .filter(([name]) => name !== 'background')
        .sort((a, b) => b[1] - a[1])
        .slice(0, 10);
    
    const max = Math.max(...sorted.map(s => s[1]));
    
    container.innerHTML = sorted.map(([name, count]) => `
        <div class="species-item">
            <span class="species-name">${name}</span>
            <span class="species-count">${count}</span>
            <div class="species-bar">
                <div class="species-bar-fill" style="width: ${(count / max) * 100}%"></div>
            </div>
        </div>
    `).join('');
}

function buildActivityBar(data) {
    const bar = document.getElementById('activityBar');
    const segments = 48; // 30-minute segments for 24 hours
    const counts = new Array(segments).fill(0);
    
    const now = new Date();
    const startOfDay = new Date(now.getFullYear(), now.getMonth(), now.getDate());
    
    data.forEach(det => {
        const detTime = new Date(det.timestamp);
        const minutesSinceMidnight = (detTime - startOfDay) / (1000 * 60);
        const segment = Math.floor(minutesSinceMidnight / 30);
        if (segment >= 0 && segment < segments) {
            counts[segment]++;
        }
    });
    
    const max = Math.max(...counts, 1);
    
    bar.innerHTML = counts.map((count, i) => {
        const hour = Math.floor(i / 2);
        const min = (i % 2) * 30;
        const label = `${hour.toString().padStart(2, '0')}:${min.toString().padStart(2, '0')}`;
        const active = count > 0 ? 'active' : '';
        const opacity = count > 0 ? 0.3 + (count / max) * 0.7 : 1;
        
        return `<div class="activity-segment ${active}" data-count="${count} at ${label}" style="opacity: ${opacity}"></div>`;
    }).join('');
}

function showDetail(id) {
    const det = detections.find(d => d.id === id);
    if (det) {
        updateLatest(det);
        // Scroll to detail on mobile
        if (window.innerWidth < 1024) {
            document.querySelector('.detail-section').scrollIntoView({ behavior: 'smooth' });
        }
    }
}

function getSpeciesName(det) {
    if (det.visual_classification && det.visual_classification.length > 0) {
        const sp = det.visual_classification[0].species;
        if (sp && sp !== 'background') {
            // Clean up species name - take just the common name
            const match = sp.match(/\(([^)]+)\)$/);
            return match ? match[1] : sp.split('(')[0].trim();
        }
    }
    return det.detection_label || 'Unknown';
}

function getConfidence(det) {
    if (det.visual_classification && det.visual_classification.length > 0) {
        return det.visual_classification[0].confidence;
    }
    return det.detection_confidence || 0;
}

window.addEventListener('beforeunload', () => {
    if (eventSource) eventSource.close();
});
