# Custom Invoice Calculation Module

## Overview

This module allows you to write custom Python code in product templates to calculate invoice line totals dynamically. It works similarly to Odoo's salary rules - you write the logic, and it executes via `safe_eval`.

---

## Setup

1. Go to **Products** app
2. Create or edit a product
3. Open the **Custom Calculation** tab (at the bottom)
4. Check **"Use Custom Calculation"**
5. Write your Python calculation code in **"Custom Calculation Code"**

---

## Available Variables

| Variable | Description |
|----------|-------------|
| `line` | Current invoice line (`account.move.line` record) |
| `move` | Parent invoice (`account.move` record) - access `move.bdt_rate`, `move.amount_untaxed`, etc. |
| `product` | The product selected on the line |
| `siblings` | All invoice lines sorted by sequence |
| `prev_line` | Immediate previous line in sequence (or `None`) |
| `result` | **SET THIS** to the calculated amount (float) |

---

## Using type_code for Product Grouping

### What is type_code?
A field on products that allows grouping multiple products together for calculations. Unlike barcode which should be unique, multiple products can share the same type_code.

### Where to Set
- Product Form → Custom Calculation Tab → Type Code field

### Available in Formula as
- `line.product_id.type_code`
- `product.type_code`

### Examples

#### Example 1: Sum All Lines with Specific type_code
```python
# Sum all GCP type products
gcp_lines = siblings.filtered(lambda l: l.product_id.type_code == 'GCP')
result = sum(l.price_subtotal or 0.0 for l in gcp_lines)
```

#### Example 2: Multiple type_codes
```python
# Include multiple type_codes
included_types = ['GCP', 'AMC', 'SERVICE']
filtered = siblings.filtered(lambda l: l.product_id.type_code in included_types)
result = sum(l.price_subtotal or 0.0 for l in filtered)
```

#### Example 3: Priority Lookup with type_code (First Found)
```python
# Find first line with priority type_code
type_priority = ['BILL_BDT', 'PRODUCT']
ref_line = None
for code in type_priority:
    found = siblings.filtered(lambda l: l.product_id.type_code == code)
    if found:
        ref_line = found[0]
        break

if ref_line:
    result = ref_line.price_subtotal * 0.05
else:
    result = 0.0
```

#### Example 4: Sum Multiple type_codes and Apply Formula
```python
# Complex: (CONSUMPTION - PAID - CREDIT) + MASTER
consumption = sum(l.price_subtotal or 0.0 for l in siblings.filtered(lambda x: x.product_id.type_code == 'CONSUMPTION'))
paid = sum(l.price_subtotal or 0.0 for l in siblings.filtered(lambda x: x.product_id.type_code == 'PAID'))
credit = sum(l.price_subtotal or 0.0 for l in siblings.filtered(lambda x: x.product_id.type_code == 'CREDIT'))
master = sum(l.price_subtotal or 0.0 for l in siblings.filtered(lambda x: x.product_id.type_code == 'MASTER'))

result = (consumption - paid - credit) + master
```

#### Example 5: Filter and Apply Percentage
```python
# Find all PRODUCT type lines, sum them, apply percentage
product_lines = siblings.filtered(lambda l: l.product_id.type_code == 'PRODUCT')
total_amount = sum(l.price_subtotal or 0.0 for l in product_lines)

discount_pct = line.percent or 0.0
result = total_amount * (discount_pct / 100)
set_price_unit = result
```

---

## Common Patterns

### 1. First Line as Base (Both Tax & VAT from Line 1)

**For 20% Tax Line:**
```python
# Get all lines in sequence order
siblings = line.move_id.invoice_line_ids.sorted('sequence')

# Get the first line as base
if siblings:
    base_line = siblings[0]
    result = base_line.price_subtotal * 0.20
else:
    result = 0.0
```

**For 15% VAT Line:**
```python
# Get all lines in sequence order
siblings = line.move_id.invoice_line_ids.sorted('sequence')

# Get the first line as base (Line 1)
if siblings:
    base_line = siblings[0]
    result = base_line.price_subtotal * 0.15
else:
    result = 0.0
```

---

### 2. VAT on Sum of First Two Lines

**For 15% VAT Line (Line 3) - Base = Line 1 + Line 2:**
```python
# Get all lines in sequence order
siblings = line.move_id.invoice_line_ids.sorted('sequence')

# Get first two lines and sum them
if len(siblings) >= 2:
    first_line = siblings[0]
    second_line = siblings[1]
    total = (first_line.price_subtotal or 0.0) + (second_line.price_subtotal or 0.0)
    result = total * 0.15
else:
    result = 0.0
```

---

### 3. Immediate Line Above (Previous Line)

```python
# Get all lines in sequence order
siblings = line.move_id.invoice_line_ids.sorted('sequence')

# Find immediate line above
prev_line = None
for sib in siblings:
    if sib.id == line.id:
        break
    prev_line = sib

# Calculate based on immediate previous line
if prev_line:
    result = prev_line.price_subtotal * 0.15
else:
    result = 0.0
```

---

### 4. All Lines Above in Same Section

```python
# Get all lines above current line
all_lines = line.move_id.invoice_line_ids.sorted('sequence')
above_lines = all_lines.filtered(lambda l: l.sequence < line.sequence)

# Find section boundary
section_seq = 0
for above in above_lines.sorted('sequence', reverse=True):
    if above.display_type == 'line_section':
        section_seq = above.sequence
        break

# Get lines in the same section
scoped_lines = above_lines.filtered(lambda l: l.sequence > section_seq)
scoped_total = sum(l.price_subtotal or 0.0 for l in scoped_lines)
result = scoped_total * 0.05
```

