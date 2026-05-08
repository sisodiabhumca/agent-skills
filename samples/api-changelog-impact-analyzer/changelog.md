# API Changelog (Sample)

## 2026-05-01
- Added `discount_code` field to `POST /checkout` request body.
- Default page size for `GET /orders` changed from 50 to 25.
- Deprecated `GET /orders/legacy` endpoint; it will be removed on 2026-08-01.

## 2026-04-15
- Removed `customer_phone` field from `GET /customers/{id}` response.
- Renamed `status` to `order_status` in `GET /orders/{id}` response.
- Authentication scopes changed: `orders.read` is now required for `GET /orders`.
