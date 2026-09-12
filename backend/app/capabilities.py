POLICY_READ = "policy:read"
INVENTORY_READ = "inventory:read"
ORDER_CREATE = "order:create"
EMAIL_SEND = "email:send"

ALL_CAPABILITIES = frozenset({POLICY_READ, INVENTORY_READ, ORDER_CREATE, EMAIL_SEND})

ALLOWED_TOOLS = frozenset(
    {
        "retrieve_policy",
        "lookup_inventory",
        "draft_order",
        "execute_order",
        "draft_email",
        "execute_email",
    }
)
