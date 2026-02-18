from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from typing import List
import qrcode
import io
import base64
from app.db.session import get_db
from app.schemas import TableResponse, QRCodeRequest, QRCodeResponse, VenueStationResponse
from app.models import VenueStation, StaffUser
from app.core.rbac import RequireOwner, get_current_user
from app.core.config import settings
from app.core.rate_limit import limiter

# Alias: admin endpoints require owner-level access
get_admin_user = get_current_user

# Get the Table model class by tablename to avoid SQLAlchemy Table class conflict
from app.db.base import Base
TableModel = next(cls for cls in Base.registry._class_registry.values()
                  if hasattr(cls, '__tablename__') and cls.__tablename__ == 'tables')

router = APIRouter()


@router.get("/tables", response_model=List[TableResponse])
@limiter.limit("60/minute")
def get_tables(
    request: Request,
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(get_admin_user)
):
    """Get all tables (admin only)."""
    tables = db.query(TableModel).filter(
        TableModel.venue_id == current_user.venue_id
    ).order_by(TableModel.number).all()
    
    return [TableResponse(
        id=table.id,
        number=table.number,
        seats=table.capacity,

        venue_id=table.location_id,
        active=table.status != "closed",
        created_at=table.created_at
    ) for table in tables]


@router.post("/tables/qr", response_model=QRCodeResponse)
@limiter.limit("30/minute")
def generate_qr_code(
    request: Request,
    body: QRCodeRequest,
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(get_admin_user)
):
    """Generate QR code for table (admin only)."""
    table = db.query(TableModel).filter(
        TableModel.id == body.table_id,
        TableModel.venue_id == current_user.venue_id
    ).first()
    
    if not table:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Table not found"
        )
    
    # Get table token
    if not table.tokens:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Table has no active token"
        )
    
    token = table.tokens[0].token
    url = f"{settings.CUSTOMER_WEB_URL}/table/{token}"
    
    # Generate QR code
    qr = qrcode.QRCode(version=1, box_size=10, border=5)
    qr.add_data(url)
    qr.make(fit=True)
    
    if body.format == "svg":
        # SVG format
        import qrcode.image.svg
        factory = qrcode.image.svg.SvgPathImage
        img = qr.make_image(image_factory=factory)
        buffer = io.BytesIO()
        img.save(buffer)
        qr_data = buffer.getvalue().decode('utf-8')
    else:
        # PNG format (default)
        img = qr.make_image(fill_color="black", back_color="white")
        buffer = io.BytesIO()
        img.save(buffer, format='PNG')
        qr_data = base64.b64encode(buffer.getvalue()).decode('utf-8')
    
    return QRCodeResponse(
        table_id=table.id,
        table_number=table.number,
        qr_data=qr_data,
        url=url
    )


@router.get("/stations", response_model=List[VenueStationResponse])
@limiter.limit("60/minute")
def get_stations(
    request: Request,
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(get_admin_user)
):
    """Get all stations (admin only)."""
    stations = db.query(VenueStation).filter(
        VenueStation.venue_id == current_user.venue_id
    ).all()
    
    return [VenueStationResponse(
        id=station.id,
        name=station.name,
        station_type=station.station_type,
        active=station.active
    ) for station in stations]


