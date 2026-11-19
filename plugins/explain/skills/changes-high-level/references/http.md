# HTTP interfaces, server and client

How to write the endpoints a change serves or calls, with their request and response shapes before and after, into a fragment so the page can draw them as a diff. All examples are invented.

## Before and after

Read the request and response types at the base and at the head and follow nested types; an API spec in the repository at both ends is a shortcut. For a client, also find the target: the base-URL configuration key and the service it names.

`changes` lists the changes one per line in plain words, with the field path: "removed the request property `items/weightGrams`". Write every field of a changed body, including the unchanged ones with `"status": "unchanged"`, nested objects under `fields`. Mark type changes, required and optional flips, and enum changes with `was`. The page prints each body as a JSON-like diff: the type as the value, required or optional and the `note` as a trailing `//` comment.

## Cost and rollout

- **cost:** an endpoint other services or a frontend call means `other consumers must change` for a removed field or a type change; going back needs a new version of the path, so say so in `text`. A client call to another service is `code change only` on this side.
- **rollout:** a new optional request field or a new response field is `backward compatible`. A removed request field, a new required one, a narrowed type (string to enum) or a removed response field `breaks existing callers`. A client that calls an endpoint the other service does not serve yet `needs deploy order`: say which service goes first.

## Fragment shape

```json
{
  "direction": "server",
  "method": "POST",
  "path": "/orders/{orderId}/shipments",
  "lead": "Takes an optional delivery window and a priority enum and drops the item weight; callers that send free-text priority get a 400.",
  "area": "shipments",
  "status": "changed",
  "source": "code",
  "ref": "shipments/src/main/kotlin/com/example/shipments/api/ShipmentController.kt:41",
  "changes": ["added the optional request property `deliveryWindow`", "removed the request property `items/weightGrams`"],
  "request": {
    "type": "ShipmentRequest",
    "fields": [
      {"name": "carrier", "status": "unchanged", "type": "string", "required": true},
      {"name": "priority", "status": "changed", "type": "enum [STANDARD, EXPRESS]", "was": {"type": "string"}},
      {"name": "items[]", "status": "unchanged", "type": "array<object>", "fields": [
        {"name": "weightGrams", "status": "removed", "type": "integer"},
        {"name": "quantity", "status": "changed", "type": "integer", "required": true, "was": {"required": false}}
      ]}
    ]
  },
  "responses": [{"status": "201", "type": "ShipmentResponse", "fields": [{"name": "trackingUrl", "status": "added", "type": "string", "required": false}]}],
  "cost": {"labels": ["other consumers must change"]},
  "rollout": {"label": "breaks existing callers", "text": "A caller that leaves out quantity gets a 400."}
}
```

A client endpoint has `"direction": "client"` and `"target": {"service": "customer-service", "config_key": "clients.customer.base-url"}`.
