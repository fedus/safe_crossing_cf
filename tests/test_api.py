import unittest
from app import create_app, db
from app.models.models import User, City, CityVersion, Crossing, Vote
import json
import uuid

class TestAPI(unittest.TestCase):
    def setUp(self):
        self.app = create_app('testing')
        self.app_context = self.app.app_context()
        self.app_context.push()
        db.create_all()
        self.client = self.app.test_client()
        
        # Create test data
        self.city = City(name='Test City', description='Test Description')
        db.session.add(self.city)
        db.session.commit()
        
        self.version = CityVersion(
            city_id=self.city.id,
            version_number=1,
            is_active=True
        )
        db.session.add(self.version)
        db.session.commit()
        
        self.crossing = Crossing(
            id='node/123456789',
            city_id=self.city.id,
            version_id=self.version.id,
            lat=49.6116,
            lon=6.1319,
            neighbourhood='Test Neighbourhood',
            street='Test Street'
        )
        db.session.add(self.crossing)
        db.session.commit()
        
        self.user_uuid = str(uuid.uuid4())
        self.user = User(id=self.user_uuid, initialized=True)
        db.session.add(self.user)
        db.session.commit()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.app_context.pop()

    def test_initialize_user(self):
        # Test new user initialization
        response = self.client.post('/api/initialize-user', 
            json={'userUuid': str(uuid.uuid4())})
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(data['status'], 'USER_INITIALIZED')
        
        # Test existing user initialization
        response = self.client.post('/api/initialize-user', 
            json={'userUuid': self.user_uuid})
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(data['status'], 'USER_ALREADY_INITIALIZED')

    def test_get_cities(self):
        response = self.client.get('/api/cities')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]['name'], 'Test City')
        self.assertIn('currentVersion', data[0])
        self.assertIn('completion', data[0])

    def test_get_city_version_crossings(self):
        response = self.client.get(f'/api/cities/{self.city.id}/versions/{self.version.id}/crossings')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]['id'], 'node/123456789')
        self.assertEqual(data[0]['neighbourhood'], 'Test Neighbourhood')

    def test_get_unvoted_crossings(self):
        # First get unvoted crossings
        response = self.client.get(
            f'/api/cities/{self.city.id}/versions/{self.version.id}/unvoted?userUuid={self.user_uuid}')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]['id'], 'node/123456789')
        
        # Add a vote
        vote = Vote(
            user_id=self.user_uuid,
            crossing_id='node/123456789',
            vote=1
        )
        db.session.add(vote)
        db.session.commit()
        
        # Now get unvoted crossings again
        response = self.client.get(
            f'/api/cities/{self.city.id}/versions/{self.version.id}/unvoted?userUuid={self.user_uuid}')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(len(data), 0)

    def test_vote(self):
        # Test new vote
        response = self.client.post('/api/vote', json={
            'userUuid': self.user_uuid,
            'crossingNodeId': 'node/123456789',
            'vote': 1,
            'city_id': self.city.id,
            'version_id': self.version.id
        })
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(data['status'], 'VOTE_RECORDED')
        
        # Verify vote was recorded by checking Vote table
        votes = Vote.query.filter_by(crossing_id='node/123456789').all()
        self.assertEqual(len(votes), 1)
        self.assertEqual(votes[0].vote, 1)  # 1 = okay
        
        # Test adding another vote (not_okay)
        response = self.client.post('/api/vote', json={
            'userUuid': self.user_uuid,
            'crossingNodeId': 'node/123456789',
            'vote': -1,  # -1 = not_okay
            'city_id': self.city.id,
            'version_id': self.version.id
        })
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(data['status'], 'VOTE_RECORDED')
        
        # Verify new vote was added (no update, just new vote)
        votes = Vote.query.filter_by(crossing_id='node/123456789').all()
        self.assertEqual(len(votes), 2)  # Two separate votes now
        vote_values = [v.vote for v in votes]
        self.assertIn(1, vote_values)  # Original okay vote
        self.assertIn(-1, vote_values)  # New not_okay vote
        
        # Test legacy value 2 (should be mapped to -1)
        response = self.client.post('/api/vote', json={
            'userUuid': self.user_uuid,
            'crossingNodeId': 'node/123456789',
            'vote': 2,  # Legacy value for not_okay
            'city_id': self.city.id,
            'version_id': self.version.id
        })
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(data['status'], 'VOTE_RECORDED')
        
        # Verify legacy vote was mapped correctly
        votes = Vote.query.filter_by(crossing_id='node/123456789').all()
        self.assertEqual(len(votes), 3)  # Three separate votes now
        vote_values = [v.vote for v in votes]
        self.assertIn(1, vote_values)  # Original okay vote
        self.assertEqual(vote_values.count(-1), 2)  # Two not_okay votes (one -1, one mapped from 2)

    def test_get_user_votes(self):
        # Add a vote
        vote = Vote(
            user_id=self.user_uuid,
            crossing_id='node/123456789',
            vote=1
        )
        db.session.add(vote)
        db.session.commit()
        
        # Get user's votes
        response = self.client.get(f'/api/votes/{self.user_uuid}')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]['crossing_id'], 'node/123456789')
        self.assertEqual(data[0]['vote'], 1)

if __name__ == '__main__':
    unittest.main() 