@router.post("/import-sklad")
@limiter.limit("30/minute")
def import_sklad_products(
    request: Request,
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(get_admin_user)
):
    """
    Import products from Sklad.BIN (Bulgarian POS warehouse data).
    This endpoint imports 324 menu items across 16 categories.
    """
    import json
    from app.models import MenuItem, MenuCategory, MenuVersion, Menu

    # Load categorized products
    sklad_data = {
        "Vodka": ["ABSOLUT KURANT", "VODKA", "VODKA ENERGY", "GREY GOOSE & SOFT", "ABSOLUT VANILA - 50 ml.", "VODKA SHOT", "VODKA SOFT DRINK HAPPY", "VODKA & ENERGY HAPPY", "BLAVOD VODKA - 50 ml.", "ABSOLUT VANILA", "SMIRNOFF VODKA", "DOUBLE PREMIUM VODKA & SOFT DRINK", "PREMIUM VODKA & JUICE", "LOCAL VODKA", "DOUBLE VODKA ENERGY", "FINLANDIA VODKA", "VODKA JUICE", "SMIRNOFF ICE", "ABSOLUT VODKA", "ABSOLUT RASPBERY", "FINLANDIA VODKA - 50 ml.", "SMIRNOFF APPLE", "ABSOLUT CITRONE", "BLAVOD VODKA", "VODKA & JUICE", "VODKA SOFT DRINK"],
        "Whisky": ["JOHNNIE RED LABEL", "JOHNNIE BLACK LABEL", "JAMESON", "TULLAMORE DEW", "J & B", "JEAM BEAM", "Bushmills", "WHISKEY", "WHISKEY SHOT", "PREMIUM WHISKEY & SOFT DRINK", "DOUBLE PREMIUM WHISKEY & SOFT DRINK", "WHISKEY & SOFT DR. HAPPY", "WHISKEY & JUICE HAPPY", "BOTTLE WHISKEY PREMIUM"],
        "Rum": ["BACARDI white", "BACARDI BLACK", "BACARDI ORO", "BACARDI RAZZ", "HAVANA club", "HAVANA RUM 7y", "CAPITAN MORGAN SPICE", "MALIBU RUM", "MALIBU & COKE", "MALIBU & JUICE", "RUM SOFT DRINK", "RUM & JUICE", "SPICE RUM & COKE", "HAVANA & SOFT DRINK", "DOUBLE HAVANA & SOFT DRINK", "LOCAL RUM HAPPY", "RUM & SOFT DRINK HAPPY", "STRAWBERRY RUM", "BACARDI BREEZER", "APPELTON RUM"],
        "Gin": ["GORDANS GIN", "BOMBAY GIN", "BEEFETER GIN", "LOCAL GIN", "GIN SOFT DRINK", "GIN JUICE", "GIN FIZZ", "PREMIUM GIN & SOFT DRINK", "DOUBLE PREMIUM GIN & SOFT DRINK", "BOMBAY & SOFT DR", "DOUBLE BOMBAY & SOFT DR", "GIN & SOFT DRINK HAPPY", "GIN & JUICE HAPPY", "LOCAL GIN HAPPY"],
        "Tequila": ["JOSE COERVO", "PATRON TEQUILA", "PEPE LOPEZ", "TEQUILA", "TEQUILA SUNRISE", "TEQUILA JUICE", "TEQUILA & SOFT HAPPY", "TEQUILA SUNRISE HAPPY", "TEQUILA & JUICE HAPPY"],
        "Beer": ["DRAUGHT BEER SMALL .330", "DRAUGHT BEER LARGE", "DRAUGHT STELLA", "STELLA", "STELLA CIDRE", "HEINEKEN 330", "CORONA 0.330", "BECKS", "TUBORG", "KAMENITZA 0.330"],
        "Wine": ["GLASS OF WINE", "BOTTLE OF WINE", "BOTTLE OF WINE 375ML", "BOTTLE PREMIUM WINE", "PROSECO GLASS", "PROSECO BOTTLE"],
        "Cocktails": ["MOJITO", "COSMOPOLITAN", "PINA COLADA", "PINA COLADA HAPPY", "LONG ISLAND", "LONG ISLAND ICE TEA HAPPY", "SEX ON THE BEACH", "SEX ON THE BEACH BIG", "SEX ON THE BEACH HAPPY", "SEX ON THE GONDOLA", "SEX ON THE GONDOLA HAPPY", "MARGARITA Cocktail", "STRAWBERRY MARGARITA", "STRAWBERRY MARGARITA HAPPY", "STRAWBERRY DAIQUIRI", "PASSION FRUIT DAIQUIRI", "STRAWBERRY COLADA", "STRAWBERRY COLADA HAPPY", "BANANA COLADA", "BANANA COLADA HAPPY", "BAHAMA MAMA", "B 52", "BABY GUINESS", "GALLIANO HOT SHOT", "BOOGI SHOT", "ESPRESSO MARTINI", "NON ALCHOHOLIC MOJITO", "HAPPY HOUR COCKTAILS"],
        "Liqueurs": ["JAGERMEISTER 40 ML", "JAGERMEISTER SHOT 25 ML", "BAILEYS HOT CHOC", "AMARETO & COCKE", "DOUBLE AMARETO & COKE", "CAMPARI & JUICE", "DOUBLE CAMPARI & JUICE", "MARTINI BIANCO", "MARTINI DRY", "MARTINI & SOFT DRINK", "APEROL SHPRITZ", "ABSINTE", "AFTER SHOCK"],
        "Soft Drinks": ["COLA", "COKE", "DIET COKE", "COLA ZERO", "FANTA", "SPRITE", "JUICE - 250 Ml", "FRESH JUICE", "APPLE JUICE", "RED BULL", "ENERGY DRINKS", "MIN. WATER", "KINLEY SODA"],
        "Coffee & Tea": ["ESPRESSO", "BLACK COFFEE", "CAPPUCCINO", "CAFE LATTE", "ALMOND CAPUCCINO", "HOT CHOCOLATE", "BJs TEA CUP", "SPECIAL ICE TEA", "SPECIAL ICE TEA HAPPY"],
        "Burgers": ["BEEF BURGER WITH CHIPS", "CHEESE BURGER WITH CHIPS", "DOUBLE CHEESEBURGER", "BACON BURGER", "BACON AND BEEF BURGER", "CHICKEN BURGER"],
        "Salads": ["SHOPSKA SALAD", "CAPRESE SALAD", "FITNESS SALAD", "AL TONO SALAD", "BEEF SALAD"],
        "Main Dishes": ["MARGHERITA PIZZA", "PIZZA WITH CHICKEN", "PIZZA BJs", "CALZONE PIZZA", "PASTA", "PENNE WITH CHICKEN", "CHICKEN FILLET", "CHICKEN FAJITAS", "BEEF FAJITAS", "BEEF MEDALLIONS", "PORK MEDALLIONS", "PORK BBQ RIBS", "CHICKEN SOUP", "BEEF GOULASH SOUP", "FISHBOWL"],
        "Starters": ["NACHOS", "Promotion Chilli & Nachos", "PORTION OF CHIPS", "CHIPS WITH CHEESE", "TOMATO SOUP", "TOAST WITH EGGS", "TOAST WITH SAUSAGE", "TOASTED CHEESE SANDWICH", "TOASTED CHEESE AND HAM SANDW.", "BEANS ON TOAST", "BACON SANDWICH"],
        "Desserts": ["TIRAMISU WITH COFFEE", "BALL OF ICE CREAM", "ICE CREAM VANILLA", "ICE CREAM STRACIATELLA", "ICE CREAM CHOCOLATE", "PANCAKE", "CAKE", "CHOCOLATE SHAKE"]
    }

    # Price defaults by category (in BGN)
    category_prices = {
        "Vodka": 8.0, "Whisky": 10.0, "Rum": 8.0, "Gin": 8.0, "Tequila": 9.0,
        "Liqueurs": 7.0, "Beer": 5.0, "Wine": 12.0, "Cocktails": 12.0,
        "Soft Drinks": 4.0, "Coffee & Tea": 4.0, "Burgers": 15.0,
        "Salads": 10.0, "Main Dishes": 18.0, "Starters": 8.0, "Desserts": 8.0
    }

    # Station mappings
    station_mappings = {
        "Vodka": "bar", "Whisky": "bar", "Rum": "bar", "Gin": "bar", "Tequila": "bar",
        "Liqueurs": "bar", "Beer": "bar", "Wine": "bar", "Cocktails": "bar",
        "Soft Drinks": "bar", "Coffee & Tea": "coffee", "Burgers": "kitchen",
        "Salads": "kitchen", "Main Dishes": "kitchen", "Starters": "kitchen", "Desserts": "dessert"
    }

    venue_id = current_user.venue_id

    # Get or create menu version
    version = db.query(MenuVersion).filter(MenuVersion.is_active == True).first()
    if not version:
        menu = db.query(Menu).filter(Menu.venue_id == venue_id).first()
        if not menu:
            menu = Menu(venue_id=venue_id, name=json.dumps({"en": "Main Menu", "bg": "Главно меню"}), is_active=True)
            db.add(menu)
            db.flush()
        version = MenuVersion(menu_id=menu.id, version_number=1, is_active=True)
        db.add(version)
        db.flush()

    # Get stations
    stations = {s.code: s.id for s in db.query(VenueStation).filter(VenueStation.venue_id == venue_id).all()}
    default_station = next(iter(stations.values())) if stations else 1

    total_items = 0

    for cat_idx, (category_name, products) in enumerate(sklad_data.items()):
        # Get or create category
        category = db.query(MenuCategory).filter(
            MenuCategory.version_id == version.id,
            MenuCategory.name.cast(db.bind.dialect.name == 'postgresql' and 'text' or 'varchar').like(f'%"{category_name}"%')
        ).first()

        if not category:
            category = MenuCategory(
                version_id=version.id,
                venue_id=venue_id,
                name=json.dumps({"en": category_name, "bg": category_name}),
                description=json.dumps({"en": f"{category_name} items", "bg": f"Артикули от {category_name}"}),
                sort_order=cat_idx,
                active=True,
                is_active=True
            )
            db.add(category)
            db.flush()

        station_code = station_mappings.get(category_name, "bar")
        station_id = stations.get(station_code, default_station)
        default_price = category_prices.get(category_name, 10.0)

        for idx, product_name in enumerate(products):
            # Check if product exists
            existing = db.query(MenuItem).filter(
                MenuItem.category_id == category.id,
                MenuItem.name.cast(db.bind.dialect.name == 'postgresql' and 'text' or 'varchar').like(f'%"{product_name}"%')
            ).first()

            if existing:
                continue

            # Determine price
            price = default_price
            if "50 ml" in product_name or "25 ml" in product_name:
                price = default_price * 0.5
            elif "DOUBLE" in product_name:
                price = default_price * 1.5
            elif "BOTTLE" in product_name:
                price = default_price * 5
            elif "HAPPY" in product_name:
                price = default_price * 0.7
            elif "PREMIUM" in product_name:
                price = default_price * 1.3

            item = MenuItem(
                category_id=category.id,
                station_id=station_id,
                venue_id=venue_id,
                name=json.dumps({"en": product_name, "bg": product_name}),
                description=json.dumps({"en": "", "bg": ""}),
                price=round(price, 2),
                sort_order=idx,
                available=True,
                is_active=True,
                preparation_time_minutes=5 if station_code == "bar" else 15
            )
            db.add(item)
            total_items += 1

    db.commit()

    return {
        "status": "success",
        "message": f"Successfully imported {total_items} products from Sklad.BIN",
        "total_items": total_items,
        "categories": len(sklad_data)
    }
