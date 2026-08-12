# -*- coding: utf-8 -*-
from odoo import models

class PosSession(models.Model):
    _inherit = 'pos.session'

    def _loader_params_pos_config(self):
        """ Whitelists custom fields so they are sent to the JS frontend """
        res = super()._loader_params_pos_config()
        res['search_params']['fields'].extend([
            'hr_api_url',
            'hr_enable_qr',
            'hr_json_mapping'
        ])
        return res