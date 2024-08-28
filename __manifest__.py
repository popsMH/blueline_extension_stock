#!/usr/bin/python
# -*- coding: utf-8 -*-

# Copyright Nov 2022

{
    "name": """Stock extension""",
    "summary": """extension for the inventory module ( tracking product, send mail, reset stock.quant, ... )""",
    "category": "Warehouse",
    "images": [],
    "version": "10.0.0.1",
    "application": False,

    "author": "Moriaa Henintsoa, Blueline",

    "depends": ['base', 'mail', 'product', 'sale', 'stock', 'blueline'],
    "external_dependencies": {"python": [], "bin": []},
    "data": [
        # data
        'data/cron_balance.xml',
        'data/email_template.xml',
        
        # security
        'security/ir.model.access.csv',
        'security/security.xml',
        
        # view
        'views/view.xml',
    ],

    "auto_install": False,
    "installable": True,
}
