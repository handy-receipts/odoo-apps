from odoo import fields, models

class PosConfig(models.Model):
    _inherit = 'pos.config'

    # Using 'hr_' prefix to avoid conflicts with other modules
    hr_api_key = fields.Char(string='API Key')
    hr_csid = fields.Char(string='Store ID')
    hr_api_url = fields.Char(
        string='Endpoint'
    )
    hr_enable_qr = fields.Boolean(string='Enable Dynamic QR', default=False)
    hr_json_mapping = fields.Text(
        string="Dynamic JSON Mapping", 
        help="Example: order.amount_total, line.product_id.name, payment.payment_method_id.name",
        default="order.pos_reference, order.amount_total, line.product_id.name, line.qty, payment.amount"
    )