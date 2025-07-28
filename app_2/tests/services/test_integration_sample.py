"""
Integration Sample Test - Menu Processor v2
Demonstrates real-world usage patterns with comprehensive dummy data
"""
import pytest
from unittest.mock import AsyncMock
from app_2.services.allergen_service import AllergenService
from app_2.services.ingredient_service import IngredientService


class TestIntegrationSample:
    """Integration tests demonstrating real-world usage patterns"""
    
    @pytest.fixture
    def mock_clients(self):
        """Mock both clients with realistic responses"""
        allergen_client = AsyncMock()
        ingredient_client = AsyncMock()
        
        # Real-world allergen responses
        allergen_responses = {
            "Chocolate Chip Cookie": {
                "allergens": [
                    {"allergen": "wheat", "category": "grain", "severity": "major", "likelihood": "high", "source": "flour"},
                    {"allergen": "eggs", "category": "protein", "severity": "major", "likelihood": "high", "source": "binding agent"},
                    {"allergen": "milk", "category": "dairy", "severity": "major", "likelihood": "medium", "source": "butter and chocolate chips"}
                ],
                "allergen_free": False,
                "dietary_warnings": ["Contains gluten", "Contains eggs", "Contains dairy"],
                "notes": "Traditional cookie recipe with major allergens",
                "confidence": 0.95
            },
            "Garden Salad": {
                "allergens": [],
                "allergen_free": True,
                "dietary_warnings": [],
                "notes": "Fresh vegetables only, no known allergens",
                "confidence": 0.90
            },
            "Pad Thai": {
                "allergens": [
                    {"allergen": "peanuts", "category": "nuts_seeds", "severity": "major", "likelihood": "high", "source": "garnish"},
                    {"allergen": "fish_sauce", "category": "seafood", "severity": "major", "likelihood": "high", "source": "seasoning"},
                    {"allergen": "soy", "category": "vegetables", "severity": "minor", "likelihood": "medium", "source": "possible soy sauce"}
                ],
                "allergen_free": False,
                "dietary_warnings": ["Contains peanuts", "Contains fish products", "May contain soy"],
                "notes": "Traditional Thai dish with multiple allergen sources",
                "confidence": 0.88
            }
        }
        
        # Real-world ingredient responses
        ingredient_responses = {
            "Chocolate Chip Cookie": {
                "main_ingredients": [
                    {"ingredient": "flour", "category": "grain", "subcategory": "wheat_flour", "origin": "processed", "importance": "primary", "nutritional_category": "carbohydrate"},
                    {"ingredient": "butter", "category": "dairy", "subcategory": "fat", "origin": "animal", "importance": "primary", "nutritional_category": "fat"},
                    {"ingredient": "chocolate_chips", "category": "other", "subcategory": "confection", "origin": "processed", "importance": "primary", "nutritional_category": "fat"},
                    {"ingredient": "sugar", "category": "other", "subcategory": "sweetener", "origin": "processed", "importance": "secondary", "nutritional_category": "carbohydrate"}
                ],
                "cooking_method": ["baking"],
                "cuisine_category": "American",
                "dietary_info": {"vegetarian": True, "vegan": False, "gluten_free": False, "dairy_free": False, "low_carb": False, "keto_friendly": False},
                "confidence": 0.92
            },
            "Garden Salad": {
                "main_ingredients": [
                    {"ingredient": "lettuce", "category": "vegetable", "subcategory": "leafy_greens", "origin": "plant", "importance": "primary", "nutritional_category": "fiber"},
                    {"ingredient": "tomatoes", "category": "vegetable", "subcategory": "fruit_vegetable", "origin": "plant", "importance": "secondary", "nutritional_category": "vitamin_mineral"},
                    {"ingredient": "cucumbers", "category": "vegetable", "subcategory": "fresh_vegetable", "origin": "plant", "importance": "secondary", "nutritional_category": "water"},
                    {"ingredient": "olive_oil", "category": "oil", "subcategory": "vegetable_oil", "origin": "plant", "importance": "minor", "nutritional_category": "fat"}
                ],
                "cooking_method": ["fresh", "no_cooking"],
                "cuisine_category": "Mediterranean",
                "dietary_info": {"vegetarian": True, "vegan": True, "gluten_free": True, "dairy_free": True, "low_carb": True, "keto_friendly": True},
                "confidence": 0.95
            },
            "Pad Thai": {
                "main_ingredients": [
                    {"ingredient": "rice_noodles", "category": "grain", "subcategory": "noodles", "origin": "processed", "importance": "primary", "nutritional_category": "carbohydrate"},
                    {"ingredient": "shrimp", "category": "protein", "subcategory": "shellfish", "origin": "animal", "importance": "primary", "nutritional_category": "protein"},
                    {"ingredient": "bean_sprouts", "category": "vegetable", "subcategory": "sprouts", "origin": "plant", "importance": "secondary", "nutritional_category": "fiber"},
                    {"ingredient": "peanuts", "category": "protein", "subcategory": "nuts", "origin": "plant", "importance": "minor", "nutritional_category": "protein"}
                ],
                "cooking_method": ["stir_frying"],
                "cuisine_category": "Thai",
                "dietary_info": {"vegetarian": False, "vegan": False, "gluten_free": True, "dairy_free": True, "low_carb": False, "keto_friendly": False},
                "confidence": 0.88
            }
        }
        
        # Configure mock responses
        def allergen_side_effect(menu_item, category=""):
            return allergen_responses.get(menu_item, {"allergens": [], "allergen_free": True, "confidence": 0.5})
        
        def ingredient_side_effect(menu_item, category=""):
            return ingredient_responses.get(menu_item, {"main_ingredients": [], "dietary_info": {}, "confidence": 0.5})
        
        allergen_client.extract_allergens.side_effect = allergen_side_effect
        ingredient_client.extract_ingredients.side_effect = ingredient_side_effect
        
        return allergen_client, ingredient_client
    
    @pytest.fixture
    def services(self, mock_clients):
        """Create service instances with mocked clients"""
        allergen_client, ingredient_client = mock_clients
        allergen_service = AllergenService(allergen_client=allergen_client)
        ingredient_service = IngredientService(ingredient_client=ingredient_client)
        return allergen_service, ingredient_service
    
    @pytest.mark.asyncio
    async def test_dessert_analysis_workflow(self, services):
        """Test comprehensive analysis workflow for a dessert item"""
        allergen_service, ingredient_service = services
        
        # Analyze a chocolate chip cookie
        menu_item = "Chocolate Chip Cookie"
        category = "desserts"
        
        # Get allergen information
        allergen_result = await allergen_service.analyze_allergens(menu_item, category)
        
        # Get ingredient information
        ingredient_result = await ingredient_service.analyze_ingredients(menu_item, category)
        main_ingredients = await ingredient_service.get_main_ingredients(menu_item, category)
        
        # Check dietary restrictions
        is_vegetarian = await ingredient_service.is_vegetarian(menu_item, category)
        is_vegan = await ingredient_service.is_vegan(menu_item, category)
        is_gluten_free = await ingredient_service.is_gluten_free(menu_item, category)
        
        # Verify allergen analysis
        assert allergen_result["allergen_free"] == False
        assert len(allergen_result["allergens"]) == 3
        allergen_names = [a["allergen"] for a in allergen_result["allergens"]]
        assert "wheat" in allergen_names
        assert "eggs" in allergen_names
        assert "milk" in allergen_names
        
        # Verify ingredient analysis
        assert len(main_ingredients) == 4
        assert "flour" in main_ingredients
        assert "chocolate_chips" in main_ingredients
        assert ingredient_result["cuisine_category"] == "American"
        
        # Verify dietary restrictions
        assert is_vegetarian == True  # No meat
        assert is_vegan == False      # Contains dairy
        assert is_gluten_free == False  # Contains wheat flour
        
        print(f"\n=== {menu_item} Analysis ===")
        print(f"Allergens: {len(allergen_result['allergens'])} found")
        print(f"Ingredients: {', '.join(main_ingredients)}")
        print(f"Vegetarian: {is_vegetarian}, Vegan: {is_vegan}, Gluten-Free: {is_gluten_free}")
    
    @pytest.mark.asyncio
    async def test_healthy_option_analysis(self, services):
        """Test analysis workflow for a healthy menu option"""
        allergen_service, ingredient_service = services
        
        # Analyze a garden salad
        menu_item = "Garden Salad"
        category = "salads"
        
        # Get comprehensive analysis
        allergen_result = await allergen_service.analyze_allergens(menu_item, category)
        ingredient_result = await ingredient_service.analyze_ingredients(menu_item, category)
        main_ingredients = await ingredient_service.get_main_ingredients(menu_item, category)
        
        # Check all dietary restrictions
        is_vegetarian = await ingredient_service.is_vegetarian(menu_item, category)
        is_vegan = await ingredient_service.is_vegan(menu_item, category)
        is_gluten_free = await ingredient_service.is_gluten_free(menu_item, category)
        
        # Verify this is a healthy, allergen-free option
        assert allergen_result["allergen_free"] == True
        assert len(allergen_result["allergens"]) == 0
        assert len(allergen_result["dietary_warnings"]) == 0
        
        # Verify healthy ingredients
        assert len(main_ingredients) == 4
        assert "lettuce" in main_ingredients
        assert "tomatoes" in main_ingredients
        assert ingredient_result["cuisine_category"] == "Mediterranean"
        
        # Should be suitable for all dietary restrictions
        assert is_vegetarian == True
        assert is_vegan == True
        assert is_gluten_free == True
        
        print(f"\n=== {menu_item} Analysis ===")
        print(f"Allergen-Free: {allergen_result['allergen_free']}")
        print(f"Ingredients: {', '.join(main_ingredients)}")
        print(f"Suitable for: Vegetarian, Vegan, Gluten-Free")
    
    @pytest.mark.asyncio
    async def test_complex_international_dish(self, services):
        """Test analysis workflow for a complex international dish"""
        allergen_service, ingredient_service = services
        
        # Analyze Pad Thai
        menu_item = "Pad Thai"
        category = "asian"
        
        # Get comprehensive analysis
        allergen_result = await allergen_service.analyze_allergens(menu_item, category)
        ingredient_result = await ingredient_service.analyze_ingredients(menu_item, category)
        main_ingredients = await ingredient_service.get_main_ingredients(menu_item, category)
        
        # Check dietary restrictions
        is_vegetarian = await ingredient_service.is_vegetarian(menu_item, category)
        is_vegan = await ingredient_service.is_vegan(menu_item, category)
        is_gluten_free = await ingredient_service.is_gluten_free(menu_item, category)
        
        # Verify complex allergen profile
        assert allergen_result["allergen_free"] == False
        assert len(allergen_result["allergens"]) == 3
        
        # Check for expected allergens
        allergen_names = [a["allergen"] for a in allergen_result["allergens"]]
        assert "peanuts" in allergen_names
        assert "fish_sauce" in allergen_names
        
        # Verify complex ingredient profile
        assert len(main_ingredients) == 4
        assert "rice_noodles" in main_ingredients
        assert "shrimp" in main_ingredients
        assert ingredient_result["cuisine_category"] == "Thai"
        
        # Verify dietary restrictions (complex dish)
        assert is_vegetarian == False  # Contains shrimp
        assert is_vegan == False       # Contains shrimp and fish sauce
        assert is_gluten_free == True  # Rice noodles are gluten-free
        
        print(f"\n=== {menu_item} Analysis ===")
        print(f"Allergens: {[a['allergen'] for a in allergen_result['allergens']]}")
        print(f"Ingredients: {', '.join(main_ingredients)}")
        print(f"Cuisine: {ingredient_result['cuisine_category']}")
        print(f"Gluten-Free: {is_gluten_free} (rice noodles)")
    
    @pytest.mark.asyncio
    async def test_error_handling_workflow(self, services):
        """Test error handling in real-world scenarios"""
        allergen_service, ingredient_service = services
        
        # Test with empty menu item
        with pytest.raises(ValueError):
            await allergen_service.analyze_allergens("")
        
        with pytest.raises(ValueError):
            await ingredient_service.analyze_ingredients("")
        
        # Test with unknown menu item (should return fallback data)
        unknown_item = "Mystery Dish"
        
        allergen_result = await allergen_service.analyze_allergens(unknown_item)
        ingredient_result = await ingredient_service.analyze_ingredients(unknown_item)
        main_ingredients = await ingredient_service.get_main_ingredients(unknown_item)
        
        # Should get fallback responses
        assert allergen_result["allergen_free"] == True  # Fallback safe response
        assert len(main_ingredients) == 0  # No ingredients found
        assert ingredient_result["confidence"] == 0.5  # Low confidence
        
        print(f"\n=== Error Handling Test ===")
        print(f"Unknown item handled gracefully with fallback data")
        print(f"Allergen-free (safe default): {allergen_result['allergen_free']}")
        print(f"Ingredients found: {len(main_ingredients)}")
    
    @pytest.mark.asyncio 
    async def test_menu_planning_scenario(self, services):
        """Test a realistic menu planning scenario"""
        allergen_service, ingredient_service = services
        
        # Simulate analyzing multiple menu items for a customer with restrictions
        menu_items = [
            ("Chocolate Chip Cookie", "desserts"),
            ("Garden Salad", "salads"), 
            ("Pad Thai", "asian")
        ]
        
        suitable_for_vegan = []
        suitable_for_gluten_free = []
        allergen_free_options = []
        
        print(f"\n=== Menu Planning Analysis ===")
        
        for item, category in menu_items:
            # Analyze each item
            allergen_result = await allergen_service.analyze_allergens(item, category)
            
            is_vegan = await ingredient_service.is_vegan(item, category)
            is_gluten_free = await ingredient_service.is_gluten_free(item, category)
            
            # Categorize options
            if is_vegan:
                suitable_for_vegan.append(item)
            if is_gluten_free:
                suitable_for_gluten_free.append(item)
            if allergen_result["allergen_free"]:
                allergen_free_options.append(item)
            
            print(f"{item}: Vegan={is_vegan}, GF={is_gluten_free}, Allergen-Free={allergen_result['allergen_free']}")
        
        # Verify menu planning results
        assert "Garden Salad" in suitable_for_vegan
        assert "Garden Salad" in suitable_for_gluten_free
        assert "Garden Salad" in allergen_free_options
        assert "Pad Thai" in suitable_for_gluten_free
        
        print(f"Vegan options: {suitable_for_vegan}")
        print(f"Gluten-free options: {suitable_for_gluten_free}")
        print(f"Allergen-free options: {allergen_free_options}") 