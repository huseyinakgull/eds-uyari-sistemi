// EDS Uyarı Sistemi Pro - Advanced Utility Functions
// Version 2.0.0 - Bu dosya isteğe bağlıdır, ana JavaScript index.html içinde inline olarak yazılmıştır

class EDSUtils {
    // Gelişmiş mesafe hesaplama (Haversine formülü)
    static calculateDistance(lat1, lon1, lat2, lon2) {
        const R = 6371e3; // Earth's radius in meters
        const φ1 = lat1 * Math.PI / 180;
        const φ2 = lat2 * Math.PI / 180;
        const Δφ = (lat2 - lat1) * Math.PI / 180;
        const Δλ = (lon2 - lon1) * Math.PI / 180;

        const a = Math.sin(Δφ / 2) * Math.sin(Δφ / 2) +
                  Math.cos(φ1) * Math.cos(φ2) *
                  Math.sin(Δλ / 2) * Math.sin(Δλ / 2);
        const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));

        return R * c;
    }

    // Bearing hesaplama (yön bulma)
    static calculateBearing(lat1, lon1, lat2, lon2) {
        const φ1 = lat1 * Math.PI / 180;
        const φ2 = lat2 * Math.PI / 180;
        const Δλ = (lon2 - lon1) * Math.PI / 180;

        const y = Math.sin(Δλ) * Math.cos(φ2);
        const x = Math.cos(φ1) * Math.sin(φ2) - Math.sin(φ1) * Math.cos(φ2) * Math.cos(Δλ);

        const θ = Math.atan2(y, x);
        return (θ * 180 / Math.PI + 360) % 360; // Normalize to 0-360
    }

    // Yön adını döndür
    static getDirectionName(bearing) {
        const directions = [
            'Kuzey', 'Kuzeydoğu', 'Doğu', 'Güneydoğu',
            'Güney', 'Güneybatı', 'Batı', 'Kuzeybatı'
        ];
        const index = Math.round(bearing / 45) % 8;
        return directions[index];
    }

    // Gelişmiş mesafe formatlaması
    static formatDistance(meters, precision = 1) {
        if (meters < 1000) {
            return Math.round(meters) + 'm';
        } else if (meters < 10000) {
            return (meters / 1000).toFixed(precision) + 'km';
        } else {
            return Math.round(meters / 1000) + 'km';
        }
    }

    // Gelişmiş zaman formatlaması
    static formatTime(seconds, includeMillis = false) {
        const hours = Math.floor(seconds / 3600);
        const minutes = Math.floor((seconds % 3600) / 60);
        const secs = Math.floor(seconds % 60);
        const millis = Math.floor((seconds % 1) * 1000);
        
        if (hours > 0) {
            return `${hours.toString().padStart(2, '0')}:${minutes.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
        } else if (includeMillis) {
            return `${minutes.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}.${millis.toString().padStart(3, '0')}`;
        } else {
            return `${minutes.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
        }
    }

    // Hız formatlaması
    static formatSpeed(speed, unit = 'kmh') {
        if (unit === 'kmh') {
            return Math.round(speed) + ' km/h';
        } else if (unit === 'ms') {
            return (speed / 3.6).toFixed(1) + ' m/s';
        } else if (unit === 'mph') {
            return Math.round(speed * 0.621371) + ' mph';
        }
        return speed.toString();
    }

    // Kamera tipine göre icon
    static getCameraIcon(type) {
        const icons = {
            'OHITS': 'fas fa-camera',
            'MOBILE': 'fas fa-car',
            'REDLIGHT': 'fas fa-traffic-light',
            'AVERAGE_SPEED': 'fas fa-tachometer-alt',
            'SECTION_CONTROL': 'fas fa-road',
            'WEIGHT_CONTROL': 'fas fa-truck',
            'TUNNEL': 'fas fa-tunnel'
        };
        return icons[type] || 'fas fa-camera';
    }

    // Kamera tipine göre renk
    static getCameraColor(type) {
        const colors = {
            'OHITS': '#ff4757',
            'MOBILE': '#ffa502',
            'REDLIGHT': '#ff3838',
            'AVERAGE_SPEED': '#ff6348',
            'SECTION_CONTROL': '#ff7675',
            'WEIGHT_CONTROL': '#a29bfe',
            'TUNNEL': '#6c5ce7'
        };
        return colors[type] || '#ff4757';
    }

    // Kamera tipine göre Türkçe isim
    static getCameraName(type) {
        const names = {
            'OHITS': 'Sabit Hız Kamerası',
            'MOBILE': 'Mobil Radar',
            'REDLIGHT': 'Kırmızı Işık Kamerası',
            'AVERAGE_SPEED': 'Ortalama Hız Kamerası',
            'SECTION_CONTROL': 'Kesit Kontrol',
            'WEIGHT_CONTROL': 'Ağırlık Kontrolü',
            'TUNNEL': 'Tünel Kamerası'
        };
        return names[type] || type;
    }

    // Gelişmiş Text-to-Speech
    static speak(text, options = {}) {
        if ('speechSynthesis' in window) {
            // Cancel any existing speech
            speechSynthesis.cancel();
            
            const utterance = new SpeechSynthesisUtterance(text);
            utterance.lang = options.lang || 'tr-TR';
            utterance.rate = options.rate || 1.0;
            utterance.volume = options.volume || 0.8;
            utterance.pitch = options.pitch || 1.0;
            
            // Try to use a Turkish voice if available
            const voices = speechSynthesis.getVoices();
            const turkishVoice = voices.find(voice => voice.lang.startsWith('tr'));
            if (turkishVoice) {
                utterance.voice = turkishVoice;
            }
            
            speechSynthesis.speak(utterance);
            
            return new Promise((resolve, reject) => {
                utterance.onend = resolve;
                utterance.onerror = reject;
            });
        }
        return Promise.reject(new Error('Speech synthesis not supported'));
    }

    // Gelişmiş vibration patterns
    static vibrate(pattern = 'default') {
        if ('vibrate' in navigator) {
            const patterns = {
                'default': [200, 100, 200],
                'warning': [300, 150, 300, 150, 300],
                'critical': [500, 200, 500, 200, 500],
                'success': [100, 50, 100],
                'error': [1000],
                'heartbeat': [100, 30, 100, 30, 100, 200, 200, 30, 200, 30, 200, 200, 100, 30, 100, 30, 100]
            };
            
            const vibrationPattern = typeof pattern === 'string' ? 
                patterns[pattern] || patterns.default : pattern;
                
            navigator.vibrate(vibrationPattern);
        }
    }

    // Gelişmiş notification
    static async showNotification(title, options = {}) {
        if ('Notification' in window) {
            if (Notification.permission === 'granted') {
                const notification = new Notification(title, {
                    icon: '/assets/icons/camera-icon.png',
                    badge: '/assets/icons/badge-icon.png',
                    vibrate: [200, 100, 200],
                    requireInteraction: true,
                    ...options
                });
                
                // Auto close after 6 seconds unless requireInteraction is true
                if (!options.requireInteraction) {
                    setTimeout(() => notification.close(), 6000);
                }
                
                return notification;
            } else if (Notification.permission === 'default') {
                const permission = await Notification.requestPermission();
                if (permission === 'granted') {
                    return this.showNotification(title, options);
                }
            }
        }
        return null;
    }

    // Local Storage helpers with error handling
    static setStorage(key, value, expiry = null) {
        try {
            const item = {
                value: value,
                timestamp: Date.now(),
                expiry: expiry
            };
            localStorage.setItem(`eds_${key}`, JSON.stringify(item));
            return true;
        } catch (error) {
            console.warn('Storage error:', error);
            return false;
        }
    }

    static getStorage(key, defaultValue = null) {
        try {
            const itemStr = localStorage.getItem(`eds_${key}`);
            if (!itemStr) return defaultValue;
            
            const item = JSON.parse(itemStr);
            
            // Check expiry
            if (item.expiry && Date.now() > item.expiry) {
                localStorage.removeItem(`eds_${key}`);
                return defaultValue;
            }
            
            return item.value;
        } catch (error) {
            console.warn('Storage error:', error);
            return defaultValue;
        }
    }

    static removeStorage(key) {
        try {
            localStorage.removeItem(`eds_${key}`);
            return true;
        } catch (error) {
            console.warn('Storage error:', error);
            return false;
        }
    }

    static clearStorage() {
        try {
            const keys = Object.keys(localStorage);
            keys.forEach(key => {
                if (key.startsWith('eds_')) {
                    localStorage.removeItem(key);
                }
            });
            return true;
        } catch (error) {
            console.warn('Storage error:', error);
            return false;
        }
    }

    // GPS accuracy assessment
    static assessGPSAccuracy(accuracy) {
        if (accuracy <= 5) return { level: 'excellent', text: 'Mükemmel', color: '#2ed573' };
        if (accuracy <= 10) return { level: 'good', text: 'İyi', color: '#26d0ce' };
        if (accuracy <= 20) return { level: 'fair', text: 'Orta', color: '#ffa502' };
        if (accuracy <= 50) return { level: 'poor', text: 'Zayıf', color: '#ff6348' };
        return { level: 'very_poor', text: 'Çok Zayıf', color: '#ff4757' };
    }

    // Speed limit violation detection
    static checkSpeedViolation(currentSpeed, speedLimit, tolerance = 5) {
        const threshold = speedLimit + tolerance;
        if (currentSpeed <= speedLimit) {
            return { violation: false, level: 'safe', excess: 0 };
        } else if (currentSpeed <= threshold) {
            return { violation: false, level: 'warning', excess: currentSpeed - speedLimit };
        } else if (currentSpeed <= speedLimit + 10) {
            return { violation: true, level: 'minor', excess: currentSpeed - speedLimit };
        } else if (currentSpeed <= speedLimit + 20) {
            return { violation: true, level: 'major', excess: currentSpeed - speedLimit };
        } else {
            return { violation: true, level: 'severe', excess: currentSpeed - speedLimit };
        }
    }

    // Device detection
    static getDeviceInfo() {
        const userAgent = navigator.userAgent;
        const platform = navigator.platform;
        
        return {
            isMobile: /Android|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(userAgent),
            isTablet: /iPad|Android(?!.*Mobile)/i.test(userAgent),
            isIOS: /iPad|iPhone|iPod/.test(userAgent),
            isAndroid: /Android/i.test(userAgent),
            platform: platform,
            hasTouch: 'ontouchstart' in window,
            hasVibration: 'vibrate' in navigator,
            hasGeolocation: 'geolocation' in navigator,
            hasNotifications: 'Notification' in window,
            hasSpeechSynthesis: 'speechSynthesis' in window,
            hasServiceWorker: 'serviceWorker' in navigator,
            screen: {
                width: screen.width,
                height: screen.height,
                availWidth: screen.availWidth,
                availHeight: screen.availHeight
            }
        };
    }

    // Performance monitoring
    static measurePerformance(name, fn) {
        const start = performance.now();
        const result = fn();
        const end = performance.now();
        const duration = end - start;
        
        console.log(`Performance [${name}]: ${duration.toFixed(2)}ms`);
        
        // Mark performance in browser DevTools
        if (performance.mark && performance.measure) {
            performance.mark(`${name}-start`);
            performance.mark(`${name}-end`);
            performance.measure(name, `${name}-start`, `${name}-end`);
        }
        
        return { result, duration };
    }

    // Battery status
    static async getBatteryInfo() {
        if ('getBattery' in navigator) {
            try {
                const battery = await navigator.getBattery();
                return {
                    level: Math.round(battery.level * 100),
                    charging: battery.charging,
                    chargingTime: battery.chargingTime,
                    dischargingTime: battery.dischargingTime
                };
            } catch (error) {
                console.warn('Battery API error:', error);
            }
        }
        return null;
    }

    // Network information
    static getNetworkInfo() {
        if ('connection' in navigator) {
            const connection = navigator.connection;
            return {
                effectiveType: connection.effectiveType,
                downlink: connection.downlink,
                rtt: connection.rtt,
                saveData: connection.saveData
            };
        }
        return null;
    }

    // URL parameters handling
    static getURLParams() {
        const params = new URLSearchParams(window.location.search);
        const result = {};
        for (const [key, value] of params) {
            result[key] = value;
        }
        return result;
    }

    static handleShortcuts() {
        const params = this.getURLParams();
        
        if (params.action) {
            switch (params.action) {
                case 'start-tracking':
                    setTimeout(() => {
                        if (window.app && !window.app.isTracking) {
                            document.getElementById('toggleTracking')?.click();
                        }
                    }, 2000);
                    break;
                case 'test-alert':
                    setTimeout(() => {
                        if (window.testAlert) {
                            window.testAlert();
                        }
                    }, 1000);
                    break;
                case 'open-settings':
                    setTimeout(() => {
                        document.getElementById('settingsBtn')?.click();
                    }, 1000);
                    break;
            }
        }
    }

    // Debug logging with levels
    static debug(level, ...args) {
        const levels = {
            error: { color: '#ff4757', emoji: '❌' },
            warn: { color: '#ffa502', emoji: '⚠️' },
            info: { color: '#3742fa', emoji: 'ℹ️' },
            success: { color: '#2ed573', emoji: '✅' },
            debug: { color: '#747d8c', emoji: '🔧' }
        };
        
        const logLevel = levels[level] || levels.info;
        
        if (window.location.hostname === 'localhost' || window.location.search.includes('debug=true')) {
            console.log(
                `%c${logLevel.emoji} [EDS ${level.toUpperCase()}]`,
                `color: ${logLevel.color}; font-weight: bold;`,
                ...args
            );
        }
    }

    // Analytics helper
    static trackEvent(eventName, properties = {}) {
        // This would integrate with analytics services
        const event = {
            name: eventName,
            timestamp: Date.now(),
            properties: {
                ...properties,
                userAgent: navigator.userAgent,
                url: window.location.href
            }
        };
        
        this.debug('info', 'Analytics Event:', event);
        
        // Store in localStorage for offline events
        const events = this.getStorage('analytics_events', []);
        events.push(event);
        
        // Keep only last 100 events
        if (events.length > 100) {
            events.splice(0, events.length - 100);
        }
        
        this.setStorage('analytics_events', events);
    }
}

// Utility functions as standalone exports
const utils = {
    distance: EDSUtils.calculateDistance,
    bearing: EDSUtils.calculateBearing,
    direction: EDSUtils.getDirectionName,
    formatDistance: EDSUtils.formatDistance,
    formatTime: EDSUtils.formatTime,
    formatSpeed: EDSUtils.formatSpeed,
    speak: EDSUtils.speak,
    vibrate: EDSUtils.vibrate,
    notify: EDSUtils.showNotification,
    store: {
        get: EDSUtils.getStorage,
        set: EDSUtils.setStorage,
        remove: EDSUtils.removeStorage,
        clear: EDSUtils.clearStorage
    },
    performance: EDSUtils.measurePerformance,
    device: EDSUtils.getDeviceInfo(),
    debug: EDSUtils.debug,
    track: EDSUtils.trackEvent
};

// Auto-initialize shortcuts
document.addEventListener('DOMContentLoaded', () => {
    EDSUtils.handleShortcuts();
});

// Export for global usage
if (typeof window !== 'undefined') {
    window.EDSUtils = EDSUtils;
    window.utils = utils;
}

// Export for module usage
if (typeof module !== 'undefined' && module.exports) {
    module.exports = { EDSUtils, utils };
}