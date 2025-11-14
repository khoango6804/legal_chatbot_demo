// Sidebar toggle functionality
document.addEventListener('DOMContentLoaded', function() {
    const sidebar = document.getElementById('sidebar');
    const sidebarToggle = document.getElementById('sidebar-toggle');
    const main = document.getElementById('main');
    
    // Toggle sidebar
    function toggleSidebar() {
        sidebar.classList.toggle('closed');
    }
    
    // Close sidebar on mobile when clicking outside
    function closeSidebarOnMobile() {
        if (window.innerWidth <= 768) {
            sidebar.classList.add('closed');
        }
    }
    
    // Event listeners
    if (sidebarToggle) {
        sidebarToggle.addEventListener('click', toggleSidebar);
    }
    
    // Close sidebar when clicking on main content on mobile
    if (main) {
        main.addEventListener('click', closeSidebarOnMobile);
    }
    
    // Handle window resize
    window.addEventListener('resize', function() {
        if (window.innerWidth > 768) {
            sidebar.classList.remove('closed');
        }
    });
}); 