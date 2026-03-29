/** @odoo-module **/

import { registry } from "@web/core/registry";
import { Component, useState, onWillStart } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";

export class DriverPerformanceDashboard extends Component {
    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.state = useState({
            periodType: 'monthly',
            topDrivers: [],
            performanceData: [],
            statistics: {
                totalDrivers: 0,
                avgScore: 0,
                totalRewards: 0,
                excellentDrivers: 0
            }
        });

        onWillStart(async () => {
            await this.loadDashboardData();
        });
    }

    async loadDashboardData() {
        try {
            const domain = [
                ['period_type', '=', this.state.periodType],
                ['state', 'in', ['calculated', 'approved', 'rewarded']]
            ];

            // Get current month data
            const today = new Date();
            const firstDay = new Date(today.getFullYear(), today.getMonth(), 1);
            const lastDay = new Date(today.getFullYear(), today.getMonth() + 1, 0);

            domain.push(['period_start', '>=', firstDay.toISOString().split('T')[0]]);
            domain.push(['period_end', '<=', lastDay.toISOString().split('T')[0]]);

            // Load performance records
            const performances = await this.orm.searchRead(
                'simply.fleet.driver.performance',
                domain,
                ['driver_id', 'performance_score', 'reward_amount', 'average_mileage',
                 'total_distance', 'performance_grade'],
                { order: 'performance_score desc', limit: 10 }
            );

            this.state.topDrivers = performances;

            // Calculate statistics
            const allPerformances = await this.orm.searchRead(
                'simply.fleet.driver.performance',
                domain,
                ['performance_score', 'reward_amount', 'performance_grade']
            );

            const totalScore = allPerformances.reduce((sum, p) => sum + p.performance_score, 0);
            const totalRewards = allPerformances.reduce((sum, p) => sum + p.reward_amount, 0);
            const excellentCount = allPerformances.filter(p => p.performance_grade === 'excellent').length;

            this.state.statistics = {
                totalDrivers: allPerformances.length,
                avgScore: allPerformances.length > 0 ? (totalScore / allPerformances.length).toFixed(2) : 0,
                totalRewards: totalRewards.toFixed(2),
                excellentDrivers: excellentCount
            };

            this.state.performanceData = allPerformances;
        } catch (error) {
            console.error('Error loading dashboard data:', error);
        }
    }

    async onPeriodChange(periodType) {
        this.state.periodType = periodType;
        await this.loadDashboardData();
    }

    openPerformanceRecord(performanceId) {
        this.action.doAction({
            type: 'ir.actions.act_window',
            res_model: 'simply.fleet.driver.performance',
            res_id: performanceId,
            views: [[false, 'form']],
            target: 'current',
        });
    }

    openAllPerformances() {
        this.action.doAction({
            name: 'Driver Performance',
            type: 'ir.actions.act_window',
            res_model: 'simply.fleet.driver.performance',
            views: [[false, 'tree'], [false, 'form']],
            target: 'current',
        });
    }

    getGradeClass(grade) {
        const gradeMap = {
            'excellent': 'score_excellent',
            'good': 'score_good',
            'average': 'score_average',
            'below_average': 'score_below',
            'poor': 'score_below'
        };
        return gradeMap[grade] || 'score_average';
    }

    getGradeLabel(grade) {
        const labelMap = {
            'excellent': 'Excellent',
            'good': 'Good',
            'average': 'Average',
            'below_average': 'Below Avg',
            'poor': 'Poor'
        };
        return labelMap[grade] || grade;
    }
}

DriverPerformanceDashboard.template = "simply_fleet_performance.DriverPerformanceDashboard";

registry.category("actions").add("driver_performance_dashboard", DriverPerformanceDashboard);