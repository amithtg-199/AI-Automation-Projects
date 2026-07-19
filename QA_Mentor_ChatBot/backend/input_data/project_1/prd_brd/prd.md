Product Requirement Document: Sauce Labs Swag Labs E-commerce Application

1. Introduction

Sauce Labs Swag Labs is a demonstration e-commerce website designed for testing and learning purposes. The application allows users to browse products, add them to a shopping cart, and complete a purchase through a checkout process.

2. Goals

Provide a simple, intuitive interface for users to browse and purchase products.

Demonstrate standard e-commerce functionality including login, product listing, cart management, and checkout.

Serve as a testing ground for automated and manual testing scenarios.

3. Features

3.1 User Authentication

Login Page: Users must authenticate with a valid username and password to access the application.

URL: https://www.saucedemo.com/ 

Credentials:

Username: standard_user (all lowercase)

Password: secret_source (all lowercase)

Validation:

Invalid credentials display an error message: "Epic sadface: Username and password do not match any user in this service"

Locked out user (locked_out_user) displays: "Epic sadface: Sorry, this user has been locked out."

3.2 Product Inventory

Product Listing: After login, users see a grid of available products.

Product Information: Each product displays:

Product image

Product title

Product description

Product price

Actions:

"Add to cart" button for each product

Product titles are clickable (navigate to product detail page in some versions)

Sorting: Users can sort products by:

Name (A to Z)

Name (Z to A)

Price (low to high)

Price (high to low)

Cart Badge: Displays the number of items in the shopping cart in the header.

3.3 Shopping Cart

Access: Clicking the cart icon in the header navigates to the cart page.

Cart Page:

Lists all items added to the cart

For each item:

Product image

Product title

Product description (via link)

Quantity

Price

"Remove" button to delete item from cart

"Continue Shopping" button returns to inventory page

"Checkout" button initiates checkout process

3.4 Checkout Process

Step 1: Checkout Information

Form fields for:

First Name

Last Name

Postal Code

"Cancel" button returns to cart

"Continue" button validates form and proceeds to overview

Validation: All fields are required; missing fields display error messages

Step 2: Checkout Overview

Displays:

List of items in cart with quantities and prices

Subtotal

Tax (8%)

Total

"Cancel" button returns to cart

"Finish" button completes the order

Step 3: Checkout Complete

Confirmation message: "Thank you for your order!"

Dispatch timestamp

"Back Home" button returns to inventory page

3.5 Header Components

Menu Button: In some versions, opens a sidebar menu with:

"All Items"

"About"

"Logout"

"Reset App State"

Shopping Cart Icon: Displays item count and navigates to cart page

Title: "Swag Labs" or similar branding

3.6 Footer

Contains links to:

Sauce Labs website

Social media (Twitter, Facebook, LinkedIn)

4. User Stories

4.1 Authentication

As a user, I want to log in with valid credentials so that I can access the product inventory.

As a user, I want to see an error message when I enter invalid credentials so that I know I need to correct my input.

As a locked out user, I want to see an appropriate error message so that I understand my account is temporarily inaccessible.

4.2 Product Browsing

As a user, I want to view a list of products with images, titles, descriptions, and prices so that I can evaluate items for purchase.

As a user, I want to sort products by name or price so that I can easily find what I'm looking for.

As a user, I want to add products to my cart so that I can purchase them later.

As a user, I want to see a cart badge showing the number of items in my cart so that I can track my selections.

4.3 Cart Management

As a user, I want to view my cart so that I can review the items I've selected.

As a user, I want to remove items from my cart so that I can modify my purchase before checkout.

As a user, I want to continue shopping from the cart page so that I can add more items.

As a user, I want to proceed to checkout from the cart page so that I can complete my purchase.

4.4 Checkout

As a user, I want to enter my shipping information so that the order can be processed.

As a user, I want to see an error if I miss required checkout information so that I can correct it.

As a user, I want to review my order details including taxes and total before submitting so that I can verify the purchase.

As a user, I want to receive a confirmation message after completing my order so that I know it was successful.

As a user, I want to return to the home page after completing an order so that I can shop again.

5. Acceptance Criteria

5.1 Login

Valid credentials (standard_user/secret_source) redirect to inventory page.

Invalid credentials display error message and remain on login page.

Locked out user (locked_out_user) displays locked out message.

Password field masks input for security.

5.2 Inventory

At least 6 products are displayed by default.

Each product shows image, title, description, and price.

"Add to cart" button increments cart badge when clicked.

Sorting options correctly reorder products.

5.3 Cart

Cart badge shows correct number of items.

Cart page lists all items with correct details.

"Remove" button deletes item and updates cart badge.

"Continue Shopping" returns to inventory with cart state preserved.

"Checkout" button enables only when cart has items.

5.4 Checkout

Checkout form validates required fields.

Error messages appear for missing fields.

Order summary shows correct subtotal, tax, and total.

"Finish" button displays completion page.

Completion page shows thank you message and dispatch timestamp.

"Back Home" button returns to inventory with empty cart.

6. Non-Functional Requirements

6.1 Performance

Page load times under 3 seconds on standard broadband.

Interactive elements respond within 200ms.

6.2 Usability

Intuitive navigation with clear labels.

Responsive design for mobile and desktop views.

Accessible color contrast and font sizes.

6.3 Security

Passwords masked in input fields.

No sensitive data stored client-side.

Session-based authentication.

6.4 Compatibility

Compatible with modern browsers: Chrome, Firefox, Safari, Edge.

Responsive layout for mobile devices (touch-friendly buttons).

7. Assumptions and Dependencies

The application is a demonstration site and not intended for production use.

No actual payment processing occurs; orders are simulated.

Product data is static and predefined in the application.

No user account creation or password reset functionality.

Reliance on JavaScript for dynamic rendering and state management.

8. Open Questions

Does the application support internationalization (i18n) for multiple languages?

Are there additional user roles beyond standard_user (e.g., problem_user, performance_user)?

What specific error conditions are simulated for problem_user and performance_user?

