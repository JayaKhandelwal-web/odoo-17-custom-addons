/** @odoo-module **/

import { FormController } from "@web/views/form/form_controller";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { onMounted, onWillUnmount, onPatched } from "@odoo/owl";

export class FleetBookingDashboardController extends FormController {
    setup() {
        super.setup();
        this.notification = useService("notification");
        this.chartInstances = {};
        this.chartsInitialized = false;
        this.chartJSLoaded = false;
        this.initializationTimeout = null;

        onMounted(() => {
            this.loadChartJS().then(() => {
                this.chartJSLoaded = true;
                // Initialize charts with proper delay
                this.scheduleChartInitialization(1500);
                // Set up tab click handlers
                this.setupTabHandlers();
            });
        });

        onPatched(() => {
            // Re-initialize charts after any DOM updates
            if (this.chartJSLoaded) {
                this.scheduleChartInitialization(300);
            }
        });

        onWillUnmount(() => {
            this.cleanupCharts();
            if (this.initializationTimeout) {
                clearTimeout(this.initializationTimeout);
            }
        });
    }

    scheduleChartInitialization(delay = 500) {
        // Clear any existing timeout to prevent multiple initializations
        if (this.initializationTimeout) {
            clearTimeout(this.initializationTimeout);
        }

        this.initializationTimeout = setTimeout(() => {
            this.initializeCharts();
        }, delay);
    }

    async loadChartJS() {
        return new Promise((resolve, reject) => {
            // Check if Chart.js is already loaded
            if (typeof window.Chart !== 'undefined') {
                console.log('Chart.js already loaded');
                resolve();
                return;
            }

            // Check if script already exists
            if (document.querySelector('script[src*="chart.min.js"]')) {
                // Wait for it to load
                const checkLoaded = setInterval(() => {
                    if (typeof window.Chart !== 'undefined') {
                        clearInterval(checkLoaded);
                        console.log('Chart.js loaded from existing script');
                        resolve();
                    }
                }, 100);
                return;
            }

            const script = document.createElement('script');
            script.src = 'https://cdnjs.cloudflare.com/ajax/libs/Chart.js/3.9.1/chart.min.js';
            script.onload = () => {
                console.log('Chart.js loaded successfully');
                resolve();
            };
            script.onerror = () => {
                console.error('Failed to load Chart.js');
                reject(new Error('Failed to load Chart.js'));
            };
            document.head.appendChild(script);
        });
    }

    setupTabHandlers() {
        // Set up tab switching handlers to re-render charts
        const tabLinks = document.querySelectorAll('.o_notebook .nav-link');
        tabLinks.forEach(tab => {
            tab.addEventListener('click', (e) => {
                // Wait for tab content to be visible before rendering charts
                setTimeout(() => {
                    this.resizeVisibleCharts();
                    // Force chart re-initialization if tab contains charts
                    this.scheduleChartInitialization(400);
                }, 200);
            });
        });
    }

    resizeVisibleCharts() {
        // Resize charts that are currently visible
        Object.keys(this.chartInstances).forEach(chartId => {
            const canvas = document.getElementById(chartId);
            if (canvas && this.isElementVisible(canvas)) {
                const chart = this.chartInstances[chartId];
                if (chart) {
                    try {
                        chart.resize();
                        chart.update('none'); // Update without animation for faster response
                    } catch (error) {
                        console.error(`Error resizing chart ${chartId}:`, error);
                    }
                }
            }
        });
    }

    isElementVisible(element) {
        return element.offsetParent !== null &&
               element.offsetWidth > 0 &&
               element.offsetHeight > 0 &&
               window.getComputedStyle(element).display !== 'none' &&
               window.getComputedStyle(element).visibility !== 'hidden';
    }

    async onRecordSaved(record) {
        await super.onRecordSaved(record);
        // Reset initialization flag and schedule chart re-initialization
        this.chartsInitialized = false;
        this.scheduleChartInitialization(800);
    }

    initializeCharts() {
        try {
            // Check if Chart.js is available
            if (typeof window.Chart === 'undefined') {
                console.error('Chart.js is not loaded');
                return;
            }

            const record = this.model.root;
            if (!record || !record.data) {
                console.log('No record data available for charts');
                return;
            }

            console.log('Initializing charts with data:', record.data);

            // Clean up existing charts first
            this.cleanupCharts();

            // Initialize all charts with error handling
            const chartMethods = [
                () => this.createStatusChart(record.data),
                () => this.createBookingTypeChart(record.data),
                () => this.createRevenueChart(record.data),
                () => this.createVehicleUtilizationChart(record.data),
                () => this.createDailyTrendChart(record.data),
                () => this.createCancellationChart(record.data)
            ];

            // Initialize charts with small delays to prevent DOM conflicts
            chartMethods.forEach((method, index) => {
                setTimeout(() => {
                    try {
                        method();
                    } catch (error) {
                        console.error(`Error initializing chart ${index}:`, error);
                    }
                }, index * 50);
            });

            this.chartsInitialized = true;
            console.log('All charts initialization scheduled');

        } catch (error) {
            console.error('Error initializing charts:', error);
        }
    }

