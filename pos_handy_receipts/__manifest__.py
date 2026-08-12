# -*- coding: utf-8 -*-
{
    'name': 'Handy Receipts: WhatsApp & Interactive Digital Receipts for POS',
    'version': '19.0.1.0.1',
    'category': 'Point of Sale',
    'summary': 'Send interactive digital receipts via WhatsApp, SMS, or Privacy QR directly from Odoo POS. Embed coupons, collect NPS feedback, and eliminate thermal paper costs.',
    'description': """
Handy Receipts: The Ultimate Post-Purchase Engagement Tool for Odoo POS
=======================================================================
Stop sending dead PDFs and wasting money on toxic thermal paper. 
This module connects your Odoo POS directly to the Handy Receipts platform.

Key Features:
- WhatsApp & SMS Receipt Delivery
- Static as well as Dynamic Customer-Facing QR Codes (No phone number required)
- Embedded "Next Visit" Discount Coupons
- Instant NPS & Customer Feedback Collection
- 100% Eco-friendly and Paperless Checkout

*Note: This add-on requires an active subscription API Key from handyreceipts.co.in*
    """,
    'author': 'Neuroceptive Technologies LLP',
    'company': 'Neuroceptive Technologies LLP',
    'maintainer': 'Neuroceptive Technologies LLP',
    'website': 'https://handyreceipts.co.in',
    'depends': ['base', 'point_of_sale'],
    'data': [
        'data/ir_cron_data.xml',
        'views/res_config_settings_views.xml',
    ],
   'assets': {
        'point_of_sale._assets_pos': [
            'pos_handy_receipts/static/src/app/css/pos_custom.css',
            'pos_handy_receipts/static/src/app/screens/payment_screen/payment_screen.js',
            'pos_handy_receipts/static/src/app/screens/payment_screen/payment_screen.xml',
            'pos_handy_receipts/static/src/app/screens/receipt_screen/receipt_screen.xml',
            'pos_handy_receipts/static/src/app/models/pos_order.js',

        ],
    },
    'images': ['static/description/thumbnail.png'],
    'license': 'LGPL-3',
    'installable': True,
    'application': False,
    'auto_install': False,
    'price': 0.00,
    'currency': 'USD',
}