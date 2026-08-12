# -*- coding: utf-8 -*-
from odoo import fields, models, api
import requests
import logging

_logger = logging.getLogger(__name__)

# Number of pending orders processed per cron run, to avoid one run
# holding a long-lived transaction if a backlog builds up.
HANDY_RECEIPTS_CRON_BATCH_SIZE = 50


class PosOrder(models.Model):
    _inherit = 'pos.order'

    hr_delivery_type = fields.Char("Delivery Type", readonly=True)
    hr_delivery_value = fields.Char("Delivery Value", readonly=True)
    hr_qr_url = fields.Char("QR URL", readonly=True)
    hr_api_status = fields.Selection([
        ('not_required', 'Not Required'),
        ('pending', 'Pending'),
        ('success', 'Success'),
        ('failed', 'Failed'),
    ], default='not_required', string="API Status", readonly=True)

    def action_retry_hr_api(self):
        """ Manual retry button for the backend UI. This is an explicit
        staff-triggered action (not part of the checkout flow), so it's
        fine for it to stay synchronous. """
        for order in self:
            qr_url = order._send_to_hr_api()
            if qr_url:
                order.sudo().write({'hr_qr_url': qr_url, 'hr_api_status': 'success'})
            else:
                order.sudo().write({'hr_api_status': 'failed'})
        return True

    def _resolve_path(self, record, path):
        """ Safe Recursive Resolver for Dynamic Mapping """
        try:
            if path == 'tax_details':
                return self._get_native_tax_details(record)

            val = record
            # Depth limit of 5 to prevent N+1 performance bottlenecks
            for part in path.split('.')[:5]:
                val = getattr(val, part, None)
                if not val:
                    break

            if val is None:
                return None
            if isinstance(val, models.BaseModel):
                return val.display_name
            if isinstance(val, (fields.Datetime, fields.Date)):
                return val.isoformat()
            return val
        except Exception:
            return None

    def _get_native_tax_details(self, record):
        """ Uses Odoo internal engine to calculate precise taxes """
        if record._name == 'pos.order.line':
            currency = record.order_id.currency_id
            res = record.tax_ids.compute_all(
                record.price_unit * (1 - (record.discount or 0.0) / 100.0),
                currency, record.qty, product=record.product_id, partner=record.order_id.partner_id
            )
            return [{
                "name": t['name'],
                "amount": currency.round(t['amount']),
                "rate": record.tax_ids.filtered(lambda x: x.id == t['id']).amount
            } for t in res['taxes']]

        elif record._name == 'pos.order':
            # ORDER LEVEL: Group taxes from all lines
            tax_summary = {}
            for line in record.lines:
                line_taxes = self._get_native_tax_details(line)
                for tax in line_taxes:
                    name = tax['name']
                    if name not in tax_summary:
                        tax_summary[name] = {"name": name, "amount": 0, "rate": tax['rate']}
                    tax_summary[name]['amount'] += tax['amount']

            # Clean up totals and return as list
            return [{"name": v['name'], "amount": round(v['amount'], 2), "rate": v['rate']} for v in tax_summary.values()]

        return None

    def _prepare_hr_payload(self):
        config = self.config_id
        mapping_str = config.hr_json_mapping or ""
        items = [i.strip() for i in mapping_str.split(',') if '.' in i]

        payload = {
            "store_info": {
                "name": config.name,
                "currency": self.currency_id.name,
            },
            "customer": {},
            "odoo_order_data": {
                "pos_reference": self.pos_reference,
                "uuid": self.uuid,
                "amount_total": self.amount_total,
                "amount_tax": self.amount_tax,
                "amount_paid": self.amount_paid,
                "amount_return": self.amount_return,
                "amount_difference": self.amount_difference,
                "amount_rounding": getattr(self, 'amount_rounding', 0.0),  # Handling rounding
                "date_order": self.date_order.isoformat(),
                "lines": [],
                "payments": [{"method": p.payment_method_id.name, "amount": p.amount} for p in self.payment_ids]
            }
        }

        for line in self.lines:
            parent_id = False
            if hasattr(line, 'combo_parent_id') and line.combo_parent_id:
                parent_id = line.combo_parent_id.id

            payload['odoo_order_data']['lines'].append({
                "product_id": line.product_id.id,
                "qty": line.qty,
                "price_subtotal_incl": line.price_subtotal_incl,
                "is_combo": bool(parent_id),
                "parent_line_id": parent_id
            })

        # Dynamic injection loop
        for item in items:
            path_part, json_key = item.split(':') if ':' in item else (item, item.split('.')[-1])
            prefix, attr = path_part.split('.', 1)

            if prefix == 'store':
                val = self._resolve_path(self.company_id, attr)
                if val is not None:
                    payload['store_info'][json_key] = val
            elif prefix == 'customer' and self.partner_id:
                val = self._resolve_path(self.partner_id, attr)
                if val is not None:
                    payload['customer'][json_key] = val
            elif prefix == 'order':
                val = self._resolve_path(self, attr)
                if val is not None:
                    payload['odoo_order_data'][json_key] = val
            elif prefix == 'line':
                for i, line in enumerate(self.lines):
                    val = self._resolve_path(line, attr)
                    if val is not None:
                        payload['odoo_order_data']['lines'][i][json_key] = val
            elif prefix == 'payment':
                for i, pay in enumerate(self.payment_ids):
                    val = self._resolve_path(pay, attr)
                    if val is not None:
                        payload['odoo_order_data']['payments'][i][json_key] = val

        return payload

    @api.model
    def _process_order(self, order, *args, **kwargs):
        """
        Version-Agnostic Hook.
        Works on Odoo 17/18 (3 args) and Odoo 19 (2 args).

        IMPORTANT: this does NOT call the external API directly anymore.
        This method runs inside the checkout RPC the POS frontend waits
        on, so any blocking network call here directly delays the
        cashier's screen (and, if Handy Receipts's API is slow or down,
        can stall checkout for every till using it). Instead we just
        flag the order as 'pending' and let a scheduled action
        (see _cron_process_pending_hr_orders) push it shortly
        after, off the checkout critical path.
        """
        res = super(PosOrder, self)._process_order(order, *args, **kwargs)

        order_id = res
        is_draft = order.get('state') == 'draft'
        delivery_value = order.get('hr_delivery_value')

        if not is_draft and delivery_value:
            pos_order = self.browse(order_id)
            config = pos_order.config_id
            pos_order.sudo().write({
                'hr_delivery_type': order.get('hr_delivery_type'),
                'hr_delivery_value': delivery_value,
                'hr_api_status': 'pending',
            })
             # HYBRID LOGIC: Sync vs Async
            if config.hr_enable_qr:
                # SYNCHRONOUS: We need the QR URL immediately for the frontend screen
                try:
                    qr_url = pos_order._send_to_hr_api()
                    if qr_url:
                        pos_order.sudo().write({'hr_qr_url': qr_url, 'hr_api_status': 'success'})
                        
                        # IMPORTANT: We must inject the qr_url into the response dictionary
                        # so the OWL frontend can grab it!
                        if isinstance(res, list) and len(res) > 0 and isinstance(res[0], dict):
                            res[0]['hr_qr_url'] = qr_url
                    else:
                        pos_order.sudo().write({'hr_api_status': 'failed'})
                except Exception as e:
                    _logger.error("Handy Receipts Sync API Error: %s", str(e))
                    pos_order.sudo().write({'hr_api_status': 'failed'})
            else:
                # ASYNCHRONOUS: No QR needed on screen. Trigger background cron.
                # Ask the scheduler to run the push job right away (typically
                # within a few seconds) instead of waiting for its normal
                # interval. This is still fully non-blocking for checkout —
                # _trigger() just queues the job, it doesn't run or wait for
                # it here. The cron's own interval (data/ir_cron_data.xml) is
                # only a safety net for anything a trigger call might miss
                # (e.g. the job wasn't picked up before a server restart).
                cron = self.env.ref(
                    'pos_handy_receipts.ir_cron_process_pending_hr_orders',
                    raise_if_not_found=False,
                )
                if cron:
                    cron.sudo()._trigger()
            
        return res

    @api.model
    def _cron_process_pending_hr_orders(self):
        """ Scheduled Action: picks up orders flagged 'pending' by
        _process_order and pushes them to Handy Receipts asynchronously,
        so checkout is never blocked waiting on the external API.
        Runs in small batches and commits per-order so one slow/failed
        call doesn't hold up or lose progress on the rest of the batch. """
        pending_orders = self.search(
            [('hr_api_status', '=', 'pending')],
            limit=HANDY_RECEIPTS_CRON_BATCH_SIZE,
        )
        for order in pending_orders:
            try:
                qr_url = order._send_to_hr_api()
                if qr_url:
                    order.write({'hr_qr_url': qr_url, 'hr_api_status': 'success'})
                else:
                    order.write({'hr_api_status': 'failed'})
            except Exception:
                _logger.exception("Handy Receipts: unexpected error processing order %s", order.id)
                order.write({'hr_api_status': 'failed'})
            # Commit progressively: keeps a failure on one order from
            # rolling back status updates already made on earlier ones.
            self.env.cr.commit()

    def _send_to_hr_api(self):
        config = self.config_id
        icp = self.env['ir.config_parameter'].sudo()

        api_key = config.hr_api_key or icp.get_param('pos_handy_receipts.api_key')
        api_url = config.hr_api_url or icp.get_param('pos_handy_receipts.api_url')
        csid = config.hr_csid or icp.get_param('pos_handy_receipts.csid')

        if not api_key or not api_url:
            return False

        payload = self._prepare_hr_payload()
        payload.update({
            'CSID': csid,
            'delivery_target': {
                'type': self.hr_delivery_type,
                'input_value': self.hr_delivery_value
            }
        })

        try:
            resp = requests.post(api_url, json=payload, timeout=15,
                                  headers={'Content-Type': 'application/json', 'X-API-KEY': api_key})
            if resp.status_code == 200:
                return resp.json().get('qr_url')
        except Exception as e:
            _logger.error("Handy Receipts API Error: %s", str(e))
        return False