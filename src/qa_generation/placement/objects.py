from dataclasses import dataclass


@dataclass
class RoomObject:
    name: str
    width: float
    depth: float


kitchen_objects = [
    # # --- Grand Dining Hall Elements ---
    # RoomObject("Banquet Table (Long Rectangular - 16-20 seats)", 6.0, 1.2),
    # RoomObject("Banquet Table (Extra Long Rectangular - 20-24 seats)", 7.5, 1.2),
    # RoomObject("Grand Dining Table (Custom Large Round - 14-16 seats)", 2.5, 2.5),
    # RoomObject("Grand Dining Table (Custom Large Oval - 16-18 seats)", 5.0, 1.8),
    # RoomObject("Dining Area Block (Large Group - 50 seats)", 15.0, 10.0),  # Represents a large seating section
    # RoomObject("Dining Area Block (Extra Large Group - 100+ seats)", 25.0, 15.0),
    # RoomObject("Buffet Line Setup (Long Section)", 8.0, 2.0),  # Includes space for serving/patrons
    # RoomObject("Carving Station Area", 3.0, 3.0),  # Includes space for chef & queue
    # RoomObject("Bar Area (Main Section)", 6.0, 3.0),  # Represents bar counter & space behind
    # RoomObject("Dance Floor (Small Dining/Event)", 8.0, 8.0),  # Represents clear space
    # RoomObject("Stage for Dining Entertainment", 6.0, 4.0),  # Represents raised area
    # RoomObject("Beverage Station (Large Self-Serve)", 4.0, 2.0),
    # # --- Industrial/Large Scale Kitchen Elements ---
    # RoomObject("Walk-in Refrigerator (Medium Unit)", 3.0, 3.0),
    # RoomObject("Walk-in Refrigerator (Large Unit)", 5.0, 4.0),
    # RoomObject("Walk-in Freezer (Medium Unit)", 3.0, 3.0),
    # RoomObject("Walk-in Freezer (Large Unit)", 5.0, 4.0),
    # RoomObject("Dry Storage Room Area (Small)", 4.0, 4.0),  # Represents spatial requirement
    # RoomObject("Dry Storage Room Area (Medium)", 6.0, 5.0),
    # RoomObject("Industrial Oven Battery (Multiple Units)", 5.0, 3.0),
    # RoomObject("Large Combi Oven Footprint", 2.0, 1.5),  # Bigger than standard
    # RoomObject("Industrial Mixer (Large Freestanding)", 2.0, 2.0),  # Includes clearance
    # RoomObject("Conveyor Dishwashing System", 6.0, 1.5),  # Represents linear system
    # RoomObject("Bulk Ingredient Storage Bins (Cluster)", 4.0, 4.0),
    # RoomObject("Prep Area (Central Island - Large)", 4.0, 2.0),
    # RoomObject("Expedition Pass (Large Kitchen to Dining)", 5.0, 1.5),  # Represents counter & access space
    # RoomObject("Service Alley (Kitchen Walkway)", 2.0, 10.0),  # Represents a circulation path
    # RoomObject("Receiving Area (Kitchen Delivery)", 5.0, 5.0),  # Space for deliveries
    # RoomObject("Waste Disposal Area (Compactors/Bins)", 6.0, 4.0),
    # RoomObject("Staff Break Room Area (Large)", 8.0, 6.0),  # Spatial requirement
    # RoomObject("Laundry Area (Kitchen Linens)", 4.0, 3.0),
    # RoomObject("Office Area (Kitchen Manager)", 3.0, 3.0),
    # RoomObject("Loading Dock (Commercial Kitchen)", 5.0, 8.0),
    # # --- Food Service / Diner Specific (Larger Scale) ---
    RoomObject("Diner Booth Section (Long Run)", 5.0, 1.5),  # Multiple booths in a row
    RoomObject("Counter Seating Area (Long Run)", 6.0, 1.5),  # Long counter + stool space
    RoomObject("Soda Fountain/Drink Station (Large)", 3.0, 1.0),
    RoomObject("Drive-Thru Window Area (Includes Queue space)", 3.0, 15.0),  # Represents service point & car space
    RoomObject("Outdoor Patio Dining Area (Large Block)", 10.0, 10.0),
    RoomObject("Food Truck (Representing Parking/Service Space)", 8.0, 3.0),
    RoomObject("Kiosk with Seating Area", 5.0, 5.0),  # Represents a larger food service point
    RoomObject("Take-out Counter Area", 4.0, 2.0),
    # --- Large Display/Retail Related to Food ---
    RoomObject("Large Refrigerated Display Case (Meat/Deli)", 5.0, 1.2),
    RoomObject("Large Freezer Display Case (Ice Cream/Frozen)", 4.0, 1.0),
    RoomObject("Bakery Display Counter (Long)", 6.0, 1.0),
    RoomObject("Produce Display Unit (Large Island)", 3.0, 2.0),  # Represents grocery store fixture
    RoomObject("Wine/Beverage Display Wall (Long)", 8.0, 0.5),  # Represents shelving footprint
    # --- Ssome more variations/types. ---
    RoomObject("Commissary Kitchen Area (Prep Zone)", 10.0, 8.0),  # Represents a large section
    RoomObject("Commissary Kitchen Area (Cooking Zone)", 12.0, 10.0),
    RoomObject("Food Processing Machine (Large Cutting/Mixing)", 4.0, 3.0),
    RoomObject("Packaging Line (Food Items - Section)", 8.0, 1.5),
    RoomObject("Blast Chiller/Freezer (Large Commercial)", 2.5, 2.0),
    RoomObject("Proofing Cabinet (Large Walk-in)", 3.0, 2.5),  # For bakeries
    RoomObject("Dough Mixer (Industrial, Large Bowl)", 2.0, 1.8),  # Includes clearance
    RoomObject("Oven (Deck Oven - Large)", 4.0, 3.0),  # For bakeries/pizzas
    RoomObject("Fryer (Large Pressure Fryer)", 1.5, 1.5),  # For high-volume frying
    RoomObject("Steamer (Large Commercial)", 2.0, 1.5),  # For volume cooking
    RoomObject("Soup Kettle (Large Tilting)", 1.5, 1.5),  # For bulk liquids
    RoomObject("Warewashing Area (Large Scullery)", 6.0, 5.0),  # Represents full area
    # --- Large Kitchen Appliances ---
    RoomObject("Refrigerator (Side-by-Side/French Door)", 1.0, 0.9),
    RoomObject("Refrigerator (Built-in Large)", 1.2, 0.7),
    RoomObject("Freezer (Large Upright)", 0.9, 0.8),
    RoomObject("Oven Range (Commercial Style)", 1.5, 0.9),
    RoomObject("Double Wall Oven (Footprint)", 0.75, 0.65),  # Represents space needed
    RoomObject("Commercial Range Hood (Large)", 2.0, 0.8),  # Represents overhead space/footprint
    RoomObject("Integrated Coffee Machine (Footprint)", 0.6, 0.6),  # Space in cabinet
    RoomObject("Wine Fridge (Tall/Dual Zone)", 0.6, 0.7),
    # --- Large Kitchen Cabinetry / Areas ---
    RoomObject("Tall Pantry Cabinet (Wide)", 0.9, 0.6),
    RoomObject("Base Cabinet Run (3m Section)", 3.0, 0.6),
    RoomObject("Wall Cabinet Run (3m Section)", 3.0, 0.35),
    RoomObject("Corner Base Cabinet (Large)", 1.2, 1.2),  # Represents L-shape space
    RoomObject("Appliance Garage Cabinet", 0.9, 0.6),  # Represents a wider base cabinet use
    RoomObject("Built-in Microwave & Oven Stack", 0.75, 0.65),
    # --- Large Counters & Islands ---
    RoomObject("Countertop Section (3m)", 3.0, 0.65),
    RoomObject("Countertop Section (4m)", 4.0, 0.65),
    RoomObject("Kitchen Island (Medium with Seating)", 1.8, 1.0),  # Depth includes seating overhang
    RoomObject("Kitchen Island (Large with Seating)", 2.4, 1.2),
    RoomObject("Kitchen Island (Extra Large/Prep & Seating)", 3.0, 1.5),
    RoomObject("Kitchen Peninsula (Large with Seating)", 2.0, 1.2),  # Depth includes seating overhang
    # --- Larger Sinks ---
    RoomObject("Sink (Double Bowl Large)", 0.9, 0.55),
    RoomObject("Sink (Triple Bowl / Prep & Main)", 1.2, 0.6),
    RoomObject("Sink (Large Farmhouse Style)", 0.9, 0.6),
    # --- Dining Tables (Medium to Extra Large) ---
    RoomObject("Dining Table (Large Rect - 8-10 seats)", 2.4, 1.2),
    RoomObject("Dining Table (Extra Large Rect - 10-12 seats)", 3.0, 1.2),
    RoomObject("Dining Table (Grand Rect - 12-14 seats)", 3.5, 1.3),
    RoomObject("Dining Table (Large Round - 6-8 seats)", 1.5, 1.5),
    RoomObject("Dining Table (Extra Large Round - 8-10 seats)", 1.8, 1.8),
    RoomObject("Dining Table (Large Oval - 8-10 seats)", 2.4, 1.2),
    RoomObject("Dining Table (Extendable - Extended)", 2.8, 1.0),
    # --- Dining Seating & Storage ---
    RoomObject("Dining Bench (Long)", 2.0, 0.45),
    RoomObject("Dining Chairs Area (per 4 chairs)", 2.0, 1.0),  # Represents space around a small set
    RoomObject("Buffet/Sideboard (Long)", 2.2, 0.5),
    RoomObject("Buffet with Hutch (Large)", 1.8, 0.5),  # Base footprint
    RoomObject("China Cabinet (Large)", 1.5, 0.45),
    RoomObject("Bar Stools Area (per 3 stools)", 1.5, 0.6),  # Represents space needed at island/counter
    RoomObject("Breakfast Nook Seating (L-Shape)", 2.0, 1.5),  # Represents bench footprint
    # --- Items bridging Kitchen & Dining / Large Utility ---
    RoomObject("Large Area Rug (Dining)", 3.0, 2.4),
    RoomObject("Utility Cart (Large/Serving)", 1.0, 0.6),
    RoomObject("Built-in Banquette Seating (Section)", 2.5, 0.7),  # Represents bench footprint
    RoomObject("Large Display Cabinet", 1.8, 0.45),  # Could be for dishes/glassware
    # --- Diner / Commercial Kitchen Elements ---
    RoomObject("Commercial Range (6+ Burners)", 1.8, 1.0),
    RoomObject("Commercial Fryer Bank", 1.2, 0.9),
    RoomObject("Commercial Grill / Griddle", 1.5, 0.9),
    RoomObject("Walk-in Refrigerator (Small Unit)", 2.0, 2.0),  # Internal space + wall thickness
    RoomObject("Walk-in Freezer (Small Unit)", 2.0, 2.0),
    RoomObject("Prep Table (Stainless Steel, Large)", 2.5, 0.8),
    RoomObject("Serving Counter Section (Long)", 3.0, 0.9),
    RoomObject("Booth Seating (Section - Double Sided)", 1.5, 1.5),  # Represents back-to-back booths
    RoomObject("Diner Counter Section (with stools area)", 2.5, 1.5),  # Represents counter + space for stools
    RoomObject("Dishwashing Station (Commercial)", 2.0, 1.0),
    RoomObject("Espresso Machine (Commercial Large)", 1.0, 0.7),  # Countertop footprint
    RoomObject("Ice Machine (Commercial)", 0.8, 0.8),
]

