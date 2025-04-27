import unittest
from app import create_app, db
from app.models.models import User, Crossing, Vote

class VotingTestCase(unittest.TestCase):
    def setUp(self):
        # Set up the test app and database
        self.app = create_app('testing')  # Ensure 'testing' config uses a test database
        self.client = self.app.test_client()
        with self.app.app_context():
            db.create_all()
            # Add test data
            user = User(id='test-user-uuid')
            crossing = Crossing(id='test-crossing-id', city='Test City', version=1)
            db.session.add(user)
            db.session.add(crossing)
            db.session.commit()

    def tearDown(self):
        # Clean up the database
        with self.app.app_context():
            db.session.remove()
            db.drop_all()

    def test_vote(self):
        # Test voting
        response = self.client.post('/vote', json={
            'userUuid': 'test-user-uuid',
            'crossingNodeId': 'test-crossing-id',
            'vote': 1,  # OK
            'city_id': 1,  # Test city ID
            'version_id': 1  # Test version ID
        })
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertEqual(data['status'], 'VOTE_RECORDED')
        self.assertEqual(data['new_result'], 1)  # OK

        # Verify database changes
        with self.app.app_context():
            crossing = Crossing.query.filter_by(id='test-crossing-id').first()
            self.assertEqual(crossing.votes_ok, 1)
            self.assertEqual(crossing.votes_total, 1)

if __name__ == '__main__':
    unittest.main()