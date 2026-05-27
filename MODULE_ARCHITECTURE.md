# Module Architecture Documentation

## Overview

This workspace contains four Odoo 18 modules that work together to provide custom calculation, reporting, and template features for invoices and sale orders.

```
account + product
    └── custom_invoice_report  (core: custom calc engine for invoices)
            ├── invoice_template  (reusable templates using custom calc)
            └── custom_sale_calculation  (adapts same engine for sale orders)
digital_signature_spacer  (independent: signature spacer for invoices, PO, stock)
```

---

## Module 1: `custom_invoice_report` (v18.0.4.0.0)

### Purpose
Provides flexible Python-driven custom calculations for invoice lines and invoice totals, with configurable report display options.

### Dependencies
- `account`
- `product`

### Models

#### 1. `product.template` (inherit)
**File:** `model/product_template.py`

| Field | Type | Description |
|---|---|---|
| `use_custom_calc` | Boolean | Enable custom Python calculation for this product's invoice lines |
| `custom_calc_code` | Text | Python code executed via `safe_eval` to compute `price_subtotal` |
| `line_type` | Selection | `main_invoice_only`, `breakdown`, `conditional`, `both` — controls where line appears in reports |
| `display_currency_id` | Many2one → res.currency | Override display currency on invoices |
| `type_code` | Text | Arbitrary code for grouping products in calculations |

#### 2. `account.move.line` (inherit)
**File:** `model/account_move_line.py`

| Field | Type | Description |
|---|---|---|
| `use_custom_calc` | Boolean (computed) | Inherited from product template |
| `display_subtotal_from_line` | Many2one → account.move.line | Show subtotal from another line instead |
| `line_type` | Selection (computed) | Resolved from product template; `conditional` type depends on `move.print_breakdown` |

**Key method override:** `_compute_totals()`
- Regular lines → standard Odoo computation via `super()`
- Custom calc lines → `safe_eval` executes product's `custom_calc_code`

**safe_eval context:**
```python
{
    'line': line,           # current account.move.line
    'move': line.move_id,   # parent account.move
    'product': product,     # product.product record
    'siblings': siblings,   # all invoice lines (sorted by sequence)
    'prev_line': prev_line, # immediate previous line or None
    'result': 0.0,          # SET THIS to calculated amount
}
```

#### 3. `account.move` (inherit)
**File:** `model/account_move.py`

| Field | Type | Description |
|---|---|---|
| `total_type_id` | Many2one → invoice.total.type | Select a predefined total calculation method |
| `use_custom_total` | Boolean | Enable custom invoice-level total |
| `custom_total_code` | Text | Python formula for invoice-level total |
| `custom_total` | Monetary (computed) | Calculated custom total (store=True, readonly=False) |
| `print_breakdown` | Boolean | Print separate breakdown section in report |
| `split_table_by_section` | Boolean | Split invoice table by section lines |
| `show_bin` | Boolean | Display BIN number on report |
| `show_exchange_rate` | Boolean | Display exchange rate on report |

**Key methods:**
- `_compute_custom_total()` — evaluates `custom_total_code` or `total_type_id.total_code`
- `action_recalculate_custom_lines()` — recalculates all custom lines + total
- `_onchange_total_type_id()` — auto-fills `custom_total_code` from selected type

**safe_eval context (invoice-level):**
```python
{
    'move': move,          # current account.move
    'lines': lines,        # all invoice lines (recordset)
    'result': 0.0,         # SET THIS to calculated total
}
```

#### 4. `invoice.total.type` (new model)
**File:** `model/invoice_total_type.py`

| Field | Type | Description |
|---|---|---|
| `name` | Char (required) | Name of the calculation type |
| `description` | Text | Description |
| `total_code` | Text (required) | Python formula using `move`, `lines`, `result` |
| `active` | Boolean | Default True |

### Data Files

