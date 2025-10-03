import logging
from middleware.auth import clerk_required
from flask_restful import Resource
from flask import request
from models import db, User, Match
from models.messages import Message
from utils.response import success_response, error_response
from datetime import datetime

logger = logging.getLogger(__name__)


class MessageResource(Resource):
    """Resource for sending and retrieving messages"""
    
    @clerk_required
    def post(self):
        """
        Send a message and persist to database.
        Syncs with Firebase for real-time delivery.
        """
        try:
            user_id = request.user.get('sub')
            data = request.get_json()
            
            if not data:
                return error_response("No data provided", 400)
            
            match_id = data.get('match_id')
            receiver_id = data.get('receiver_id')
            message_text = data.get('message_text') or data.get('text')
            
            if not all([match_id, receiver_id, message_text]):
                return error_response("match_id, receiver_id, and message_text are required", 400)
            
            # Verify match exists and user is part of it
            match = Match.query.get(match_id)
            if not match:
                return error_response("Match not found", 404)
            
            # Verify user is part of this match
            if match.user_id_1 != user_id and match.user_id_2 != user_id:
                return error_response("Unauthorized: You are not part of this match", 403)
            
            # Verify match is active
            if match.match_status != 'matched':
                return error_response("Cannot send messages to an inactive match", 400)
            
            # Verify receiver is the other person in the match
            expected_receiver = match.user_id_2 if match.user_id_1 == user_id else match.user_id_1
            if receiver_id != expected_receiver:
                return error_response("Invalid receiver for this match", 400)
            
            # Create message in database
            message = Message(
                match_id=match_id,
                sender_id=user_id,
                message_text=message_text,
                is_read=False
            )
            
            db.session.add(message)
            db.session.commit()
            
            logger.info(f"Message sent: {user_id} → {receiver_id} in match {match_id}")
            
            # Return message data
            message_data = {
                'id': str(message.id),
                'match_id': str(message.match_id),
                'sender_id': message.sender_id,
                'receiver_id': receiver_id,
                'message_text': message.message_text,
                'is_read': message.is_read,
                'created_at': message.created_at.isoformat() if message.created_at else None
            }
            
            return success_response(
                message_data,
                "Message sent successfully"
            )
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error sending message: {str(e)}")
            return error_response("Failed to send message", 500)


class MatchMessagesResource(Resource):
    """Resource for getting messages in a specific match"""
    
    @clerk_required
    def get(self, match_id):
        """
        Get all messages for a specific match.
        Returns messages in chronological order.
        """
        try:
            user_id = request.user.get('sub')
            
            # Verify match exists and user is part of it
            match = Match.query.get(match_id)
            if not match:
                return error_response("Match not found", 404)
            
            # Verify user is part of this match
            if match.user_id_1 != user_id and match.user_id_2 != user_id:
                return error_response("Unauthorized: You are not part of this match", 403)
            
            # Get query parameters
            limit = request.args.get('limit', type=int, default=100)
            offset = request.args.get('offset', type=int, default=0)
            
            # Fetch messages
            messages_query = Message.query.filter_by(match_id=match_id)\
                .order_by(Message.created_at.asc())\
                .limit(limit)\
                .offset(offset)
            
            messages = messages_query.all()
            
            # Determine the other user in the match
            other_user_id = match.user_id_2 if match.user_id_1 == user_id else match.user_id_1
            
            # Format messages
            messages_data = []
            for msg in messages:
                messages_data.append({
                    'id': str(msg.id),
                    'match_id': str(msg.match_id),
                    'sender_id': msg.sender_id,
                    'receiver_id': other_user_id if msg.sender_id == user_id else user_id,
                    'message_text': msg.message_text,
                    'is_read': msg.is_read,
                    'created_at': msg.created_at.isoformat() if msg.created_at else None
                })
            
            # Mark unread messages as read
            unread_messages = Message.query.filter(
                Message.match_id == match_id,
                Message.sender_id != user_id,
                Message.is_read == False
            ).all()
            
            for msg in unread_messages:
                msg.is_read = True
            
            if unread_messages:
                db.session.commit()
                logger.info(f"Marked {len(unread_messages)} messages as read for user {user_id}")
            
            return success_response(
                {
                    'messages': messages_data,
                    'total': len(messages_data),
                    'has_more': len(messages) == limit
                },
                "Messages retrieved successfully"
            )
            
        except Exception as e:
            logger.error(f"Error fetching messages: {str(e)}")
            return error_response("Failed to fetch messages", 500)


class UnreadMessagesResource(Resource):
    """Resource for getting unread message count"""
    
    @clerk_required
    def get(self):
        """
        Get total unread message count for the current user.
        Optionally filter by match_id.
        """
        try:
            user_id = request.user.get('sub')
            match_id = request.args.get('match_id')
            
            # Build query for unread messages sent to this user
            query = Message.query.filter(
                Message.is_read == False
            )
            
            # Get all matches where user is involved to filter messages
            user_matches = Match.query.filter(
                db.or_(
                    Match.user_id_1 == user_id,
                    Match.user_id_2 == user_id
                )
            ).all()
            
            match_ids = [str(m.id) for m in user_matches]
            
            if match_id:
                # Filter by specific match
                if match_id not in match_ids:
                    return error_response("Match not found or unauthorized", 404)
                
                unread_count = query.filter(
                    Message.match_id == match_id,
                    Message.sender_id != user_id
                ).count()
                
                return success_response(
                    {
                        'match_id': match_id,
                        'unread_count': unread_count
                    },
                    "Unread count retrieved"
                )
            else:
                # Get unread count across all matches
                unread_count = query.filter(
                    Message.match_id.in_(match_ids),
                    Message.sender_id != user_id
                ).count()
                
                return success_response(
                    {
                        'total_unread': unread_count
                    },
                    "Total unread count retrieved"
                )
            
        except Exception as e:
            logger.error(f"Error fetching unread count: {str(e)}")
            return error_response("Failed to fetch unread count", 500)


class MarkMessagesReadResource(Resource):
    """Resource for marking messages as read"""
    
    @clerk_required
    def post(self, match_id):
        """Mark all messages in a match as read"""
        try:
            user_id = request.user.get('sub')
            
            # Verify match exists and user is part of it
            match = Match.query.get(match_id)
            if not match:
                return error_response("Match not found", 404)
            
            if match.user_id_1 != user_id and match.user_id_2 != user_id:
                return error_response("Unauthorized", 403)
            
            # Mark messages as read (only messages sent TO this user)
            updated = Message.query.filter(
                Message.match_id == match_id,
                Message.sender_id != user_id,
                Message.is_read == False
            ).update({'is_read': True})
            
            db.session.commit()
            
            logger.info(f"Marked {updated} messages as read for user {user_id} in match {match_id}")
            
            return success_response(
                {'marked_read': updated},
                f"Marked {updated} messages as read"
            )
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error marking messages as read: {str(e)}")
            return error_response("Failed to mark messages as read", 500)
