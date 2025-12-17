{
    "name": "Payment Reconcile Fix",
    "version": "1.0.0",
    "description": """
        This module fixes reconciliation mismatches between payments and invoices.
        It provides a script that:
        - Resets all payment reconcile amounts to 0
        - Updates payment reconcile amounts based on actual invoice reconciliations
        - Ensures data consistency between payments and invoices
    """,
    "author": "Custom Development",
    "category": "Accounting",
    "depends": [
        "account",
        "auto_reconcile_payment",
        "base",
    ],
    "data": [
        "security/ir.model.access.csv",
        "views/res_company_views.xml",
    ],
    "installable": True,
    "auto_install": False,
    "application": False,
}
