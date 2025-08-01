tools = [
    {
        "type": "function",
        "function": {
            "name": "auth_vendor",
            "description": "Authenticate a vendor using their phone number",
            "parameters": {
                "type": "object",
                "properties": {
                    "phone_no": {"type": "string"}
                },
                "required": ["phone_no"]
            }
        }
    },
   {
        "type": "function",
        "function": {
            "name": "create_store",
            "description": "Create a store for the vendor based on business categories. Always ask the user for confirmation of category before going ahead and creating a store.",
            "parameters": {
            "type": "object",
            "properties": {
                "categories": {
                "type": "array",
                "items": {
                    "type": "string",
                    "enum": [
                    "Animals & Pet Supplies",
                    "Apparel & Accessories",
                    "Arts & Entertainment",
                    "Baby & Toddler",
                    "Bundles",
                    "Business & Industrial",
                    "Cameras & Optics",
                    "Electronics",
                    "Food, Beverages & Tobacco",
                    "Furniture",
                    "Gift Cards",
                    "Hardware",
                    "Health & Beauty",
                    "Home & Garden",
                    "Luggage & Bags",
                    "Mature",
                    "Media",
                    "Office Supplies",
                    "Product Add-Ons",
                    "Religious & Ceremonial",
                    "Services",
                    "Software",
                    "Sporting Goods",
                    "Toys & Games",
                    "Uncategorized",
                    "Vehicles & Parts"
                    ]
                }
                },
                "token": {
                "type": "string"
                }
            },
            "required": ["categories", "token"]
            }
        }
    }

]
