from flask import Flask
from flask_cors import CORS
from flask_restful import Api, Resource
from flask_migrate import Migrate
from models import db
from dotenv import load_dotenv
import os
import logging

load_dotenv()

app = Flask(__name__)

app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

CORS(app)

migrate = Migrate(app, db)
db.init_app(app)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s %(name)s %(message)s'
)

api = Api(app)

class HealthCheck(Resource):
    def get(self):
        return {"status": "ok"}


api.add_resource(HealthCheck, '/health')

from resources.webhooks import ClerkWebhook
from resources.users import CurrentUserResource, UserProfileResource
from resources.match import (
    DiscoverMatchesResource, 
    MatchActionResource, 
    UserMatchesResource,
    MatchedUsersResource,
    MatchDetailResource
)
from resources.messages import (
    MessageResource,
    MatchMessagesResource,
    UnreadMessagesResource,
    MarkMessagesReadResource
)
from resources.payments import (
    InitializePaymentResource,
    VerifyPaymentResource,
    PaystackWebhookResource,
    SubscriptionStatusResource,
    PaymentPlansResource
)

api.add_resource(ClerkWebhook, '/webhooks/clerk')
api.add_resource(CurrentUserResource, '/users/me')
api.add_resource(UserProfileResource, '/users/<string:user_id>')

# Payment routes
api.add_resource(PaymentPlansResource, '/payments/plans')
api.add_resource(InitializePaymentResource, '/payments/initialize')
api.add_resource(VerifyPaymentResource, '/payments/verify/<string:reference>')
api.add_resource(PaystackWebhookResource, '/webhooks/paystack')
api.add_resource(SubscriptionStatusResource, '/payments/subscription/status')

# Matching routes (Premium required)
api.add_resource(DiscoverMatchesResource, '/matches/discover')
api.add_resource(MatchActionResource, '/matches/action')
api.add_resource(UserMatchesResource, '/matches')
api.add_resource(MatchDetailResource, '/matches/<string:match_id>')

# Message routes (Premium required)
api.add_resource(MessageResource, '/messages')
api.add_resource(MatchMessagesResource, '/messages/match/<string:match_id>')
api.add_resource(UnreadMessagesResource, '/messages/unread')
api.add_resource(MarkMessagesReadResource, '/messages/match/<string:match_id>/read')

if __name__ == '__main__':
    app.run(debug=True)
