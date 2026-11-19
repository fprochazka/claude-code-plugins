# Messaging objects

How to write the exchanges, queues, bindings, producers, consumers and message types a change touches into a fragment so the page can draw them as a diff. All examples are invented.

## Model

A route is: producer → exchange (name, type) → binding key → queue (name, type, arguments such as the dead-letter exchange, TTL, max length) → consumer, plus the message type it carries. Each element has its own status, so a new queue on an existing exchange shows the exchange unchanged and the queue added.

Kafka maps onto the same shape: the topic is the exchange (type `topic`), the binding key is `*`, and the consumer group is the queue.

A message type is only what crosses a process boundary: the class the producer serializes onto the broker. An in-process event or record that never leaves the service is not a message, however it is named. A message type is its own object with its full payload, like an HTTP body: every field, with nested objects under `fields`, and the unchanged ones marked `unchanged`. Take the payload from the class the producer serializes, at the base and at the head.

## Cost and rollout

- **cost:** a queue's arguments cannot be changed in place on RabbitMQ; the queue has to be deleted and declared again, which is `multi-step change` and often `downtime or failover`. A renamed queue or exchange is a `multi-step change` (declare the new one, bind both, drain the old one). A message type other services consume means `other consumers must change` for any field removal or type change.
- **rollout:** a new optional field is `backward compatible`. A removed or renamed field, a type change, or a new required field `breaks existing callers` when old consumers or old producers are still running. A changed queue declaration that the broker will refuse at startup `needs deploy order`; say what has to happen first.

## Fragment shape

```json
{
  "routes": [{
    "area": "invoicing",
    "status": "added",
    "source": "declaration",
    "ref": "billing/src/main/kotlin/com/example/billing/reminder/ReminderMessagingConfig.kt:21",
    "producer": {"name": "InvoiceReminderScheduler", "status": "added"},
    "exchange": {"name": "billing.events", "type": "topic", "status": "unchanged"},
    "key": "invoice.reminder.due",
    "queue": {"name": "billing.invoice-reminder", "status": "added", "type": "quorum",
              "arguments": [{"name": "x-dead-letter-exchange", "value": "billing.dlx", "status": "added"}]},
    "consumer": {"name": "ReminderMailListener", "status": "added"},
    "message": "InvoiceReminderDue",
    "lead": "Reminders travel on a new queue bound to the existing billing exchange.",
    "cost": {"labels": ["multi-step change"]},
    "rollout": {"label": "backward compatible"}
  }],
  "messages": [{
    "name": "InvoiceReminderDue",
    "area": "invoicing",
    "status": "added",
    "source": "code",
    "ref": "billing/src/main/kotlin/com/example/billing/reminder/InvoiceReminderDue.kt:5",
    "format": "JSON",
    "lead": "A new message with two required fields; only the reminder listener consumes it.",
    "fields": [
      {"name": "invoiceId", "status": "added", "type": "long", "required": true},
      {"name": "channel", "status": "added", "type": "enum [EMAIL, SMS]", "required": true}
    ],
    "cost": {"labels": ["other consumers must change"]},
    "rollout": {"label": "backward compatible"}
  }]
}
```

Routes are page components drawn as lanes, and payloads as JSON-like diffs with `//` comments; do not draw them in a Mermaid diagram. A field's `note` becomes its comment, so keep it short.
