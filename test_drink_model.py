"""Drink model tests"""

import os, requests
from unittest import TestCase
from models import Category, Glass, db, Drink, Ingredient, Language

os.environ["DATABASE_URL"] = "postgresql:///mixology-test"
from app import app

app.config["SQLALCHEMY_ECHO"] = False

db.drop_all()
db.create_all()

json_data = requests.get(f"https://www.thecocktaildb.com/api/json/v1/1/lookup.php?i=11007").json()
drink_data = json_data["drinks"][0]

ingr_data = requests.get("https://www.thecocktaildb.com/api/json/v1/1/list.php?i=list").json()
ingredients = [Ingredient(name=ingr["strIngredient1"].lower()) for ingr in ingr_data["drinks"]]

languages = [
    Language(code="EN", name="English"),
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

class DrinkModelTestCase(TestCase):
    """Test cases for Drink model"""

    def setUp(self):
        """Set up Drink model"""

        [drink, instructions, drink_ingredients] = Drink.parse_drink_data(drink_data)

        db.session.add(drink)
        db.session.commit()

        db.session.add_all(instructions)
        db.session.add_all(drink_ingredients)

        db.session.commit()

        self.drink = Drink.query.get(11007)
    
    def tearDown(self) -> None:
        """Delete all drinks from table"""

        Drink.query.delete()

    def test_parse_drink_data(self):
        """Tests that the parse_drink_data class method from Drink model works"""

        self.assertIsInstance(self.drink, Drink)
        self.assertNotEqual(len(self.drink.instructions), 0)
        self.assertNotEqual(len(self.drink.ingredients), 0)
        self.assertIsInstance(self.drink.glass, Glass)
    
    def test_repr(self):
        """Test for the __repr__ method"""

        self.assertEqual(self.drink.__repr__(), f"<Drink {self.drink.name}>")

    def test_serialize(self):
        """Test for serialize method.
        Should return dict object of Drink data."""

        self.assertDictEqual(self.drink.serialize(), {
            "id": self.drink.id,
            "name": self.drink.name.title(),
            "image_url": self.drink.image_url,
            "image_attribution": self.drink.image_attribution,
            "alcoholic": self.drink.alcoholic,
            "optional_alc": self.drink.optional_alc,
            "category": self.drink.category.name.title(),
            "category_id": self.drink.category_id
        })

    def test_get_video_url_id(self):
        """Test for get_video_url_id method.
        Should return video ID from YouTube URL"""

        self.drink.video_url = "https://www.youtube.com/watch?v=zzAwspdDFO4"

        self.assertEqual(self.drink.get_video_url_id(), "zzAwspdDFO4")

        