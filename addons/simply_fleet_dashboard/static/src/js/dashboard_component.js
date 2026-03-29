/** @odoo-module */

import { Component, onWillStart, onMounted, useState, useRef } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { loadJS } from "@web/core/assets";

export class FleetDashboard extends Component {
    setup() {
        this.orm = useService("orm");
        this.actionService = useService("action");

        this.state = useState({
            kpis: {},
            dateFilter: 'this_month',
            vehicleFilter: 0,      // Tracks the selected vehicle
            vehicles: [],          // Holds the list of vehicles for the dropdown
            isLoading: true
        });

        // Canvas references
        this.pieChartRef = useRef("pieChart");
        this.lineChartRef = useRef("lineChart");
        this.barChartRef = useRef("barChart");
        this.colChartRef = useRef("colChart");
        this.mileageChartRef = useRef("mileageChart");

        // Keep track of chart instances to destroy them before re-rendering
        this.chartInstances = {};

        onWillStart(async () => {
            await loadJS("/web/static/lib/Chart/Chart.js");
            await this.fetchData();
            // Turn off loading ONLY once during the initial mount
            this.state.isLoading = false;
        });

        onMounted(() => {
            this.renderCharts();
        });
    }

    async fetchData() {
        // Send both filters to the Python backend
        const result = await this.orm.call(
            "simply.fleet.dashboard",
            "get_dashboard_data",
            [this.state.dateFilter, parseInt(this.state.vehicleFilter)] 
        );
        this.state.kpis = result.kpis;
        this.chartData = result.charts;
        this.state.vehicles = result.vehicles;
    }

    async onFilterChange(ev) {
        this.state.dateFilter = ev.target.value;
        await this.fetchData();
        this.renderCharts();
    }

    async onVehicleFilterChange(ev) {
        this.state.vehicleFilter = parseInt(ev.target.value);
        await this.fetchData();
        this.renderCharts();
    }

    renderCharts() {
        if (this.state.isLoading) return;

        // Clean up old charts safely
        Object.values(this.chartInstances).forEach(chart => {
            if (chart) chart.destroy();
        });

        // 1. Pie Chart (Vehicle Status)
        if (this.pieChartRef.el) {
            this.chartInstances.pie = new Chart(this.pieChartRef.el, {
                type: 'pie',
                data: {
                    labels: this.chartData.vehicle_pie.labels,
                    datasets: [{
                        data: this.chartData.vehicle_pie.data,
                        backgroundColor: ['#00E396', '#FEB019', '#FF4560']
                    }]
                },
                options: { responsive: true, maintainAspectRatio: false }
            });
        }

        // 2. Line Chart (Fuel Consumption)
        if (this.lineChartRef.el) {
            this.chartInstances.line = new Chart(this.lineChartRef.el, {
                type: 'line',
                data: {
                    labels: this.chartData.fuel_line.labels,
                    datasets: [{
                        label: 'Fuel Consumed (Liters)',
                        data: this.chartData.fuel_line.data,
                        borderColor: '#008FFB',
                        tension: 0.3,
                        fill: true,
                        backgroundColor: 'rgba(0, 143, 251, 0.2)'
                    }]
                },
                options: { responsive: true, maintainAspectRatio: false }
            });
        }

        // 3. Bar Chart (Work Order Costs)
        if (this.barChartRef.el) {
            this.chartInstances.bar = new Chart(this.barChartRef.el, {
                type: 'bar',
                data: {
                    labels: this.chartData.wo_bar.labels,
                    datasets: [{
                        label: 'Total Cost',
                        data: this.chartData.wo_bar.data,
                        backgroundColor: '#775DD0'
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    indexAxis: 'y'
                }
            });
        }

        // 4. Column Chart (Tanker Levels)
        if (this.colChartRef.el) {
            this.chartInstances.col = new Chart(this.colChartRef.el, {
                type: 'bar',
                data: {
                    labels: this.chartData.tanker_col.labels,
                    datasets: [
                        {
                            label: 'Current Fuel',
                            data: this.chartData.tanker_col.current,
                            backgroundColor: '#00E396'
                        },
                        {
                            label: 'Total Capacity',
                            data: this.chartData.tanker_col.capacity,
                            backgroundColor: '#D1D5DB'
                        }
                    ]
                },
                options: { responsive: true, maintainAspectRatio: false }
            });
        }

        // 5. Dynamic Line Chart (Vehicle Mileage)
        if (this.mileageChartRef.el) {
            this.chartInstances.mileage = new Chart(this.mileageChartRef.el, {
                type: 'line',
                data: {
                    labels: this.chartData.mileage_line.labels,
                    datasets: [{
                        label: this.chartData.mileage_line.label, // Dynamic label from Python
                        data: this.chartData.mileage_line.data,
                        borderColor: '#FF4560',
                        backgroundColor: 'rgba(255, 69, 96, 0.1)',
                        tension: 0.4,
                        fill: true,
                        pointBackgroundColor: '#FF4560',
                        pointRadius: 4,
                        pointHoverRadius: 6
                    }]
                },
                options: { 
                    responsive: true, 
                    maintainAspectRatio: false,
                    scales: {
                        y: {
                            beginAtZero: true,
                            title: { display: true, text: 'Mileage (km/l)' }
                        }
                    }
                }
            });
        }
    }

    // Action routers for KPI clicks
    openVehicles() {
        this.actionService.doAction({
            type: "ir.actions.act_window",
            res_model: "simply.fleet.vehicle",
            views: [[false, "list"], [false, "form"]],
            domain: [['state', '=', 'active']]
        });
    }
}

FleetDashboard.template = "simply_fleet_dashboard.DashboardTemplate";
registry.category("actions").add("simply_fleet_dashboard_action", FleetDashboard);
