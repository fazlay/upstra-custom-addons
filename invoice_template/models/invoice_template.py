# models/invoice_template.py
from odoo import fields, models, api, Command


class InvoiceTemplate(models.Model):
    _name = 'invoice.template'
    _description = 'Invoice Template'
    _order = 'name'

    name = fields.Char(required=True, string='Template Name')
    note = fields.Text(string='Note')
    line_ids = fields.One2many(
        'invoice.template.line',
        'template_id',
        string='Lines'
    )
    total_type_id = fields.Many2one(
        'invoice.total.type',
        string='Total Calculation Method',
        help='Select a total calculation method to apply when this template is used'
    )
    journal_id = fields.Many2one(
        'account.journal',
        string='Invoicing Journal',
        domain=[('type', 'in', ('sale', 'general'))],
        help='If set, invoice with this template will use this journal'
    )
    active = fields.Boolean(default=True)


# Extend account.move to add template field and onchange
class AccountMove(models.Model):
    _inherit = 'account.move'

    template_id = fields.Many2one(
        'invoice.template',
        string='Invoice Template',
        help='Select a template to pre-fill invoice lines'
    )

    def _prepare_invoice_line_values(self, template_line):
        """Prepare values for creating an invoice line from a template line"""
        return template_line._prepare_invoice_line_values()
    def _sanitize_vals(self, vals):
        if vals.get('invoice_line_ids') and vals.get('line_ids'):
            inv_virtuals = {
                cmd[1] for cmd in vals['invoice_line_ids'] if cmd[0] == 0
            }
            line_virtuals = {
                cmd[1] for cmd in vals['line_ids'] if cmd[0] == 0
            }
            if inv_virtuals and line_virtuals and not (inv_virtuals & line_virtuals):
                del vals['line_ids']
        return super()._sanitize_vals(vals)
    @api.onchange('template_id')
    def _onchange_template_id(self):
        if not self.template_id:
            return

        template = self.template_id
        new_lines = []

        for tl in template.line_ids.sorted('sequence'):
            if not tl.product_id:
                continue

            product = tl.product_id.with_company(self.company_id)
     

            new_lines.append(Command.create({
                'product_id': product.id,
                'name': tl.name or product.display_name,
                'quantity': tl.quantity,
                'price_unit': (
                    tl.price_unit if tl.price_unit != 0.0
                    else product.lst_price
                ),
                'sequence': tl.sequence,
     
            }))

        self.invoice_line_ids = [Command.clear()] + new_lines

        # self.template_id = template

        if template.total_type_id:
            self.total_type_id = template.total_type_id
        if template.journal_id:
            self.journal_id = template.journal_id
    unit_price_column = fields.Boolean(string="Unit Price", default=True)
    quantity_column = fields.Boolean(string="Quantity", default=True)
