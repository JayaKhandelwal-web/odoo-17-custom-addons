/** @odoo-module **/

import { Component, onMounted, onWillUnmount, onPatched } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { FormController } from "@web/views/form/form_controller";

export class MyOperatorDashboardFormController extends FormController {
    setup() {
        super.setup();
        this.charts = {};

        onMounted(() => {
            this.loadChartJS().then(() => {
                this.renderAllCharts();
            });
        });

        onPatched(() => {
            // Re-render charts when data updates
            setTimeout(() => {
                this.renderAllCharts();
            }, 100);
        });

        onWillUnmount(() => {
            this.destroyAllCharts();
        });
    }

    async loadChartJS() {
        if (window.Chart) {
            return Promise.resolve();
        }

        return new Promise((resolve, reject) => {
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

    getChartData(fieldName) {
        try {
            // Try to get data from the form record
            if (this.model && this.model.root && this.model.root.data) {
                const fieldValue = this.model.root.data[fieldName];
                if (fieldValue) {
                    return JSON.parse(fieldValue);
                }
            }

            // Fallback: try to get from DOM
            const element = document.querySelector(`[name="${fieldName}"]`);
            if (element) {
                const dataStr = element.textContent || element.value || element.getAttribute('value');
                if (dataStr && dataStr !== 'False') {
                    return JSON.parse(dataStr);
                }
            }

            return null;
        } catch (e) {
            console.error(`Error parsing chart data for ${fieldName}:`, e);
            return null;
        }
    }

    renderAllCharts() {
        if (!window.Chart) {
            console.warn('Chart.js not loaded yet');
            return;
        }

        // Destroy existing charts before creating new ones
        this.destroyAllCharts();

        // Wait a bit for DOM to be ready
        setTimeout(() => {
            this.renderChart('callTypeChart', 'call_type_chart_data', 'pie', {
                title: 'Call Type Distribution'
            });

            this.renderChart('callStatusChart', 'call_status_chart_data', 'pie', {
                title: 'Call Status Distribution'
            });

            this.renderChart('dailyCallsChart', 'daily_calls_chart_data', 'line', {
                title: 'Daily Calls Trend',
                scales: {
                    y: {
                        beginAtZero: true,
                        title: { display: true, text: 'Number of Calls' }
                    },
                    x: {
                        title: { display: true, text: 'Date' }
                    }
                }
            });

            this.renderChart('hourlyChart', 'hourly_distribution_chart_data', 'bar', {
                title: 'Hourly Call Distribution',
                scales: {
                    y: {
                        beginAtZero: true,
                        title: { display: true, text: 'Number of Calls' }
                    },
                    x: {
                        title: { display: true, text: 'Hour of Day' }
                    }
                }
            });

            this.renderChart('topCallersChart', 'top_callers_chart_data', 'bar', {
                title: 'Top Callers',
                indexAxis: 'y',
                scales: {
                    x: {
                        beginAtZero: true,
                        title: { display: true, text: 'Number of Calls' }
                    }
                }
            });

            this.renderChart('conversationStatusChart', 'conversation_status_chart_data', 'pie', {
                title: 'Conversation Status Distribution'
            });

            this.renderChart('messageTypesChart', 'message_types_chart_data', 'doughnut', {
                title: 'Message Types Distribution'
            });

            this.renderChart('dailyMessagesChart', 'daily_messages_chart_data', 'line', {
                title: 'Daily Messages Trend',
                fill: true,
                scales: {
                    y: {
                        beginAtZero: true,
                        title: { display: true, text: 'Number of Messages' }
                    },
                    x: {
                        title: { display: true, text: 'Date' }
                    }
                }
            });

            this.renderChart('agentPerformanceChart', 'agent_performance_chart_data', 'bar', {
                title: 'Agent Performance',
                scales: {
                    y: {
                        beginAtZero: true,
                        title: { display: true, text: 'Number of Conversations' }
                    }
                }
            });

            this.renderChart('communicationTrendChart', 'communication_trend_chart_data', 'bar', {
                title: 'Communication Trend (Calls vs Messages)',
                scales: {
                    y: {
                        type: 'linear',
                        display: true,
                        position: 'left',
                        title: { display: true, text: 'Number of Calls' }
                    },
                    y1: {
                        type: 'linear',
                        display: true,
                        position: 'right',
                        title: { display: true, text: 'Number of Messages' },
                        grid: { drawOnChartArea: false }
                    }
                }
            });

            this.renderChart('contactEngagementChart', 'contact_engagement_chart_data', 'scatter', {
                title: 'Contact Engagement Analysis',
                scales: {
                    x: {
                        title: { display: true, text: 'Number of Calls' }
                    },
                    y: {
                        title: { display: true, text: 'Number of WhatsApp Conversations' }
                    }
                }
            });
        }, 200);
    }

    renderChart(canvasId, dataField, chartType, options = {}) {
        const canvas = document.getElementById(canvasId);
        if (!canvas) {
            console.warn(`Canvas element not found: ${canvasId}`);
            return;
        }

        const data = this.getChartData(dataField);
        if (!data) {
            console.warn(`No data found for: ${dataField}`);
            this.renderEmptyChart(canvas, chartType, options.title || '');
            return;
        }

        try {
            const ctx = canvas.getContext('2d');

            const config = {
                type: chartType,
                data: data,
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        title: {
                            display: true,
                            text: options.title || '',
                            font: { size: 16, weight: 'bold' }
                        },
                        legend: {
                            position: chartType === 'bar' && options.indexAxis === 'y' ? 'top' : 'bottom',
                            labels: { boxWidth: 12 }
                        },
                        tooltip: {
                            callbacks: chartType === 'scatter' ? {
                                label: function(context) {
                                    const point = context.raw;
                                    return (point.label || 'Contact') + ': (' + point.x + ', ' + point.y + ')';
                                }
                            } : undefined
                        }
                    },
                    indexAxis: options.indexAxis || 'x',
                    scales: options.scales || {},
                    elements: options.fill ? {
                        line: { tension: 0.4 },
                        point: { radius: 3 }
                    } : undefined
                }
            };

            // Apply fill for area charts
            if (options.fill && data.datasets) {
                data.datasets.forEach(dataset => {
                    dataset.fill = true;
                });
            }

            this.charts[canvasId] = new Chart(ctx, config);
            console.log(`Chart rendered successfully: ${canvasId}`);

        } catch (error) {
            console.error(`Error creating chart ${canvasId}:`, error);
            this.renderEmptyChart(canvas, chartType, options.title || '');
        }
    }

    renderEmptyChart(canvas, chartType, title) {
        try {
            const ctx = canvas.getContext('2d');
            const emptyData = {
                labels: ['No Data Available'],
                datasets: [{
                    label: 'No Data',
                    data: [0],
                    backgroundColor: ['#e0e0e0'],
                    borderColor: ['#bdbdbd']
                }]
            };

            this.charts[canvas.id] = new Chart(ctx, {
                type: chartType === 'scatter' ? 'bar' : chartType,
                data: emptyData,
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        title: {
                            display: true,
                            text: title,
                            font: { size: 16, weight: 'bold' }
                        },
                        legend: { display: false }
                    }
                }
            });
        } catch (error) {
            console.error(`Error creating empty chart for ${canvas.id}:`, error);
        }
    }

    destroyAllCharts() {
        Object.keys(this.charts).forEach(chartId => {
            if (this.charts[chartId]) {
                try {
                    this.charts[chartId].destroy();
                } catch (error) {
                    console.warn(`Error destroying chart ${chartId}:`, error);
                }
            }
        });
        this.charts = {};
    }
}

// Register the custom form controller
registry.category("views").add("myoperator_dashboard_form", {
    ...registry.category("views").get("form"),
    Controller: MyOperatorDashboardFormController,
});