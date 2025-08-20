from odoo.tools.sql import column_exists, create_column


def pre_init_hook(env):
    # Speed up the installation of the module on an existing Odoo instance
    # by not computing the pricelist for every invoice. Also avoids
    # a possible computation error of
    # computing all pricelists -> _check_currency constraint error before the
    # currency can recompute itself
    if not column_exists(env.cr, "account_move", "pricelist_id"):
        create_column(env.cr, "account_move", "pricelist_id", "int4")
