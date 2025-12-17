# Product BoM Components

Manage Bill of Materials components directly from the product form with automatic bidirectional synchronization.

## Features

### 📋 Manage BoM from Product Form
- View and edit BoM components directly in the product form
- New dedicated "BoM Components" page in product form
- Clean and intuitive interface

### 🔄 Bidirectional Sync
- **Product → BoM**: Changes in product form automatically update the Bill of Materials
- **BoM → Product**: Changes in BoM automatically update the product form
- Real-time synchronization prevents data inconsistency

### 🎯 Key Capabilities
- **Load from BoM**: One-click button to import existing BoM components
- **Drag & Drop**: Reorder components using sequence handles
- **Auto-fill UoM**: Unit of Measure automatically filled from product
- **Smart Sync**: Prevents infinite loops and duplicate updates
- **Graceful Degradation**: Works without MRP module (limited functionality)

## Installation

1. Copy the `product_bom_components` folder to your Odoo addons directory
2. Restart Odoo server
3. Update Apps List (Apps → Update Apps List)
4. Search for "Product BoM Components"
5. Click "Install"

## Usage

### Adding Components

1. Open a product form
2. Go to the "BoM Components" page
3. Click "Add a line" or "Load from BoM" button
4. Select component product
5. Enter quantity
6. Unit of Measure is auto-filled
7. Save - the BoM is automatically updated!

### Loading from Existing BoM

1. Open a product that has a Bill of Materials
2. Go to the "BoM Components" page
3. Click "Load from BoM" button
4. All components from the first BoM are loaded
5. Edit as needed - changes sync automatically

### Editing Components

- Changes in the product form automatically update the BoM
- Changes in the BoM automatically update the product form
- Drag and drop to reorder components
- Delete components from either location

## Technical Details

### Models

**product.bom.component**
- Links product template to BoM components
- Fields: product_tmpl_id, product_id, product_qty, product_uom_id, bom_line_id, sequence
- Automatic sync to mrp.bom.line (when MRP installed)

### Sync Mechanism

- Uses context flag `skip_bom_sync` to prevent infinite loops
- Forward sync: ProductBomComponent → MrpBomLine
- Reverse sync: MrpBomLine → ProductBomComponent
- Smart detection of sync source

### Dependencies

- **Required**: product, stock
- **Optional**: mrp (for full BoM integration)

## Configuration

No configuration needed. Works out of the box!

## Support

For issues or questions, please contact your system administrator.

## Credits

- Author: Your Company
- Version: 18.0.1.0.0
- License: LGPL-3
