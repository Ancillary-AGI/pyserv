#!/usr/bin/env python3
"""
Pyserv  Enhanced Widgets Demo

This script demonstrates the new advanced widgets including:
- Theme System (AUTO theme that follows current application theme)
- Date and Time widgets (RichDateTime, RichDate, RichTime)
- File Management widgets (RichFileManager)
- Commerce widgets (RichPrice, RichQuantity, RichProductCard, RichShoppingCart)
- Enhanced widgets (RichText, RichSelect)
"""

from datetime import datetime, date, time
from pyserv.widgets import (
    # Date and Time Widgets
    RichDateTime, RichDate, RichTime,
    # File Management Widgets
    RichFile, RichFileManager,
    # Commerce Widgets
    RichPrice, RichQuantity, RichProductCard, RichShoppingCart,
    # Enhanced Widgets
    RichText, RichSelect,
    # Theme Management
    ThemeManager, WidgetTheme
)


def demo_date_time_widgets():
    """Demonstrate date and time widgets"""
    print("🕐 Date and Time Widgets Demo")
    print("=" * 40)

    # Rich DateTime Picker
    datetime_picker = RichDateTime(
        name='event_datetime',
        label='Event Date & Time',
        value=datetime(2025, 12, 25, 15, 30, 0),
        date_format='YYYY-MM-DD',
        time_format='HH:mm:ss',
        show_date=True,
        show_time=True,
        show_seconds=True,
        timezone='UTC',
        locale='en',
        theme='blue',
        help_text='Select the date and time for your event'
    )

    print("RichDateTime Widget:")
    print(datetime_picker.render())
    print()

    # Rich Date Picker
    date_picker = RichDate(
        name='birth_date',
        label='Birth Date',
        value=date(1990, 1, 1),
        date_format='MM/DD/YYYY',
        min_date='1900-01-01',
        max_date='2010-12-31',
        locale='en',
        theme='green'
    )

    print("RichDate Widget:")
    print(date_picker.render())
    print()

    # Rich Time Picker
    time_picker = RichTime(
        name='meeting_time',
        label='Meeting Time',
        value=time(14, 30),
        time_format='HH:mm',
        show_seconds=False,
        step=30,
        theme='purple'
    )

    print("RichTime Widget:")
    print(time_picker.render())
    print()


def demo_file_widgets():
    """Demonstrate file management widgets"""
    print("📁 File Management Widgets Demo")
    print("=" * 40)

    # Rich File Uploader
    file_uploader = RichFile(
        name='attachments',
        label='Upload Files',
        multiple=True,
        accept='image/*,.pdf,.doc,.docx',
        max_size=10 * 1024 * 1024,  # 10MB
        max_files=5,
        show_preview=True,
        allow_drag_drop=True,
        auto_upload=False,
        theme='green'
    )

    print("RichFile Widget:")
    print(file_uploader.render())
    print()

    # Rich File Manager
    file_manager = RichFileManager(
        name='file_browser',
        label='File Manager',
        root_path='/uploads',
        allowed_extensions=['.jpg', '.png', '.pdf', '.txt'],
        show_hidden=False,
        enable_upload=True,
        enable_delete=True,
        enable_rename=True,
        enable_create_folder=True,
        view_mode='list',
        theme='blue'
    )

    print("RichFileManager Widget:")
    print(file_manager.render())
    print()


def demo_commerce_widgets():
    """Demonstrate commerce widgets"""
    print("🛒 Commerce Widgets Demo")
    print("=" * 40)

    # Rich Price Input
    price_input = RichPrice(
        name='product_price',
        label='Product Price',
        value=29.99,
        currency='USD',
        currency_symbol='$',
        currency_position='before',
        decimals=2,
        min_value=0,
        max_value=1000,
        step=0.01,
        theme='green'
    )

    print("RichPrice Widget:")
    print(price_input.render())
    print()

    # Rich Quantity Selector
    quantity_selector = RichQuantity(
        name='quantity',
        label='Quantity',
        value=1,
        min_value=1,
        max_value=99,
        step=1,
        show_buttons=True,
        button_labels={'minus': '−', 'plus': '+'},
        theme='blue'
    )

    print("RichQuantity Widget:")
    print(quantity_selector.render())
    print()

    # Rich Product Card
    product_card = RichProductCard(
        name='product_card',
        product_id='prod-123',
        title='Wireless Bluetooth Headphones',
        description='High-quality wireless headphones with noise cancellation',
        price=89.99,
        original_price=119.99,
        currency='USD',
        image_url='/images/headphones.jpg',
        in_stock=True,
        stock_quantity=15,
        rating=4.5,
        review_count=128,
        badges=['sale', 'featured'],
        show_add_to_cart=True,
        show_wishlist=True,
        show_quick_view=True,
        theme='light'
    )

    print("RichProductCard Widget:")
    print(product_card.render())
    print()

    # Rich Shopping Cart
    cart_items = [
        {
            'id': 'item-1',
            'name': 'Wireless Headphones',
            'price': 89.99,
            'quantity': 1,
            'image': '/images/headphones.jpg'
        },
        {
            'id': 'item-2',
            'name': 'Phone Case',
            'price': 24.99,
            'quantity': 2,
            'image': '/images/case.jpg'
        }
    ]

    shopping_cart = RichShoppingCart(
        name='shopping_cart',
        items=cart_items,
        currency='USD',
        show_subtotal=True,
        show_tax=True,
        show_shipping=True,
        tax_rate=0.08,
        shipping_cost=5.99,
        free_shipping_threshold=100,
        allow_quantity_edit=True,
        allow_item_removal=True,
        checkout_url='/checkout',
        theme='blue'
    )

    print("RichShoppingCart Widget:")
    print(f"Subtotal: ${shopping_cart.get_subtotal():.2f}")
    print(f"Tax: ${shopping_cart.get_tax():.2f}")
    print(f"Shipping: ${shopping_cart.get_shipping():.2f}")
    print(f"Total: ${shopping_cart.get_total():.2f}")
    print(shopping_cart.render())
    print()


