from odoo import models, fields, api, _
from odoo.exceptions import UserError


class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    approval_state = fields.Selection([
        ('pending', 'Pending Approval'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ], string='Approval Status', default='pending',
       tracking=True, copy=False, readonly=True)

    rejection_reason = fields.Text(
        string='Rejection Reason', readonly=True, copy=False
    )

    approved_by = fields.Many2one(
        'res.users', string='Approved By', readonly=True, copy=False
    )

    approved_date = fields.Datetime(
        string='Approved Date', readonly=True, copy=False
    )

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            # Keep employee inactive until approved
            vals['active'] = False
        employees = super().create(vals_list)
        for employee in employees:
            employee._send_approval_email()
        return employees

    def _send_approval_email(self):
        """
        Send approval request email to manager.

        ROOT CAUSE FIX:
        Employee is active=False at this point. When Odoo's mail.template
        renders the email body, it internally calls:
            env['hr.employee'].browse(record_id)
        The default ORM domain includes active=True, so the inactive employee
        record returns EMPTY → all {{ object.xxx }} render as raw Jinja2 text.

        Fix: Pass active_test=False in context so the ORM includes
        inactive records during template rendering.
        """
        self.ensure_one()

        template = self.env.ref(
            'hr_employee_approval.email_template_employee_approval',
            raise_if_not_found=False
        )
        if not template:
            return

        # Resolve recipient email — priority order:
        # 1. Manager's work_email
        # 2. Manager's linked user email
        # 3. First HR Manager in the system as fallback
        recipient_email = False

        # sudo() + active_test=False needed since record is inactive
        employee = self.sudo().with_context(active_test=False)

        if employee.parent_id:
            manager = employee.parent_id
            recipient_email = (
                manager.work_email
                or (manager.user_id and manager.user_id.email)
                or False
            )

        if not recipient_email:
            # Fallback: send to first HR Manager user
            hr_group = self.env.ref('hr.group_hr_manager', raise_if_not_found=False)
            if hr_group and hr_group.users:
                recipient_email = hr_group.users[0].email

        if not recipient_email:
            self.message_post(
                body=_('⚠️ Approval email could not be sent: No manager or HR manager email found.'),
                subject=_('Approval Email Failed'),
            )
            return

        # KEY FIX: active_test=False ensures ORM includes inactive employee
        # when template renders {{ object.name }}, {{ object.parent_id.name }}, etc.
        template.sudo().with_context(active_test=False).send_mail(
            self.id,
            force_send=True,
            email_values={
                'email_to': recipient_email,
                'email_from': self.env.user.email_formatted or self.env.user.email,
            }
        )

    def action_approve(self):
        """Approve the employee — activate them in the system."""
        for employee in self:
            if employee.approval_state == 'approved':
                raise UserError(_('Employee is already approved.'))
            employee.write({
                'approval_state': 'approved',
                'active': True,
                'approved_by': self.env.user.id,
                'approved_date': fields.Datetime.now(),
                'rejection_reason': False,
            })
            employee.message_post(
                body=_('✅ Employee has been <b>Approved</b> by %s') % self.env.user.name,
                subject=_('Employee Approved'),
            )
            employee._send_approval_result_email(approved=True)

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Approved!'),
                'message': _('Employee %s has been approved and is now active.') % self.name,
                'type': 'success',
                'sticky': False,
            }
        }

    def action_reject(self):
        """Open wizard to reject employee with a reason."""
        return {
            'type': 'ir.actions.act_window',
            'name': _('Reject Employee'),
            'res_model': 'hr.employee.reject.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_employee_id': self.id},
        }

    def _send_approval_result_email(self, approved=True):
        """
        Notify the person who created the employee about the result.
        No active_test needed here — employee is already active=True after approval.
        """
        template_ref = (
            'hr_employee_approval.email_template_employee_approved'
            if approved else
            'hr_employee_approval.email_template_employee_rejected'
        )
        template = self.env.ref(template_ref, raise_if_not_found=False)
        if not template:
            return

        creator_email = self.sudo().create_uid.email or False
        if not creator_email:
            return

        template.sudo().send_mail(
            self.id,
            force_send=True,
            email_values={
                'email_to': creator_email,
            }
        )


class HrEmployeeRejectWizard(models.TransientModel):
    _name = 'hr.employee.reject.wizard'
    _description = 'Reject Employee Wizard'

    employee_id = fields.Many2one('hr.employee', string='Employee', required=True)
    rejection_reason = fields.Text(string='Rejection Reason', required=True)

    def action_confirm_reject(self):
        employee = self.employee_id
        employee.write({
            'approval_state': 'rejected',
            'active': False,
            'rejection_reason': self.rejection_reason,
        })
        employee.message_post(
            body=_('❌ Employee has been <b>Rejected</b> by %s.<br/>Reason: %s')
                 % (self.env.user.name, self.rejection_reason),
            subject=_('Employee Rejected'),
        )
        employee._send_approval_result_email(approved=False)
        return {'type': 'ir.actions.act_window_close'}
