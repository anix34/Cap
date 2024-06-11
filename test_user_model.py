"""User model tests"""

import os, requests
from unittest import TestCase
from models import Bookmark, db, Language, User, Glass, Category, Ingredient, Drink

os.environ["DATABASE_URL"] = "postgresql:///mixology-test"
from app import app

app.config["SQLALCHEMY_ECHO"] = False

db.drop_all()
db.create_all()

english = Language(code="EN", name="English")
db.session.add(english)
db.session.commit()

class UserModelTestCase(TestCase):
    """Test cases for User model class"""

    def setUp(self) -> None:
        """Clear users table, and create test user"""

        db.session.commit()

        self.testuser = User.register("test", "test123", 1)
    
    def tearDown(self) -> None:
        """Empty users table"""
        
        User.query.delete()

    def test_user_registration(self):
        """Test User class method "register"."""

        self.assertEqual(self.testuser.username, "test")
        self.assertEqual(self.testuser.language_pref.name, "English")
        self.assertEqual(len(User.query.all()), 1)
    
    def test_user_authentication(self):
        """Test User class method authenticate"""

        self.assertTrue(User.authenticate("test", "test123"))
        self.assertFalse(User.authenticate("test", "123"))
        self.assertFalse(User.authenticate("not_user", "123"))
    
    def test_check_username(self):
        """Tests User class method check_username"""

        self.assertTrue(User.check_username("test"))
        self.assertFalse(User.check_username("123"))
    
    def test_serialize_user(self):
        """Tests User instance serialize method"""

        self.assertDictEqual(self.testuser.serialize(), {
            "id": self.testuser.id,
            "username": self.testuser.username,
            "language_pref": self.testuser.language_pref.code
        })
    
    def test_has_bookmark(self):
        """Test User method has_bookmark instance method"""

        self.assertFalse(self.testuser.has_bookmark(1))

        json_data = requests.get(f"https://www.thecocktaildb.com/api/json/v1/1/lookup.php?i=11007").json()
        drink_data = json_data["drinks"][0]

        ingr_data = requests.get("https://www.thecocktaildb.com/api/json/v1/1/list.php?i=list").json()
        ingredients = [Ingredient(name=ingr["strIngredient1"].lower()) for ingr in ingr_data["drinks"]]

        languages = [
            Language(code="DE", name="German"),
            Language(code="ES", name="Spanish"),
            Language(code="FR", name="French"),
            Language(code="IT", name="Italian"),
            Language(code="ZH-HANS", name="Mandarin Chinese, Simplified"),
            Language(code="ZH-HANT", name="Mandarin Chinese, Traditional")
        ]
        glass = Glass(name=drink_data["strGlass"].lower())
        category = Category(name=drink_data["strCategory"].lower())

        db.session.add_all([*ingredients, glass, *languages, category])
        db.session.commit()

        [drink, instructions, drink_ingredients] = Drink.parse_drink_data(drink_data)

        db.session.add(drink)
        db.session.commit()

        db.session.add_all([*instructions, *drink_ingredients])
        db.session.commit()

        testbookmark = Bookmark(user_id=self.testuser.id, drink_id=drink.id)
        db.session.add(testbookmark)
        db.session.commit()

        self.assertTrue(self.testuser.has_bookmark(drink.id))