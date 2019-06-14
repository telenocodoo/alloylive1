from odoo import api, tools, fields, models, _
import base64
from odoo import modules
from odoo.exceptions import UserError, ValidationError
from odoo.addons import decimal_precision as dp
import datetime
from datetime import datetime, timedelta
from odoo.tools import float_is_zero, float_compare


# import  math
#
# class AccountAnalyticLine(models.Model):
#     _inherit = 'account.analytic.line'
#
#     cost = fields.Float('Labor_cost',compute='get_labor_cost',store=True)
#
#
#     @api.one
#     def get_labor_cost(self):
#         if self.employee_id and self.unit_amount:
#             result = '{0:02.0f}:{1:02.0f}'.format((self.unit_amount * 60)/ 60)
#             print(result)
#             employee = self.env['hr.employee'].search([('id','=',self.employee_id.id)])
#             if employee and employee.timesheet_cost:
#                 self.unit_amount/employee.timesheet_cost


class Account_invoice(models.Model):
    _inherit = 'account.invoice'

    sale_id = fields.Many2one('sale.order')


class tasks(models.Model):
    _inherit = 'project.task'

    sale = fields.Char('sale.order')
    sub_component_sale = fields.One2many('subtask.component', 'task')

    is_task_finished = fields.Boolean('is_task_finish', compute='_compute_kanban_state_label')
    delivery_count = fields.Integer(string='Delivery Orders', compute='_compute_picking_ids')
    picking_ids = fields.One2many('stock.picking', 'task_id', string='Pickings')

    # total_cost = fields.Float('Total Labor Cost', compute='_compute_total_cost')
    #
    #
    #
    # def get_total_labor_cost(self):
    #     if self.timesheet_ids:
    #         pass

    @api.depends('picking_ids')
    def _compute_picking_ids(self):
        for order in self:
            order.delivery_count = len(order.picking_ids)

    @api.depends('stage_id', 'kanban_state')
    def _compute_kanban_state_label(self):
        for task in self:
            if task.kanban_state == 'normal':
                task.kanban_state_label = task.legend_normal
            elif task.kanban_state == 'blocked':
                task.kanban_state_label = task.legend_blocked
            else:
                task.kanban_state_label = task.legend_done
            if task.stage_id.name == 'Delivery':
                print ('..........its called')
                task.is_task_finished = True
                if not task.picking_ids:
                    for tasksub in task.sub_component_sale:
                        tasksub._action_launch_stock_rule()

            else:
                task.is_task_finished = False

    @api.multi
    def action_view_deliverys(self):
        '''
        This function returns an action that display existing delivery orders
        of given sales order ids. It can either be a in a list or in a form
        view, if there is only one delivery order to show.
        '''
        action = self.env.ref('stock.action_picking_tree_all').read()[0]

        pickings = self.mapped('picking_ids')
        if len(pickings) > 1:
            action['domain'] = [('id', 'in', pickings.ids)]
        elif pickings:
            action['views'] = [(self.env.ref('stock.view_picking_form').id, 'form')]
            action['res_id'] = pickings.id
        return action


    @api.one
    def get_payment_term(self, terms):
        if terms:
            terms_obj = self.env['account.payment.term'].search([('name', '=', terms)])
            return terms_obj

    @api.one
    def get_product_obj(self, product_id):
        if product_id:
            product = self.env['product.product'].search([('id', '=', product_id)])
            return product

    @api.one
    def get_product_account(self, invoice, partner_id, product):
        if product:
            domain = {}
            part = partner_id
            fpos = invoice.fiscal_position_id
            company = self.env.user.company_id
            type = 'out_invoice'

            if not part:
                warning = {
                    'title': _('Warning!'),
                    'message': _('You must first select a partner.'),
                }
                return {'warning': warning}
            else:
                account = self.env['account.invoice.line'].get_invoice_line_account(type, product, fpos, company)
                if account:
                    return account.id

    @api.multi
    def create_invoice(self):
        if self.sale and self.sub_component_sale:

            sale = self.env['sale.order'].search([('id', '=', self.sale)])
            partner = sale.partner_id
            payment_term = 1
            account_id_credit = partner.property_account_receivable_id.id
            sales_journal = self.env['account.journal'].search([], limit=1)
            if sales_journal:
                ValueError(_('Set Sales Journal'))

            invoice_obj = self.env['account.invoice'].create(
                {'account_id': account_id_credit, 'sale_id': sale.id, 'user_id': 1, 'type': 'out_invoice',
                 'journal_id': sales_journal.id, 'partner_id': partner.id,
                 'payment_term_id': payment_term, 'date_invoice': datetime.now().date()})

            if invoice_obj:
                for all_line in self.sub_component_sale:
                    analytic_account_tag = []
                    product = self.get_product_obj(all_line.product_id.id)
                    # create invoices
                    account_id_product = self.get_product_account(invoice_obj, partner.id,
                                                                  product[0])
                    for analytic_accounttag in all_line.analytic_tag_ids:
                        analytic_account_tag.append(analytic_accounttag.id)
                    self.env['account.invoice.line'].create(
                        {'invoice_id': invoice_obj.id, 'account_id': account_id_product[0],
                         'product_id': product[0].id, 'name': all_line.product_id.name,
                         'quantity': all_line.product_uom_qty,
                         'price_unit': all_line.price_unit, 'discount': all_line.discount,
                         'analytic_tag_ids': [(6, 0, analytic_account_tag)]})

            view = self.env.ref('account.invoice_form')
            return {
                'name': 'Invoice',
                'view_type': 'form',
                'view_mode': 'form',
                'view_id': view.id,
                'res_model': 'account.invoice',
                'type': 'ir.actions.act_window',
                'res_id': invoice_obj.id,
                'context': self.env.context
            }

    def close_task(self):
        stage = self.env['project.task.type'].search([('name', '=', 'Delivery')])
        if stage:
            self.write({'stage_id': stage.id})


