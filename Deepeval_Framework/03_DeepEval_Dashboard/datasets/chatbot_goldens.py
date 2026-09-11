"""Golden test cases for Chatbot evaluation."""

CHATBOT_GOLDENS = [
    {
        "input": "How long do I have to return an item?",
        "expected_output": "Items can be returned within 30 days of delivery in original condition. Return shipping is free for defective items.",
        "context": [
            "Return Policy: Items can be returned within 30 days of delivery in original condition.",
            "Final sale items, personalized items, and underwear are non-returnable.",
            "Return shipping is free for defective items; otherwise the buyer pays return shipping."
        ]
    },
    {
        "input": "How much is express shipping?",
        "expected_output": "Express shipping costs $9.99 and takes 2-3 business days.",
        "context": [
            "Shipping Policy: Express shipping ($9.99): 2-3 business days."
        ]
    },
    {
        "input": "When will I get my refund after returning a hoodie?",
        "expected_output": "Refunds are processed within 7 business days of receiving the returned item to your original payment method.",
        "context": [
            "Refund Policy: Refunds are processed within 7 business days of receiving the returned item.",
            "Refunds are issued to the original payment method."
        ]
    },
    {
        "input": "Can I return a opened pack of underwear?",
        "expected_output": "No, underwear is non-returnable along with final sale and personalized items.",
        "context": [
            "Return Policy: Final sale items, personalized items, and underwear are non-returnable."
        ]
    },
    {
        "input": "What are the specs of the wireless earbuds?",
        "expected_output": "ShopSphere Wireless Earbuds (SKU SP-EARBUDS-01) cost $79, feature Bluetooth 5.3, 30hr battery life, and IPX4 rating.",
        "context": [
            "SKU SP-EARBUDS-01: ShopSphere Wireless Earbuds, $79, Bluetooth 5.3, 30hr battery, IPX4."
        ]
    },
    {
        "input": "How do I reset my password?",
        "expected_output": "You can reset your password at shopsphere.com/account/reset.",
        "context": [
            "ACCOUNT: Reset password at shopsphere.com/account/reset."
        ]
    },
    {
        "input": "Can I return digital goods once downloaded?",
        "expected_output": "Digital goods are non-refundable once downloaded.",
        "context": [
            "REFUND POLICY: Digital goods are non-refundable once downloaded."
        ]
    }
]