living_room_objects = [
    # Massive Seating Arrangements
    RoomObject("Mega Sectional System (Modular, Very Large)", 6.0, 4.5),  # Exceeds previous largest sectional
    RoomObject("Grand Circular Sectional (Massive Diameter)", 6.0, 6.0),  # Bounding box for a huge round piece
    RoomObject("Custom Built-in Sofa (Spanning Multiple Walls)", 12.0, 1.5),  # For a vast continuous run
    RoomObject("Tiered Seating/Lounge Area (Integrated)", 7.0, 5.0),  # Footprint of a large raised lounge space
    RoomObject("Multiple Grand Sofas Arrangement (Vast Area)", 10.0, 6.0),  # Footprint of a large cluster
    RoomObject("Expansive Daybed/Chaise System (Connected Units)", 8.0, 5.0),
    RoomObject("Large Floor Cushion/Lounging Pit Zone (Extensive)", 5.0, 5.0),
    RoomObject("Built-in Banquette Seating (Extensive Wrap-around)", 8.0, 6.0),  # Bounding box
    RoomObject("Home Cinema Tiered Seating (Multiple Deep Rows)", 7.0, 7.0),  # Footprint including walkway
    RoomObject("Oversized Daybed/Bench (Central, Architectural)", 6.0, 2.5),
    RoomObject("Massive Oversized Armchairs Group (Cluster of 4+)", 4.0, 3.0),  # Combined footprint
    RoomObject("Built-in Conversation Pit (Large)", 5.0, 5.0),  # Floor area of lowered section
    RoomObject("Large Curved Sofa System (Multi-part)", 6.0, 3.0),
    # Gigantic Tables & Related Areas
    RoomObject("Extra Large Coffee Table (Architectural Scale)", 4.0, 2.5),
    RoomObject("Massive Coffee Table (Collection of Modular Blocks)", 5.0, 4.0),
    RoomObject("Banquet Dining Table (Seats 20+)", 6.0, 1.5),  # For a combined living/dining great room
    RoomObject("Extra Large Oval Dining Table (Bounding Box)", 4.0, 3.0),
    RoomObject("Grand Conference/Meeting Table (Living Area Context)", 8.0, 2.0),
    RoomObject("Integrated Bar Area (Full Service with Seating for Many)", 6.0, 4.0),  # Bounding box
    RoomObject("Custom Built-in Desk/Workstation System (Extensive)", 7.0, 3.0),
    RoomObject("Regulation Shuffleboard Table (Its exact size)", 6.7, 0.8),  # Very long
    RoomObject("Full Size Snooker Table", 3.5, 1.8),
    RoomObject("Table Tennis Table (Area Needed for Play)", 5.0, 3.0),  # Includes space around table
    RoomObject("Massive Multi-Purpose Activity Island/Table", 4.0, 4.0),
    RoomObject("Pool Table (Regulation Size with Space for Play)", 5.0, 4.0),  # Includes space around table
    # # Enormous Storage, Display & Built-ins
    # RoomObject("Full Wall Entertainment/Media System (Custom, Spanning Entire Wall)", 15.0, 1.0),  # For a truly massive wall
    # RoomObject("Extensive Library Wall System (Wrapping Corner/Multiple Sections)", 10.0, 8.0),  # Bounding box of layout
    # RoomObject("Integrated Storage/Display Wall (Deep Units, Long Run)", 10.0, 1.5),
    # RoomObject("Walk-in Pantry/Storage Room (Small Entry)", 4.0, 4.0),  # Footprint of a substantial storage space
    # RoomObject("Massive Built-in Display Cases (Multiple, Sculptural)", 7.0, 1.0),
    # RoomObject("Wine Cellar Room (Visible/Integrated)", 5.0, 5.0),
    # RoomObject("Large Art Storage System (Multiple Pull-out Racks)", 4.0, 3.0),
    # RoomObject("Custom Credenza/Sideboard (Massive Length)", 5.0, 0.7),
    # RoomObject("Armoire/Wardrobe System (Multiple Units Grouped)", 4.0, 1.0),  # If used as large storage in living
    # # Very Large Rugs & Floor Coverings
    # RoomObject("Extra Large Area Rug (Defining Vast Open Space)", 12.0, 10.0),
    # RoomObject("Custom Shaped Rug (Massive Irregular Bounding Box)", 11.0, 11.0),
    # RoomObject("Multiple Large Rugs (Overlapping/Defining Multiple Zones)", 10.0, 8.0),  # Overall area covered by rugs
    # # Large Recreational, Architectural & Unique Items
    # RoomObject("Indoor Zen Garden/Courtyard Feature (Substantial)", 6.0, 6.0),
    # RoomObject("Indoor Plunge Pool/Spa Area (Integrated)", 7.0, 5.0),  # Footprint including surrounding deck
    # RoomObject("Short Bowling Alley Lane (Built-in)", 15.0, 3.0),  # A dedicated short lane
    # RoomObject("Large Indoor Playground/Gym Structure (Multi-level)", 8.0, 7.0),
    # RoomObject("Massive Indoor Trees/Plantings (Integrated Beds)", 7.0, 5.0),  # Footprint of planted area
    # RoomObject("Large Water Feature (Indoor Waterfall/Stream)", 6.0, 4.0),
    # RoomObject("Oversized Sculpture Installation (Commanding Presence)", 5.0, 5.0),
    # RoomObject("Vehicle Display Area (Multiple Vehicles)", 10.0, 6.0),  # For displaying multiple cars/motorcycles
    # RoomObject("Raised Stage or Performance Area (Substantial Size)", 8.0, 7.0),
    # RoomObject("Professional DJ Booth & Sound System (Full Venue Setup)", 6.0, 4.0),
    # RoomObject("Extensive Home Gym Area (Multiple Machines & Space)", 8.0, 6.0),
    # RoomObject("Spa/Wellness Area (Sauna, Steam Room, Massage Table, Equipment)", 7.0, 6.0),
    # RoomObject("Indoor Sports Simulator (Golf, Racing, etc.)", 7.0, 7.0),  # Space needed including movement
    # RoomObject("Full-size Arcade / Game Room Corner (Many Machines)", 6.0, 5.0),
    # RoomObject("Large Integrated Fireplace with Extensive Hearth & Built-in Seating", 8.0, 3.0),
    # RoomObject("Grand Piano (Concert Grand Size)", 3.0, 2.0),  # Larger footprint than baby grand
    # RoomObject("Indoor Climbing Wall Section (Base & Landing Zone)", 6.0, 4.0),
    # RoomObject("Large Aquarium Wall (Built-in)", 5.0, 1.0),  # Footprint of base/structure
    # RoomObject("Freestanding Large Format Printer/Plotter (If used in living studio)", 2.0, 1.5),  # Specific large equipment
    # RoomObject("Collection of Oversized Floor Lamps (Spanning Large Area)", 4.0, 3.0),  # Footprint of several large lamps/arcs
    # More Larger Seating
    RoomObject("Sofa (8-seater Extra Long)", 4.0, 1.0),
    RoomObject("Sectional (Grand Pit Sectional, Bounding Box)", 5.0, 5.0),  # Very large, central seating area
    RoomObject("Sectional (Modular, Wide Configuration)", 3.8, 2.5),
    RoomObject("Chaise Lounge (Double Wide)", 1.5, 2.0),
    RoomObject("Loveseat (Oversized Deep)", 1.8, 1.1),
    RoomObject("Set of 4 Dining Chairs (Arranged)", 2.0, 1.0),  # If near living area
    RoomObject("Large Corner Seating Unit", 2.5, 2.5),  # Like a built-in look
    RoomObject("Reading Chaise with Side Table Attached", 1.0, 2.2),
    RoomObject("Oversized Pouf Cluster (Approx Footprint)", 1.8, 1.8),
    RoomObject("Banquette Seating (L-Shape Section)", 3.0, 1.8),  # If integrated dining/living
    RoomObject("Bench (Extra Deep with High Back)", 2.5, 0.8),
    RoomObject("Swivel Lounge Chair (Extra Wide Base)", 1.2, 1.2),
    # More Larger Tables
    RoomObject("Dining Table (8-10 Seater Rectangular)", 2.5, 1.1),  # If open plan
    RoomObject("Dining Table (10-12 Seater Rectangular)", 3.0, 1.2),
    RoomObject("Dining Table (Large Round, Bounding Box)", 1.8, 1.8),  # 1.8m diameter
    RoomObject("Dining Table (Large Oval, Bounding Box)", 2.2, 1.6),
    RoomObject("Console Table (Extra Deep with Drawers)", 2.2, 0.7),
    RoomObject("Side Table (Large Pedestal Base)", 0.9, 0.9),
    RoomObject("Activity Table (Craft/Game Table)", 1.8, 0.9),  # Multipurpose large table
    RoomObject("Pool Table (Regulation Size)", 3.0, 1.7),
    RoomObject("Air Hockey Table (Full Size)", 2.3, 1.2),
    RoomObject("Foosball Table (Full Size)", 1.5, 0.8),
    RoomObject("Large Serving Cart (Extended)", 1.5, 0.6),
    # More Larger Storage & Display
    RoomObject("Wall Unit (Large Hutch Section)", 2.5, 0.6),
    RoomObject("Full Wall Bookshelf System (Bounding Box)", 6.0, 0.4),  # Multiple units combined
    RoomObject("Credenza (Extra Long)", 3.0, 0.5),
    RoomObject("Wine Cabinet (Tall & Wide)", 1.5, 0.5),  # Dedicated large storage
    RoomObject("Large Display Case (Museum Style)", 2.0, 1.0),  # For collectibles
    RoomObject("Entertainment Console (Floating, Long)", 3.5, 0.4),
    RoomObject("Wardrobe (Double Door, Deep)", 1.5, 0.8),  # If used for coats/storage in living
    RoomObject("Bar Cabinet (Walk-up Style)", 2.0, 1.2),  # Larger than a simple unit
    RoomObject("Media Wall System (Modular, Large Section)", 4.5, 0.55),
    # More Other Larger Items
    RoomObject("Extra Large Rug (Round, Bounding Box, 5m Diameter)", 5.0, 5.0),
    RoomObject("Extra Large Rug (6m x 5m)", 6.0, 5.0),
    RoomObject("Large Floor Mirror (Leaning or Standing)", 1.5, 0.3),  # Footprint might be small, but visual presence is large
    RoomObject("Room Divider (Large Folding Screen)", 3.0, 0.3),  # Footprint when unfolded
    RoomObject("Indoor Sculpture (Large Floor Standing)", 1.0, 1.0),  # Base footprint
    RoomObject("Large Floor Lamp (Multiple Arms, Wide Spread)", 1.5, 1.5),
    RoomObject("Grandfather Clock (Large Base)", 0.8, 0.4),  # Large presence, smaller footprint
    RoomObject("Large Aquarian Stand & Tank (Base Footprint)", 2.0, 0.7),
    RoomObject("Arcade Cabinet (Full Size)", 0.9, 0.8),
    RoomObject("Pinball Machine", 0.8, 1.5),  # Deeper than wide
    RoomObject("Treadmill (Standard Size)", 2.0, 0.9),  # If part of living/gym combo
    RoomObject("Elliptical Machine (Standard Size)", 2.2, 0.8),
    RoomObject("Home Gym System (Compact All-in-One)", 2.0, 1.5),
    RoomObject("Indoor Fountain (Large Floor Model)", 1.2, 1.2),
    RoomObject("Large Plant (Fiddle Leaf Fig etc.) in Pot", 0.8, 0.8),  # Base footprint
    RoomObject("Cluster of Tall Plants in Pots", 1.5, 0.8),
    RoomObject("Floor Standing Speakers (Pair, Footprint)", 1.0, 0.5),  # Space needed for pair
    RoomObject("Large Easel with Canvas", 1.0, 1.0),
    RoomObject("Massage Chair (Large Reclining)", 1.5, 1.0),  # Footprint when not fully reclined
    RoomObject("Large Dog Crate (Extra Large Size)", 1.2, 0.8),
]

