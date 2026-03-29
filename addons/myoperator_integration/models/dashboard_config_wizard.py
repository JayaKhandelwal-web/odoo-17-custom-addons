from odoo import models, fields, api, _
from datetime import datetime, timedelta
from odoo.exceptions import UserError


class DashboardConfigWizard(models.TransientModel):
    _name = 'dashboard.config.wizard'
    _description = 'Dashboard Configuration Wizard'

    # Date range options
    date_range = fields.Selection([
        ('today', 'Today'),
        ('yesterday', 'Yesterday'),
        ('this_week', 'This Week'),
        ('last_week', 'Last Week'),
        ('this_month', 'This Month'),
        ('last_month', 'Last Month'),
        ('this_quarter', 'This Quarter'),
        ('last_quarter', 'Last Quarter'),
        ('this_year', 'This Year'),
        ('last_year', 'Last Year'),
        ('custom', 'Custom Range')
    ], string='Date Range', default='this_month', required=True)

    date_from = fields.Datetime('Date From')
    date_to = fields.Datetime('Date To')

    # Dashboard customization options
    include_call_analytics = fields.Boolean('Include Call Analytics', default=True)
    include_chat_analytics = fields.Boolean('Include Chat Analytics', default=True)
    include_performance_metrics = fields.Boolean('Include Performance Metrics', default=True)
    include_agent_performance = fields.Boolean('Include Agent Performance', default=True)

    # Chart preferences
    chart_style = fields.Selection([
        ('colorful', 'Colorful'),
        ('professional', 'Professional'),
        ('minimal', 'Minimal')
    ], string='Chart Style', default='colorful')

    # Export options
    auto_refresh = fields.Boolean('Auto Refresh Every 5 Minutes', default=False)
    export_format = fields.Selection([
        ('pdf', 'PDF Report'),
        ('excel', 'Excel Spreadsheet'),
        ('csv', 'CSV Data')
    ], string='Export Format', default='pdf')

    @api.onchange('date_range')
    def _onchange_date_range(self):
        """Automatically set date_from and date_to based on selected range"""
        today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)

        if self.date_range == 'today':
            self.date_from = today
            self.date_to = today.replace(hour=23, minute=59, second=59)
        elif self.date_range == 'yesterday':
            yesterday = today - timedelta(days=1)
            self.date_from = yesterday
            self.date_to = yesterday.replace(hour=23, minute=59, second=59)
        elif self.date_range == 'this_week':
            # Start of current week (Monday)
            start_week = today - timedelta(days=today.weekday())
            self.date_from = start_week
            self.date_to = start_week + timedelta(days=6, hours=23, minutes=59, seconds=59)
        elif self.date_range == 'last_week':
            # Start of last week
            start_last_week = today - timedelta(days=today.weekday() + 7)
            self.date_from = start_last_week
            self.date_to = start_last_week + timedelta(days=6, hours=23, minutes=59, seconds=59)
        elif self.date_range == 'this_month':
            # Start of current month
            start_month = today.replace(day=1)
            self.date_from = start_month
            # End of current month
            if today.month == 12:
                end_month = today.replace(year=today.year + 1, month=1, day=1) - timedelta(days=1)
            else:
                end_month = today.replace(month=today.month + 1, day=1) - timedelta(days=1)
            self.date_to = end_month.replace(hour=23, minute=59, second=59)
        elif self.date_range == 'last_month':
            # Start of last month
            if today.month == 1:
                start_last_month = today.replace(year=today.year - 1, month=12, day=1)
                end_last_month = today.replace(day=1) - timedelta(days=1)
            else:
                start_last_month = today.replace(month=today.month - 1, day=1)
                end_last_month = today.replace(day=1) - timedelta(days=1)
            self.date_from = start_last_month
            self.date_to = end_last_month.replace(hour=23, minute=59, second=59)
        elif self.date_range == 'this_quarter':
            # Start of current quarter
            quarter = (today.month - 1) // 3 + 1
            start_quarter = today.replace(month=(quarter - 1) * 3 + 1, day=1)
            self.date_from = start_quarter
            # End of current quarter
            if quarter == 4:
                end_quarter = today.replace(year=today.year + 1, month=1, day=1) - timedelta(days=1)
            else:
                end_quarter = today.replace(month=quarter * 3 + 1, day=1) - timedelta(days=1)
            self.date_to = end_quarter.replace(hour=23, minute=59, second=59)
        elif self.date_range == 'last_quarter':
            # Start of last quarter
            current_quarter = (today.month - 1) // 3 + 1
            if current_quarter == 1:
                last_quarter = 4
                year = today.year - 1
            else:
                last_quarter = current_quarter - 1
                year = today.year

            start_last_quarter = today.replace(year=year, month=(last_quarter - 1) * 3 + 1, day=1)
            end_last_quarter = today.replace(year=year, month=last_quarter * 3 + 1, day=1) - timedelta(days=1)

            self.date_from = start_last_quarter
            self.date_to = end_last_quarter.replace(hour=23, minute=59, second=59)
        elif self.date_range == 'this_year':
            # Start of current year
            start_year = today.replace(month=1, day=1)
            self.date_from = start_year
            self.date_to = today.replace(month=12, day=31, hour=23, minute=59, second=59)
        elif self.date_range == 'last_year':
            # Last year
            last_year = today.year - 1
            self.date_from = today.replace(year=last_year, month=1, day=1)
            self.date_to = today.replace(year=last_year, month=12, day=31, hour=23, minute=59, second=59)
        elif self.date_range == 'custom':
            # Don't change dates for custom range
            pass

    def action_open_dashboard(self):
        """Open dashboard with configured settings"""
        if self.date_range == 'custom' and (not self.date_from or not self.date_to):
            raise UserError(_('Please specify both start and end dates for custom range.'))

        if self.date_from and self.date_to and self.date_from > self.date_to:
            raise UserError(_('Start date cannot be later than end date.'))

        # Create or update dashboard record
        dashboard = self.env['myoperator.dashboard'].search([], limit=1)
        if not dashboard:
            dashboard = self.env['myoperator.dashboard'].create({
                'name': 'MyOperator Analytics Dashboard',
                'date_from': self.date_from,
                'date_to': self.date_to,
            })
        else:
            dashboard.write({
                'date_from': self.date_from,
                'date_to': self.date_to,
            })

        # Return action to open dashboard
        return {
            'type': 'ir.actions.act_window',
            'name': _('MyOperator Analytics Dashboard'),
            'res_model': 'myoperator.dashboard',
            'res_id': dashboard.id,
            'view_mode': 'form',
            'target': 'current',
            'context': {
                'default_date_from': self.date_from,
                'default_date_to': self.date_to,
            }
        }

    def action_export_data(self):
        """Export dashboard data in selected format"""
        if not self.date_from or not self.date_to:
            raise UserError(_('Please specify date range first.'))

        # Create dashboard record for export
        dashboard = self.env['myoperator.dashboard'].create({
            'name': f'Export - {self.date_range.replace("_", " ").title()}',
            'date_from': self.date_from,
            'date_to': self.date_to,
        })

        if self.export_format == 'pdf':
            return {
                'type': 'ir.actions.report',
                'report_name': 'myoperator_integration.dashboard_report_template',
                'report_type': 'qweb-pdf',
                'data': {'dashboard_id': dashboard.id},
                'context': self.env.context,
            }
        elif self.export_format == 'excel':
            return self._export_excel(dashboard)
        elif self.export_format == 'csv':
            return self._export_csv(dashboard)

    def _export_excel(self, dashboard):
        """Export dashboard data to Excel"""
        # Implementation would require xlsxwriter or openpyxl
        # For now, return a notification
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Excel Export'),
                'message': _('Excel export functionality coming soon!'),
                'type': 'info',
                'sticky': False,
            }
        }

    def _export_csv(self, dashboard):
        """Export dashboard data to CSV"""
        # Implementation for CSV export
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('CSV Export'),
                'message': _('CSV export functionality coming soon!'),
                'type': 'info',
                'sticky': False,
            }
        }

    def action_quick_insights(self):
        """Generate quick insights based on current data"""
        if not self.date_from or not self.date_to:
            raise UserError(_('Please specify date range first.'))

        # Get basic metrics
        call_count = self.env['myoperator.call.log'].search_count([
            ('timestamp', '>=', self.date_from),
            ('timestamp', '<=', self.date_to)
        ])

        conversation_count = self.env['myoperator.conversation'].search_count([
            ('last_message_at', '>=', self.date_from),
            ('last_message_at', '<=', self.date_to)
        ])

        message_count = self.env['myoperator.message'].search_count([
            ('timestamp', '>=', self.date_from),
            ('timestamp', '<=', self.date_to)
        ])

        # Generate insights message
        insights = []

        if call_count > 0:
            insights.append(f"📞 {call_count} calls recorded")

        if conversation_count > 0:
            insights.append(f"💬 {conversation_count} WhatsApp conversations")

        if message_count > 0:
            insights.append(f"📨 {message_count} total messages")

        if not insights:
            message = "No communication data found for the selected period."
        else:
            message = "Quick Insights:\n" + "\n".join(insights)

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Quick Insights'),
                'message': message,
                'type': 'info',
                'sticky': True,
            }
        }