class subtaskcomponent(models.Model):
    _name = 'subtask.component'

    task = fields.Many2one('project.task', ondelete='cascade', index=True, copy=False, readonly=True)

    product_id = fields.Many2one('product.product', string='Product', domain=[('sale_ok', '=', True)],
                                 change_default=True, ondelete='restrict')
    product_uom_qty = fields.Float(string='Ordered Quantity', digits=dp.get_precision('Product Unit of Measure'),
                                   required=True, default=1.0)
    product_uom = fields.Many2one('uom.uom', string='Unit of Measure')
    price_unit = fields.Float('Unit Price', required=True, digits=dp.get_precision('Product Price'), default=0.0)
    discount = fields.Float(string='Discount (%)', digits=dp.get_precision('Discount'), default=0.0)
    price_subtotal = fields.Float(compute='_compute_amount', string='Subtotal', readonly=True, store=True)
    tax_id = fields.Many2many('account.tax', string='Taxes',
                              domain=['|', ('active', '=', False), ('active', '=', True)])

    customer_lead = fields.Float(
        'Delivery Lead Time', required=True, default=0.0,
        help="Number of days between the order confirmation and the shipping of the products to the customer",
        oldname="delay")
    analytic_tag_ids = fields.Many2many('account.analytic.tag', string='Analytic Tags')
    move_ids = fields.One2many('stock.move', 'task_line_id', string='Stock Moves')
    price_tax = fields.Float(compute='_compute_amount', string='Total Tax', readonly=True, store=True)
    price_total = fields.Float(compute='_compute_amount', string='Total', readonly=True, store=True)

    def _get_qty_procurement(self):
        self.ensure_one()
        qty = 0.0
        for move in self.move_ids.filtered(lambda r: r.state != 'cancel'):
            if move.picking_code == 'outgoing':
                qty += move.product_uom._compute_quantity(move.product_uom_qty, self.product_uom,
                                                          rounding_method='HALF-UP')
            elif move.picking_code == 'incoming':
                qty -= move.product_uom._compute_quantity(move.product_uom_qty, self.product_uom,
                                                          rounding_method='HALF-UP')
        return qty

    @api.multi
    def _action_launch_stock_rule(self):
        """
        Launch procurement group run method with required/custom fields genrated by a
        sale order line. procurement group will launch '_run_pull', '_run_buy' or '_run_manufacture'
        depending on the sale order line product rule.
        """
        if self.task.sale:
            sale = self.env['sale.order'].search(
                [('id', '=', self.task.sale), ('company_id', '=', self.env.user.company_id.id)])
            precision = self.env['decimal.precision'].precision_get('Product Unit of Measure')
            errors = []
            for line in self:
                if not line.product_id.type in ('consu', 'product'):
                    continue
                qty = line._get_qty_procurement()
                if float_compare(qty, line.product_uom_qty, precision_digits=precision) >= 0:
                    continue

                group_id = sale.procurement_group_id
                if not group_id:
                    group_id = self.env['procurement.group'].create({
                        'name': self.task.name, 'move_type': sale.picking_policy,
                        'task_id': self.task.id,
                        'partner_id': sale.partner_shipping_id.id,
                    })
                    sale.procurement_group_id = group_id
                else:
                    # In case the procurement group is already created and the order was
                    # cancelled, we need to update certain values of the group.
                    updated_vals = {}
                    if group_id.partner_id != sale.partner_shipping_id:
                        updated_vals.update({'partner_id': sale.partner_shipping_id.id})
                    if group_id.move_type != sale.picking_policy:
                        updated_vals.update({'move_type': sale.picking_policy})
                    if updated_vals:
                        group_id.write(updated_vals)

                values = line._prepare_procurement_values(sale, group_id=group_id)
                product_qty = line.product_uom_qty - qty

                procurement_uom = line.product_uom
                quant_uom = line.product_id.uom_id
                get_param = self.env['ir.config_parameter'].sudo().get_param
                if procurement_uom.id != quant_uom.id and get_param('stock.propagate_uom') != '1':
                    product_qty = line.product_uom._compute_quantity(product_qty, quant_uom, rounding_method='HALF-UP')
                    procurement_uom = quant_uom

                try:
                    self.env['procurement.group'].run(line.product_id, product_qty, procurement_uom,
                                                      sale.partner_shipping_id.property_stock_customer, line.product_id.name,
                                                      sale.name, values)
                except UserError as error:
                    errors.append(error.name)
            if errors:
                raise UserError('\n'.join(errors))
            return True

    @api.multi
    def _prepare_procurement_values(self, sale, group_id=False):
        """ Prepare specific key for moves or other components that will be created from a stock rule
        comming from a sale order line. This method could be override in order to add other custom key that could
        be used in move/po creation.
        """
        self.ensure_one()
        vals = {}
        date_planned = sale.confirmation_date \
                       + timedelta(days=self.customer_lead or 0.0) - timedelta(
            days=sale.company_id.security_lead)
        vals.update({
            'company_id': sale.company_id.id,
            'group_id': group_id,
            'task_line_id': self.id,
            'date_planned': date_planned,
            # 'route_ids': self.route_id,
            'warehouse_id': sale.warehouse_id or False,
            'partner_id': sale.partner_shipping_id.id,
        })
        # for line in self.filtered("sale.commitment_date"):
        #     date_planned = fields.Datetime.from_string(sale.commitment_date) - timedelta(
        #         days=sale.company_id.security_lead)
        #     vals.update({
        #         'date_planned': fields.Datetime.to_string(date_planned),
        #     })
        return vals

    @api.multi
    @api.onchange('product_id')
    def product_id_change(self):
        if self.task:
            task = self.env['project.task'].search([('id', '=', self._context.get('default_sale'))])
            sale = self.env['sale.order'].search(
                [('id', '=', task.sale), ('company_id', '=', self.env.user.company_id.id)])
            if not self.product_id:
                return {'domain': {'product_uom': []}}

            vals = {}
            domain = {'product_uom': [('category_id', '=', self.product_id.uom_id.category_id.id)]}
            if not self.product_uom or (self.product_id.uom_id.id != self.product_uom.id):
                vals['product_uom'] = self.product_id.uom_id
                vals['product_uom_qty'] = self.product_uom_qty or 1.0

            product = self.product_id.with_context(
                lang=sale.partner_id.lang,
                partner=sale.partner_id,
                quantity=vals.get('product_uom_qty') or self.product_uom_qty,
                date=sale.date_order,
                pricelist=sale.pricelist_id.id,
                uom=self.product_uom.id
            )

            result = {'domain': domain}

            title = False
            message = False
            warning = {}
            if product.sale_line_warn != 'no-message':
                title = _("Warning for %s") % product.name
                message = product.sale_line_warn_msg
                warning['title'] = title
                warning['message'] = message
                result = {'warning': warning}
                if product.sale_line_warn == 'block':
                    self.product_id = False
                    return result

            self._compute_tax_id(sale)
            if sale.pricelist_id and sale.partner_id:
                vals['price_unit'] = self.env['account.tax']._fix_tax_included_price_company(
                    self._get_display_price(product, sale), product.taxes_id, self.tax_id, sale.company_id)
                print (self.env['account.tax']._fix_tax_included_price_company(
                    self._get_display_price(product, sale), product.taxes_id, self.tax_id, sale.company_id))
            self.update(vals)

            return result

    @api.multi
    def _get_display_price(self, product, sale):

        if sale.pricelist_id.discount_policy == 'with_discount':
            return product.with_context(pricelist=sale.pricelist_id.id).price
        product_context = dict(self.env.context, partner_id=sale.partner_id.id, date=sale.date_order,
                               uom=self.product_uom.id)

        final_price, rule_id = self.order_id.pricelist_id.with_context(product_context).get_product_price_rule(
            self.product_id, self.product_uom_qty or 1.0, sale.partner_id)
        base_price, currency = self.with_context(product_context)._get_real_price_currency(product, rule_id,
                                                                                           self.product_uom_qty,
                                                                                           self.product_uom,
                                                                                           sale.pricelist_id.id)
        if currency != sale.pricelist_id.currency_id:
            base_price = currency._convert(
                base_price, sale.pricelist_id.currency_id,
                sale.company_id, sale.date_order or fields.Date.today())
        # negative discounts (= surcharge) are included in the display price
        return max(base_price, final_price)

    @api.multi
    def _compute_tax_id(self, sale):

        for line in self:
            fpos = sale.fiscal_position_id or sale.partner_id.property_account_position_id
            # If company_id is set, always filter taxes by the company
            taxes = line.product_id.taxes_id.filtered(lambda r: not sale.company_id or r.company_id == sale.company_id)
            line.tax_id = fpos.map_tax(taxes, line.product_id, sale.partner_shipping_id) if fpos else taxes

    @api.one
    @api.depends('product_uom_qty', 'discount', 'price_unit', 'tax_id')
    def _compute_amount(self):
        """
        Compute the amounts of the SO line.
        """
        if self.task:
            sale = self.env['sale.order'].search([('id', '=', self.task.sale)])
            for line in self:
                price = line.price_unit * (1 - (line.discount or 0.0) / 100.0)
                taxes = line.tax_id.compute_all(price, sale.currency_id, line.product_uom_qty,
                                                product=line.product_id, partner=sale.partner_shipping_id)
                line.update({
                    'price_tax': sum(t.get('amount', 0.0) for t in taxes.get('taxes', [])),
                    'price_total': taxes['total_included'],
                    'price_subtotal': taxes['total_excluded'],
                })


