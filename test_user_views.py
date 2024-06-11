import os, requests
from unittest import TestCase
from models import db, User, Language, Bookmark, Ingredient, Glass, Category, Drink

os.environ["DATABASE_URL"] = "postgresql:///mixology-test"

from app import app, USER_KEY

app.config["SQLALCHEMY_DATABASE_URI"] = "postgresql:///mixology-test"
app.config["SQLALCHEMY_ECHO"] = False
app.config["WTF_CSRF_ENABLED"] = False

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

[drink, instructions, drink_ingredients] = Drink.parse_drink_data(drink_data)

db.session.add(drink)
db.session.commit()

db.session.add_all([*instructions, *drink_ingredients])
db.session.commit()

drink = Drink.query.one()

class UserViewsTestCase(TestCase):
    """Test cases for user views"""

    def setUp(self):
        """Create test user"""

        User.register("test", "test123", 1)
        
        self.testuser = User.query.filter_by(username="test").one()
        self.testdrink = Drink.query.one()

    def tearDown(self):
        """Delete user table"""

        User.query.delete()

    def test_home_page_logged_in(self):
        """Test home page when user is logged in"""

        with app.test_client() as c:
            with c.session_transaction() as sess:
                sess[USER_KEY] = self.testuser.id
            
            resp = c.get("/")
            html = resp.get_data(as_text=True)

            self.assertEqual(resp.status_code, 200)
            self.assertIn("Profile", html)
            self.assertIn("Log Out", html)
            self.assertNotIn("Log In", html)
            self.assertNotIn("Register", html)
    
    def test_home_page_logged_out(self):
        """Test home page when logged out."""

        with app.test_client() as c:

            resp = c.get("/")
            html = resp.get_data(as_text=True)

            self.assertEqual(resp.status_code, 200)
            self.assertNotIn("Profile", html)
            self.assertNotIn("Log Out", html)
            self.assertIn("Log In", html)
            self.assertIn("Register", html)

    def test_user_registration_view(self):
        """Test user registration page"""
        
        with app.test_client() as c:
            
            resp = c.get("/register")
            html = resp.get_data(as_text=True)

            self.assertEqual(resp.status_code, 200)
            self.assertIn("Register", html)
    
    def test_user_registration_view_logged_in(self):
        """Test user registration page while logged in"""

        with app.test_client() as c:
            with c.session_transaction() as sess:
                sess[USER_KEY] = self.testuser.id
            
            resp = c.get("/register")
            
            self.assertEqual(resp.status_code, 302)
    
    def test_user_login_view(self):
        """Test user login page"""

        with app.test_client() as c:

            resp = c.get("/login")
            html = resp.get_data(as_text=True)

            self.assertEqual(resp.status_code, 200)
            self.assertIn("Login", html)
    
    def test_user_login_view_logged_in(self):
        """Test user login page while already logged in"""

        with app.test_client() as c:
            with c.session_transaction() as sess:
                sess[USER_KEY] = self.testuser.id
            
            resp = c.get("/login")

            self.assertEqual(resp.status_code, 302)

    def test_user_profile_logged_in(self):
        """Test user profile page with user logged in"""

        with app.test_client() as c:
            with c.session_transaction() as sess:
                sess[USER_KEY] = self.testuser.id

            resp = c.get("/profile")
            html = resp.get_data(as_text=True)

            self.assertEqual(resp.status_code, 200)
            self.assertIn("Profile", html)
            self.assertIn(self.testuser.username, html)
            self.assertIn("English", html)
    
    def test_user_profile_logged_out(self):
        """Test user profile page while logged out"""

        with app.test_client() as c:

            resp = c.get("/profile")

            self.assertEqual(resp.status_code, 302)
    
    def test_user_profile_with_bookmark(self):
        """Test user profile when user has a bookmarked recipe."""

        with app.test_client() as c:
            with c.session_transaction() as sess:
                sess[USER_KEY] = self.testuser.id

            testbookmark = Bookmark(user_id=self.testuser.id, drink_id=drink.id)
            db.session.add(testbookmark)
            db.session.commit()
                
            resp = c.get("/profile")
            html = resp.get_data(as_text=True)

            self.assertEqual(resp.status_code, 200)
            self.assertEqual(len(Bookmark.query.all()), 1)
            self.assertIn(Drink.query.one().name.title(), html)

    def test_user_delete_logged_in(self):
        """Test user delete route when logged in as user that wants to be deleted."""

        with app.test_client() as c:
            with c.session_transaction() as sess:
                sess[USER_KEY] = self.testuser.id
            
            resp = c.delete("/user", json={})

            self.assertEqual(resp.status_code, 200)
            self.assertEqual(len(User.query.filter_by(username=self.testuser.username).all()), 0)
            self.assertDictEqual(resp.json, {"STATUS": "OK"})

            resp = c.get("/")
            html = resp.get_data(as_text=True)
            self.assertEqual(resp.status_code, 200)
            self.assertNotIn("Profile", html)

    def test_user_delete_logged_out(self):
        """Test user delete route when logged out."""

        with app.test_client() as c:
            
            resp = c.delete(f"/user", json={})

            self.assertEqual(resp.status_code, 200)
            self.assertEqual(len(User.query.filter_by(username=self.testuser.username).all()), 1)
            self.assertDictEqual(resp.json, {"STATUS": "FAIL"})

            resp = c.get("/")
            html = resp.get_data(as_text=True)

            self.assertEqual(resp.status_code, 200)
            self.assertNotIn("Profile", html)
            self.assertIn("Log In", html)
            self.assertIn("You must be logged in to do this.", html)
    
    def test_add_and_delete_bookmark_route(self):
        """Test deletion of bookmarked recipe"""

        with app.test_client() as c:
            with c.session_transaction() as sess:
                sess[USER_KEY] = self.testuser.id

            testbookmark = Bookmark(user_id=self.testuser.id, drink_id=drink.id)
            db.session.add(testbookmark)
            db.session.commit()

            resp = c.delete("/bookmark", json={"id": drink.id})

            self.assertEqual(resp.status_code, 200)
            self.assertDictEqual(resp.json, {
                "STATUS": "OK",
                "CLASS": "bi bi-bookmark fs-2"
            })
            self.assertEqual(len(Bookmark.query.all()), 0)

            resp = c.get("/profile")
            html = resp.get_data(as_text=True)

            self.assertEqual(resp.status_code, 200)
            self.assertNotIn(drink.name.title(), html)

            resp = c.post("/bookmark", json={"id": drink.id})

            self.assertEqual(resp.status_code, 200)
            self.assertDictEqual(resp.json, {
                "STATUS": "OK",
                "CLASS": "bi bi-bookmark-fill fs-2"
            })
            self.assertEqual(len(Bookmark.query.all()), 1)

            resp = c.get("/profile")
            html = resp.get_data(as_text=True)
            
            self.assertEqual(resp.status_code, 200)
            self.assertIn(drink.name.title(), html)