# 07 — Payments, Telegram Stars, and Gifts

Gramly supports Telegram Stars end to end: invoices, pre-checkout validation, successful
payments, refunds, subscriptions, gifts, Premium, and emoji status.

Currency for Stars is `"XTR"`. The minimum invoice price is **10 Stars**.

## Payment flow

```text
bot.invoice(...)            user receives the invoice
      |
      v
@bot.onCheckout             validate; pco.accept() or pco.reject("reason")
      |
      v
@bot.onPayment              payment confirmed; deliver the product
      |
      v
bot.refund(...)             optional, using msg.payment.chargeId
```

Never deliver a product in `onCheckout`; it only approves or rejects the charge. Deliver in
`onPayment`, after the charge is confirmed.

## Invoices

### `bot.invoice`

```text
bot.invoice(
    target,                     # chat ID, Message, CallbackQuery
    title: str,
    description: str,
    payload: str,               # your internal identifier, echoed back on payment
    stars: int,                 # price in Stars, minimum 10
    photoUrl: str = None,
    inline=None,
    protectContent: bool = False,
    **kwargs,
)
```

```python
bot.invoice(msg, "Digital Art", "Beautiful artwork", "order_123", stars=10)

bot.invoice(
    msg,
    "PapaCofe",
    "Arabica coffee",
    "coffee_arabica",
    stars=150,
    photoUrl="coffee-arabica.jpg",
)
```

### `bot.createInvoiceLink`

Creates a reusable invoice link without sending a message.

```text
bot.createInvoiceLink(
    title: str,
    description: str,
    payload: str,
    stars: int,
    photoUrl: str = None,
    subscriptionPeriod: int = None,   # seconds, for subscriptions
    **kwargs,
) -> str
```

```python
link = bot.createInvoiceLink(
    "Subscription",
    "Monthly subscription",
    "sub_1",
    stars=50,
    subscriptionPeriod=2592000,   # 30 days
)
bot.send(msg, f"Subscribe: {link}")
```

## Pre-checkout

### `@bot.onCheckout`

```python
@bot.onCheckout
def handler(pco: PreCheckout): ...
```

| Property | Type | Meaning |
| --- | --- | --- |
| `pco.id` | `str` | Pre-checkout query ID |
| `pco.fromUser` | `User` | Buyer |
| `pco.user_id` | `int \| None` | Buyer user ID |
| `pco.currency` | `str` | Currency code, `"XTR"` for Stars |
| `pco.totalAmount` | `int` | Amount in the smallest currency unit |
| `pco.payload` | `str` | Invoice payload |

Methods:

```python
pco.accept()              # approve; the charge proceeds
pco.reject("reason")      # reject; the reason is shown to the user
```

```python
@bot.onCheckout
def checkout(pco):
    if pco.totalAmount < 50:
        pco.reject("Minimum order is 50 Stars")
        return
    if is_banned(pco.user_id):
        pco.reject("You are banned")
        return
    pco.accept()
```

Always call exactly one of `accept()` or `reject()`. If neither is called, the payment does
not proceed.

## Successful payment

### `@bot.onPayment`

```python
@bot.onPayment
def handler(msg: Message): ...
```

`msg.payment` is a `Payment` object:

| Property | Type | Meaning |
| --- | --- | --- |
| `msg.from_user` | `User` | Buyer |
| `msg.user_id` | `int` | Buyer user ID |
| `payment.currency` | `str` | Currency code, `"XTR"` for Stars |
| `payment.totalAmount` | `int` | Amount in the smallest currency unit |
| `payment.stars` | `int \| None` | Stars amount |
| `payment.payload` | `str` | Invoice payload |
| `payment.chargeId` | `str` | Telegram charge ID; use for refunds |
| `payment.providerChargeId` | `str` | Provider charge ID |
| `payment.isRecurring` | `bool` | Recurring subscription payment |
| `payment.isFirstRecurring` | `bool` | First payment of a subscription |
| `payment.subscriptionExpiration` | `int \| None` | Expiry as a Unix timestamp |

```python
@bot.onPayment
def on_payment(msg):
    pay = msg.payment

    if pay.payload == "coffee_arabica":
        deliver_coffee(msg.user_id)
        bot.send(msg, "Arabica is on its way!")
    elif pay.payload == "vip_30d":
        grant_vip(msg.user_id, days=30)
        bot.send(msg, "VIP activated for 30 days!")
    else:
        bot.send(msg, "Payment received.")
```