class InheritSale(models.Model):
    _inherit = 'sale.order'

    project = fields.Many2one('project.project', string='Project')
    agency_name = fields.Many2one('res.partner', string='Agency Name')

    def action_task(self):
        action = self.env.ref('project.project_task_action_sub_task').read()[0]
        ctx = self.env.context.copy()
        ctx.update({
#             'default_parent_id': self.id,
            'default_project_id': self.env.context.get('project_id', self.project.id),
            'default_name': self.env.context.get('name', self.name) + ':',
            'default_partner_id': self.env.context.get('partner_id', self.partner_id.id),
            'search_default_project_id': self.env.context.get('project_id', self.project.id),
        })
        action['context'] = ctx
        action['domain'] = [ ('name', 'ilike', self.name)]
        return action
    
    @api.multi
    def action_confirm_replica(self):
        self.write({
            'state': 'sale',
            'confirmation_date': fields.Datetime.now()
        })
        if self.project:
            stage_id = 1
            stage = self.env['project.task.type'].search([('name', '=', 'New')], limit=1)
            if stage:
                stage_id = stage.id
#             task = self.env['project.task'].create(
#                 {'name': self.partner_id.name + '-' + self.name, 'sale': self.id, 'stage_id': stage_id,
#                  'project_id': self.project.id})

            for line in self.order_line:
                tax_list = []
                analytic_account_tag = []
                for tax in line.tax_id:
                    tax_list.append(tax.id)
                for analytic_accounttag in line.analytic_tag_ids:
                    analytic_account_tag.append(analytic_accounttag.id)

                task =self.env['project.task'].create(
                    {'name': line.product_id.name + '-' + str(self.x_studio_field_DuczH.brand_id.name)+'-'+str(self.x_studio_field_DuczH.name)+'-'+ self.name  ,'sale': self.id, 'stage_id': stage_id, 'project_id': self.project.id,'date_assign': fields.Datetime.now(), 'date_deadline': fields.Date.today()+timedelta(hours=90)})

