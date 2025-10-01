import unittest
import json
import uuid
from app import create_app, db
from app.models.models import User, City, CityVersion, Crossing, Vote

class CityCompletionTestCase(unittest.TestCase):
    def setUp(self):
        # Set up the test app and database
        self.app = create_app('testing')
        self.client = self.app.test_client()
        
        with self.app.app_context():
            db.create_all()
            
            # Generate a unique suffix for test data
            self.unique_suffix = str(uuid.uuid4())[:8]
            
            # Create test user with unique ID
            self.user = User(id=f'test-user-{self.unique_suffix}')
            db.session.add(self.user)
            
            # Create test city with unique name
            self.city = City(
                name=f'Test City {self.unique_suffix}',
                description='Test city description',
                information_text='Test info',
                is_active=True
            )
            db.session.add(self.city)
            db.session.flush()
            
            # Create test city version
            self.version = CityVersion(
                city_id=self.city.id,
                version_number=1,
                description='Test version',
                is_active=True
            )
            db.session.add(self.version)
            db.session.flush()
            
            # Create test crossings with varying vote counts
            for i in range(10):
                crossing = Crossing(
                    id=f'node/{self.unique_suffix}/{i}',
                    city_id=self.city.id,
                    version_id=self.version.id,
                    lat=1.0 + (i * 0.001),
                    lon=1.0 + (i * 0.001),
                    neighbourhood='Test Neighbourhood',
                    street='Test Street'
                )
                db.session.add(crossing)
            
            db.session.commit()
            
            # Add votes to some crossings
            # 3 crossings will have enough votes (5+)
            # 7 crossings will have fewer votes
            crossings = Crossing.query.filter_by(city_id=self.city.id).all()
            
            # Add 6 votes to first crossing
            self._add_votes(crossings[0].id, 6, vote_type=1)  # OK votes
            
            # Add 5 votes to second crossing
            self._add_votes(crossings[1].id, 5, vote_type=2)  # Too close votes
            
            # Add 7 votes to third crossing
            self._add_votes(crossings[2].id, 7, vote_type=0)  # Not sure votes
            
            # Add 1-3 votes to the rest
            for i in range(3, 10):
                self._add_votes(crossings[i].id, i % 3 + 1, vote_type=i % 3)
            
            db.session.commit()
            
            # Store the city ID for later use
            self.city_id = self.city.id
            self.version_id = self.version.id

    def _add_votes(self, crossing_id, count, vote_type=1):
        """Helper to add votes to a crossing"""
        for i in range(count):
            # Create unique user IDs with additional uniqueness from the test run
            user_id = f'user-{self.unique_suffix}-{crossing_id}-{i}'
            user = User(id=user_id)
            db.session.add(user)
            
            vote = Vote(
                user_id=user_id,
                crossing_id=crossing_id,
                vote=vote_type  # 0: Not sure, 1: OK, 2: Too close
            )
            db.session.add(vote)
            
            # No per-crossing counters anymore; aggregation is live from Vote rows

    def tearDown(self):
        # Clean up the database
        with self.app.app_context():
            db.session.remove()
            db.drop_all()

    def test_cities_endpoint_completion_data(self):
        """Test that the cities endpoint includes completion data"""
        with self.app.app_context():
            response = self.client.get('/api/cities')
            self.assertEqual(response.status_code, 200)
            
            data = json.loads(response.data)
            self.assertGreater(len(data), 0)
            
            # Find our test city in the response
            city = None
            for c in data:
                if c['name'] == f'Test City {self.unique_suffix}':
                    city = c
                    break
                
            self.assertIsNotNone(city, "Test city not found in response")
            self.assertIn('completion', city)
            
            completion = city['completion']
            self.assertIn('total_votes', completion)
            self.assertIn('votes_limit', completion)
            self.assertIn('total_crossings', completion)
            self.assertIn('crossings_with_enough_votes', completion)
            self.assertIn('completion_percentage', completion)
            
            # Verify the values
            self.assertEqual(completion['total_crossings'], 10)
            self.assertEqual(completion['votes_limit'], 5)
            
            # Expected values based on our setup
            expected_total_votes = 6 + 5 + 7 + sum(i % 3 + 1 for i in range(3, 10))
            self.assertEqual(completion['total_votes'], expected_total_votes)
            
            # Expected 3 crossings with enough votes (5+)
            self.assertEqual(completion['crossings_with_enough_votes'], 3)
            
            # Expected completion percentage: 3/10 * 100 = 30%
            self.assertEqual(completion['completion_percentage'], 30.0)

    def test_city_completion_endpoint(self):
        """Test the specific city completion endpoint"""
        with self.app.app_context():
            # Use the stored city_id instead of the city object
            response = self.client.get(f'/api/cities/{self.city_id}/completion')
            self.assertEqual(response.status_code, 200)
            
            data = json.loads(response.data)
            
            # Verify all required fields are present
            required_fields = ['city_id', 'version_id', 'total_crossings', 'total_votes',
                             'votes_limit', 'crossings_with_enough_votes', 'completion_percentage']
            
            for field in required_fields:
                self.assertIn(field, data)
            
            # Verify the values
            self.assertEqual(data['city_id'], self.city_id)
            self.assertEqual(data['version_id'], self.version_id)
            self.assertEqual(data['total_crossings'], 10)
            self.assertEqual(data['votes_limit'], 5)
            
            # Expected values based on our setup
            expected_total_votes = 6 + 5 + 7 + sum(i % 3 + 1 for i in range(3, 10))
            self.assertEqual(data['total_votes'], expected_total_votes)
            
            # Expected 3 crossings with enough votes (5+)
            self.assertEqual(data['crossings_with_enough_votes'], 3)
            
            # Expected completion percentage: 3/10 * 100 = 30%
            self.assertEqual(data['completion_percentage'], 30.0)

if __name__ == '__main__':
    unittest.main() 