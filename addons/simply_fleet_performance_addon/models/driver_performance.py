# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
import logging

_logger = logging.getLogger(__name__)


class DriverPerformance(models.Model):
    _name = 'simply.fleet.driver.performance'
    _description = 'Driver Performance Tracking'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'period_start desc, performance_score desc'

    name = fields.Char(string='Reference', required=True, copy=False,
                       readonly=True, default='New')
    driver_id = fields.Many2one('hr.employee', string='Driver',
                                required=True, tracking=True,
                                domain=[('job_id.name', 'ilike', 'driver')])
    period_type = fields.Selection([
        ('weekly', 'Weekly'),
        ('monthly', 'Monthly')
    ], string='Period Type', required=True, default='weekly', tracking=True)

    period_start = fields.Date(string='Period Start', required=True, tracking=True)
    period_end = fields.Date(string='Period End', required=True, tracking=True)

    # Performance Metrics
    total_trips = fields.Integer(string='Total Trips', compute='_compute_metrics', store=True)
    total_distance = fields.Float(string='Total Distance (km)', compute='_compute_metrics',
                                  store=True, digits=(16, 2))
    total_fuel_consumed = fields.Float(string='Total Fuel (L)', compute='_compute_metrics',
                                       store=True, digits=(16, 2))
    average_mileage = fields.Float(string='Avg Mileage (km/L)', compute='_compute_metrics',
                                   store=True, digits=(16, 2))
    total_fuel_cost = fields.Float(string='Total Fuel Cost', compute='_compute_metrics',
                                   store=True, digits=(16, 2))
    cost_per_km = fields.Float(string='Cost per KM', compute='_compute_metrics',
                               store=True, digits=(16, 2))

    # Performance Score (0-100)
    performance_score = fields.Float(string='Performance Score',
                                     compute='_compute_performance_score',
                                     store=True, tracking=True)

    # Reward Calculation
    reward_points = fields.Integer(string='Reward Points',
                                   compute='_compute_reward_points',
                                   store=True, tracking=True)
    reward_amount = fields.Float(string='Reward Amount',
                                 compute='_compute_reward_amount',
                                 store=True, tracking=True)

    performance_grade = fields.Selection([
        ('excellent', 'Excellent (90-100)'),
        ('good', 'Good (75-89)'),
        ('average', 'Average (60-74)'),
        ('below_average', 'Below Average (40-59)'),
        ('poor', 'Poor (0-39)')
    ], string='Performance Grade', compute='_compute_performance_grade',
        store=True, tracking=True)

    # Fuel Log Lines
    fuel_log_ids = fields.One2many('simply.fleet.fuel.log', 'performance_id',
                                   string='Fuel Logs')

    # Additional Metrics
    best_mileage = fields.Float(string='Best Mileage (km/L)',
                                compute='_compute_best_worst', store=True)
    worst_mileage = fields.Float(string='Worst Mileage (km/L)',
                                 compute='_compute_best_worst', store=True)

    state = fields.Selection([
        ('draft', 'Draft'),
        ('calculated', 'Calculated'),
        ('approved', 'Approved'),
        ('rewarded', 'Rewarded')
    ], string='Status', default='draft', tracking=True)

    notes = fields.Text(string='Notes')
    active = fields.Boolean(default=True)

    # Company-wide comparison
    rank = fields.Integer(string='Rank', compute='_compute_rank', store=True)
    total_drivers = fields.Integer(string='Total Drivers', compute='_compute_rank', store=True)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                vals['name'] = self.env['ir.sequence'].next_by_code(
                    'simply.fleet.driver.performance') or 'New'
        return super().create(vals_list)

    @api.depends('driver_id', 'period_start', 'period_end')
    def _compute_metrics(self):
        for record in self:
            if not record.driver_id or not record.period_start or not record.period_end:
                record.total_trips = 0
                record.total_distance = 0
                record.total_fuel_consumed = 0
                record.average_mileage = 0
                record.total_fuel_cost = 0
                record.cost_per_km = 0
                continue

            # Get fuel logs for this driver in the period
            fuel_logs = self.env['simply.fleet.fuel.log'].search([
                ('driver_id', '=', record.driver_id.id),
                ('date', '>=', record.period_start),
                ('date', '<=', record.period_end)
            ])

            record.fuel_log_ids = fuel_logs
            record.total_trips = len(fuel_logs)
            record.total_fuel_consumed = sum(fuel_logs.mapped('liters'))
            record.total_distance = sum(fuel_logs.mapped('distance_travelled'))
            record.total_fuel_cost = sum(fuel_logs.mapped('total_amount'))

            if record.total_fuel_consumed > 0:
                record.average_mileage = record.total_distance / record.total_fuel_consumed
            else:
                record.average_mileage = 0

            if record.total_distance > 0:
                record.cost_per_km = record.total_fuel_cost / record.total_distance
            else:
                record.cost_per_km = 0

    @api.depends('fuel_log_ids', 'fuel_log_ids.mileage')
    def _compute_best_worst(self):
        for record in self:
            mileages = record.fuel_log_ids.mapped('mileage')
            mileages = [m for m in mileages if m > 0]  # Filter out zero values

            if mileages:
                record.best_mileage = max(mileages)
                record.worst_mileage = min(mileages)
            else:
                record.best_mileage = 0
                record.worst_mileage = 0

    @api.depends('average_mileage', 'total_trips', 'cost_per_km', 'total_distance')
    def _compute_performance_score(self):
        for record in self:
            if not record.total_trips:
                record.performance_score = 0
                continue

            score = 0

            # 1. Mileage Score (40 points) - Higher is better
            # Assuming average mileage benchmark of 5 km/L for buses
            mileage_benchmark = 5.0
            if record.average_mileage > 0:
                mileage_score = min((record.average_mileage / mileage_benchmark) * 40, 40)
                score += mileage_score

            # 2. Cost Efficiency Score (30 points) - Lower cost per km is better
            # Assuming benchmark of ₹10 per km
            cost_benchmark = 10.0
            if record.cost_per_km > 0:
                cost_efficiency = cost_benchmark / record.cost_per_km
                cost_score = min(cost_efficiency * 30, 30)
                score += cost_score

            # 3. Consistency Score (20 points) - Check variance in mileage
            mileages = record.fuel_log_ids.mapped('mileage')
            mileages = [m for m in mileages if m > 0]
            if len(mileages) > 1:
                import statistics
                avg = statistics.mean(mileages)
                variance = statistics.variance(mileages)
                # Lower variance = more consistent = better
                consistency_score = max(20 - (variance / avg * 10), 0)
                score += consistency_score
            elif len(mileages) == 1:
                score += 15

            # 4. Activity Score (10 points) - Based on number of trips
            # Assuming benchmark of 20 trips per period
            trip_benchmark = 20 if record.period_type == 'weekly' else 80
            activity_score = min((record.total_trips / trip_benchmark) * 10, 10)
            score += activity_score

            record.performance_score = min(score, 100)

    @api.depends('performance_score')
    def _compute_performance_grade(self):
        for record in self:
            if record.performance_score >= 90:
                record.performance_grade = 'excellent'
            elif record.performance_score >= 75:
                record.performance_grade = 'good'
            elif record.performance_score >= 60:
                record.performance_grade = 'average'
            elif record.performance_score >= 40:
                record.performance_grade = 'below_average'
            else:
                record.performance_grade = 'poor'

    @api.depends('performance_score', 'performance_grade')
    def _compute_reward_points(self):
        for record in self:
            # Points based on grade
            grade_points = {
                'excellent': 100,
                'good': 75,
                'average': 50,
                'below_average': 25,
                'poor': 0
            }

            base_points = grade_points.get(record.performance_grade, 0)

            # Bonus points for exceptional performance
            if record.performance_score >= 95:
                base_points += 20

            record.reward_points = base_points

    @api.depends('reward_points', 'performance_grade', 'period_type')
    def _compute_reward_amount(self):
        for record in self:
            # Base amount per point
            point_value = 10  # ₹10 per point

            # Multiplier based on period type
            period_multiplier = 1.5 if record.period_type == 'monthly' else 1.0

            record.reward_amount = record.reward_points * point_value * period_multiplier

    @api.depends('driver_id', 'period_start', 'period_end', 'performance_score')
    def _compute_rank(self):
        for record in self:
            if not record.driver_id or not record.period_start or not record.period_end:
                record.rank = 0
                record.total_drivers = 0
                continue

            # Get all performance records for the same period
            same_period_records = self.search([
                ('period_start', '=', record.period_start),
                ('period_end', '=', record.period_end),
                ('period_type', '=', record.period_type),
                ('state', 'in', ['calculated', 'approved', 'rewarded'])
            ], order='performance_score desc')

            record.total_drivers = len(same_period_records)

            # Find rank
            for idx, perf_record in enumerate(same_period_records, 1):
                if perf_record.id == record.id:
                    record.rank = idx
                    break
            else:
                record.rank = 0

    @api.constrains('period_start', 'period_end')
    def _check_dates(self):
        for record in self:
            if record.period_start and record.period_end:
                if record.period_start > record.period_end:
                    raise ValidationError(_('Period start date cannot be after period end date.'))

    def action_calculate_performance(self):
        """Calculate performance metrics"""
        self.ensure_one()
        self._compute_metrics()
        self._compute_best_worst()
        self._compute_performance_score()
        self._compute_performance_grade()
        self._compute_reward_points()
        self._compute_reward_amount()
        self._compute_rank()
        self.write({'state': 'calculated'})

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Success'),
                'message': _('Performance calculated successfully!'),
                'type': 'success',
                'sticky': False,
            }
        }

    def action_approve(self):
        """Approve performance record"""
        self.ensure_one()
        if self.state != 'calculated':
            raise ValidationError(_('Please calculate performance before approving.'))
        self.write({'state': 'approved'})

    def action_mark_rewarded(self):
        """Mark as rewarded"""
        self.ensure_one()
        if self.state != 'approved':
            raise ValidationError(_('Please approve performance before marking as rewarded.'))
        self.write({'state': 'rewarded'})

        # Create activity or notification
        self.message_post(
            body=_('Reward of ₹%s has been processed for driver %s') %
                 (self.reward_amount, self.driver_id.name),
            subject=_('Reward Processed')
        )

    def action_reset_to_draft(self):
        """Reset to draft"""
        self.write({'state': 'draft'})

    def action_view_fuel_logs(self):
        """View related fuel logs"""
        self.ensure_one()
        return {
            'name': _('Fuel Logs'),
            'type': 'ir.actions.act_window',
            'res_model': 'simply.fleet.fuel.log',
            'view_mode': 'tree,form',
            'domain': [('id', 'in', self.fuel_log_ids.ids)],
            'context': {'create': False}
        }

    @api.model
    def generate_weekly_performance(self):
        """Cron job to generate weekly performance records"""
        today = fields.Date.today()
        # Get Monday of current week
        start_of_week = today - timedelta(days=today.weekday())
        # Get Sunday of current week
        end_of_week = start_of_week + timedelta(days=6)

        # Get all active drivers
        drivers = self.env['hr.employee'].search([
            ('job_id.name', 'ilike', 'driver'),
            ('active', '=', True)
        ])

        for driver in drivers:
            # Check if performance record already exists
            existing = self.search([
                ('driver_id', '=', driver.id),
                ('period_start', '=', start_of_week),
                ('period_end', '=', end_of_week),
                ('period_type', '=', 'weekly')
            ])

            if not existing:
                perf = self.create({
                    'driver_id': driver.id,
                    'period_type': 'weekly',
                    'period_start': start_of_week,
                    'period_end': end_of_week,
                })
                perf.action_calculate_performance()

        _logger.info("Weekly performance records generated successfully")

    @api.model
    def generate_monthly_performance(self):
        """Cron job to generate monthly performance records"""
        today = fields.Date.today()
        # Get first day of current month
        start_of_month = today.replace(day=1)
        # Get last day of current month
        end_of_month = (start_of_month + relativedelta(months=1)) - timedelta(days=1)

        # Get all active drivers
        drivers = self.env['hr.employee'].search([
            ('job_id.name', 'ilike', 'driver'),
            ('active', '=', True)
        ])

        for driver in drivers:
            # Check if performance record already exists
            existing = self.search([
                ('driver_id', '=', driver.id),
                ('period_start', '=', start_of_month),
                ('period_end', '=', end_of_month),
                ('period_type', '=', 'monthly')
            ])

            if not existing:
                perf = self.create({
                    'driver_id': driver.id,
                    'period_type': 'monthly',
                    'period_start': start_of_month,
                    'period_end': end_of_month,
                })
                perf.action_calculate_performance()

        _logger.info("Monthly performance records generated successfully")


