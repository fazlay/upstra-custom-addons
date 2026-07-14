# -*- coding: utf-8 -*-

from odoo import models, fields, api, _

class SaleOrder(models.Model):
    _inherit = 'sale.order'

    parent_sale_order_id = fields.Many2one(
        'sale.order',
        string='Parent Sale Order',
        ondelete='set null',
        copy=False,
    )

    child_sale_order_ids = fields.One2many(
        'sale.order',
        'parent_sale_order_id',
        string='Alternative Offers',
    )

    is_alternative_offer = fields.Boolean(
        string='Is Alternative Offer',
        default=False,
        copy=False,
    )

    offer_name = fields.Char(
        string='Offer Name',
        copy=True,
    )

    alternative_offers_count = fields.Integer(
        string='Alternative Offers Count',
        compute='_compute_alternative_offers_count',
    )

    @api.depends('child_sale_order_ids')
    def _compute_alternative_offers_count(self):
        for order in self:
            order.alternative_offers_count = len(order.child_sale_order_ids)

    def action_generate_alternative_offers(self):
        self.ensure_one()
        return {
            'name': _('Generate Alternative Offers'),
            'type': 'ir.actions.act_window',
            'res_model': 'sale.alternative.offer.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_sale_order_id': self.id,
            }
        }

    def action_print_all_offers(self):
        self.ensure_one()
        parent_order = self.parent_sale_order_id or self
        return self.env.ref('sale_alternative_offer.action_report_sale_alternative').report_action(parent_order)