### Subscriptions

```python
@bot.onPayment
def on_payment(msg):
    pay = msg.payment
    if pay.isFirstRecurring:
        bot.send(msg, "Subscription started.")
    elif pay.isRecurring:
        bot.send(msg, "Subscription renewed.")
```

Store `pay.chargeId` for later cancellation or refunds.

### Refunds

```python
refunded = bot.refund(user_id, charge_id)   # returns bool
```

```python
@bot.onPayment
def on_payment(msg):
    pay = msg.payment
    if not can_deliver(pay.payload):
        bot.refund(msg.user_id, pay.chargeId)
        bot.send(msg, "Out of stock. Refunded.")
        return
    deliver(msg.user_id, pay.payload)
```

Refund from `onPayment` only after verifying the charge. Keep a record of processed
`chargeId` values and make delivery idempotent; Telegram may retry updates.

## Gifts

### `bot.getGifts()`

Returns the gifts available for sending.

| Property | Type | Meaning |
| --- | --- | --- |
| `.id` | `str` | Gift ID for `bot.gift()` |
| `.star_count` | `int` | Cost in Stars |
| `.sticker` | `Obj` | Sticker object |
| `.total_count` | `int` | Available count |

```python
gifts = bot.getGifts()
cheapest = min(gifts, key=lambda g: g.star_count)
bot.gift(msg.user_id, cheapest.id)
```

### `bot.gift`

```python
bot.gift(userId, giftId, payForUpgrade=False, text=None)
```

```python
bot.gift(user_id, gift_id)
bot.gift(user_id, gift_id, text="Happy birthday!")
bot.gift(user_id, gift_id, payForUpgrade=True)
```

### Other gift methods

```python
bot.upgradeGift(giftId, keepOriginalDetails=False)
bot.convertGiftToStars(giftId)
bot.transferGift(giftId, userId)
```

- `upgradeGift` upgrades to a unique gift and costs Stars from the bot balance.
- `convertGiftToStars` converts a gift into Stars on the bot balance.
- `transferGift` sends a gift to another user.

## Stars

### Balance

```python
stars = bot.getStarBalance()   # int | None
```

Returns `None` on failure instead of raising.

```python
@bot.onMessage(commands="balance")
def balance(msg):
    stars = bot.getStarBalance()
    if stars is None:
        bot.send(msg, "Could not fetch the balance.")
    else:
        bot.send(msg, f"Bot balance: {stars} Stars")
```

### Transactions

```python
bot.getStarTransactions(offset=0, limit=100)
```

```python
tx = bot.getStarTransactions(limit=10)
for t in tx.transactions:
    print(t.id, t.amount, t.date)
```

### Subscriptions

```python
bot.editStarSubscription(
    userId,
    telegramPaymentChargeId,
    isCanceled,      # True to cancel, False to reactivate
)
```

```python
bot.editStarSubscription(user_id, charge_id, isCanceled=True)
```

### Premium and emoji status

```python
bot.giftPremium(userId, **kwargs)
bot.setEmojiStatus(userId, customEmojiId=None, **kwargs)
```

```python
bot.giftPremium(msg.user_id, month_count=3)

bot.setEmojiStatus(msg.user_id, "5361800828313167901")
bot.setEmojiStatus(msg.user_id)   # clear
```

`setEmojiStatus` requires the user to have granted the bot permission through Business Mode
or a Mini App.

## Payload design

Treat `payload` as your order key, not as JSON. Keep it short and stable:

```text
product:coffee_arabica
product:vip_30d
subscription:pro_monthly
```

Validate it against a server-side catalog in `onCheckout` and `onPayment`. Never trust the
client or the payload alone for price or entitlement; look up the expected price and grant
the entitlement idempotently.

## Payment checklist

- [ ] `stars >= 10`.
- [ ] `payload` identifies a server-side product.
- [ ] `onCheckout` calls exactly one of `accept()` / `reject()`.
- [ ] Delivery happens in `onPayment`, not `onCheckout`.
- [ ] `chargeId` is stored and delivery is idempotent.
- [ ] Refunds are issued with the original `chargeId`.
- [ ] Subscription cancellation stores the original charge ID.
- [ ] Errors are logged; users get a clear message.