#### `data/charge_product.xml` (noupdate=1)
Defines 4 predefined products with `use_custom_calc=True`:
- Transfer Cost (15%)
- Outward Remittance TAX (20%)
- Outward Remittance VAT (15%)
- Local VAT (5%)

All use `type=service`, `list_price=0.0`, no taxes.

#### `data/total_types.xml` (noupdate=1)
Defines 1 total calculation type:
- **"Remit (Add last Two Line)"** — sums only the last 2 invoice lines

### Report Templates

| Template ID | Inherits | Purpose |
|---|---|---|
| `report_invoice_document_inherit_custom` | `account.report_invoice_document` | Display currency override; BIN after invoice #; exchange rate; custom total in BDT |
| `report_invoice_document_inherit_custom_table` | `account.report_invoice_document` | Filter main lines by `line_type`; inject breakdown table on new page |
| `report_invoice_document_split_table` | `account.report_invoice_document` | Hide original table when `split_table_by_section`; render per-section tables |
| `invoice_upstra_custom_tax_totals` | `account.document_tax_totals_template` | Replace total row with `custom_total` in BDT |

### Views

| View ID | Inherits | Changes |
|---|---|---|
| `view_move_form_custom_calc` | `account.view_move_form` | Total type dropdown; Report Options group; Recalculate button; Custom Total fields |
| `view_move_form_inherit_usd_to_bdt` | `account.view_move_form` | BDT Conversion group showing `custom_total` |
| `view_invoice_line_form_inherit` | `account.view_move_form` | `display_subtotal_from_line` in invoice line tree |
| `product_template_form_view_inherit` | `product.product_template_form_view` | "Custom Calculation" notebook page |

### Security
- `invoice.total.type`: full CRUD for `base.group_user`

---

## Module 2: `invoice_template` (v1.0.0)

### Purpose
Create reusable invoice templates with predefined product lines, total calculation methods, and journal settings.

### Dependencies
- `account`
- `product`
- `custom_invoice_report`

### Models

#### 1. `invoice.template` (new model)
**File:** `models/invoice_template.py`

| Field | Type | Description |
|---|---|---|
| `name` | Char (required) | Template name |
| `note` | Text | Optional notes |
| `line_ids` | One2many → invoice.template.line | Template lines |
| `total_type_id` | Many2one → invoice.total.type | Default total calculation method |
| `journal_id` | Many2one → account.journal | Default journal (domain: `sale` or `general`) |
| `active` | Boolean | Default True |

#### 2. `invoice.template.line` (new model)
**File:** `models/invoice_template_line.py`

| Field | Type | Description |
|---|---|---|
| `template_id` | Many2one → invoice.template (required, cascade) | Parent template |
| `sequence` | Integer | Line ordering |
| `product_id` | Many2one → product.product (required) | Product |
| `name` | Text | Description override |
| `quantity` | Float | Quantity |
| `price_unit` | Float | Unit price |

#### 3. `account.move` (inherit)
**File:** `models/invoice_template.py`

| Field | Type | Description |
|---|---|---|
| `template_id` | Many2one → invoice.template | Template selector on invoice |
| `unit_price_column` | Boolean | Show/hide unit price column on report |
| `quantity_column` | Boolean | Show/hide quantity column on report |

**Key method:** `_onchange_template_id()` — clears existing lines and creates new ones from template; sets `total_type_id` and `journal_id` from template.

**Key method:** `_sanitize_vals()` — overridden to prevent `line_ids` key conflicts during template application.

### Reports

| Template ID | Inherits | Purpose |
|---|---|---|
| `report_invoice_document_custom` | `account.report_invoice_document` | Conditional quantity/unit price columns based on `o.quantity_column`/`o.unit_price_column` |

### Views

| View ID | Inherits | Changes |
|---|---|---|
| `view_invoice_template_list` | (base) | List view for template |
| `view_invoice_template_form` | (base) | Form view with lines editable tree |
| `action_invoice_template` | (act_window) | Window action for templates |
| `menu_invoice_template` | (menuitem) | Under Accounting → Configuration |
| `view_account_move_form_inherit` | `account.view_move_form` | Template dropdown after partner; qty/price column toggles |

