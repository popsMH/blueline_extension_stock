#!/usr/bin/python
# -*- coding: utf-8 -*-

# Copyright Nov - Dec 2022

from odoo import api, fields, models
from openerp.http import request

import logging


class ProductTemplate(models.Model):
    _inherit = 'product.template'
    
    tracking = fields.Selection(track_visibility='onchange')
        
    # envoi mail
    @api.multi
    def write(self, vals):
        
        res = super(ProductTemplate, self).write(vals)
        
        if 'tracking' in vals and vals.get('tracking') != 'serial':
            
            logging.error("---------------------- sending mail (alert tracking by serial number changed) ----------------------")
            
            ## Obtenir le modèle d'e-mail
            template_obj = request.env['mail.template'].sudo().search([('name','=','Alert Suivi de produit')], limit=1)
            
            mail_to = ['sitraka.rasoamiaramanana@gulfsat.mg', 'tantely.razanajaona@staff.blueline.mg', 'rahim.remtola@staff.blueline.mg']
            # mail_to = ['moria.miraifahasoavana@staff.blueline.mg']
            mail_cc = ['dev@si.blueline.mg']
            
            tracking_value = dict(self._fields['tracking'].selection).get(self.tracking)
            if tracking_value == 'By Lots':
                tracking = 'Suivi par lots'
            else:
                tracking = 'Pas de suivi'
                
            current_id = self.id
            current_model = self._name
            
            base_url = 'http://odoo.malagasy.com'
            complete_url = base_url + '/web#id={}&view_type=form&model={}'.format(current_id, current_model)
            
            # Obtenir le current user
            context = self._context
            current_uid = context.get('uid')
            user = self.env['res.users'].browse(current_uid)
            current_username = str(user.name)
            
            if template_obj:
                default_body = template_obj.body_html
                
                custom_body = """
                    <div style="font-family: 'Lucida Grande', Ubuntu, Arial, Verdana, sans-serif; font-size: 12px; color: rgb(34, 34, 34); background-color: #FFF; ">
                        <font style="font-size: 20px;">
                            <p>Le champ "Suivi Par numero de serie unique" de l'article &#60;&#60; <a href="{}"><u>{}</u></a> &#62;&#62; est modifi&eacute; en &#60;&#60; <u>{}</u> &#62;&#62; par l'utilisateur &#60;&#60; <u>{}</u> &#62;&#62; </p>
                        </font>
                    </div>
                """.format(complete_url, self.name, tracking, current_username)
                
                body = default_body + custom_body
                
                mail_values = {
                    'subject': template_obj.subject,
                    'body_html': body,
                    'email_to': ';'.join(map(lambda x: x, mail_to)),
                    'email_cc': ';'.join(map(lambda x: x, mail_cc)),
                    'email_from': template_obj.email_from,
                }
                
                create_and_send_email = self.env['mail.mail'].create(mail_values).send()
                logging.info("---------------------- mail sent ---------------------------")
                logging.error(mail_to)
                # return True
                
        return res
    
