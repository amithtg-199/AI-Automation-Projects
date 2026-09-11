"""Golden test cases for RAG Explorer evaluation."""

RAG_GOLDENS = [
    {
        "input": "What is the return window for defective items?",
        "expected_output": "Items can be returned within 30 days of delivery. For defective items, return shipping is completely free.",
        "expected_context_keywords": ["30 days", "defective", "free"],
        "expected_sources": ["return_policy.md"]
    },
    {
        "input": "How much does express shipping cost and how long does it take?",
        "expected_output": "Express shipping costs $9.99 and takes 2-3 business days inside the US.",
        "expected_context_keywords": ["$9.99", "2-3 business days"],
        "expected_sources": ["shipping_policy.md"]
    },
    {
        "input": "What features does the LED Desk Lamp have?",
        "expected_output": "The ShopSphere LED Desk Lamp (SKU SP-LAMP-LED) costs $39, features 3 brightness levels, and charges via USB-C.",
        "expected_context_keywords": ["SP-LAMP-LED", "$39", "brightness", "USB-C"],
        "expected_sources": ["products.md"]
    },
    {
        "input": "Are international shipping customs fees covered by ShopSphere?",
        "expected_output": "No, customs fees for international shipping are the buyer's responsibility.",
        "expected_context_keywords": ["international", "customs", "buyer's responsibility"],
        "expected_sources": ["shipping_policy.md"]
    },
    {
        "input": "How many days does a standard refund take to process?",
        "expected_output": "Refunds are processed within 7 business days of receiving the returned item to your original payment method.",
        "expected_context_keywords": ["7 business days", "original payment method"],
        "expected_sources": ["refund_policy.md"]
    }
]
