/**
 * Dashboard Charts
 * This file contains functions for initializing dashboard charts
 */

/**
 * Initialize the occupancy rate chart
 * @param {string} canvasId - The ID of the canvas element
 * @param {object} data - The occupancy data object
 */
function initOccupancyChart(canvasId, data) {
    const ctx = document.getElementById(canvasId);
    if (!ctx) return;
    
    // Extract labels and values from data
    const labels = Object.keys(data).map(date => {
        // Format date if it's a date string
        if (date.includes('-')) {
            const [year, month, day] = date.split('-');
            return `${month}/${day}`;
        }
        return date;
    });
    
    const values = Object.values(data);
    
    new Chart(ctx, {
        type: 'line',
        data: {
            labels: labels,
            datasets: [{
                label: 'Occupancy Rate (%)',
                data: values,
                borderColor: 'rgba(54, 162, 235, 1)',
                backgroundColor: 'rgba(54, 162, 235, 0.1)',
                borderWidth: 2,
                tension: 0.3,
                fill: true
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                y: {
                    beginAtZero: true,
                    max: 100,
                    ticks: {
                        callback: function(value) {
                            return value + '%';
                        }
                    }
                }
            },
            plugins: {
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            return `Occupancy: ${context.parsed.y}%`;
                        }
                    }
                }
            }
        }
    });
}

/**
 * Initialize the room status chart
 * @param {string} canvasId - The ID of the canvas element
 * @param {object} data - The room status data object
 */
function initRoomStatusChart(canvasId, data) {
    const ctx = document.getElementById(canvasId);
    if (!ctx) return;
    
    // Extract labels and values
    const labels = Object.keys(data).map(status => status.replace(/([A-Z])/g, ' $1').trim());
    const values = Object.values(data);
    
    // Define colors for each status
    const backgroundColors = [
        'rgba(54, 162, 235, 0.7)', // Available - Blue
        'rgba(255, 99, 132, 0.7)',  // Occupied - Red
        'rgba(255, 205, 86, 0.7)',  // Cleaning - Yellow
        'rgba(75, 192, 192, 0.7)',  // Maintenance - Green
        'rgba(153, 102, 255, 0.7)' // Other - Purple
    ];
    
    new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: labels,
            datasets: [{
                data: values,
                backgroundColor: backgroundColors.slice(0, values.length),
                borderWidth: 1
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: 'right',
                }
            }
        }
    });
}

/**
 * Initialize the revenue by room type chart
 * @param {string} canvasId - The ID of the canvas element
 * @param {object} data - The revenue data object
 */
function initRevenueChart(canvasId, data) {
    const ctx = document.getElementById(canvasId);
    if (!ctx) return;
    
    // Extract labels and values
    const labels = Object.keys(data);
    const values = Object.values(data);
    
    new Chart(ctx, {
        type: 'bar',
        data: {
            labels: labels,
            datasets: [{
                label: 'Revenue ($)',
                data: values,
                backgroundColor: 'rgba(75, 192, 192, 0.7)',
                borderColor: 'rgba(75, 192, 192, 1)',
                borderWidth: 1
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                y: {
                    beginAtZero: true,
                    ticks: {
                        callback: function(value) {
                            return '$' + value;
                        }
                    }
                }
            },
            plugins: {
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            return `Revenue: $${context.parsed.y.toFixed(2)}`;
                        }
                    }
                }
            }
        }
    });
}

/**
 * Initialize the user roles chart
 * @param {string} canvasId - The ID of the canvas element
 * @param {object} data - The user roles data object
 */
function initUserRolesChart(canvasId, data) {
    const ctx = document.getElementById(canvasId);
    if (!ctx) return;
    
    // Extract labels and values
    const labels = Object.keys(data).map(role => role.charAt(0).toUpperCase() + role.slice(1));
    const values = Object.values(data);
    
    // Define colors for each role
    const backgroundColors = [
        'rgba(255, 99, 132, 0.7)',  // Customer - Red
        'rgba(54, 162, 235, 0.7)',  // Receptionist - Blue
        'rgba(255, 205, 86, 0.7)',  // Manager - Yellow
        'rgba(75, 192, 192, 0.7)',  // Housekeeping - Green
        'rgba(153, 102, 255, 0.7)'  // Admin - Purple
    ];
    
    new Chart(ctx, {
        type: 'pie',
        data: {
            labels: labels,
            datasets: [{
                data: values,
                backgroundColor: backgroundColors.slice(0, values.length),
                borderWidth: 1
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false
        }
    });
} 