---

### 5. All Lines Above (Any Type)

```python
# Get all lines above current line
all_lines = line.move_id.invoice_line_ids.sorted('sequence')
above_lines = all_lines.filtered(lambda l: l.sequence < line.sequence)

# Sum all lines above
total = sum(l.price_subtotal or 0.0 for l in above_lines)
result = total * 0.10
```

---

### 6. Using Move-Level Fields (e.g., bdt_rate)

```python
# Convert previous line amount using move's bdt_rate
rate = move.bdt_rate or 1.0
if prev_line:
    result = prev_line.price_subtotal * rate
else:
    result = 0.0
```

---

### 7. Filter by Product/Category

```python
# Find lines with specific product
siblings = line.move_id.invoice_line_ids.sorted('sequence')
service_lines = siblings.filtered(lambda l: l.product_id.categ_id.name == 'Services')

total = sum(l.price_subtotal or 0.0 for l in service_lines)
result = total * 0.05
```

---

### 8. Filter Non-Custom Lines Only

```python
# Get regular (non-custom calc) lines only
siblings = line.move_id.invoice_line_ids.sorted('sequence')
regular_lines = siblings.filtered(lambda l: not l.use_custom_calc)

if regular_lines:
    base_line = regular_lines[0]
    result = base_line.price_subtotal * 0.20
else:
    result = 0.0
```

---

### 9. Fixed Amount

```python
result = 100.0
```

---

### 10. Quantity-Based Calculation

```python
# Multiply by quantity
result = 50.0 * line.quantity
```

---

## Quick Reference

| Scenario | Key Code |
|----------|----------|
| First line as base | `siblings = line.move_id.invoice_line_ids.sorted('sequence'); base = siblings[0]` |
| Immediate above | Loop until `line.id` matches, keep `prev_line` |
| All above | `all_lines.filtered(lambda l: l.sequence < line.sequence)` |
| Section-based | Check `display_type == 'line_section'` |
| Move fields | `move.bdt_rate`, `move.currency_id`, etc. |
| Product-specific | `line.product_id`, `product.categ_id` |

---

## Important Notes

1. **Set `result` variable** - Your code must assign a value to `result`
2. **safe_eval restrictions** - No imports, no file operations, restricted built-ins
3. **Works automatically** - Recalculates when any sibling line changes
4. **Manual recalculate** - Use "Recalculate Custom Lines" button on invoice form
5. **Errors** - If code has errors, you'll see a clear error message with product name
6. **Setting price_unit** - Use `set_price_unit = result` instead of `line.price_unit = result` (the latter is forbidden in safe_eval)
7. **type_code grouping** - Use `l.product_id.type_code` to filter products by type for group calculations

---

## Troubleshooting

**Line not recalculating?**
- Check that "Use Custom Calculation" is checked on the product
- Ensure `result` is set in your code
- Click "Recalculate Custom Lines" button manually

**Getting an error?**
- Check Python syntax (no imports allowed)
- Ensure variables like `prev_line` are checked for `None` before using

**Need to debug?**
- Add `result = 0.0` at start as fallback
- Check that `siblings` contains expected lines
- Print values temporarily: `result = first_line.price_subtotal or 0.0`

---

## Custom Invoice Total (Global)

In addition to per-line calculations, you can also define a custom total for the entire invoice. When enabled, this total will replace the default `amount_total` in the invoice report.

### How to Enable

1. Open an **Invoice**
2. Go to the **Custom Total** tab (appears after checking "Use Custom Total")
3. Check **"Use Custom Total Calculation"**
4. Write your Python formula in **"Custom Total Formula"**
5. The calculated total appears in **"Custom Total"** field

### Available Variables for Custom Total

| Variable | Description |
|----------|-------------|
| `move` | Current invoice (`account.move` record) |
| `lines` | All invoice lines (`account.move.line` recordset) |
| `result` | **SET THIS** to the calculated total amount (float) |

### Example Formulas

**1. Simple sum of all lines:**
```python
result = sum(l.price_subtotal for l in lines)
```

**2. Sum only custom calculation lines:**
```python
custom_lines = lines.filtered(lambda l: l.use_custom_calc)
result = sum(l.price_subtotal for l in custom_lines)
```

**3. Convert USD to BDT:**
```python
usd_lines = lines.filtered(lambda l: l.currency_id.name == 'USD')
usd_total = sum(l.price_subtotal for l in usd_lines)
rate = move.bdt_rate or 1.0
result = usd_total * rate
```

**4. Sum of specific category:**
```python
service_lines = lines.filtered(lambda l: l.product_id.categ_id.name == 'Services')
result = sum(l.price_subtotal for l in service_lines)
```

**5. Custom formula with conditions:**
```python
total = 0.0
for l in lines:
    if l.sequence < 5:
        total += l.price_subtotal
    else:
        total += l.price_subtotal * 1.1  # Add 10% extra
result = total
```

### Important Notes

1. **Fallback**: If custom total is enabled but formula fails, it falls back to `amount_untaxed`
2. **Report display**: The invoice report shows `custom_total` instead of `amount_total` when enabled
3. **Tax handling**: Taxes are calculated separately by Odoo's standard mechanism
4. **Recalculate**: Click the "Recalculate" button or save the invoice to recalculate

---

## Quick Reference - Full Module

| Feature | Where to Configure |
|---------|-------------------|
| Line-level calculation | Product → Custom Calculation tab |
| Invoice-level total | Invoice → Custom Total tab |
| Recalculate button | Invoice form (top right area) |