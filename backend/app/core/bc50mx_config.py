# BC 50MX Configuration Additions
# Add these to app/core/config.py Settings class

# BC 50MX Fiscal Printer Configuration
BC50MX_ENABLED: bool = False
BC50MX_CONNECTION: str = "serial"  # serial, usb, network
BC50MX_PORT: str = "/dev/ttyUSB0"  # Serial/USB port
BC50MX_BAUDRATE: int = 115200
BC50MX_HOST: Optional[str] = None  # For network connection
BC50MX_NETWORK_PORT: int = 8000
BC50MX_TIMEOUT: int = 3

# Auto-print settings
BC50MX_AUTO_PRINT_KITCHEN: bool = True  # Auto print kitchen slips
BC50MX_AUTO_PRINT_RECEIPT: bool = False  # Auto print fiscal receipts
BC50MX_AUTO_PRINT_WAITER_CALLS: bool = True  # Auto print waiter call notifications

# Fiscal settings
BC50MX_VAT_GROUP_FOOD: str = "B"  # 9% VAT for food
BC50MX_VAT_GROUP_DRINKS: str = "B"  # 9% VAT for drinks
BC50MX_VAT_GROUP_ALCOHOL: str = "A"  # 20% VAT for alcohol
BC50MX_OPERATOR_PASSWORD: str = "1234"
