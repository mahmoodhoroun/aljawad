# -*- coding: utf-8 -*-
from odoo import http
from odoo.http import request
import json
from datetime import datetime


class ReplenishmentDashboardController(http.Controller):

    @http.route('/replenishment_dashboard/data', type='json', auth='user')
    def get_dashboard_data(self, filters=None):
        """
        Get replenishment data using optimized SQL queries.
        Filters: {
            'min_max_based_on': 'company' or 'branch',
            'branch_id': company_id (if based on branch),
            'start_date': 'YYYY-MM-DD',
            'end_date': 'YYYY-MM-DD',
            'product_ids': [list of product IDs] or None for all
        }
        """
        if filters is None:
            filters = {}

        cr = request.env.cr
        company_id = request.env.company.id

        min_max_based_on = filters.get('min_max_based_on', 'company')
        branch_id = filters.get('branch_id')
        start_date = filters.get('start_date')
        end_date = filters.get('end_date')
        product_ids = filters.get('product_ids')

        # Determine which companies to include based on filters
        if min_max_based_on == 'branch' and branch_id:
            # Single branch only
            target_company_ids = [int(branch_id)]
        else:
            # Get company hierarchy (parent + all branches)
            target_company_ids = self._get_company_hierarchy_ids(cr, company_id)

        # Build product filter
        product_filter = ""
        if product_ids:
            product_filter = f"AND pp.id IN ({','.join(map(str, product_ids))})"

        # Main SQL query to get all data in one go
        query = f"""
            WITH company_list AS (
                SELECT unnest(ARRAY{target_company_ids}::integer[]) as company_id
            ),
            product_list AS (
                SELECT DISTINCT pp.id as product_id,
                       pt.name->>'en_US' as product_name,
                       pp.default_code as product_code
                FROM product_product pp
                JOIN product_template pt ON pp.product_tmpl_id = pt.id
                WHERE (pt.type = 'product' OR pt.type = 'consu')
                  AND pt.active = True
                  {product_filter}
            ),
            stock_quants AS (
                SELECT sq.product_id,
                       SUM(sq.quantity) as qty_on_hand
                FROM stock_quant sq
                JOIN stock_location sl ON sq.location_id = sl.id
                JOIN company_list cl ON sq.company_id = cl.company_id
                WHERE sl.usage = 'internal'
                GROUP BY sq.product_id
            ),
            start_stock AS (
                SELECT sm.product_id,
                       SUM(CASE
                           WHEN sl_dest.usage = 'internal' THEN sm.product_qty
                           WHEN sl_src.usage = 'internal' THEN -sm.product_qty
                           ELSE 0
                       END) as start_qty
                FROM stock_move sm
                JOIN stock_location sl_src ON sm.location_id = sl_src.id
                JOIN stock_location sl_dest ON sm.location_dest_id = sl_dest.id
                JOIN company_list cl ON sm.company_id = cl.company_id
                WHERE sm.state = 'done'
                  AND sm.date < %s
                  AND (sl_src.usage = 'internal' OR sl_dest.usage = 'internal')
                GROUP BY sm.product_id
            ),
            end_stock AS (
                SELECT sm.product_id,
                       SUM(CASE
                           WHEN sl_dest.usage = 'internal' THEN sm.product_qty
                           WHEN sl_src.usage = 'internal' THEN -sm.product_qty
                           ELSE 0
                       END) as end_qty
                FROM stock_move sm
                JOIN stock_location sl_src ON sm.location_id = sl_src.id
                JOIN stock_location sl_dest ON sm.location_dest_id = sl_dest.id
                JOIN company_list cl ON sm.company_id = cl.company_id
                WHERE sm.state = 'done'
                  AND sm.date <= %s
                  AND (sl_src.usage = 'internal' OR sl_dest.usage = 'internal')
                GROUP BY sm.product_id
            ),
            sales_data AS (
                SELECT sm.product_id,
                       SUM(sm.product_qty) as sales_qty
                FROM stock_move sm
                JOIN stock_location sl_src ON sm.location_id = sl_src.id
                JOIN stock_location sl_dest ON sm.location_dest_id = sl_dest.id
                JOIN company_list cl ON sm.company_id = cl.company_id
                WHERE sm.state = 'done'
                  AND sm.date >= %s AND sm.date <= %s
                  AND sl_src.usage = 'internal'
                  AND sl_dest.usage = 'customer'
                GROUP BY sm.product_id
            ),
            sales_return_data AS (
                SELECT sm.product_id,
                       SUM(sm.product_qty) as return_qty
                FROM stock_move sm
                JOIN stock_location sl_src ON sm.location_id = sl_src.id
                JOIN stock_location sl_dest ON sm.location_dest_id = sl_dest.id
                JOIN company_list cl ON sm.company_id = cl.company_id
                WHERE sm.state = 'done'
                  AND sm.date >= %s AND sm.date <= %s
                  AND sl_src.usage = 'customer'
                  AND sl_dest.usage = 'internal'
                GROUP BY sm.product_id
            ),
            purchase_data AS (
                SELECT sm.product_id,
                       SUM(sm.product_qty) as purchase_qty
                FROM stock_move sm
                JOIN stock_location sl_src ON sm.location_id = sl_src.id
                JOIN stock_location sl_dest ON sm.location_dest_id = sl_dest.id
                JOIN company_list cl ON sm.company_id = cl.company_id
                WHERE sm.state = 'done'
                  AND sm.date >= %s AND sm.date <= %s
                  AND sl_src.usage = 'supplier'
                  AND sl_dest.usage = 'internal'
                GROUP BY sm.product_id
            ),
            purchase_return_data AS (
                SELECT sm.product_id,
                       SUM(sm.product_qty) as return_qty
                FROM stock_move sm
                JOIN stock_location sl_src ON sm.location_id = sl_src.id
                JOIN stock_location sl_dest ON sm.location_dest_id = sl_dest.id
                JOIN company_list cl ON sm.company_id = cl.company_id
                WHERE sm.state = 'done'
                  AND sm.date >= %s AND sm.date <= %s
                  AND sl_src.usage = 'internal'
                  AND sl_dest.usage = 'supplier'
                GROUP BY sm.product_id
            )
            SELECT
                pl.product_id,
                pl.product_name,
                pl.product_code,
                COALESCE(sq.qty_on_hand, 0) as qty_on_hand,
                COALESCE(st_start.start_qty, 0) as start_stock_qty,
                COALESCE(st_end.end_qty, 0) as end_stock_qty,
                COALESCE(sd.sales_qty, 0) as sales_qty,
                COALESCE(sr.return_qty, 0) as sales_return_qty,
                COALESCE(pd.purchase_qty, 0) as purchase_qty,
                COALESCE(pr.return_qty, 0) as purchase_return_qty
            FROM product_list pl
            LEFT JOIN stock_quants sq ON pl.product_id = sq.product_id
            LEFT JOIN start_stock st_start ON pl.product_id = st_start.product_id
            LEFT JOIN end_stock st_end ON pl.product_id = st_end.product_id
            LEFT JOIN sales_data sd ON pl.product_id = sd.product_id
            LEFT JOIN sales_return_data sr ON pl.product_id = sr.product_id
            LEFT JOIN purchase_data pd ON pl.product_id = pd.product_id
            LEFT JOIN purchase_return_data pr ON pl.product_id = pr.product_id
            ORDER BY pl.product_name
        """

        # Execute query with parameters
        params = [
            start_date or '1900-01-01',  # start_stock date filter
            end_date or datetime.now().strftime('%Y-%m-%d'),  # end_stock date filter
            start_date or '1900-01-01',  # sales start date
            end_date or datetime.now().strftime('%Y-%m-%d'),  # sales end date
            start_date or '1900-01-01',  # sales return start date
            end_date or datetime.now().strftime('%Y-%m-%d'),  # sales return end date
            start_date or '1900-01-01',  # purchase start date
            end_date or datetime.now().strftime('%Y-%m-%d'),  # purchase end date
            start_date or '1900-01-01',  # purchase return start date
            end_date or datetime.now().strftime('%Y-%m-%d'),  # purchase return end date
        ]

        cr.execute(query, params)
        results = cr.dictfetchall()

        # Get min/max values for products
        for row in results:
            min_max = self._get_product_min_max(
                cr,
                row['product_id'],
                min_max_based_on,
                branch_id
            )
            row.update(min_max)

            # Calculate to_order_qty
            # When based on branch: check if onhands < branch_min, then order (branch_max - onhands)
            # When based on company: check if onhands < company_min, then order (company_max - onhands)
            if min_max_based_on == 'branch':
                min_qty = min_max.get('branch_min_qty', 0)
                max_qty = min_max.get('branch_max_qty', 0)
            else:  # company
                min_qty = min_max.get('company_min_qty', 0)
                max_qty = min_max.get('company_max_qty', 0)

            # Only calculate to_order if current stock is below minimum
            if row['qty_on_hand'] < min_qty:
                row['to_order_qty'] = max(0, max_qty - row['qty_on_hand'])
            else:
                row['to_order_qty'] = 0

        return {
            'success': True,
            'data': results,
            'filters': filters
        }

    def _get_company_hierarchy_ids(self, cr, company_id):
        """Get parent company and all its branches."""
        query = """
            WITH RECURSIVE company_tree AS (
                -- Get the parent company (or current if no parent)
                SELECT
                    CASE
                        WHEN parent_id IS NOT NULL THEN parent_id
                        ELSE id
                    END as parent_id
                FROM res_company
                WHERE id = %s

                UNION

                -- Get all branches of the parent
                SELECT id
                FROM res_company
                WHERE parent_id = (
                    SELECT
                        CASE
                            WHEN parent_id IS NOT NULL THEN parent_id
                            ELSE id
                        END
                    FROM res_company
                    WHERE id = %s
                )
            )
            SELECT DISTINCT parent_id as company_id
            FROM company_tree
        """
        cr.execute(query, (company_id, company_id))
        return [row['company_id'] for row in cr.dictfetchall()]

    def _get_product_min_max(self, cr, product_id, min_max_based_on, branch_id):
        """Get min/max values for a product with inheritance logic."""
        if min_max_based_on == 'branch' and branch_id:
            target_company_id = int(branch_id)
        else:
            target_company_id = request.env.company.id

        # Get company hierarchy for inheritance
        query = """
            SELECT id, parent_id
            FROM res_company
            WHERE id = %s
        """
        cr.execute(query, (target_company_id,))
        company_data = cr.dictfetchone()

        if not company_data:
            return {
                'company_min_qty': 0,
                'company_max_qty': 0,
                'branch_min_qty': 0,
                'branch_max_qty': 0
            }

        parent_id = company_data.get('parent_id')

        # Get product min/max values
        product = request.env['product.product'].sudo().browse(product_id)

        if branch_id:
            product = product.with_company(int(branch_id))

        min_max_data = product.get_effective_min_max()

        import logging
        _logger = logging.getLogger(__name__)
        _logger.info(f"Product {product_id} min/max data: {min_max_data}")

        return {
            'company_min_qty': min_max_data.get('company_min', 0),
            'company_max_qty': min_max_data.get('company_max', 0),
            'branch_min_qty': min_max_data.get('branch_min', 0),
            'branch_max_qty': min_max_data.get('branch_max', 0)
        }

    @http.route('/replenishment_dashboard/branches', type='json', auth='user')
    def get_branches(self):
        """Get list of all companies/branches for filter dropdown."""
        cr = request.env.cr
        query = """
            SELECT id, name, parent_id
            FROM res_company
            WHERE active = True
            ORDER BY parent_id NULLS FIRST, name
        """
        cr.execute(query)
        companies = cr.dictfetchall()

        return {
            'success': True,
            'branches': companies
        }

    @http.route('/replenishment_dashboard/products', type='json', auth='user')
    def get_products(self, search_term=''):
        """Get list of products for search/filter."""
        cr = request.env.cr
        search_filter = ""
        if search_term:
            search_filter = f"""
                AND (pt.name->>'en_US' ILIKE '%{search_term}%'
                     OR pp.default_code ILIKE '%{search_term}%')
            """

        query = f"""
            SELECT pp.id,
                   pt.name->>'en_US' as name,
                   pp.default_code as code
            FROM product_product pp
            JOIN product_template pt ON pp.product_tmpl_id = pt.id
            WHERE (pt.type = 'product' OR pt.type = 'consu')
              AND pt.active = True
              {search_filter}
            ORDER BY pt.name->>'en_US'
            LIMIT 100
        """
        cr.execute(query)
        products = cr.dictfetchall()

        return {
            'success': True,
            'products': products
        }
