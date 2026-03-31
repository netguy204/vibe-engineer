// Chunk: docs/chunks/landing_page_veng_dev
// Single source of truth for the hero code example.
// Rendered twice: with backreferences (Section 1) and without (Section 2).

export interface CodeLine {
  text: string;
  type: 'keyword' | 'string' | 'comment' | 'backreference' | 'function' | 'class' | 'number' | 'plain';
}

// Raw lines of the hero code example. Each line is tagged with its syntax type.
// The CodeBlock component uses this to render with or without backreferences.
export const heroLines: CodeLine[] = [
  { text: 'import time', type: 'keyword' },
  { text: 'from payments.gateway import StripeClient', type: 'keyword' },
  { text: 'from orders.models import Order, PaymentAttempt', type: 'keyword' },
  { text: '', type: 'plain' },
  { text: '# Subsystem: docs/subsystems/payment_pipeline', type: 'backreference' },
  { text: '# Chunk: docs/chunks/checkout_retry', type: 'backreference' },
  { text: '', type: 'plain' },
  { text: 'def process_checkout(order: Order, token: str) -> PaymentAttempt:', type: 'function' },
  { text: '    """Process payment with vendor-aware retry logic."""', type: 'string' },
  { text: '    client = StripeClient(api_key=order.merchant.stripe_key)', type: 'plain' },
  { text: '', type: 'plain' },
  { text: '    for attempt in range(3):', type: 'keyword' },
  { text: '        try:', type: 'keyword' },
  { text: '            result = client.charges.create(', type: 'plain' },
  { text: '                amount=order.total_cents,', type: 'plain' },
  { text: '                currency=order.currency,', type: 'plain' },
  { text: '                source=token,', type: 'plain' },
  { text: '                idempotency_key=f"{order.id}-{attempt}",', type: 'string' },
  { text: '            )', type: 'plain' },
  { text: '            return PaymentAttempt.record(order, result, success=True)', type: 'keyword' },
  { text: '', type: 'plain' },
  { text: '        except client.RateLimitError:', type: 'keyword' },
  { text: '            # Decision: docs/trunk/DECISIONS.md#stripe-retry-policy', type: 'backreference' },
  { text: '            time.sleep(3)', type: 'plain' },
  { text: '', type: 'plain' },
  { text: '        except client.CardError as e:', type: 'keyword' },
  { text: '            return PaymentAttempt.record(order, e, success=False)', type: 'keyword' },
  { text: '', type: 'plain' },
  { text: '    raise CheckoutExhaustedError(order_id=order.id, attempts=3)', type: 'keyword' },
];