#                 self.env['subtask.component'].create(
#                     {'task': task.id, 'product_id': line.product_id.id, 'price_subtotal': line.price_subtotal,
#                      'product_uom': line.product_uom.id, 'product_uom_qty': line.product_uom_qty,
#                      'price_unit': line.price_unit, 'tax_id': [(6, 0, tax_list)], 'discount': line.discount,
#                      'analytic_tag_ids': [(6, 0, analytic_account_tag)]})
                
                task.toggle_start()
                
                
#             view = self.env.ref('project.view_task_form2')
#             return {
#                 'name': 'Task created',
#                 'view_type': 'form',
#                 'view_mode': 'form',
#                 'view_id': view.id,
#                 'res_model': 'project.task',
#                 'type': 'ir.actions.act_window',
#                 'res_id': task.id,
#                 'context': self.env.context
#             }




class StockPicking(models.Model):
    _inherit = 'stock.picking'

    task_id = fields.Many2one(related='group_id.task_id', string="Task", store=True, readonly=False)


class StockMove(models.Model):
    _inherit = "stock.move"
    task_line_id = fields.Many2one('subtask.component', 'Sale Line')


class ProcurementGroup(models.Model):
    _inherit = 'procurement.group'

    task_id = fields.Many2one('project.task', 'Task')