    destroyExistingChart(chartId) {
        if (this.chartInstances[chartId]) {
            try {
                this.chartInstances[chartId].destroy();
                delete this.chartInstances[chartId];
                console.log(`Chart ${chartId} destroyed successfully`);
            } catch (error) {
                console.error(`Error destroying chart ${chartId}:`, error);
                // Force remove from instances even if destroy failed
                delete this.chartInstances[chartId];
            }
        }
    }

    createChartWithErrorHandling(chartId, chartConfig, chartData) {
        const canvas = document.getElementById(chartId);
        if (!canvas) {
            console.warn(`${chartId} canvas not found in DOM`);
            return;
        }

        // Check if canvas is visible (important for tab-based layouts)
        if (!this.isElementVisible(canvas)) {
            console.log(`${chartId} canvas is not visible, skipping for now`);
            return;
        }

        this.destroyExistingChart(chartId);

        try {
            let parsedData;
            try {
                parsedData = chartData ? JSON.parse(chartData) : { labels: [], data: [] };
                console.log(`Parsed data for ${chartId}:`, parsedData);
            } catch (parseError) {
                console.error(`Error parsing ${chartId} data:`, parseError);
                parsedData = { labels: [], data: [] };
            }

            // Validate data before creating chart
            if (!parsedData.labels || !Array.isArray(parsedData.labels)) {
                console.warn(`Invalid labels for ${chartId}, using empty array`);
                parsedData.labels = [];
            }

            const ctx = canvas.getContext('2d');
            if (!ctx) {
                console.error(`Could not get 2D context for ${chartId}`);
                return;
            }

            // Create chart configuration
            const config = chartConfig(parsedData);

            // Ensure canvas dimensions are set
            if (canvas.offsetWidth === 0 || canvas.offsetHeight === 0) {
                console.warn(`Canvas ${chartId} has zero dimensions`);
                // Set minimum dimensions
                canvas.style.width = canvas.style.width || '400px';
                canvas.style.height = canvas.style.height || '300px';
            }

            this.chartInstances[chartId] = new window.Chart(ctx, config);
            console.log(`${chartId} created successfully`);

        } catch (error) {
            console.error(`Error creating ${chartId}:`, error);
            // Ensure the failed chart is not left in instances
            delete this.chartInstances[chartId];
        }
    }

    createStatusChart(data) {
        this.createChartWithErrorHandling('statusPieChart', (chartData) => ({
            type: 'pie',
            data: {
                labels: chartData.labels || [],
                datasets: [{
                    data: chartData.data || [],
                    backgroundColor: [
                        '#3498db', // Enquiry - Blue
                        '#f39c12', // Quotation - Orange
                        '#e67e22', // Follow Up - Dark Orange
                        '#2ecc71', // Confirmed - Green
                        '#27ae60', // Completed - Dark Green
                        '#e74c3c', // Cancelled - Red
                    ],
                    borderWidth: 2,
                    borderColor: '#fff'
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        position: 'bottom',
                        labels: {
                            padding: 20,
                            usePointStyle: true
                        }
                    },
                    tooltip: {
                        callbacks: {
                            label: function(context) {
                                const total = context.dataset.data.reduce((a, b) => a + b, 0);
                                const percentage = total > 0 ? Math.round((context.parsed * 100) / total) : 0;
                                return context.label + ': ' + context.parsed + ' (' + percentage + '%)';
                            }
                        }
                    }
                }
            }
        }), data.status_chart_data);
    }

    createBookingTypeChart(data) {
        this.createChartWithErrorHandling('bookingTypeChart', (chartData) => ({
            type: 'doughnut',
            data: {
                labels: chartData.labels || [],
                datasets: [{
                    data: chartData.data || [],
                    backgroundColor: ['#9b59b6', '#34495e'],
                    borderWidth: 2,
                    borderColor: '#fff'
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        position: 'bottom',
                        labels: {
                            padding: 20,
                            usePointStyle: true
                        }
                    }
                }
            }
        }), data.booking_type_chart_data);
    }