### Security
- `invoice.template`: full CRUD for `base.group_user`
- `invoice.template.line`: full CRUD for `base.group_user`

---

## Module 3: `digital_signature_spacer` (v18.0.1.0.0)

### Purpose
Adds a customizable HTML spacer field before the signature block on invoices, purchase orders, and stock picking reports.

### Dependencies
- `digital_signature`
- `account`
- `purchase`
- `stock`

### Models

All three models get the same field:

| Model | Field | Type |
|---|---|---|
| `account.move` | `signature_spacer` | Html |
| `purchase.order` | `signature_spacer` | Html |
| `stock.picking` | `signature_spacer` | Html |

### Views
Each model's form view inherits the `digital_signature` module's view to add `signature_spacer` before `sign_by`:
- `account.move` → `digital_signature.view_move_form`
- `purchase.order` → `digital_signature.purchase_order_form`
- `stock.picking` → `digital_signature.view_picking_form`

### Reports
Each report template renders `signature_spacer` HTML before the `sign_by` signature:
- `account.move` → `digital_signature.report_invoice_report_inherit_sale`
- `purchase.order` → `digital_signature.purchase_report`
- `stock.picking` → `digital_signature.stock_picking_report` + `digital_signature.stock_delivery_slip_inherit`

---

## Data Flow Diagrams

### Invoice Line Custom Calculation
```
Product Template                          Invoice
┌──────────────────┐                     ┌──────────────────────┐
│ use_custom_calc  │                     │ invoice_line_ids     │
│ custom_calc_code │──→ product_id ─────→│   ├─ line 1 (regular)│
│ line_type        │                     │   ├─ line 2 (custom) │
│ display_currency │                     │   └─ line 3 (custom) │
│ type_code        │                     │ total_type_id        │
└──────────────────┘                     │ use_custom_total     │
                                         │ custom_total_code    │
                                         │ custom_total         │
                                         └──────────────────────┘

On save: _compute_totals()
  ├─ Regular lines → super()._compute_totals() (standard Odoo)
  └─ Custom lines  → safe_eval(product.custom_calc_code)
                      with {line, move, product, siblings, prev_line, result}
                      → line.price_subtotal = result

Then: _compute_custom_total()
  └─ safe_eval(move.custom_total_code or total_type_id.total_code)
     with {move, lines, result}
     → move.custom_total = result
```

### Invoice Template Application
```
Invoice Template                    Invoice
┌─────────────────────┐            ┌─────────────────────────┐
│ name                │            │ template_id             │
│ line_ids            │──onchange──│ invoice_line_ids (clear + create)
│   ├─ product_id     │            │ total_type_id (set from template)
│   ├─ quantity       │            │ journal_id (set from template)
│   └─ price_unit     │            └─────────────────────────┘
│ total_type_id       │
│ journal_id          │
└─────────────────────┘
```

---

## Report Display Logic

### Line Type Resolution
```
product_template.line_type
├── main_invoice_only  →  line.line_type = "main_invoice_only"
├── breakdown          →  line.line_type = "breakdown"
├── conditional        →  if move.print_breakdown
│                          then "breakdown"
│                          else "main_invoice_only"
└── both               →  line.line_type = "both"

Main table filtered by: line_type IN ('main_invoice_only', 'both')
Breakdown table filtered by: line_type IN ('breakdown', 'both')
```

### Split Table Logic
When `split_table_by_section` is enabled:
1. Original table hidden (`t-if="not o.split_table_by_section"`)
2. Standard total block hidden
3. Lines are grouped by `line_section` display_type boundaries
4. Each group renders as a separate table with section header

---

## Module 4: `custom_sale_calculation` (v18.0.1.0.0)

Adapts `custom_invoice_report` patterns for `sale.order` and `sale.order.line` models.

