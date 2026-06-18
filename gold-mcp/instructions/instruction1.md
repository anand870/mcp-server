The Gold MCP Server has already been implemented.

Do **not** regenerate the project.

Instead, update the existing codebase with the following enhancements while maintaining the current architecture, coding style, tests, and project structure.

---

# 1. Multi-Currency Support

Enhance the server to support multiple currencies.

Initially support:

* USD
* AED
* INR

The default currency should be configurable in `config.yaml`.

Example:

```yaml
default_currency: AED

supported_currencies:
  - USD
  - AED
  - INR
```

All existing MCP tools that return prices should accept an optional `currency` parameter.

Example:

```python
get_gold_price(currency="AED")
```

If no currency is provided, use the configured default.

---

# 2. Local Price Providers

Refactor the provider architecture to support currency-specific providers.

Instead of one provider per API, support providers by market.

Example:

```
USD
 ├── FreeGoldAPI
 ├── Metals.dev
 ├── GoldAPI
 └── Yahoo Finance

AED
 ├── iGold
 ├── Dubai City of Gold
 └── USD Conversion (fallback)

INR
 ├── Local provider (if available)
 └── USD Conversion (fallback)
```

Implement automatic fallback.

Example:

For AED:

1. iGold
2. Dubai City of Gold
3. USD + FX conversion

For INR:

1. Local provider (if implemented)
2. USD + FX conversion

The response should indicate which provider was used.

---

# 3. Currency Conversion

Only use currency conversion as a fallback.

Never override a local market price with a converted price if a local provider is available.

Store metadata indicating:

```json
{
  "source": "igold",
  "price_type": "local"
}
```

or

```json
{
  "source": "usd_conversion",
  "price_type": "converted"
}
```

---

# 4. Gold Carat Support

Extend the server to support multiple gold purities.

Support:

* 24K
* 22K
* 21K
* 18K

If a provider exposes multiple carat prices, return the provider values directly.

If only a 24K price is available, derive the other purities using standard purity ratios.

Purity ratios:

24K = 1.000

22K = 22 / 24

21K = 21 / 24

18K = 18 / 24

The response must indicate whether a value is:

* provider supplied
* calculated

Example:

```json
{
    "carat": "22K",
    "price": 374.60,
    "calculated": true
}
```

or

```json
{
    "carat": "22K",
    "price": 376.10,
    "calculated": false
}
```

---

# 5. Database Changes

Update the SQLite schema.

Include:

* currency
* carat
* provider
* price_type
* calculated

Example:

```
timestamp
currency
carat
provider
price
price_type
calculated
```

Ensure migrations preserve existing data.

---

# 6. Historical Storage

Store historical prices independently for every:

* currency
* carat

Examples:

USD 24K

AED 24K

AED 22K

AED 21K

AED 18K

INR 24K

etc.

Historical queries should filter correctly.

---

# 7. MCP Tool Improvements

Update:

## get_gold_price

Support:

```
currency
carat
```

Example:

```
get_gold_price(
    currency="AED",
    carat="22K"
)
```

---

## get_gold_prices

Create a new tool that returns all supported currencies and carats.

Example response:

```json
{
  "USD": {
    "24K": {...},
    "22K": {...}
  },
  "AED": {
    "24K": {...},
    "22K": {...},
    "21K": {...},
    "18K": {...}
  },
  "INR": {
    "24K": {...},
    "22K": {...}
  }
}
```

---

## analyze_buy_opportunity

Support:

```
currency
carat
```

Analysis should always use the requested market.

Example:

```
analyze_buy_opportunity(
    currency="AED",
    carat="24K"
)
```

---

## get_market_summary

Update to display all configured currencies.

Example:

```
Gold Prices

AED (iGold)

24K
22K
21K
18K

USD Spot

24K

INR

24K

Buy Score

Recommendation
```

The summary should clearly indicate:

* provider
* local vs converted price
* calculated vs provider-supplied carat prices

---

# 8. Configuration

Add:

```yaml
default_currency: AED

default_carat: 24K

currencies:
  USD:
    enabled: true

  AED:
    enabled: true

  INR:
    enabled: true

carats:
  - 24K
  - 22K
  - 21K
  - 18K

providers:

  USD:
    - freegoldapi
    - metalsdev
    - goldapi

  AED:
    - igold
    - dubaicityofgold
    - usd_conversion

  INR:
    - local
    - usd_conversion
```

---

# 9. Backfill and Collection Scripts

Update:

* collect_current_price.py
* refresh_history.py
* backfill_history.py

to collect all configured currencies and all supported carats.

Avoid duplicate records.

---

# 10. Backward Compatibility

Do not break existing MCP clients.

Existing calls such as:

```
get_gold_price()
```

should continue to work using the configured defaults.

---

Update all tests, documentation, schemas, and configuration files accordingly. Preserve the existing architecture and modify only what is necessary to support these enhancements.
