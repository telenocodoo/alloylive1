from odoo import api,tools,fields, models,_
import base64
from odoo import modules

class partnerinherit(models.Model):
    _inherit ='res.partner'

    jobcard_no= fields.Char('JobCard No')
    customer_arabic_name = fields.Char('')
    customer_code = fields.Char()
    agency_name_arbi = fields.Char('اسم الوكالة')
    car_type_arbi = fields.Char('نوع ة السيار')
    claim_no_arbi = fields.Char('‫رقم‬ ‫المطالبة‬')
    service_advisor_arbi = fields.Char('اسم المشر ف')
    plate_no_arbi = fields.Char('رقم ة اللوح')
    chasis_no_arbi = fields.Char('‫‫رقم الشاصية‬')
    odoo_meter_arbi = fields.Char('قراءة د العدا')
    jobcard_no_arbi = fields.Char('‫رقم ‫كرت‬ ‫عمل ‫الوكالة')
    street1_arbi = fields.Char('street')
    street2_arbi = fields.Char('street')
    is_agency = fields.Boolean('Agency')
    is_service_provider = fields.Boolean('Service Provider')

    @api.one
    @api.constrains('mobile')
    def unique_mobileidentity(self):
        if self.mobile:
            identities = self.env['res.partner'].search_count([('mobile', '=', self.mobile)])
            if identities > 1:
                raise ValueError(_('This Mobile No. is already exist'))

    @api.multi
    def name_get(self):
        data = []
        for rec in self:
            display_value = ''
            if rec.customer_code:
                display_value += rec.customer_code
            if rec.name:
                display_value += '-'+rec.name
            if rec.customer_arabic_name:
                display_value += '-'+rec.customer_arabic_name
            data.append((rec.id, display_value))
        return data



class InheritSale(models.Model):
    _inherit = 'sale.order'

    vehicle= fields.Many2one('vehicle')
    claim_no = fields.Char('Claim#')
    is_insured = fields.Boolean('insured',default=False)
    service_advisor = fields.Many2one('res.partner',string='Service Advisor')


    @api.onchange('vehicle')
    def onchage_vehicle(self):
        if self.vehicle and self.vehicle.is_insured:
            self.is_insured =True
    @api.one
    @api.constrains('claim_no')
    def unique_identity(self):
        if self.claim_no:
            identities = self.env['sale.order'].search_count([('claim_no', '=', self.claim_no)])
            if identities > 1:
                raise ValueError(_('This claim_no is already exist'))