### Dependencies
- `sale`
- `product`
- `custom_invoice_report`

### Models

#### 1. `product.template` (inherit)
**File:** `models/product_template.py`

Same fields as `custom_invoice_report`: `use_custom_calc`, `custom_calc_code`, `line_type`, `display_currency_id`, `type_code`.

#### 2. `sale.order.line` (inherit)
**File:** `models/sale_order_line.py`

| Field | Type | Description |
|---|---|---|
| `use_custom_calc` | Boolean (computed) | Inherited from product template |
| `display_subtotal_from_line` | Many2one → sale.order.line | Show subtotal from another line instead |
| `line_type` | Selection (computed) | Resolved from product template |

**Key method override:** `_compute_amount()` — same safe_eval pattern as invoice version.

**safe_eval context:**
```python
{
    'line': line,
    'order': line.order_id,
    'product': product,
    'siblings': siblings,
    'prev_line': prev_line,
    'result': 0.0,
}
```

#### 3. `sale.order` (inherit)
**File:** `models/sale_order.py`

| Field | Type | Description |
|---|---|---|
| `total_type_id` | Many2one → sale.total.type | Select a predefined total calculation method |
| `use_custom_total` | Boolean | Enable custom order-level total |
| `custom_total_code` | Text | Python formula for order-level total |
| `custom_total` | Monetary (computed) | Calculated custom total |
| `print_breakdown` | Boolean | Print breakdown section |
| `split_table_by_section` | Boolean | Split table by section lines |
| `show_bin` | Boolean | Display BIN number |
| `show_exchange_rate` | Boolean | Display exchange rate |

**Key methods:**
- `_compute_custom_total()` — evaluates formula
- `action_recalculate_custom_lines()` — recalculates
- `_onchange_total_type_id()` — auto-fills code
- `_prepare_invoice()` — propagates fields to invoice

#### 4. `sale.total.type` (new model)
**File:** `models/sale_total_type.py`

| Field | Type | Description |
|---|---|---|
| `name` | Char (required) | Name of the calculation type |
| `description` | Text | Description |
| `total_code` | Text (required) | Python formula |
| `active` | Boolean | Default True |

### Propagation to Invoice
When `_create_invoices()` is called, `_prepare_invoice()` propagates:
- `total_type_id`, `use_custom_total`, `custom_total_code`
- `print_breakdown`, `split_table_by_section`
- `show_bin`, `show_exchange_rate`

### Data Files
- `data/charge_product.xml` — same 4 charge products as invoice module
- `data/total_types.xml` — 1 total type (Remit - Add last Two Lines)

### Reports
- `report_saleorder_document_inherit_custom` — display currency override, BIN
- `report_saleorder_custom_table` — line type filtering, breakdown page
- `report_saleorder_split_table` — section-based table splitting
- `sale_custom_tax_totals` — custom total in BDT

### Views
- Product form: "Custom Calculation" notebook page
- Sale order form: total type dropdown, report toggles, recalculate button
- Sale total type: list/form views under Sales menu

### Security
- `sale.total.type`: full CRUD for `base.group_user`

### Key Differences from Invoice Version

| Aspect | Invoice (`custom_invoice_report`) | Sale (planned) |
|---|---|---|
| Line model | `account.move.line` | `sale.order.line` |
| Eval context variable | `move` | `order` |
| Amount method | `_compute_totals()` | `_compute_amount()` |
| Lines accessor | `move.invoice_line_ids` | `order.order_line` |
| Report template | `account.report_invoice_document` | `sale.report_saleorder_document` |
| Tax totals inherit | `account.document_tax_totals_template` | `sale.document_tax_totals` |

### Propagation from Sale Order → Invoice
When `_create_invoices()` is called, the following fields propagate:
- `total_type_id`
- `use_custom_total`
- `custom_total_code`
- `print_breakdown`
- `split_table_by_section`
- `show_bin`
- `show_exchange_rate`
