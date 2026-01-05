# -*- coding: utf-8 -*-
from odoo import http
from odoo.http import request
import json
from datetime import datetime
import io
import csv

try:
    import xlsxwriter
    HAS_XLSXWRITER = True
except ImportError:
    HAS_XLSXWRITER = False


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
            'product_ids': [list of product IDs] or None for all,
            'limit': integer (optional, for initial fast loading)
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
        limit = filters.get('limit')

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

        # Add limit clause if specified
        limit_clause = f"LIMIT {int(limit)}" if limit else ""

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
            {limit_clause}
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

    @http.route('/replenishment_dashboard/export_excel', type='http', auth='user')
    def export_excel(self, filters='{}'):
        """Export dashboard data to Excel/CSV file."""
        try:
            filters = json.loads(filters)
        except:
            filters = {}

        # Get the dashboard data using the same method
        result = self.get_dashboard_data(filters)

        if not result.get('success'):
            return request.make_response(
                'Error getting data',
                headers=[('Content-Type', 'text/plain')]
            )

        data = result.get('data', [])

        if HAS_XLSXWRITER:
            return self._export_to_excel(data, filters)
        else:
            return self._export_to_csv(data, filters)

    def _export_to_excel(self, data, filters):
        """Export to Excel using xlsxwriter."""
        # Create Excel file in memory
        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        worksheet = workbook.add_worksheet('Replenishment Report')

        # Define formats
        header_format = workbook.add_format({
            'bold': True,
            'bg_color': '#4472C4',
            'font_color': 'white',
            'border': 1,
            'align': 'center',
            'valign': 'vcenter'
        })

        cell_format = workbook.add_format({
            'border': 1,
            'align': 'center',
            'valign': 'vcenter'
        })

        number_format = workbook.add_format({
            'border': 1,
            'align': 'center',
            'valign': 'vcenter',
            'num_format': '0.00'
        })

        # Write headers
        headers = [
            'Product Code',
            'Product Name',
            'Qty On Hand',
            'Start Stock',
            'End Stock',
            'Sales Qty',
            'Sales Return',
            'Purchase Qty',
            'Purchase Return',
            'Company Min',
            'Company Max',
            'Branch Min',
            'Branch Max',
            'To Order Qty'
        ]

        for col, header in enumerate(headers):
            worksheet.write(0, col, header, header_format)

        # Set column widths
        worksheet.set_column(0, 0, 15)  # Product Code
        worksheet.set_column(1, 1, 35)  # Product Name
        worksheet.set_column(2, 13, 12)  # All other columns

        # Write data
        for row_idx, row_data in enumerate(data, start=1):
            worksheet.write(row_idx, 0, row_data.get('product_code', ''), cell_format)
            worksheet.write(row_idx, 1, row_data.get('product_name', ''), cell_format)
            worksheet.write(row_idx, 2, row_data.get('qty_on_hand', 0), number_format)
            worksheet.write(row_idx, 3, row_data.get('start_stock_qty', 0), number_format)
            worksheet.write(row_idx, 4, row_data.get('end_stock_qty', 0), number_format)
            worksheet.write(row_idx, 5, row_data.get('sales_qty', 0), number_format)
            worksheet.write(row_idx, 6, row_data.get('sales_return_qty', 0), number_format)
            worksheet.write(row_idx, 7, row_data.get('purchase_qty', 0), number_format)
            worksheet.write(row_idx, 8, row_data.get('purchase_return_qty', 0), number_format)
            worksheet.write(row_idx, 9, row_data.get('company_min_qty', 0), number_format)
            worksheet.write(row_idx, 10, row_data.get('company_max_qty', 0), number_format)
            worksheet.write(row_idx, 11, row_data.get('branch_min_qty', 0), number_format)
            worksheet.write(row_idx, 12, row_data.get('branch_max_qty', 0), number_format)
            worksheet.write(row_idx, 13, row_data.get('to_order_qty', 0), number_format)

        # Add filter info at the bottom
        info_row = len(data) + 3
        info_format = workbook.add_format({'bold': True, 'italic': True})

        worksheet.write(info_row, 0, 'Export Info:', info_format)
        worksheet.write(info_row + 1, 0, f"Export Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        worksheet.write(info_row + 2, 0, f"Date Range: {filters.get('start_date', 'N/A')} to {filters.get('end_date', 'N/A')}")
        worksheet.write(info_row + 3, 0, f"Min/Max Based On: {filters.get('min_max_based_on', 'company').title()}")

        workbook.close()
        output.seek(0)

        # Generate filename
        filename = f"Replenishment_Report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"

        # Return file
        return request.make_response(
            output.read(),
            headers=[
                ('Content-Type', 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'),
                ('Content-Disposition', f'attachment; filename="{filename}"')
            ]
        )

    def _export_to_csv(self, data, filters):
        """Export to CSV format (Excel compatible)."""
        output = io.StringIO()
        writer = csv.writer(output)

        # Write headers
        headers = [
            'Product Code',
            'Product Name',
            'Qty On Hand',
            'Start Stock',
            'End Stock',
            'Sales Qty',
            'Sales Return',
            'Purchase Qty',
            'Purchase Return',
            'Company Min',
            'Company Max',
            'Branch Min',
            'Branch Max',
            'To Order Qty'
        ]
        writer.writerow(headers)

        # Write data
        for row_data in data:
            writer.writerow([
                row_data.get('product_code', ''),
                row_data.get('product_name', ''),
                f"{row_data.get('qty_on_hand', 0):.2f}",
                f"{row_data.get('start_stock_qty', 0):.2f}",
                f"{row_data.get('end_stock_qty', 0):.2f}",
                f"{row_data.get('sales_qty', 0):.2f}",
                f"{row_data.get('sales_return_qty', 0):.2f}",
                f"{row_data.get('purchase_qty', 0):.2f}",
                f"{row_data.get('purchase_return_qty', 0):.2f}",
                f"{row_data.get('company_min_qty', 0):.2f}",
                f"{row_data.get('company_max_qty', 0):.2f}",
                f"{row_data.get('branch_min_qty', 0):.2f}",
                f"{row_data.get('branch_max_qty', 0):.2f}",
                f"{row_data.get('to_order_qty', 0):.2f}",
            ])

        # Add export info
        writer.writerow([])
        writer.writerow(['Export Info:'])
        writer.writerow([f"Export Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"])
        writer.writerow([f"Date Range: {filters.get('start_date', 'N/A')} to {filters.get('end_date', 'N/A')}"])
        writer.writerow([f"Min/Max Based On: {filters.get('min_max_based_on', 'company').title()}"])

        output.seek(0)

        # Generate filename
        filename = f"Replenishment_Report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"

        # Return file
        return request.make_response(
            output.getvalue(),
            headers=[
                ('Content-Type', 'text/csv'),
                ('Content-Disposition', f'attachment; filename="{filename}"')
            ]
        )
