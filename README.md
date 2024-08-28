# stock_extension

extension pour le module inventaire
- tracking product,
- send mail,
- reset stock.quant : pour corriger une erreur dans odoo 10 car dans la table stock_qty le stock est mal écrit. Nous devons donc recalculer le stock à partir des stock_moves.