def demo_theme_system():
    """Demonstrate the theme system"""
    print("🎨 Theme System Demo")
    print("=" * 40)

    print("Current theme:", ThemeManager.get_current_theme().value)

    # Set a specific theme
    ThemeManager.set_current_theme(WidgetTheme.DARK)
    print("Changed to DARK theme:", ThemeManager.get_current_theme().value)

    # Create widgets with AUTO theme
    auto_datetime = RichDateTime(
        name='auto_datetime',
        label='Auto Theme DateTime',
        theme=WidgetTheme.AUTO,  # Will follow current theme
        help_text='This widget uses AUTO theme and will match the current application theme'
    )

    auto_price = RichPrice(
        name='auto_price',
        label='Auto Theme Price',
        theme=WidgetTheme.AUTO,  # Will follow current theme
        value=49.99
    )

    print("RichDateTime with AUTO theme:")
    print(auto_datetime.render())
    print()

    print("RichPrice with AUTO theme:")
    print(auto_price.render())
    print()

    # Change theme and see widgets update
    ThemeManager.set_current_theme(WidgetTheme.BLUE)
    print("Changed to BLUE theme:", ThemeManager.get_current_theme().value)

    # Create new widgets to show theme change
    blue_datetime = RichDateTime(
        name='blue_datetime',
        label='Blue Theme DateTime',
        theme=WidgetTheme.BLUE
    )

    print("RichDateTime with BLUE theme:")
    print(blue_datetime.render())
    print()


def demo_enhanced_widgets():
    """Demonstrate enhanced widgets"""
    print("✨ Enhanced Widgets Demo")
    print("=" * 40)

    # Rich Text Editor
    rich_text = RichText(
        name='article_content',
        label='Article Content',
        format='html',
        toolbar='full',
        max_length=5000,
        placeholder='Write your article here...',
        autosave=True,
        word_count=True,
        theme='dark'
    )

    print("RichText Widget:")
    print(rich_text.render())
    print()

    # Rich Select with search
    rich_select = RichSelect(
        name='categories',
        label='Categories',
        options=[
            ('tech', 'Technology'),
            ('business', 'Business'),
            ('health', 'Health & Wellness'),
            ('education', 'Education'),
            ('entertainment', 'Entertainment'),
            ('sports', 'Sports'),
            ('travel', 'Travel'),
            ('food', 'Food & Cooking'),
            ('fashion', 'Fashion'),
            ('science', 'Science')
        ],
        searchable=True,
        allow_multiple=True,
        max_selections=3,
        allow_custom=True,
        placeholder='Select categories...',
        theme='purple'
    )

    print("RichSelect Widget:")
    print(rich_select.render())
    print()


def main():
    """Run all widget demos"""
    print("🎉 Pyserv  Enhanced Widgets Demo")
    print("=" * 50)
    print()

    try:
        demo_theme_system()
        demo_date_time_widgets()
        demo_file_widgets()
        demo_commerce_widgets()
        demo_enhanced_widgets()

        print("✅ All widgets demonstrated successfully!")
        print()
        print("📝 Note: These widgets require corresponding JavaScript and CSS files")
        print("   to be loaded for full functionality:")
        print("   - datetime-picker.js/css")
        print("   - date-picker.js/css")
        print("   - time-picker.js/css")
        print("   - file-uploader.js/css")
        print("   - file-manager.js/css")
        print("   - price-input.js/css")
        print("   - quantity-selector.js/css")
        print("   - product-card.js/css")
        print("   - shopping-cart.js/css")
        print("   - rich-text-editor.js/css")
        print("   - rich-select.js/css")

    except Exception as e:
        print(f"❌ Error running demo: {e}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    main()




