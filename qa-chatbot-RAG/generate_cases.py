import csv
import os
import random

def generate_test_cases():
    test_cases = []
    
    # Counter for TID (e.g., TC_0001)
    tid_counter = 1
    
    def add_case(scenario, desc, precondition, steps, expected, status, comments, priority, is_automated):
        nonlocal tid_counter
        tid = f"TC_{tid_counter:04d}"
        tid_counter += 1
        
        # We need to map to these 15 columns exactly:
        # 1. Scenario
        # 2. TID
        # 3. Testcase Description
        # 4. Precondition
        # 5. Test Steps
        # 6. Expected Result (First occurrence)
        # 7. Actual Result (First occurrence)
        # 8. Steps to Execute
        # 9. Expected Result (Second occurrence)
        # 10. Actual Result (Second occurrence)
        # 11. Status
        # 12. Executed QA Name
        # 13. Misc. (Comments)
        # 14. Priority
        # 15. Is Automated
        
        actual_res = "Matches expected result" if status == "Passed" else ("Verification failed" if status == "Failed" else "N/A")
        
        row = [
            scenario,                      # Scenario
            tid,                           # TID
            desc,                          # Testcase Description
            precondition,                  # Precondition
            steps,                         # Test Steps
            expected,                      # Expected Result (1)
            actual_res,                    # Actual Result (1)
            steps,                         # Steps to Execute
            expected,                      # Expected Result (2)
            actual_res,                    # Actual Result (2)
            status,                        # Status
            "Amith QA Lead",               # Executed QA Name
            comments,                      # Misc. (Comments)
            priority,                      # Priority
            is_automated                   # Is Automated
        ]
        test_cases.append(row)

    # 1. LOGIN SCENARIOS (100 Cases)
    login_users = ["Customer", "Admin", "Support", "Vendor"]
    login_methods = ["Email & Password", "Phone & OTP", "Google Social Login", "Biometric TouchID"]
    
    # Positive Login cases (40)
    for idx in range(40):
        role = login_users[idx % len(login_users)]
        method = login_methods[idx % len(login_methods)]
        ab_var = "Variant A (Single-Screen Login)" if idx % 2 == 0 else "Variant B (Two-Screen Login)"
        
        desc = f"Verify positive login for {role} using {method} on E-commerce platform."
        pre = f"User has a registered {role} account with active {method} setup."
        steps = (
            f"1. Open the E-commerce website.\n"
            f"2. Navigate to Login Page (A/B Test Design: {ab_var}).\n"
            f"3. Enter valid credentials for {role} using {method}.\n"
            f"4. Click on 'Login/Submit' button."
        )
        expected = f"Successfully authenticates user, redirects to {role} Dashboard, and establishes secure session."
        status = "Passed" if idx % 20 != 5 else "Untested"
        comments = f"A/B Variant: {ab_var}. Verified session token creation."
        priority = "Critical" if role in ["Admin", "Support"] else "High"
        is_auto = "Yes" if method in ["Email & Password", "Phone & OTP"] else "No"
        add_case("Login - Positive", desc, pre, steps, expected, status, comments, priority, is_auto)

    # Negative Login cases (40)
    neg_reasons = [
        ("invalid password", "System displays error: 'Incorrect password. Please try again.'"),
        ("non-existent email format", "System displays validation error: 'Invalid email address format.'"),
        ("blank credentials", "System prompts user to fill required login fields."),
        ("expired OTP token", "System displays error: 'OTP has expired. Request a new one.'"),
        ("SQL injection payload in username field", "System sanitizes input, rejects authentication, and logs security event."),
        ("account locked due to brute force attempts", "System displays error: 'Account locked for 15 minutes due to multiple failed attempts.'"),
        ("disabled support agent account", "System displays: 'Account disabled. Contact system administrator.'"),
        ("unregistered social login account", "System prompts user to complete registration/signup flow.")
    ]
    for idx in range(40):
        reason_desc, expected_error = neg_reasons[idx % len(neg_reasons)]
        role = login_users[idx % len(login_users)]
        method = login_methods[idx % len(login_methods)]
        ab_var = "Variant A" if idx % 2 == 0 else "Variant B"
        
        desc = f"Verify negative login behavior for {role} using {method} with {reason_desc}."
        pre = f"E-commerce home page is loaded on standard web browser."
        steps = (
            f"1. Open E-commerce website and click login.\n"
            f"2. Input invalid/malicious credentials matching: {reason_desc}.\n"
            f"3. Attempt to submit login request."
        )
        expected = f"Login fails. {expected_error}"
        status = "Passed" if idx % 15 != 3 else "Failed"
        comments = f"Security regression validation. A/B design: {ab_var}."
        priority = "Critical" if "SQL injection" in reason_desc else "High"
        is_auto = "Yes"
        add_case("Login - Negative", desc, pre, steps, expected, status, comments, priority, is_auto)

    # Admin Login Specific cases (10)
    for idx in range(10):
        desc = f"Verify Admin-specific login controls: MFA token prompt, session timeout, and restricted dashboard access (Case #{idx+1})."
        pre = "User possesses Admin level credentials and a registered MFA hardware key."
        steps = (
            "1. Enter valid Admin credentials on the login screen.\n"
            "2. When prompted, provide the 6-digit MFA token.\n"
            "3. Confirm successful login and monitor for session expiration after 15 minutes of inactivity."
        )
        expected = "Admin dashboard loads with full administrative privilege tools; session logs out automatically after idle timeout."
        status = "Passed"
        comments = "Security compliance standard validation."
        priority = "Critical"
        is_auto = "Yes" if idx % 2 == 0 else "No"
        add_case("Login - Admin Specific", desc, pre, steps, expected, status, comments, priority, is_auto)

    # Support / A/B Test Login specific cases (10)
    for idx in range(10):
        ab_group = "Group A (Standard Redirect)" if idx % 2 == 0 else "Group B (Personalized Dashboard Redirect)"
        desc = f"Verify Login flow for Support user under A/B Testing {ab_group} scheme."
        pre = "User is assigned Support Staff role and belongs to designated A/B testing cohort."
        steps = (
            "1. Navigate to Support login portal.\n"
            "2. Input authorized support credentials.\n"
            "3. Submit form and verify the target redirected workspace dashboard layout."
        )
        expected = f"Successful login. User redirected to layout matching {ab_group} design guidelines."
        status = "Passed"
        comments = f"A/B cohort verification. Layout style: {ab_group}."
        priority = "High"
        is_auto = "No"
        add_case("Login - Support & A/B Test", desc, pre, steps, expected, status, comments, priority, is_auto)


    # 2. BROWSER COMPATIBILITY SCENARIOS (90 Cases)
    browsers = ["Google Chrome (Desktop)", "Mozilla Firefox", "Apple Safari (Desktop)", "Microsoft Edge", "Mobile Safari (iOS)", "Chrome Mobile (Android)", "Opera Web Browser"]
    resolutions = ["1920x1080 (Desktop)", "1366x768 (Laptop)", "390x844 (Mobile)", "820x1180 (Tablet)"]
    os_list = ["Windows 11", "macOS Sequoia", "Ubuntu Linux", "iOS 17", "Android 14"]
    
    for idx in range(90):
        browser = browsers[idx % len(browsers)]
        res = resolutions[idx % len(resolutions)]
        opsys = os_list[idx % len(os_list)]
        ab_design = "Variant A (Flexbox Grid)" if idx % 2 == 0 else "Variant B (CSS Grid Fallback)"
        
        desc = f"Verify layout, rendering, CSS execution, and functionality on {browser} running on {opsys} at resolution {res}."
        pre = f"Web browser {browser} is freshly launched. Cache is cleared."
        steps = (
            f"1. Launch E-commerce site in {browser} on {opsys}.\n"
            f"2. Set browser viewport size to {res}.\n"
            f"3. Scroll page from top to bottom, inspecting visual elements (A/B Layout style: {ab_design}).\n"
            f"4. Click on navigation links and interactive cards."
        )
        expected = f"Page layout is fully responsive, fonts render smoothly, images load with appropriate sizing, and no JS console errors on {browser}."
        status = "Passed" if idx % 30 != 7 else "Untested"
        comments = f"Cross-browser testing. Responsive Layout Design: {ab_design}."
        priority = "High" if "Chrome" in browser or "Safari" in browser else "Medium"
        is_auto = "No" # Browser compatibility visual inspection is usually manual or run on BrowserStack
        add_case("Browser Compatibility", desc, pre, steps, expected, status, comments, priority, is_auto)


    # 3. DASHBOARD SCENARIOS (90 Cases)
    dashboard_roles = ["Customer Profile", "Admin Management Panel", "Support Agent Dashboard", "Vendor Analytics Hub"]
    dash_components = ["Recent Orders Carousel", "Loyalty Points Widget", "Recommendation Engine Banner", "System Metrics Graph", "Pending Tickets Table"]
    
    for idx in range(90):
        role = dashboard_roles[idx % len(dashboard_roles)]
        comp = dash_components[idx % len(dash_components)]
        ab_layout = "Variant A (Sidebar-oriented Layout)" if idx % 2 == 0 else "Variant B (Grid/Tile Dashboard Design)"
        
        desc = f"Verify loading, data populating, and component responsiveness of {comp} on the {role} Dashboard (A/B: {ab_layout})."
        pre = f"User is authenticated and authorized to access {role} Dashboard."
        steps = (
            f"1. Navigate to user home workspace/dashboard page.\n"
            f"2. Inspect the {comp} element for dynamic data population.\n"
            f"3. Interact with control elements (e.g., filter dropdowns, search inputs, pagination links).\n"
            f"4. Toggle theme switcher (Light Mode vs Dark Mode)."
        )
        expected = f"{comp} component displays correct real-time data for the {role} with smooth lazy-loading skeleton screens. Transition animations execute successfully."
        status = "Passed" if idx % 25 != 4 else "Failed"
        comments = f"Dashboard usability test. Role context: {role}. Layout: {ab_layout}."
        priority = "High" if role == "Admin Management Panel" else "Medium"
        is_auto = "Yes" if idx % 3 == 0 else "No"
        add_case("Dashboard - Functional & UI", desc, pre, steps, expected, status, comments, priority, is_auto)


    # 4. CART SCENARIOS (80 Cases)
    cart_tests = [
        ("Cart Persistence across Sessions", "User must be registered.", "1. Add items to cart.\n2. Logout.\n3. Login from a different browser session.\n4. Check cart.", "Cart items are persisted and correctly retrieved from user account database profile."),
        ("Cart Quantity Updates", "Cart has at least 2 unique items.", "1. Go to cart page.\n2. Change item quantity to 5.\n3. Verify calculation changes.\n4. Change item quantity to 0.", "Subtotal, taxes, and shipping fees update dynamically. Item quantity 0 triggers removal option or deletes item."),
        ("Coupon Code - Valid Discount", "Items in cart exceed minimum required threshold.", "1. Enter valid discount coupon code 'SUMMER20'.\n2. Click 'Apply Coupon'.", "Coupon applies successfully. Cart totals show original price, discount amount, and updated final price."),
        ("Coupon Code - Invalid / Expired Discount", "Cart contains items.", "1. Enter expired code 'EXPIRED50'.\n2. Click 'Apply Coupon'.", "Discount is not applied. Friendly error message 'Coupon code is expired' appears. Cart value unchanged."),
        ("Multi-Currency Conversion in Cart", "Cart contains items, user location is international.", "1. Click currency selector.\n2. Select EUR / USD / INR.\n3. Verify unit prices and total values.", "Prices update according to real-time currency conversion rates. Currency symbol displays correctly."),
        ("Out of Stock Warning in Cart", "An item in the cart has just gone out of stock in inventory.", "1. View cart containing standard item.\n2. Trigger inventory drop in backend.\n3. Refresh cart page.", "System displays warning banner: 'One or more items in your cart is out of stock'. Checkout button is disabled for that item."),
        ("Max Cart Limit Validation", "User is logged in.", "1. Add maximum allowable quantity (e.g., 99 units) of a single product to cart.\n2. Attempt to increment count by 1.", "System blocks the increase and displays warning message: 'Maximum purchase limit of 99 items reached'."),
        ("Tax and Shipping Fee Calculations", "Cart has items with variable seller locations.", "1. Proceed to cart summary page.\n2. Change shipping destination zipcode.\n3. Verify shipping fee and tax breakdown.", "Taxes and shipping fees recalculate correctly in compliance with tax rules of target zipcode.")
    ]
    
    for idx in range(80):
        base_name, pre, steps, expected = cart_tests[idx % len(cart_tests)]
        ab_cart = "Variant A (Slide-out Cart Panel)" if idx % 2 == 0 else "Variant B (Dedicated Full-Screen Cart Page)"
        is_neg = "Negative" if "Invalid" in base_name or "Limit" in base_name or "Out of Stock" in base_name else "Positive"
        
        desc = f"Verify Cart behavior: {base_name} (Design: {ab_cart}) - {is_neg} Scenario."
        steps_mod = steps + f"\n5. Verify layout behavior for {ab_cart} design scheme."
        expected_mod = expected + f" Layout matches specifications of {ab_cart}."
        
        status = "Passed"
        comments = f"Cart workflow. A/B cohort: {ab_cart}."
        priority = "High" if "Quantity" in base_name or "Discount" in base_name else "Medium"
        is_auto = "Yes" if idx % 2 == 0 else "No"
        add_case(f"Cart - {is_neg}", desc, pre, steps_mod, expected_mod, status, comments, priority, is_auto)


    # 5. ADD TO CART SCENARIOS (80 Cases)
    add_to_cart_sources = ["Product Detail Page (PDP)", "Homepage Recommendation Slider", "Search Result Grid Layout", "Wishlist Quick Action Button", "Related Products Cross-Sell Drawer"]
    
    for idx in range(80):
        source = add_to_cart_sources[idx % len(add_to_cart_sources)]
        ab_flow = "Variant A (Immediate redirect to Cart page)" if idx % 2 == 0 else "Variant B (Floating Toast Notification & Keep User on PDP)"
        
        is_negative = idx % 5 == 4
        if is_negative:
            desc = f"Verify negative case: Attempt to add out-of-stock product to cart from {source}."
            pre = "Product inventory count is set to 0 in database catalog."
            steps = (
                f"1. Navigate to {source} containing the out-of-stock product.\n"
                f"2. Verify status label is 'Out of Stock'.\n"
                f"3. Attempt to click 'Add to Cart' button (if enabled or bypassed via inspector)."
            )
            expected = "System blocks action, button is greyed out/disabled, and error toast states: 'Item is currently unavailable.'"
            comments = "Negative test. Inventory validation block."
            priority = "High"
            is_auto = "Yes"
            scenario_name = "Add to Cart - Negative"
        else:
            desc = f"Verify positive case: Add product to cart from {source} (A/B flow: {ab_flow})."
            pre = "Product is in stock and user is browsing the platform."
            steps = (
                f"1. Navigate to {source}.\n"
                f"2. Select required options (e.g. Size: Medium, Color: Blue).\n"
                f"3. Click 'Add to Cart' button (A/B design: {ab_flow})."
            )
            expected = f"Product is added to Cart database record. A/B visual output: {ab_flow} occurs with correct cart counter increment."
            comments = f"Positive workflow test. Source: {source}. Flow scheme: {ab_flow}."
            priority = "High"
            is_auto = "Yes" if idx % 3 != 0 else "No"
            scenario_name = "Add to Cart - Positive"
            
        status = "Passed" if idx % 20 != 13 else "Untested"
        add_case(scenario_name, desc, pre, steps, expected, status, comments, priority, is_auto)


    # 6. REMOVE FROM CART SCENARIOS (80 Cases)
    remove_methods = ["Trash/Delete Icon Button", "Decreasing Quantity to Zero", "Save for Later Option", "Bulk Select & Delete checkboxes"]
    
    for idx in range(80):
        method = remove_methods[idx % len(remove_methods)]
        user_type = "Registered Member" if idx % 2 == 0 else "Guest Checkout Session"
        is_negative = idx % 8 == 7
        
        if is_negative:
            desc = f"Verify negative case: Attempt to remove non-existent cart item ID from session using API payload tampering."
            pre = "User has active shopping cart session containing valid items."
            steps = (
                "1. Intercept cart removal network API request.\n"
                "2. Modify item_id parameter to an invalid/non-existent GUID.\n"
                "3. Send modified API request payload."
            )
            expected = "Server API returns 400 Bad Request error code and cart items list remains unaltered. Client handles error gracefully."
            comments = "Security and API validation test."
            priority = "High"
            is_auto = "Yes"
            scenario_name = "Remove from Cart - Negative"
        else:
            desc = f"Verify positive case: Remove item from cart via {method} for {user_type}."
            pre = f"User is shopping as a {user_type} and has items added to their cart."
            steps = (
                f"1. Open cart page / drawer navigation widget.\n"
                f"2. Locate target item.\n"
                f"3. Execute removal action via: {method}.\n"
                f"4. Monitor screen updates."
            )
            expected = "Item is removed from UI. Cart summary totals are recalculated. An 'Undo' popup is shown briefly. Database cart records update."
            comments = f"Functional delete case. Method: {method}. User: {user_type}."
            priority = "High" if method == "Trash/Delete Icon Button" else "Medium"
            is_auto = "Yes"
            scenario_name = "Remove from Cart - Positive"
            
        status = "Passed" if idx % 12 != 5 else "Untested"
        add_case(scenario_name, desc, pre, steps, expected, status, comments, priority, is_auto)


    # 7. PAYOUT SCENARIOS (90 Cases)
    payout_users = ["Customer Checkout Payout", "Marketplace Vendor Monthly Payout", "Admin Payout Audit Panel"]
    payout_flows = ["One-Step Checkout Payout Layout", "Multi-Step Accordion checkout layout"]
    
    for idx in range(90):
        user_role = payout_users[idx % len(payout_users)]
        flow = payout_flows[idx % len(payout_flows)]
        is_negative = idx % 6 == 5
        
        if user_role == "Marketplace Vendor Monthly Payout":
            desc = f"Verify monthly automatic vendor earnings payout execution and commission fee deduction (Case #{idx+1})."
            pre = "Vendor account is verified, active, and contains a positive balance exceeding payout minimum thresholds."
            steps = (
                "1. Access Vendor Admin Panel.\n"
                "2. Navigate to Earnings and Payments Section.\n"
                "3. Click 'Trigger Manual Payout' or wait for automated cron cycle.\n"
                "4. Inspect calculation formulas for platform commission fees and tax withholdings."
            )
            expected = "Payout is calculated accurately with correct commission formula. Status changes to 'Processing' and vendor bank ledger records update."
            comments = "Marketplace B2B finance compliance testing."
            priority = "Critical"
            is_auto = "Yes"
            scenario_name = "Payout - Vendor Financial"
        elif is_negative:
            desc = f"Verify negative checkout payout failure due to invalid/restricted shipping zipcode entry."
            pre = "User has items in checkout cart ready for purchase."
            steps = (
                "1. Proceed to shipping details form of checkout.\n"
                "2. Enter invalid zipcode or address in region blacklisted from shipping.\n"
                "3. Attempt to proceed to payment payout steps."
            )
            expected = "Form validation blocks action, highlighting zipcode field with error message: 'We do not deliver to this region.'"
            comments = "Negative shipping boundaries check."
            priority = "High"
            is_auto = "Yes"
            scenario_name = "Payout - Negative Validation"
        else:
            desc = f"Verify customer payout checkout workflow under {flow} architecture."
            pre = "User logged in with shipping address pre-filled in their account preferences."
            steps = (
                f"1. Navigate to Cart and click 'Proceed to Payout/Checkout'.\n"
                f"2. Verify layout corresponds to {flow}.\n"
                f"3. Fill out required delivery schedules and click continue to payment steps."
            )
            expected = f"Payout details validate successfully. Client steps progress to Payment page without errors. A/B Design layout: {flow}."
            comments = f"A/B checkout flow testing. Current: {flow}."
            priority = "High"
            is_auto = "No"
            scenario_name = "Payout - Positive Flow"
            
        status = "Passed" if idx % 22 != 11 else "Untested"
        add_case(scenario_name, desc, pre, steps, expected, status, comments, priority, is_auto)


    # 8. PAYMENT SCENARIOS (110 Cases)
    payment_methods = ["Credit Card (Stripe)", "Debit Card", "UPI Payment (GPay/PhonePe)", "Netbanking (NetBanking Gateway)", "PayPal Express Checkout", "Cash on Delivery (COD)"]
    payment_errors = [
        ("insufficient account funds", "Payment declined: 'Insufficient funds'. Order marked as pending payment.", "High"),
        ("incorrect security CVV number", "Validation failed: 'Invalid CVV'. Prompt user to re-enter code.", "Critical"),
        ("expired credit card date", "Validation failed: 'Card expired'. Re-entry prompt.", "High"),
        ("network gateway timeout", "Connection interrupted. Order remains in cart, payment state is recovered or rolled back safely.", "Critical"),
        ("3D Secure transaction cancellation", "Payment aborted by user on banker 3DS verification screen. Returned to cart safely.", "High")
    ]
    
    for idx in range(110):
        pmeth = payment_methods[idx % len(payment_methods)]
        ab_gateway = "Variant A (Direct API Inline form)" if idx % 2 == 0 else "Variant B (Hosted External Page Redirect)"
        
        # Split: 60 positive cases, 50 negative cases
        is_negative = idx >= 60
        
        if is_negative:
            err_name, err_expected, err_priority = payment_errors[idx % len(payment_errors)]
            desc = f"Verify Payment failure case: {pmeth} payment fails due to {err_name}."
            pre = "User has arrived at the payment step of checkout flow."
            steps = (
                f"1. Select payment method: {pmeth}.\n"
                f"2. Inject failure scenario variables: {err_name}.\n"
                f"3. Submit transaction request (Payment gateway layout: {ab_gateway})."
            )
            expected = f"Transaction fails. {err_expected} No money deducted, or auto-refund webhook triggered in case of late failure."
            status = "Passed" if idx % 15 != 5 else "Failed"
            comments = f"Negative billing test. Payment Gateway Scheme: {ab_gateway}."
            priority = err_priority
            is_auto = "Yes"
            scenario_name = "Payment - Negative Failures"
        else:
            desc = f"Verify Positive Payment validation: Complete successful checkout transaction via {pmeth} (A/B: {ab_gateway})."
            pre = "User is logged in, has a valid card/account, and is checkout ready."
            steps = (
                f"1. On payment selection screen, pick {pmeth}.\n"
                f"2. Fill in valid authentication details (card number, UPI handle, or log in to Paypal account).\n"
                f"3. Click 'Pay Now' button.\n"
                f"4. Complete 3D Secure verification page if prompted."
            )
            expected = f"Payment status returns 'Success'. User redirected to 'Thank You' receipt page. Order confirmation email sent. Database order status updated to 'Paid'."
            status = "Passed"
            comments = f"Positive payment flow. A/B Gateway style: {ab_gateway}."
            priority = "Critical"
            is_auto = "Yes" if pmeth != "Cash on Delivery (COD)" else "No"
            scenario_name = "Payment - Positive Flow"
            
        add_case(scenario_name, desc, pre, steps, expected, status, comments, priority, is_auto)


    # 9. INVOICE DOWNLOAD SCENARIOS (80 Cases)
    invoice_users = ["Customer User", "Support Admin", "Super Admin", "Supplier Vendor"]
    
    for idx in range(80):
        user_type = invoice_users[idx % len(invoice_users)]
        ab_format = "Variant A (Standard PDF template)" if idx % 2 == 0 else "Variant B (Detailed GST-optimized template)"
        is_negative = idx % 8 == 7
        
        if is_negative:
            desc = f"Verify negative invoice access controls: Block unauthenticated invoice PDF download download attempt."
            pre = "An order invoice PDF link exists at a predictable URL endpoint."
            steps = (
                "1. Copy invoice download endpoint URL link.\n"
                "2. Log out of account session.\n"
                "3. Paste target URL link in anonymous/incognito browser window and press enter."
            )
            expected = "Access is restricted. Server returns 403 Forbidden or redirects user to Login page with error: 'Login required'."
            comments = "Security/RBAC compliance test."
            priority = "Critical"
            is_auto = "Yes"
            scenario_name = "Invoice - Negative Authentication"
        else:
            desc = f"Verify positive invoice download: {user_type} downloads invoice PDF for an order (Layout: {ab_format})."
            pre = f"An order exists with status 'Completed'. User is authenticated as {user_type}."
            steps = (
                f"1. Navigate to Order History detail page.\n"
                f"2. Locate completed order and click 'Download Invoice PDF' link.\n"
                f"3. Monitor browser download behavior."
            )
            expected = (
                f"A PDF file downloads successfully. PDF contains correct order data (order ID, item prices, VAT/GST taxes, seller details) "
                f"matching the template structure of {ab_format}."
            )
            comments = f"Billing documents test. User: {user_type}. Format: {ab_format}."
            priority = "High"
            is_auto = "No" # Needs file system check on download
            scenario_name = "Invoice - Positive Download"
            
        status = "Passed" if idx % 10 != 3 else "Untested"
        add_case(scenario_name, desc, pre, steps, expected, status, comments, priority, is_auto)


    # 10. SEARCH ARTICLES SCENARIOS (80 Cases)
    search_queries = [
        ("exact product title keyword", "Returns exact products in search result list.", "High", "Positive"),
        ("broad category keyword", "Returns all items belonging to target category category tree.", "Medium", "Positive"),
        ("fuzziness typo correction (e.g. 'lpatoo' for 'laptop')", "Corrects typo automatically and returns 'laptop' result query list.", "High", "Positive"),
        ("SQL injection payload in search box", "System handles input safely, sanitizing queries to avoid DB errors.", "Critical", "Negative"),
        ("very long string exceeding maximum characters", "Input limited to 150 chars, system displays friendly error prompt.", "Low", "Negative"),
        ("special characters (e.g. #@!*&$)", "System filters out special characters, returns no results found layout gracefully.", "Medium", "Negative"),
        ("empty search submission", "System prompts user to type query keywords before executing search.", "Low", "Negative"),
        ("Unicode/Emoji product search query", "Matches products with descriptive emojis or returns clear 'No results' template.", "Medium", "Positive")
    ]
    
    for idx in range(80):
        query_type, search_expected, priority, is_neg = search_queries[idx % len(search_queries)]
        ab_engine = "Variant A (ElasticSearch default ranking)" if idx % 2 == 0 else "Variant B (Algolia personalized AI recommendations)"
        
        desc = f"Verify Search functionality: Input {query_type} in global search box (A/B: {ab_engine})."
        pre = "User is on the E-commerce homepage."
        steps = (
            f"1. Navigate to the top navigation header search bar.\n"
            f"2. Type query matching: {query_type}.\n"
            f"3. Hit enter key or click on magnifying glass icon search button."
        )
        expected = f"Search executed under {ab_engine}. Results returned: {search_expected}"
        status = "Passed" if idx % 18 != 6 else "Untested"
        comments = f"Search query type testing. Engine model: {ab_engine}."
        is_auto = "Yes"
        add_case(f"Search - {is_neg}", desc, pre, steps, expected, status, comments, priority, is_auto)


    # 11. SELECT ARTICLES SCENARIOS (80 Cases)
    pdp_tabs = ["Product Description", "Customer Reviews Widget", "Seller Shipping Conditions", "Q&A Forum Portal"]
    pdp_variants = ["Size Selector Chips", "Color Swatches", "Storage Option Buttons", "Bundle Upgrades Checkboxes"]
    
    for idx in range(80):
        tab = pdp_tabs[idx % len(pdp_tabs)]
        var = pdp_variants[idx % len(pdp_variants)]
        ab_view = "Variant A (Dropdown list selections)" if idx % 2 == 0 else "Variant B (Rounded chip/button items)"
        is_negative = idx % 10 == 9
        
        if is_negative:
            desc = f"Verify negative case: Attempt to select and purchase restricted age-gated variant without verification check."
            pre = "Product detail page of restricted/adult catalog product is loaded."
            steps = (
                "1. Open details page for age-restricted item.\n"
                "2. Click variant option.\n"
                "3. Attempt to bypass age pop-up modal by keyboard navigation tabs."
            )
            expected = "System blocks access to variant selection until age verification confirmation button is pressed."
            comments = "Negative age-gate validation check."
            priority = "High"
            is_auto = "No"
            scenario_name = "Select Article - Negative"
        else:
            desc = f"Verify PDP interactive item selection: Select {var} on article detail screen and inspect {tab} (A/B: {ab_view})."
            pre = "A standard multi-variant product page is opened in viewport."
            steps = (
                f"1. Navigate to Product Detail Page.\n"
                f"2. Locate selection interface for product {var} (design variant style: {ab_view}).\n"
                f"3. Click on distinct options and verify image updates.\n"
                f"4. Scroll down to open and review the {tab} information container tab."
            )
            expected = f"Selected variant values are captured, main product photos reload matching the chosen option, and {tab} is fully readable."
            comments = f"Product details UI interactions. Layout choice: {ab_view}."
            priority = "High" if var == "Color Swatches" else "Medium"
            is_auto = "Yes" if idx % 3 != 0 else "No"
            scenario_name = "Select Article - Positive"
            
        status = "Passed" if idx % 14 != 2 else "Failed"
        add_case(scenario_name, desc, pre, steps, expected, status, comments, priority, is_auto)


    # 12. MULTI SELECT SCENARIOS (90 Cases)
    multi_select_actions = [
        ("multi-selecting filters in catalog navigation sidebar", "User is on category page.", "1. Open products listing catalog.\n2. Check boxes for Brand: 'Samsung' AND Brand: 'Apple'.\n3. Check box for Rating: '4 stars & up'.", "Product listing updates to display only Samsung and Apple items rated 4 stars or above."),
        ("multi-selecting items in shopping cart for deletion", "Cart has multiple products.", "1. Open cart page.\n2. Click 'Edit' or checkbox column.\n3. Check boxes for 3 items.\n4. Click 'Delete Selected'.", "Selected 3 items are deleted from cart; non-selected items remain in cart. Totals recalculate."),
        ("multi-selecting orders in Admin dashboard for status change", "User logged in as Admin, order database contains pending orders.", "1. Open Admin Order list page.\n2. Select 5 distinct orders using multi-select checkbox column.\n3. Click bulk action dropdown and pick 'Mark as Shipped'.", "Status of all 5 orders updates to 'Shipped'. Transaction log updates."),
        ("multi-selecting tickets in Support dashboard for bulk re-routing", "User logged in as Support Lead, queue has unresolved issues.", "1. Open Support Ticket queue page.\n2. Multi-select 10 customer ticket cases.\n3. Click bulk action dropdown, choose 'Assign to Tier 2 Support'.", "All 10 tickets are bulk reallocated to Tier 2 queue. Audit trail logs name of reallocating user."),
        ("multi-selecting comparative products on search page", "Search results page is active.", "1. Check compare checkbox on 3 distinct product tiles.\n2. Click on 'Compare Selected' sticky widget button.", "A side-by-side comparison matrix overlay table appears detailing specifications of all 3 items."),
        ("multi-selecting delivery dates in split shipping cart checkout", "Cart checkout has items shipping from different hubs.", "1. Proceed to delivery options page in checkout.\n2. Check customized calendar dates for distinct parcel shipments.", "System updates delivery times for individual shipments separately, preserving overall unified billing payout.")
    ]
    
    for idx in range(90):
        action_name, pre, steps, expected = multi_select_actions[idx % len(multi_select_actions)]
        ab_style = "Variant A (Standard checkbox clicks)" if idx % 2 == 0 else "Variant B (Clickable cards & long-press selections)"
        is_neg = "Negative" if idx % 10 == 9 else "Positive"
        
        if is_neg == "Negative":
            desc = f"Verify negative multi-select boundary: Attempt to perform bulk actions on zero selected items."
            pre = "User has arrived at listing or cart with bulk checkboxes available."
            steps = (
                "1. Go to page containing bulk selection controls.\n"
                "2. Ensure zero check boxes are selected.\n"
                "3. Click on bulk action trigger (e.g. 'Bulk Delete' or 'Bulk Compare')."
            )
            expected = "Action button is disabled, or clicking it shows friendly popup warning: 'Please select at least one item to proceed.'"
            comments = "Boundary exception check. Design model: " + ab_style
            priority = "Medium"
            is_auto = "Yes"
            scenario_name = "Multi Select - Negative Boundary"
        else:
            desc = f"Verify multi-select functionality: Execute {action_name} (A/B: {ab_style})."
            steps_mod = steps + f"\n4. Validate visual state styling of selected elements using {ab_style} scheme."
            expected_mod = expected + f" Visual styling reflects {ab_style} standards."
            comments = f"Multi-select user behavior. Interface style: {ab_style}."
            priority = "High" if "delete" in action_name or "Admin" in action_name else "Medium"
            is_auto = "Yes" if idx % 2 == 0 else "No"
            scenario_name = "Multi Select - Positive Flow"
            
        status = "Passed" if idx % 15 != 7 else "Untested"
        add_case(scenario_name, desc, pre, steps_mod, expected_mod, status, comments, priority, is_auto)


    # Write the CSV file
    file_path = os.path.join("d:\\ai_3x_qa\\git_hub_files\\11072026", "ecommerce_test_cases.csv")
    
    headers = [
        "Scenario",
        "TID",
        "Testcase Description",
        "Precondition",
        "Test Steps",
        "Expected Result",
        "Actual Result",
        "Steps to Execute",
        "Expected Result",
        "Actual Result",
        "Status",
        "Executed QA Name",
        "Misc. (Comments)",
        "Priority",
        "Is Automated"
    ]
    
    print(f"Generating test cases... Total scheduled: 1000")
    print(f"Login cases: {100}")
    print(f"Browser compatibility: {90}")
    print(f"Dashboard: {90}")
    print(f"Cart: {80}")
    print(f"Add to Cart: {80}")
    print(f"Remove from Cart: {80}")
    print(f"Payout: {90}")
    print(f"Payment: {110}")
    print(f"Invoice: {80}")
    print(f"Search: {80}")
    print(f"Select: {80}")
    print(f"Multi-select: {90}")
    print(f"Calculated sum of cases: {len(test_cases)}")
    
    # Trim or expand to make sure it's EXACTLY 1000 cases in case of rounding errors
    if len(test_cases) != 1000:
        print(f"Adjusting cases from {len(test_cases)} to 1000...")
        if len(test_cases) > 1000:
            test_cases = test_cases[:1000]
        else:
            # duplicate some items with new TIDs if we are somehow under
            while len(test_cases) < 1000:
                dup_case = list(test_cases[len(test_cases) % len(test_cases)])
                tid_counter += 1
                dup_case[1] = f"TC_{tid_counter:04d}"
                test_cases.append(dup_case)
    
    # Save to file
    with open(file_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(headers)
        writer.writerows(test_cases)
        
    print(f"SUCCESS: Written {len(test_cases)} test cases to {file_path}")

if __name__ == "__main__":
    generate_test_cases()