class StockQuantBalance(models.Model):
    _inherit = 'stock.quant'

    @api.constrains('product_id')
    def check_product_id(self):
        pass

    def action_balance_qty(self):
        
        sqlscrpt = (
            """
            WITH moves AS (
            -- tous les mouvements 'done'
            SELECT product_id, product_qty, location_id, location_dest_id, picking_id
            FROM stock_move WHERE state='done'
            ), pack_operation AS (
            -- les mouvements par pack (sans ajustements)
            SELECT pack.product_id, coalesce(pack_lot.qty, pack.qty_done, 0) AS qty, pack_lot.lot_id, pack.location_id, pack.location_dest_id, pack.picking_id
            FROM stock_pack_operation AS pack
            LEFT JOIN stock_pack_operation_lot AS pack_lot
            ON pack.id = pack_lot.operation_id
            ), moves_and_packoperation AS (
            -- mouvements avec lot_id
            SELECT moves.product_id, coalesce(pack_operation.qty, moves.product_qty, 0) AS qty_done, pack_operation.lot_id, moves.location_id, moves.location_dest_id
            FROM moves 
            LEFT JOIN pack_operation
            ON moves.product_id = pack_operation.product_id
            WHERE moves.picking_id = pack_operation.picking_id 
            AND moves.location_id = pack_operation.location_id
            AND moves.location_dest_id = pack_operation.location_dest_id
            ), adjustments AS (
            -- obtenir ajustments dans un emplacement
            SELECT product_id, product_qty, location_id, location_dest_id, inventory_id
            FROM stock_move
            WHERE state = 'done'
            AND inventory_id is not null
            GROUP BY product_id, product_qty, location_id, location_dest_id, inventory_id
            ),
            -- obtenir ajustements par pack dans un emplacement
            all_inventory AS (
            SELECT stock_inventory_line.product_id, theoretical_qty, product_qty AS real_qty, prod_lot_id AS lot_id, stock_inventory_line.location_id, inventory_id
            FROM stock_inventory_line, stock_inventory
            WHERE stock_inventory_line.inventory_id = stock_inventory.id
            AND theoretical_qty - product_qty != 0
            AND stock_inventory.state = 'done'
            ), inventory_filtered_by_lot AS (
            SELECT product_id, lot_id, sum(theoretical_qty) AS theoretical_qty, sum(real_qty) AS real_qty, sum(theoretical_qty - real_qty) AS difference
            FROM all_inventory
            GROUP BY product_id, lot_id
            ), adjustments_with_lot_id AS (
            -- ajustements avec lot_id
            SELECT adjustments.product_id, adjustments.product_qty AS qty_done, all_inventory.lot_id, adjustments.location_id, adjustments.location_dest_id
            FROM adjustments, all_inventory
            WHERE adjustments.product_id = all_inventory.product_id
            AND adjustments.inventory_id = all_inventory.inventory_id
            ), results AS (
            -- tous les mouvements
            (SELECT * FROM moves_and_packoperation)
            union all
            (SELECT * FROM adjustments_with_lot_id)
            )
            SELECT * FROM results
            """
        )

        for i in self.search([]):
            i.write({
                'qty': 0
                })
        
        self._cr.execute(sqlscrpt)
        res = self._cr.dictfetchall()
        
        print("--------------------------------------- GO ---------------------------------------")
        print("moves : {}".format(len(res)))

        for i in res:
            sqrcrd = self.search([
                    ('product_id','=',i['product_id']),
                    ('location_id','=',i['location_id']),
                    ('lot_id','=', i.get('lot_id'))
                    ], limit=1)
            if len(sqrcrd) == 0:
                self.create({
                    'product_id': i['product_id'],
                    'location_id': i['location_id'],
                    'lot_id' : i.get('lot_id'),
                    'qty': -i['qty_done']
                    })
            else:
                sqrcrd.write({
                    'qty': sqrcrd.qty - i['qty_done']
                    })
                            
            sqrcrd = self.search([
                    ('product_id','=',i['product_id']),
                    ('location_id','=',i['location_dest_id']),
                    ('lot_id','=', i.get('lot_id'))
                    ], limit=1)
            if len(sqrcrd) == 0:
                self.create({
                    'product_id': i['product_id'],
                    'location_id': i['location_dest_id'],
                    'lot_id' : i.get('lot_id'),
                    'qty': i['qty_done']
                    })
            else:
                sqrcrd.write({
                    'qty': sqrcrd.qty + i['qty_done']
                    })
            
            # supprimer les stock_quant avec qty est égal à 0
            query = """
                DELETE FROM stock_quant 
                WHERE product_id = (%s)
                AND (location_id = (%s) OR location_id = (%s))
                AND lot_id = (%s)
                AND qty = 0
            """
            self._cr.execute(query, [
                (i['product_id'],),
                (i['location_id'],),
                (i['location_dest_id'],),
                (i.get('lot_id'),)
            ])
            self._cr.commit()
                        
        print("--------------------------------------- VIta ---------------------------------------")