class DriverPerformanceComparison(models.TransientModel):
    _name = 'simply.fleet.driver.performance.comparison'
    _description = 'Driver Performance Comparison'

    period_type = fields.Selection([
        ('weekly', 'Weekly'),
        ('monthly', 'Monthly')
    ], string='Period Type', required=True, default='monthly')

    date_from = fields.Date(string='Date From', required=True)
    date_to = fields.Date(string='Date To', required=True)

    driver_ids = fields.Many2many('hr.employee', string='Drivers',
                                  domain=[('job_id.name', 'ilike', 'driver')])

    def action_generate_comparison(self):
        """Generate comparison report"""
        self.ensure_one()

        domain = [
            ('period_start', '>=', self.date_from),
            ('period_end', '<=', self.date_to),
            ('period_type', '=', self.period_type),
            ('state', 'in', ['calculated', 'approved', 'rewarded'])
        ]

        if self.driver_ids:
            domain.append(('driver_id', 'in', self.driver_ids.ids))

        return {
            'name': _('Performance Comparison'),
            'type': 'ir.actions.act_window',
            'res_model': 'simply.fleet.driver.performance',
            'view_mode': 'graph,tree,form',
            'domain': domain,
            'context': {
                'graph_measure': 'performance_score',
                'graph_mode': 'bar',
                'graph_groupbys': ['driver_id']
            }
        }


class FuelLogInherit(models.Model):
    _inherit = 'simply.fleet.fuel.log'

    performance_id = fields.Many2one('simply.fleet.driver.performance',
                                     string='Performance Record',
                                     readonly=True)