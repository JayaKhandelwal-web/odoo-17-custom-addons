/** @odoo-module **/

import { Component, useState, onMounted, onWillUnmount } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

/**
 * FleetX Dashboard Component
 */
export class FleetXDashboard extends Component {
    setup() {
        this.orm = useService("orm");
        this.notification = useService("notification");
        
        this.state = useState({
            loading: true,
            error: null,
            data: {
                vehicle_statistics: {},
                analytics: {},
                recent_vehicles: [],
                chart_data: {},
                last_sync: null
            },
            refreshInterval: null
        });

        onMounted(() => {
            this.loadDashboardData();
            this.startAutoRefresh();
        });

        onWillUnmount(() => {
            this.stopAutoRefresh();
        });
    }

    /**
     * Load dashboard data from backend
     */
    async loadDashboardData() {
        try {
            this.state.loading = true;
            this.state.error = null;

            const response = await this.orm.call(
                'fleetx.analytics',
                'get_latest_analytics',
                []
            );

            const vehicleStats = await this.orm.call(
                'fleetx.vehicle',
                'get_vehicle_statistics',
                []
            );

            const chartData = await this.orm.call(
                'fleetx.analytics',
                'get_analytics_chart_data',
                [7] // Last 7 days
            );

            const recentVehicles = await this.orm.searchRead(
                'fleetx.vehicle',
                [['last_updated_at', '!=', false]],
                ['vehicle_number', 'current_status', 'speed', 'last_updated_at'],
                { limit: 10, order: 'last_updated_at desc' }
            );

            this.state.data = {
                vehicle_statistics: vehicleStats,
                analytics: response,
                recent_vehicles: recentVehicles,
                chart_data: chartData,
                last_sync: response.create_date || null
            };

        } catch (error) {
            console.error('Error loading dashboard data:', error);
            this.state.error = error.message || 'Failed to load dashboard data';
            this.notification.add('Failed to load dashboard data', {
                type: 'danger'
            });
        } finally {
            this.state.loading = false;
        }
    }

    /**
     * Start auto refresh timer
     */
    startAutoRefresh() {
        // Get refresh interval from system parameter (default 30 seconds)
        const refreshInterval = 30000; // 30 seconds
        
        this.state.refreshInterval = setInterval(() => {
            this.loadDashboardData();
        }, refreshInterval);
    }

    /**
     * Stop auto refresh timer
     */
    stopAutoRefresh() {
        if (this.state.refreshInterval) {
            clearInterval(this.state.refreshInterval);
            this.state.refreshInterval = null;
        }
    }

    /**
     * Manual refresh action
     */
    async onRefresh() {
        await this.loadDashboardData();
        this.notification.add('Dashboard refreshed', {
            type: 'success'
        });
    }

    /**
     * Sync data with FleetX API
     */
    async onSyncData() {
        try {
            await this.orm.call(
                'fleetx.config',
                'auto_sync_vehicles',
                []
            );
            
            // Reload dashboard after sync
            await this.loadDashboardData();
            
            this.notification.add('Data synchronized successfully', {
                type: 'success'
            });
        } catch (error) {
            console.error('Error syncing data:', error);
            this.notification.add('Failed to sync data: ' + error.message, {
                type: 'danger'
            });
        }
    }

    /**
     * Get status color for vehicle
     */
    getStatusColor(status) {
        const colorMap = {
            'RUNNING': '#28a745',
            'IDLE': '#ffc107',
            'PARKED': '#17a2b8',
            'REMOVED': '#6c757d',
            'UNREACHABLE': '#dc3545',
            'NO_POWER': '#dc3545',
            'BATTERY_DISCHARGED': '#fd7e14',
            'INSHOP': '#6f42c1',
            'DISCONNECTED': '#dc3545',
            'IMMOBILISED': '#dc3545',
            'STANDBY': '#20c997'
        };
        return colorMap[status] || '#6c757d';
    }

    /**
     * Format time ago
     */
    timeAgo(dateString) {
        if (!dateString) return 'Unknown';
        
        const date = new Date(dateString);
        const now = new Date();
        const diffInSeconds = Math.floor((now - date) / 1000);
        
        if (diffInSeconds < 60) {
            return `${diffInSeconds} seconds ago`;
        } else if (diffInSeconds < 3600) {
            return `${Math.floor(diffInSeconds / 60)} minutes ago`;
        } else if (diffInSeconds < 86400) {
            return `${Math.floor(diffInSeconds / 3600)} hours ago`;
        } else {
            return `${Math.floor(diffInSeconds / 86400)} days ago`;
        }
    }
}

FleetXDashboard.template = "fleetx_integration.FleetXDashboard";

/**
 * FleetX Vehicle Map Component
 */
export class FleetXVehicleMap extends Component {
    setup() {
        this.orm = useService("orm");
        this.state = useState({
            vehicles: [],
            loading: true,
            mapInitialized: false
        });

        onMounted(() => {
            this.loadVehicles();
            this.initializeMap();
        });
    }

    async loadVehicles() {
        try {
            const vehicles = await this.orm.searchRead(
                'fleetx.vehicle',
                [['latitude', '!=', 0], ['longitude', '!=', 0]],
                ['vehicle_number', 'vehicle_name', 'current_status', 'latitude', 'longitude', 'address', 'speed']
            );
            
            this.state.vehicles = vehicles;
            this.state.loading = false;
            
            if (this.state.mapInitialized) {
                this.updateMapMarkers();
            }
        } catch (error) {
            console.error('Error loading vehicles:', error);
            this.state.loading = false;
        }
    }

    initializeMap() {
        // This would initialize Google Maps or another mapping service
        // For now, we'll just mark it as initialized
        this.state.mapInitialized = true;
        
        if (this.state.vehicles.length > 0) {
            this.updateMapMarkers();
        }
    }

    updateMapMarkers() {
        // This would update map markers based on vehicle data
        console.log('Updating map markers for', this.state.vehicles.length, 'vehicles');
    }
}

FleetXVehicleMap.template = "fleetx_integration.FleetXVehicleMap";

// Register components
registry.category("actions").add("fleetx_dashboard", FleetXDashboard);
registry.category("actions").add("fleetx_vehicle_map", FleetXVehicleMap);

// Utility functions for FleetX integration
export const FleetXUtils = {
    /**
     * Format vehicle status for display
     */
    formatStatus(status) {
        if (!status) return 'Unknown';
        return status.replace(/_/g, ' ').toLowerCase()
            .replace(/\b\w/g, l => l.toUpperCase());
    },

    /**
     * Get fuel level color based on percentage
     */
    getFuelLevelColor(percentage) {
        if (percentage > 50) return 'success';
        if (percentage > 20) return 'warning';
        return 'danger';
    },

    /**
     * Format distance for display
     */
    formatDistance(meters) {
        if (meters < 1000) {
            return `${Math.round(meters)} m`;
        } else {
            return `${(meters / 1000).toFixed(1)} km`;
        }
    },

    /**
     * Format speed for display
     */
    formatSpeed(speed) {
        return `${Math.round(speed)} km/h`;
    },

    /**
     * Generate Google Maps link
     */
    getGoogleMapsLink(lat, lng) {
        return `https://www.google.com/maps?q=${lat},${lng}`;
    }
};

// Export for use in other modules
window.FleetXUtils = FleetXUtils;