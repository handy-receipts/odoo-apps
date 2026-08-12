from odoo import fields, models

class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    # Linking the settings fields to the POS configuration
    pos_hr_api_key = fields.Char(
        related='pos_config_id.hr_api_key', 
        readonly=False
    )
    pos_hr_api_url = fields.Char(
        related='pos_config_id.hr_api_url', 
        readonly=False
    )
    pos_hr_enable_qr = fields.Boolean(
        related='pos_config_id.hr_enable_qr', 
        readonly=False
    )
    pos_hr_json_mapping = fields.Text(
            related='pos_config_id.hr_json_mapping', 
            readonly=False
        )
    pos_hr_csid = fields.Char(
        related='pos_config_id.hr_csid', 
        readonly=False
    )