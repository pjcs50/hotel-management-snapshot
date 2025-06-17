/**
 * Sidebar Management Class
 * Handles sidebar toggle, responsive behavior, and state persistence
 */
class Sidebar {
    constructor() {
        this.sidebar = document.getElementById('sidebar');
        this.sidebarWrapper = document.getElementById('sidebarWrapper');
        this.sidebarToggle = document.getElementById('sidebarToggle');
        this.mobileSidebarToggle = document.getElementById('mobileSidebarToggle');
        this.sidebarOverlay = document.getElementById('sidebarOverlay');
        this.mainContent = document.getElementById('mainContent');
        
        this.isCollapsed = this.getStoredState();
        this.isMobile = window.innerWidth < 768;
        
        this.init();
    }
    
    init() {
        this.setupEventListeners();
        this.applyInitialState();
        this.handleResize();
    }
    
    setupEventListeners() {
        // Desktop sidebar toggle
        if (this.sidebarToggle) {
            this.sidebarToggle.addEventListener('click', () => {
                this.toggleSidebar();
            });
        }
        
        // Mobile sidebar toggle
        if (this.mobileSidebarToggle) {
            this.mobileSidebarToggle.addEventListener('click', () => {
                this.toggleMobileSidebar();
            });
        }
        
        // Overlay click to close mobile sidebar
        if (this.sidebarOverlay) {
            this.sidebarOverlay.addEventListener('click', () => {
                this.closeMobileSidebar();
            });
        }
        
        // Window resize handler
        window.addEventListener('resize', () => {
            this.handleResize();
        });
        
        // Keyboard navigation
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape' && this.isMobile && this.sidebarWrapper.classList.contains('active')) {
                this.closeMobileSidebar();
            }
        });
    }
    
    toggleSidebar() {
        if (this.isMobile) {
            this.toggleMobileSidebar();
            return;
        }
        
        this.isCollapsed = !this.isCollapsed;
        this.applySidebarState();
        this.storeState();
        this.updateToggleIcon();
    }
    
    toggleMobileSidebar() {
        const isActive = this.sidebarWrapper.classList.contains('active');
        
        if (isActive) {
            this.closeMobileSidebar();
        } else {
            this.openMobileSidebar();
        }
    }
    
    openMobileSidebar() {
        this.sidebarWrapper.classList.add('active');
        this.sidebarOverlay.classList.add('active');
        document.body.style.overflow = 'hidden';
    }
    
    closeMobileSidebar() {
        this.sidebarWrapper.classList.remove('active');
        this.sidebarOverlay.classList.remove('active');
        document.body.style.overflow = '';
    }
    
    applySidebarState() {
        if (this.isMobile) {
            // On mobile, always show full sidebar when open
            this.sidebar.classList.remove('collapsed');
            this.mainContent.classList.remove('sidebar-collapsed');
            return;
        }
        
        // Desktop behavior
        if (this.isCollapsed) {
            this.sidebar.classList.add('collapsed');
            this.mainContent.classList.add('sidebar-collapsed');
        } else {
            this.sidebar.classList.remove('collapsed');
            this.mainContent.classList.remove('sidebar-collapsed');
        }
    }
    
    applyInitialState() {
        if (this.isMobile) {
            // On mobile, sidebar is hidden by default
            this.sidebar.classList.remove('collapsed');
            this.mainContent.classList.remove('sidebar-collapsed');
            this.sidebarWrapper.classList.remove('active');
            this.sidebarOverlay.classList.remove('active');
        } else {
            // Apply stored state on desktop
            this.applySidebarState();
            this.updateToggleIcon();
        }
    }
    
    handleResize() {
        const wasMobile = this.isMobile;
        this.isMobile = window.innerWidth < 768;
        
        if (wasMobile !== this.isMobile) {
            // Mobile state changed
            if (this.isMobile) {
                // Switched to mobile
                this.closeMobileSidebar();
                this.sidebar.classList.remove('collapsed');
                this.mainContent.classList.remove('sidebar-collapsed');
            } else {
                // Switched to desktop
                this.closeMobileSidebar();
                this.applySidebarState();
                this.updateToggleIcon();
            }
        }
    }
    
    updateToggleIcon() {
        if (!this.sidebarToggle) return;
        
        const icon = this.sidebarToggle.querySelector('i');
        if (icon) {
            if (this.isCollapsed) {
                icon.className = 'bi bi-chevron-right';
            } else {
                icon.className = 'bi bi-chevron-left';
            }
        }
    }
    
    getStoredState() {
        const stored = localStorage.getItem('sidebarCollapsed');
        return stored === 'true';
    }
    
    storeState() {
        localStorage.setItem('sidebarCollapsed', this.isCollapsed.toString());
    }
    
    // Public methods for external use
    collapse() {
        if (!this.isMobile) {
            this.isCollapsed = true;
            this.applySidebarState();
            this.storeState();
            this.updateToggleIcon();
        }
    }
    
    expand() {
        if (!this.isMobile) {
            this.isCollapsed = false;
            this.applySidebarState();
            this.storeState();
            this.updateToggleIcon();
        }
    }
    
    isOpen() {
        if (this.isMobile) {
            return this.sidebarWrapper.classList.contains('active');
        }
        return !this.isCollapsed;
    }
}

// Auto-initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    // Only initialize if sidebar elements exist
    if (document.getElementById('sidebar')) {
        window.sidebarInstance = new Sidebar();
    }
});

// Export for use in other scripts
if (typeof module !== 'undefined' && module.exports) {
    module.exports = Sidebar;
} 
 
 
 