    createRevenueChart(data) {
        this.createChartWithErrorHandling('revenueChart', (chartData) => ({
            type: 'bar',
            data: {
                labels: chartData.labels || [],
                datasets: [{
                    label: 'Revenue (₹)',
                    data: chartData.data || [],
                    backgroundColor: 'rgba(102, 126, 234, 0.8)',
                    borderColor: '#667eea',
                    borderWidth: 2,
                    borderRadius: 8
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
                                return '₹' + value.toLocaleString();
                            }
                        }
                    }
                },
                plugins: {
                    tooltip: {
                        callbacks: {
                            label: function(context) {
                                return 'Revenue: ₹' + context.parsed.y.toLocaleString();
                            }
                        }
                    }
                }
            }
        }), data.revenue_chart_data);
    }

    createVehicleUtilizationChart(data) {
        this.createChartWithErrorHandling('vehicleUtilizationChart', (chartData) => ({
            type: 'bar',
            data: {
                labels: chartData.labels || [],
                datasets: [{
                    label: 'Bookings',
                    data: chartData.data || [],
                    backgroundColor: 'rgba(26, 188, 156, 0.8)',
                    borderColor: '#1abc9c',
                    borderWidth: 2,
                    borderRadius: 8
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                indexAxis: 'y',
                scales: {
                    x: {
                        beginAtZero: true
                    }
                }
            }
        }), data.vehicle_utilization_chart_data);
    }

    createDailyTrendChart(data) {
        this.createChartWithErrorHandling('dailyTrendChart', (chartData) => ({
            type: 'line',
            data: {
                labels: chartData.labels || [],
                datasets: [{
                    label: 'Bookings',
                    data: chartData.bookings || [],
                    backgroundColor: 'rgba(52, 152, 219, 0.1)',
                    borderColor: '#3498db',
                    borderWidth: 3,
                    fill: true,
                    tension: 0.4,
                    yAxisID: 'y'
                }, {
                    label: 'Revenue (₹)',
                    data: chartData.revenue || [],
                    backgroundColor: 'rgba(155, 89, 182, 0.1)',
                    borderColor: '#9b59b6',
                    borderWidth: 3,
                    fill: true,
                    tension: 0.4,
                    yAxisID: 'y1'
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                interaction: {
                    mode: 'index',
                    intersect: false,
                },
                scales: {
                    y: {
                        type: 'linear',
                        display: true,
                        position: 'left',
                        title: {
                            display: true,
                            text: 'Number of Bookings'
                        }
                    },
                    y1: {
                        type: 'linear',
                        display: true,
                        position: 'right',
                        title: {
                            display: true,
                            text: 'Revenue (₹)'
                        },
                        grid: {
                            drawOnChartArea: false
                        },
                        ticks: {
                            callback: function(value) {
                                return '₹' + value.toLocaleString();
                            }
                        }
                    }
                }
            }
        }), data.daily_trend_chart_data);
    }

    createCancellationChart(data) {
        this.createChartWithErrorHandling('cancellationChart', (chartData) => ({
            type: 'bar',
            data: {
                labels: chartData.labels || [],
                datasets: [{
                    label: 'Cancellations',
                    data: chartData.cancellations || [],
                    backgroundColor: 'rgba(231, 76, 60, 0.8)',
                    borderColor: '#e74c3c',
                    borderWidth: 2,
                    borderRadius: 8,
                    yAxisID: 'y'
                }, {
                    label: 'Refunds (₹)',
                    data: chartData.refunds || [],
                    type: 'line',
                    borderColor: '#f39c12',
                    backgroundColor: 'rgba(243, 156, 18, 0.1)',
                    borderWidth: 3,
                    fill: true,
                    tension: 0.4,
                    yAxisID: 'y1'
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                interaction: {
                    mode: 'index',
                    intersect: false,
                },
                scales: {
                    y: {
                        type: 'linear',
                        display: true,
                        position: 'left',
                        title: {
                            display: true,
                            text: 'Number of Cancellations'
                        }
                    },
                    y1: {
                        type: 'linear',
                        display: true,
                        position: 'right',
                        title: {
                            display: true,
                            text: 'Refund Amount (₹)'
                        },
                        grid: {
                            drawOnChartArea: false
                        },
                        ticks: {
                            callback: function(value) {
                                return '₹' + value.toLocaleString();
                            }
                        }
                    }
                }
            }
        }), data.cancellation_chart_data);
    }

    cleanupCharts() {
        // Clean up chart instances
        for (const chartId in this.chartInstances) {
            if (this.chartInstances[chartId]) {
                try {
                    this.chartInstances[chartId].destroy();
                    console.log(`Chart ${chartId} cleaned up successfully`);
                } catch (error) {
                    console.error(`Error destroying chart ${chartId}:`, error);
                }
            }
        }
        this.chartInstances = {};
        this.chartsInitialized = false;
    }
}

// Register the controller
registry.category("views").add("fleet_booking_dashboard_form", {
    ...registry.category("views").get("form"),
    Controller: FleetBookingDashboardController,
});