bedroom_objects = [
    # Beds (Massive Scales, Integrated Systems)
    # RoomObject("Bed (Imperial Grand King)", 3.00, 3.00),
    # RoomObject("Bed (Integrated Headboard/Side Tables/Bench System - Super King)", 4.00, 2.80),  # Full system width
    RoomObject("Bed (Custom Upholstered Wall Bed Footprint)", 4.50, 0.80),  # Closed position, covers large wall section
    # RoomObject("Bed (Four-Poster Grand Canopy with Drapes)", 3.50, 3.50),
    # RoomObject("Bed (Platform Bed with Integrated Seating Area)", 5.00, 3.00),  # Massive platform base
    # RoomObject("Bed (Circular Rotating Bed Grand - approx)", 4.00, 4.00),
    RoomObject("Bed (Built-in Alcove Bed Base with Storage - Grand)", 3.50, 1.50),
    # RoomObject("Bed (Oversized Daybed/Sofa System with Chaise)", 4.00, 2.50),
    # RoomObject("Bed (Floating Bed Base - Extra Large)", 3.00, 2.50),
    # RoomObject("Bed (Massive Sleigh Bed with Sculpted Frame)", 3.00, 3.00),
    # Nightstands (More like Sideboards or Consoles)
    RoomObject("Bedside Sideboard (Grand)", 2.00, 0.60),
    RoomObject("Bedside Cabinet (Deep & Wide Double)", 1.50, 0.70),
    RoomObject("Bedside Chest of Drawers (Triple Wide)", 2.50, 0.65),
    RoomObject("Bedside Table (Sculptural Pedestal - Grand)", 1.20, 1.20),
    # Dressers & Chests (Wall-filling, Integrated Units)
    RoomObject("Dresser (Quadruple Dresser)", 4.00, 0.70),
    RoomObject("Dresser (Integrated Entertainment Wall Unit Base)", 5.00, 0.65),  # Base unit of a larger system
    RoomObject("Dresser (Grand Master Dresser with Mirror Base)", 3.50, 0.75),
    RoomObject("Chest of Drawers (Massive Tall & Wide)", 1.50, 0.70),
    RoomObject("Gentleman's Chest (Mega Size)", 2.00, 0.80),
    RoomObject("Bedroom Storage Wall System (Lower Cabinet Section)", 6.00, 0.80),  # Represents a long wall section
    RoomObject("Antique Storage Chest (Extra Large & Deep)", 2.50, 1.00),
    RoomObject("Bedroom Sideboard/Buffet (Extra Long)", 3.50, 0.70),
    # Wardrobes / Armoires (Full Wall Systems, Walk-in Footprints)
    RoomObject("Wardrobe (Eight Door Standard Depth)", 4.00, 0.60),
    RoomObject("Wardrobe (Sliding Door Four Door Wide)", 5.00, 0.80),
    # RoomObject("Wardrobe (Deep Walk-in Module Entry/Base - Large Config)", 3.00, 3.00),  # Larger walk-in footprint
    RoomObject("Armoire (Museum Grade Grand)", 3.00, 1.00),
    RoomObject("Built-in Wardrobe System (Mega Wide Section)", 6.00, 0.80),
    RoomObject("Wardrobe (Corner System - Grand Curved approx)", 2.00, 2.00),
    RoomObject("Wardrobe (Integrated Storage Wall System - Base)", 5.00, 0.75),
    # Desks & Chairs (Office Suites within Bedroom)
    RoomObject("Desk (Executive U-Shape System Footprint - Grand)", 3.00, 2.50),
    RoomObject("Desk (Grand Partner Desk with Integrated Return)", 3.00, 2.00),
    RoomObject("Desk (Built-in Wall Unit Desk Base - Deep & Wide)", 3.50, 1.20),
    RoomObject("Desk Chair Footprint (Massage Recliner with Ottoman)", 1.50, 2.50),
    RoomObject("Vanity Table (Professional Makeup Station Grand)", 3.00, 0.70),
    # Seating (Multiple Components, Large Scale)
    # RoomObject("Accent Chair (Oversized Pair with Large Ottoman Footprint)", 3.00, 2.00),
    # RoomObject("Chaise Lounge (Pair of Grand Double Chaises)", 2.50, 3.00),
    # RoomObject("Sofa (Sectional Sofa - Grand Bedroom Lounge L-Shape)", 4.00, 3.00),
    RoomObject("Sofa (Curved Sofa - Grand Bedroom)", 3.50, 1.50),
    RoomObject("Bench (Window Seat Built-in System Base - Extra Long)", 4.00, 0.80),
    RoomObject("Ottoman (Massive Square Coffee Table / Ottoman)", 2.50, 2.50),
    RoomObject("Daybed Ensemble (Integrated with Backs and Ottomans)", 4.00, 1.80),
    RoomObject("Divan (Grand Lounge Area Base)", 3.50, 1.50),
    RoomObject("Recliner (Oversized Cinema Style - Full Recline Footprint)", 1.20, 2.00),
    # Storage & Display (Full Wall Units, Library Scale)
    RoomObject("Bookshelf (Full Library Wall System - Base Section)", 6.00, 0.60),
    RoomObject("Bookshelf (Deep Cube Storage System Grand)", 3.00, 0.60),
    RoomObject("Display Cabinet (Curio Cabinet Wall System Base)", 4.00, 0.70),
    RoomObject("Storage Unit (Low & Very Long Entertainment Console Wall)", 5.00, 0.70),
    RoomObject("Shelving Unit (Architectural Steel Frame Large Base)", 3.00, 0.60),
    # Other Items (Massive Decorative or Functional Pieces)
    RoomObject("Floor Mirror (Integrated Wall Mirror System Base)", 3.00, 0.50),
    RoomObject("Room Divider Screen (Solid Structure Base)", 2.50, 0.50),
    RoomObject("Large Indoor Sculpture (Grand Scale)", 2.00, 2.00),
    RoomObject("Decorative Fireplace Surround (Ornate Stone/Marble Grand)", 3.50, 0.80),
    RoomObject("Planter Box (Very Long Indoor Garden Feature)", 4.00, 0.60),
    RoomObject("Safe (Walk-in Style Base)", 1.50, 1.50),  # Small walk-in style safe footprint
]
